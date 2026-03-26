import os
from dotenv import load_dotenv
from tqdm import tqdm
from langchain_community.document_loaders import YoutubeLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

# Configuration
VIDEO_URLS = [
    "https://www.youtube.com/watch?v=example1",
    "https://www.youtube.com/watch?v=example2",
    # Add your 100 URLs here
]

DB_DIR = "chroma_db"

def extract_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "be/" in url:
        return url.split("be/")[1].split("?")[0]
    return "unknown"

def ingest_videos(urls):
    embeddings = OpenAIEmbeddings()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    all_chunks = []

    print(f"--- Starting ingestion of {len(urls)} videos ---")
    
    for url in tqdm(urls, desc="Processing Videos", unit="video"):
        try:
            # 1. Fetch Transcripts & Metadata
            # add_video_info=True grabs Title, Author, etc.
            loader = YoutubeLoader.from_url(
                url, 
                add_video_info=True,
                language=["en", "hi"] # Supports English and Hindi transcripts
            )
            video_data = loader.load()
            
            if not video_data:
                continue

            # 2. Chunk the text
            chunks = text_splitter.split_documents(video_data)
            
            # 3. Metadata Enrichment
            video_id = extract_video_id(url)
            for chunk in chunks:
                chunk.metadata["video_id"] = video_id
                # Note: YoutubeLoader provides the full transcript as one block.
                # Standard loader metadata already includes 'title' and 'source' (URL).
            
            all_chunks.extend(chunks)

        except Exception as e:
            print(f"\nSkipping {url} due to error: {e}")
            continue

    # 4. Initialize and Save to Vector Store
    if all_chunks:
        print(f"\n--- Saving {len(all_chunks)} chunks to {DB_DIR} ---")
        vector_db = Chroma.from_documents(
            documents=all_chunks,
            embedding=embeddings,
            persist_directory=DB_DIR
        )
        print("--- Ingestion Complete ---")
    else:
        print("No data was processed.")

if __name__ == "__main__":
    ingest_videos(VIDEO_URLS)