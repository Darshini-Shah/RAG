import os
import re
import pickle
from typing import List
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from rank_bm25 import BM25Okapi
from playlist import get_video_urls

from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
from langchain_core.embeddings import Embeddings
import time
import google.api_core.exceptions

class GeminiEmbeddings(Embeddings):
    def __init__(self, model_name: str = "models/text-embedding-004"):
        self.model_names = ["models/text-embedding-004", "models/embedding-001", "models/gemini-embedding-2-preview"]
        self.actual_model = None
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

    def _get_model(self):
        if self.actual_model:
            return self.actual_model
        for m in self.model_names:
            try:
                # Test the model
                genai.embed_content(model=m, content="test", task_type="retrieval_query")
                self.actual_model = m
                print(f"Successfully connected to embedding model: {m}")
                return m
            except Exception as e:
                print(f"Model {m} not available: {e}")
                continue
        raise Exception("No supported Gemini embedding models found in your region/API version.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        # Conservative batch size for free tier
        batch_size = 50 
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            retries = 3
            while retries > 0:
                try:
                    response = genai.embed_content(
                        model=model,
                        content=batch,
                        task_type="retrieval_document"
                    )
                    all_embeddings.extend(response['embedding'])
                    # Sleep to respect 100 RPM limit
                    time.sleep(5) 
                    break 
                except Exception as e:
                    if "429" in str(e) or "Quota" in str(e):
                        print(f"Rate limit hit, waiting 60s... (Batch {i//batch_size})")
                        time.sleep(60)
                        retries -= 1
                    else:
                        print(f"Error in embedding batch {i//batch_size}: {e}")
                        raise e
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        model = self._get_model()
        response = genai.embed_content(
            model=model,
            content=text,
            task_type="retrieval_query"
        )
        return response['embedding']

def extract_video_id(url: str) -> str:
    """Extracts the video ID from a YouTube URL."""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if match:
        return match.group(1)
    return url

def get_transcript_chunks(video_id: str, chunk_size: int = 1000, overlap: int = 200) -> List[Document]:
    """Fetches transcript and chunks it up by character count, preserving start_time."""
    transcript = None
    try:
        # Try standard way (static method)
        if hasattr(YouTubeTranscriptApi, 'get_transcript'):
            # Try English first, then Hindi as fallback
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'])
            except:
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
        elif hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Try to find English or Hindi
            try:
                transcript = transcript_list.find_transcript(['en', 'hi']).fetch()
            except:
                transcript = next(iter(transcript_list)).fetch()
        elif hasattr(YouTubeTranscriptApi, 'fetch'):
            # It seems 'fetch' is an instance method in this version
            transcript = YouTubeTranscriptApi().fetch(video_id)
        else:
            # Fallback to direct call in case hasattr is being weird
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'])
            except:
                transcript = YouTubeTranscriptApi().fetch(video_id)
    except Exception as e:
        print(f"Failed to get transcript for {video_id}: {e}")
        return []

    if not transcript:
        return []

    def get_val(obj, key):
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    documents = []
    i = 0
    while i < len(transcript):
        chunk_text = ""
        start_time = get_val(transcript[i], 'start')
        j = i
        
        while j < len(transcript) and len(chunk_text) < chunk_size:
            text = get_val(transcript[j], 'text')
            chunk_text += (text if text else "") + " "
            j += 1
            
        doc = Document(
            page_content=chunk_text.strip(),
            metadata={"video_id": video_id, "start_time": start_time}
        )
        documents.append(doc)
        
        if j == len(transcript) and len(chunk_text) <= chunk_size:
            break

        # Calculate overlap step-back
        overlap_text = ""
        back_index = j - 1
        while back_index > i and len(overlap_text) < overlap:
            text = get_val(transcript[back_index], 'text')
            overlap_text = (text if text else "") + " " + overlap_text
            back_index -= 1
        
        next_i = back_index + 1
        if next_i <= i:
            next_i = i + 1
            
        i = next_i
        
    return documents

def process_playlist(playlist_url: str):
    """Processes an entire playlist, storing chunks to ChromaDB and BM25 index."""
    print(f"Extracting video URLs from {playlist_url}...")
    urls = get_video_urls(playlist_url)
    print(f"Found {len(urls)} videos.")
    
    all_documents = []
    
    for url in urls:
        video_id = extract_video_id(url)
        print(f"Fetching transcript for video ID: {video_id}...")
        docs = get_transcript_chunks(video_id, chunk_size=1000, overlap=200)
        all_documents.extend(docs)
        
    if not all_documents:
        print("No transcripts could be extracted.")
        return 0
        
    print(f"Extracted {len(all_documents)} total chunks.")
    
    try:
        print("Embedding into ChromaDB...")
        embeddings = GeminiEmbeddings()
        vectorstore = Chroma.from_documents(
            documents=all_documents,
            embedding=embeddings,
            persist_directory="./chroma_db" # stores in backend/chroma_db/
        )
    except Exception as e:
        print(f"Error during embedding/ChromaDB: {e}")
        raise e
    
    try:
        print("Building BM25 Index...")
        tokenized_corpus = [doc.page_content.lower().split() for doc in all_documents]
        bm25 = BM25Okapi(tokenized_corpus)
        with open("bm25_index.pkl", "wb") as f:
            pickle.dump({"bm25": bm25, "docs": all_documents}, f)
    except Exception as e:
        print(f"Error during BM25 generation: {e}")
        raise e
        
    print("Ingestion complete!")
    return len(all_documents)

if __name__ == "__main__":
    pass
