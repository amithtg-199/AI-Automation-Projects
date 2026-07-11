# Enterprise QA-Assistant-Chatbot & Adaptive Qdrant RAG Suite

[![Live Demo](https://img.shields.io/badge/Live%20Demo-https%3A%2F%2Fqa--rag.vercel.app%2F-ec4899)](https://qa-rag.vercel.app/) ![Status](https://img.shields.io/badge/Status-Production%20Ready-emerald) ![RAG Engine](https://img.shields.io/badge/Vector%20Store-Qdrant%201024--Cosine-indigo) ![LLM Engine](https://img.shields.io/badge/AI%20Gateway-Codestral--Latest-blue) ![Frontend](https://img.shields.io/badge/Frontend-Vite%20%2B%20React%20Glassmorphism-pink)

## 🌟 Executive Overview
**`qa-chatbot-RAG`** is an end-to-end, hardened enterprise Quality Assurance (QA) Retrieval-Augmented Generation (RAG) ecosystem. Built specifically for high-capacity test case repositories (`ecommerce_test_cases.csv`, API specs, and PRDs), this architecture bridges **Langflow Studio pipelines**, **Qdrant Vector Engine**, and **Vercel AI Gateway** with an ultra-responsive, beautiful **Vite + React Glassmorphic UI**.

👉 **Access the Live Production App Here**: **[https://qa-rag.vercel.app/](https://qa-rag.vercel.app/)**

---

## 🏗️ Core Architectural Capabilities

### 1. 🧠 Adaptive Qdrant Hybrid Retriever (`AdaptiveQdrantHybridRetriever.py`)
- **Exact Scroll Aggregation**: Automatically intercepts quantitative inventory queries (`"how many test cases in Login module"`, `"list all modules"`) and bypasses semantic vector approximation to return **100% accurate, non-hallucinated counts & lists** via direct `QdrantClient.scroll()`.
- **Deep Semantic Vector Synthesis**: For complex scenario workflows (`"Show me critical payment failure steps"`), performs 1024-dimensional cosine similarity search across indexed document embeddings.
- **Dynamic Confidence & Guardrails**: Evaluates every retrieved answer against strict numerical thresholds (`0.65` confidence threshold). If a query falls below threshold or triggers off-topic guardrails, the system blocks hallucination and returns an explicit safety alert.

### 2. ⚡ Dynamic Ingestion & Versioning Studio (`qa-assistant-chatbot`)
- **Target Collection & Versioning Control**: Features real-time state synchronization (`IngestionWorkspace.jsx`) with live Qdrant `PUT /collections/<project_name>` and `PUT /collections/<project_name>/points` REST API updates.
- **Automated Version Overrides (`Langflow API Tweaks`)**: When users upload test documents (`ecommerce_test_cases.csv`) and click *Start Ingestion Process*, the UI automatically passes a `tweaks` JSON object (`{ AdaptiveMultiFormatChunker: { project_name, version } }`) to override static `v1` nodes inside Langflow Studio (`v1` $\rightarrow$ `v2` $\rightarrow$ `v3`).
- **Clean Visual Status Badges**: Displays elegant `Auto-Increment Active`, `Metadata Prefix Active`, and `API Tweaks Override Enabled` indicators.

### 3. 🌐 Vercel AI Gateway & Multi-Model Orchestration (`EnvironmentTabs.jsx`)
- **Vercel AI Gateway Integration**: Full native support for `AI_GATEWAY_API_KEY` (`vck_...`), allowing seamless routing to high-performance AI engines (`codestral-latest`, `mistral-large-latest`, `open-mistral-nemo`, and `Claude 3.5 Sonnet`).
- **Persistent LocalStorage State**: All custom endpoints (`http://localhost:7860`), embedding dimensions (`1024 Cosine`), and third-party MCP integrations (**Jira**, **Confluence**, **GitHub**, **Slack**) persist automatically with interactive connection validation (`Not Configured` default safety).

---

## 📁 Repository Directory Structure

```text
qa-chatbot-RAG/
├── AdaptiveMultiFormatChunker.py     # Custom Langflow node for chunking CSV/MD/PDF/JSON test cases
├── AdaptiveQdrantHybridRetriever.py  # Hybrid Qdrant retriever with Exact Scroll & Confidence Guardrails
├── ContextBuilder.py                 # Structured context formatting engine for LLM prompts
├── QueryIntentRouter.py              # Natural language query classifier (Count vs. List vs. Semantic)
├── HardenedQARagPrompt.md            # Enterprise system prompt enforcing anti-hallucination & structured markdown tables
├── MetadataVersionManager.py         # Version tag lifecycle manager (v1 -> v2)
├── generate_cases.py                 # Automated generator for 1,000+ realistic ecommerce QA test cases
├── ecommerce_test_cases.csv          # Sample dataset: 1,000 multi-module test cases (Payment, Login, Cart, Search)
├── langflow_node_wiring_guide.md     # Complete step-by-step connection blueprint for Langflow Studio
└── qa-assistant-chatbot/             # Full Vite + React frontend web application
    ├── src/
    │   ├── components/
    │   │   ├── Header.jsx            # Top navigation & system status badges
    │   │   ├── IngestionWorkspace.jsx# Document upload, Qdrant REST sync, and live API tweaks preview
    │   │   ├── ChatStudio.jsx        # Grounded response studio with query history (`Showing X query responses`)
    │   │   └── EnvironmentTabs.jsx   # Vercel AI Gateway, MistralAI settings, and MCP connection manager
    │   ├── App.jsx                   # Master state controller & live Qdrant heartbeat monitor
    │   └── index.css                 # Vanilla CSS design system (Glassmorphism, vibrant gradients)
    ├── vercel.json                   # Single-Page Application (SPA) routing rules for Vercel CDN
    └── package.json                  # React 18, Lucide Icons, Canvas Confetti dependencies
```

---

## 🚀 Complete Step-by-Step Local Setup & Execution Guide

To run the entire suite locally (Frontend + Backend Engine + Vector Database), follow these three simple steps:

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

Ensure you have **Node.js 18+** installed. Navigate into the frontend workspace:

```bash
# 1. Navigate to the frontend directory inside qa-chatbot-RAG
cd qa-assistant-chatbot

# 2. Install React & UI dependencies
npm install

# 3. Launch the Vite Development Server
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

---

### Part D: Cloud Verification via Vercel Production URL

If you don't want to run the local frontend dev server, you can interact with our verified cloud deployment at any time:
👉 **[https://qa-rag.vercel.app/](https://qa-rag.vercel.app/)**
