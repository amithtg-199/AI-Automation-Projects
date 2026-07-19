# QA Mentor ChatBot

A sophisticated AI-powered QA Assistant that uses an Advanced Hybrid RAG pipeline (Retrieval-Augmented Generation) combined with GraphRAG to query test cases, framework code, PRDs, and Jira tickets.

## Architecture
- **Frontend**: Vite + React, TailwindCSS, React-Markdown.
- **Backend**: FastAPI.
- **Vector Database**: Qdrant (dense vectors) + BM25 (sparse).
- **Graph Database**: Neo4j (for entity/relationship linking).
- **LLM**: Mistral AI (Embeddings and Chat).

## Setup Instructions

### 1. Backend Setup
1. Navigate to the `backend` directory.
2. Install dependencies: `uv pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your API keys (e.g., `MISTRAL_API_KEY`).
4. Ensure Qdrant is running (e.g., via Docker: `docker run -p 6333:6333 qdrant/qdrant`).
5. Run the backend server: `uv run uvicorn api.main:app --reload`

### 2. Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`

### 3. Usage
- Go to the UI.
- Use the Config Panel to set up your environment keys.
- Upload your documents (code repos, CSVs, PDFs) into the `backend/input_data/<project_name>` folder.
- Click **Ingest** to start processing documents into chunks and embeddings.
- Start asking questions in the chat!
