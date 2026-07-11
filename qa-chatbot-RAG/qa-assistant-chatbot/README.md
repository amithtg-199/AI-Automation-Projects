# Enterprise QA-Assistant-Chatbot & Adaptive Qdrant RAG Suite

[![Live Demo](https://img.shields.io/badge/Live%20Demo-https%3A%2F%2Fqa--rag.vercel.app%2F-ec4899)](https://qa-rag.vercel.app/) ![Status](https://img.shields.io/badge/Status-Production%20Ready-emerald) ![RAG Engine](https://img.shields.io/badge/Vector%20Store-Qdrant%201024--Cosine-indigo) ![LLM Engine](https://img.shields.io/badge/AI%20Gateway-Codestral--Latest-blue) ![Frontend](https://img.shields.io/badge/Frontend-Vite%20%2B%20React%20Glassmorphism-pink)

👉 **Access the Live Production App Here**: **[https://qa-rag.vercel.app/](https://qa-rag.vercel.app/)**

---

## 🚀 Complete Step-by-Step Local Setup & Execution Guide

To run the entire suite locally (Frontend + Backend Engine + Vector Database), follow these simple steps:

### Part A: Setting Up & Running Langflow & Qdrant Backend (`Docker / Python Virtualenv`)

#### Option 1: Running via Docker (`Recommended for Zero Setup`)
If you have Docker Desktop installed, spin up Qdrant Vector Engine and Langflow Studio in separate terminal tabs:

```bash
# 1. Launch Qdrant Vector Database on port 6333
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest

# 2. Launch Langflow Studio on port 7860
docker run -d --name langflow -p 7860:7860 --link qdrant:qdrant langflowai/langflow:latest
```

#### Option 2: Running Langflow via Python (`Local Virtual Environment`)
If you prefer running Langflow natively inside Python 3.10+ (`uv` or `pip`):

```bash
# 1. Create a clean virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows PowerShell: .\.venv\Scripts\Activate.ps1

# 2. Install Langflow and Qdrant client
pip install langflow qdrant-client requests

# 3. Start Langflow Studio
langflow run --host 0.0.0.0 --port 7860
```
*Open **`http://localhost:7860`** in your browser. Create a new flow or import the custom nodes (`AdaptiveMultiFormatChunker.py`, `AdaptiveQdrantHybridRetriever.py`, `QueryIntentRouter.py`, `ContextBuilder.py`).*

---

### Part B: Setting Up & Running the Frontend UI Locally (`Vite Dev Server`)

Ensure you have **Node.js 18+** installed:

```bash
# 1. Install React & UI dependencies inside qa-assistant-chatbot
npm install

# 2. Launch the Vite Development Server
npm run dev
```
*Open your browser at **`http://localhost:5173`**. You will immediately see the interactive **QA-Assistant-Chatbot** workspace!*

---

### Part C: Connecting Your Local UI to Langflow & Vercel AI Gateway

Once your local UI (`http://localhost:5173`) and Langflow Studio (`http://localhost:7860`) are running:

1. Click on the **Model Context Protocol & Environment** tab inside the web interface.
2. **LLM Provider Selection**: Choose **`Vercel AI Gateway (Unified Proxy via AI_GATEWAY_API_KEY)`** or **`MistralAI`**.
3. **Authentication Secret Key**: Paste your `AI_GATEWAY_API_KEY` (`vck_...`) or Mistral API token (`mistral_api_key`).
4. **Orchestration Server Base URL**: Ensure this is set to **`http://localhost:7860`** (your local Langflow instance).
5. Click **Save Environment Configuration**. All credentials persist securely in browser `localStorage`!
