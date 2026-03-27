import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import ingestion
import query

load_dotenv()

app = FastAPI(title="YouTube RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    message: str

@app.post("/ingest")
def ingest_playlist(request: IngestRequest):
    try:
        chunks_count = ingestion.process_playlist(request.url)
        return {"status": "success", "chunks_processed": chunks_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat_with_playlist(request: ChatRequest):
    try:
        answer = query.process_query(request.message)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
