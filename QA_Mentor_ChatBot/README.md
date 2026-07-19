# 🍌 QA Mentor Chatbot

![QA Mentor Chatbot](https://img.shields.io/badge/UI-Apple_Nano_Banana-F59E0B) ![React](https://img.shields.io/badge/Frontend-React_Vite-61DAFB) ![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688) ![Mistral](https://img.shields.io/badge/LLM-Mistral_AI-black)

A highly sophisticated, AI-powered QA Assistant that uses an **Advanced Hybrid RAG (Retrieval-Augmented Generation)** pipeline combined with **GraphRAG** to intelligently query your team's test cases, framework code (Selenium/Playwright), PRDs, and Jira tickets.

## ✨ Key Features

- **Apple "Nano Banana" Aesthetic**: A premium, frosted-glass 3-column responsive layout built with Tailwind CSS.
- **Hybrid Search**: Combines Qdrant Dense Vectors (for semantic meaning) with BM25 Sparse Vectors (for exact keyword matching).
- **GraphRAG**: Utilizes Neo4j to map relationships between features, JIRA tickets, and test cases for deep, interconnected answers.
- **Cross-Encoder Reranking**: Re-ranks merged results from Hybrid Search and Graph retrieval to ensure only the highest-quality context is passed to the LLM.
- **Cited Answers**: Mistral AI generates responses that explicitly cite the exact file, line number, or ticket used.

---

## 🏗️ System Architecture

1. **Frontend**: Vite + React, TailwindCSS, React-Markdown.
2. **Backend**: FastAPI (Python).
3. **Vector Database**: Qdrant (for embedding storage & BM25 sparse vectors).
4. **Graph Database**: Neo4j (for entity/relationship linking).
5. **LLM & Embeddings**: Mistral AI (used for both `mistral-embed` and `open-mistral-nemo` chat completion).

### The Retrieval Pipeline
1. **Understand**: The user's query is condensed and rewritten into multiple search variants.
2. **Retrieve**: Variants are searched across Qdrant (Hybrid) and Neo4j (Graph).
3. **Fuse & Rerank**: Result lists are merged using Reciprocal Rank Fusion (RRF) and re-scored by a Cross-Encoder.
4. **Synthesize**: Mistral AI answers the query using strictly the top-ranked chunks.

---

## 🚀 Setup Instructions

### 1. Prerequisites
- Node.js (v18+)
- Python (3.10+)
- `uv` Python package manager
- Docker (for running Qdrant & Neo4j locally)

### 2. Backend Setup
Navigate to the `backend` directory:
```bash
cd backend
```
Install dependencies using `uv`:
```bash
uv pip install -r requirements.txt
```
Set up Environment Variables:
```bash
cp .env.example .env
```
*Edit `.env` and add your `MISTRAL_API_KEY`.*

Start the Vector Database (Qdrant):
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Run the backend server:
```bash
uv run uvicorn api.main:app --reload
```

### 3. Frontend Setup
Navigate to the `frontend` directory:
```bash
cd frontend
```
Install dependencies:
```bash
npm install
```
Start the development server:
```bash
npm run dev
```

---

## 📚 Usage Guide

1. **Access the UI**: Open your browser to `http://localhost:5173`.
2. **Configuration**: Use the left panel to verify your Qdrant URL and Mistral API Key.
3. **Add Knowledge**: Drop your code repositories, CSV files, and Markdown documents into the `backend/input_data/<project_name>` folder.
4. **Ingest**: Click the **open** button next to Ingest on the left panel to begin processing, chunking, and embedding the documents.
5. **Chat**: Start asking complex QA questions in the central chat interface!

---

## 📂 Project Structure

```text
├── backend/
│   ├── api/                 # FastAPI routes and endpoints
│   ├── core/                # RAG logic (Chunking, Hybrid Search, Neo4j Graph)
│   ├── input_data/          # Folder for raw documents (CSV, MD, code)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/      # ChatBox, ConfigPanel, InfoPanel
│   │   ├── App.tsx          # 3-column layout orchestration
│   │   └── index.css        # Tailwind directives and Inter font configs
│   ├── package.json
│   └── tailwind.config.js
└── README.md
```
