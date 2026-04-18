# 🎥 YouTube RAG: Advanced Video Intelligence System

A cutting-edge Retrieval-Augmented Generation (RAG) platform that allows users to ingest YouTube playlists and perform complex semantic searches across video transcripts. Built with a focus on precision, transparency, and a premium user experience.

![Project Preview](https://img.shields.io/badge/Stack-FastAPI_%7C_React_%7C_Gemini-blue?style=for-the-badge)
![RAG Architecture](https://img.shields.io/badge/Architecture-Hybrid_Search_%2B_Reranking-indigo?style=for-the-badge)

## 🚀 Key Highlights

### 1. Hybrid Retrieval Engine
Unlike basic RAG systems that rely solely on vector math, this project implements a dual-search strategy:
*   **Vector Search (Semantic):** Uses **Google Gemini (`text-embedding-004`)** and **ChromaDB** to find context based on meaning and intent.
*   **Keyword Search (Lexical):** Implements the **BM25 algorithm** to capture specific terms, technical jargon, and names that vector embeddings might miss.

### 2. Precision Pipeline (Agentic Features)
The system goes beyond simple "retrieve and generate":
*   **Query Decomposition:** Complex user questions are automatically broken down into simpler sub-queries using LLM chain logic to ensure no nuance is lost.
*   **Parallel Execution:** Search operations for sub-queries are executed in parallel for maximum performance.
*   **Cohere Reranking:** Top results from both search methods are passed through **Cohere's Rerank v3.0** model to identify the absolute most relevant chunks.
*   **The "Judge" Step:** A self-correction mechanism where an LLM evaluates the final answer for relevance and hallucinations before showing it to the user.

### 3. Hyper-Specific Citations
Every claim made by the assistant is backed by a timestamped citation.
*   **Deep Linking:** The frontend automatically converts citations into clickable links (e.g., `[dQw4w9WgXcQ:124.5]`).
*   **One-Click Seek:** Clicking a citation opens the YouTube video and jumps exactly to the second mentioned in the context.

### 4. Resilient Architecture
*   **Auto-Model Detection:** Dynamically detects and falls back between different Gemini models (Flash, Pro, 8B) based on availability and region.
*   **Rate-Limit Management:** Built-in retry logic and exponential backoff to handle Google Gemini's free tier quotas gracefully.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite, Tailwind CSS (Custom Dark Theme) |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **RAG Framework** | LangChain, LangChain-Community |
| **Vector Store** | ChromaDB |
| **LLMs & AI** | Google Gemini (LLM & Embeddings), Cohere (Reranking) |
| **Data Extraction** | youtube-transcript-api, yt-dlp, pytube |

---

## 📂 Project Structure

```bash
rag_project/
├── backend/
│   ├── ingestion.py      # Transcript extraction & Hybrid Index building
│   ├── query.py          # Decomp, Hybrid Search, Rerank & Generation logic
│   ├── main.py           # FastAPI server & route handlers
│   ├── playlist.py       # YouTube metadata & URL extraction utils
│   └── chroma_db/         # Persistent vector storage
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Chat UI & Interactive terminal
│   │   └── index.css     # Premium styling & animations
│   └── package.json
└── README.md
```

---

## ⚡ Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   Google Gemini API Key
*   Cohere API Key

### Backend Setup
1.  Navigate to `backend/`
2.  Install dependencies: `pip install -r requirements.txt`
3.  Create a `.env` file:
    ```env
    GEMINI_API_KEY=your_gemini_key
    COHERE_API_KEY=your_cohere_key
    ```
4.  Run the server: `python -m uvicorn main:app --reload`

### Frontend Setup
1.  Navigate to `frontend/`
2.  Install dependencies: `npm install`
3.  Run the development server: `npm run dev`

---

## 🌟 Premium UX
The frontend features a custom **Neutral-950 Dark Aesthetic** with:
*   **Glassmorphism** headers and cards.
*   **Micro-animations** for loading and chat transitions.
*   **Gradient Accents** and smooth hover effects.
*   **Streamlined Ingestion Flow** with real-time status updates.
