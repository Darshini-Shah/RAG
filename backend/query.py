import os
import pickle
import time
import concurrent.futures
from typing import List, Optional
from dotenv import load_dotenv

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_cohere import CohereRerank
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, Field

load_dotenv()

class GeminiLLM:
    _actual_model: Optional[str] = None
    
    @classmethod
    def get_model(cls) -> str:
        if cls._actual_model:
            return str(cls._actual_model)
        
        # Priority list for Chat LLM
        model_names = [
            "models/gemini-1.5-flash", 
            "models/gemini-1.5-flash-8b",
            "models/gemini-1.5-pro", 
            "models/gemini-2.0-flash-exp",
            "models/gemini-2.0-flash",
            "models/gemini-pro",
            "models/gemini-1.0-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash",
            "gemini-pro"
        ]
        
        for name in model_names:
            try:
                # Test connectivity
                genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
                model = genai.GenerativeModel(name)
                # Just a tiny test to see if the model exists in the region
                model.generate_content("test", generation_config={"max_output_tokens": 1})
                cls._actual_model = name
                print(f"Successfully connected to Chat LLM: {name}")
                return name
            except Exception as e:
                print(f"Model {name} not available for chat: {e}")
                continue
        
        # ULTIMATE SAFETY NET: Use the first available model that supports generation
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if available:
                cls._actual_model = available[0]
                print(f"Using fallback Chat LLM: {available[0]}")
                return available[0]
        except:
            pass
            
        raise Exception("No working Gemini Chat LLM found in this region.")

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
                genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
                genai.embed_content(model=m, content="test", task_type="retrieval_query")
                self.actual_model = m
                print(f"Successfully connected to embedding model: {m}")
                return m
            except:
                continue
        
        # UNIVERSAL FALLBACK: Find any available embedding model
        try:
            available = [m.name for m in genai.list_models() if 'embedContent' in m.supported_generation_methods]
            if available:
                self.actual_model = available[0]
                print(f"Using fallback embedding model: {available[0]}")
                return available[0]
        except:
            pass
            
        raise Exception("No working Gemini embedding model found in this region.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
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
                    time.sleep(5) # Slow and steady
                    break
                except Exception as e:
                    if "429" in str(e) or "Quota" in str(e):
                        print(f"Rate limit hit, waiting 45s... (Batch {i//batch_size})")
                        time.sleep(45)
                        retries -= 1
                    else: raise e
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        model = self._get_model()
        response = genai.embed_content(
            model=model,
            content=text,
            task_type="retrieval_query"
        )
        return response['embedding']

# We need to initialize the models and DB lazily to prevent crashing if not ingested yet
def get_retrievers():
    embeddings = GeminiEmbeddings()
    vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    try:
        with open("bm25_index.pkl", "rb") as f:
            bm25_data = pickle.load(f)
            bm25_index = bm25_data["bm25"]
            bm25_docs = bm25_data["docs"]
    except FileNotFoundError:
        bm25_index = None
        bm25_docs = []
    return vectorstore, bm25_index, bm25_docs

class DecomposedQueries(BaseModel):
    queries: List[str] = Field(description="The independent queries extracted from the user input")

def decompose_query(user_query: str) -> List[str]:
    # Using auto-detected model name
    model_name = GeminiLLM.get_model()
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    prompt = PromptTemplate.from_template(
        "You are an expert at breaking down complex questions into simpler, independent search queries.\n"
        "If a question asks about multiple distinct things, break it down into up to 3 separate questions.\n"
        "If the question is simple, just return the question itself as a single item in the list.\n"
        "User question: {query}\n"
    )
    chain = prompt | llm.with_structured_output(DecomposedQueries)
    try:
        result = chain.invoke({"query": user_query})
        return result.queries
    except Exception as e:
        print(f"Error decomposing query: {e}")
        return [user_query]

def hybrid_search(query: str, top_k: int = 10) -> List[Document]:
    vectorstore, bm25_index, bm25_docs = get_retrievers()
    if not vectorstore:
        return []
        
    # 1. Vector Search
    vector_results = vectorstore.similarity_search(query, k=top_k)
    
    # 2. Keyword Search
    keyword_results = []
    if bm25_index:
        tokenized_query = query.lower().split()
        bm25_scores = bm25_index.get_scores(tokenized_query)
        top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
        keyword_results = [bm25_docs[i] for i in top_indices if bm25_scores[i] > 0]
    
    # Merge and deduplicate
    seen = set()
    merged = []
    for doc in vector_results + keyword_results:
        doc_id = f"{doc.metadata.get('video_id', '')}_{doc.metadata.get('start_time', '')}"
        if doc_id not in seen:
            seen.add(doc_id)
            merged.append(doc)
            
    return merged

def rerank_chunks(query: str, chunks: List[Document], top_n: int = 3) -> List[Document]:
    if not chunks:
        return []
    # Added explicit model name to fix validation error
    reranker = CohereRerank(
        cohere_api_key=os.environ.get("COHERE_API_KEY"), 
        model="rerank-english-v3.0",
        top_n=top_n
    )
    return reranker.compress_documents(documents=chunks, query=query)

class JudgeResult(BaseModel):
    is_relevant: bool = Field(description="True if the answer actually answers the user query based on the context. False if it fails to answer or hallucinates.")
    reasoning: str = Field(description="Explanation for why it is relevant or not")

def process_query(user_query: str) -> str:
    # 1. Decompose
    queries = decompose_query(user_query)
    
    # 2. Parallel Hybrid Search
    all_chunks = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(hybrid_search, q): q for q in queries}
        for future in concurrent.futures.as_completed(futures):
            all_chunks.extend(future.result())
            
    # Deduplicate chunks from different queries
    seen = set()
    unique_chunks = []
    for doc in all_chunks:
        doc_id = f"{doc.metadata.get('video_id', '')}_{doc.metadata.get('start_time', '')}"
        if doc_id not in seen:
            seen.add(doc_id)
            unique_chunks.append(doc)
            
    # 3. Rerank
    top_chunks = rerank_chunks(user_query, unique_chunks, top_n=3)
    
    # 4. Generate Answer
    context = ""
    for doc in top_chunks:
        start_time = doc.metadata.get('start_time', 0)
        video_id = doc.metadata.get('video_id', '')
        # Formatting so the LLM knows the citation format
        context += f"[Cite: video={video_id}, time={start_time}]\nContent: {doc.page_content}\n\n"
        
    generation_prompt = PromptTemplate.from_template(
        "You are a helpful assistant answering questions based on video transcripts.\n"
        "Use the following context chunks to answer the user's question.\n"
        "Whenever you use information from a chunk, you MUST cite it using the exact format: [video_id:start_time].\n"
        "For example, if you use a chunk with video='dQw4w9WgXcQ' and time='124.5', you write [dQw4w9WgXcQ:124.5].\n"
        "If the answer is not contained in the context, say 'I cannot find the answer in the provided playlist.'\n\n"
        "Context:\n{context}\n\n"
        "User Question: {query}\n"
    )
    
    model_name = GeminiLLM.get_model()
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    chain = generation_prompt | llm
    
    # Add retry logic for 429s during generation
    answer = "I'm sorry, I encountered an error while generating the answer."
    retries = 3
    while retries > 0:
        try:
            answer_msg = chain.invoke({"context": context, "query": user_query})
            answer = answer_msg.content
            break
        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                print(f"Generation Rate limit hit, waiting 30s...")
                time.sleep(30)
                retries -= 1
            else:
                print(f"Error in generation: {e}")
                break
    
    # 5. Judge Relevance
    judge_prompt = PromptTemplate.from_template(
        "Evaluate the following answer to the user's question.\n"
        "Did the answer successfully address the user's query using the context, or did it fail/hallucinate/stating it doesn't know?\n"
        "Question: {query}\n"
        "Answer: {answer}\n"
    )
    judge_chain = judge_prompt | llm.with_structured_output(JudgeResult)
    try:
        # Also retry judge for 429s
        retries_j = 2
        while retries_j > 0:
            try:
                judge_eval = judge_chain.invoke({"query": user_query, "answer": answer})
                if not judge_eval.is_relevant:
                    return "I'm sorry, there is no information about this in the playlist."
                break
            except Exception as e:
                if "429" in str(e) or "Quota" in str(e):
                    time.sleep(20)
                    retries_j -= 1
                else: raise e
    except Exception as e:
        print(f"Error in judge: {e}")
        
    return answer
