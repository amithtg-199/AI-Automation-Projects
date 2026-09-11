# DeepEval Quality & Security Evaluation Framework

An enterprise **DeepEval Evaluation Framework and UI Dashboard** for evaluating AI Chatbots (**Subsystem A**) and RAG Systems (**Subsystem B**), powered by **Google Gemini** (`gemini-3.6-flash`) and **Mistral AI** (`mistral-small-latest`, `mistral-large-latest`) LLM APIs (with Groq and offline Mock mode support).

---

## 🏗️ Framework Architecture

```
Deepeval_Framework/
├── 01_Chatbot_Shopeasy_chatbot/   # Subsystem A: Chatbot Support Service (Port 8201)
├── 02_RAG_Explorer/               # Subsystem B: RAG Explorer Knowledge Base (Port 8202)
├── 03_DeepEval_Dashboard/          # Subsystem C: DeepEval UI & Metric Engine (Port 8203)
│   ├── llm_providers/             # Gemini & Mistral DeepEval Base LLM Judges
│   ├── metrics_catalog.py         # 25 Metric Specifications & Scale Hints
│   ├── datasets/                  # Golden QA & 27 Security Attack Datasets
│   ├── targets/                   # Target API runners (Port 8201 & 8202 & AleeUp API)
│   ├── tests/                     # Pytest suite
│   └── dashboard/                 # FastAPI server & interactive Web UI
├── run_all.py                     # One-click multi-subsystem launcher
└── README.md
```

---

## 🔌 Subsystem Port Mapping

| Subsystem | Folder Path | Port | Health Check URL |
|---|---|---|---|
| **Subsystem A (Chatbot)** | `01_Chatbot_Shopeasy_chatbot/01_chatbot/backend` | `8201` | `http://localhost:8201/health` |
| **Subsystem B (RAG Explorer)** | `02_RAG_Explorer/02_rag_explorer` | `8202` | `http://localhost:8202/api/health` |
| **Subsystem C (DeepEval UI)** | `03_DeepEval_Dashboard` | `8203` | `http://localhost:8203` |

---

## ✨ Key Features & Enhancements

- **25 Comprehensive Metrics**: Covers Answer Relevancy, Faithfulness, Hallucination, Toxicity, Bias, PII Leakage, Prompt Injection, Jailbreak Defense, Obfuscation, Data Exfiltration, Role Violation, and Domain Misuse.
- **Multi-Model Judge Support**: Native integration with Google Gemini (`gemini-3.6-flash`) and Mistral AI (`mistral-small-latest`, `mistral-large-latest`), plus Groq and mock fallbacks.
- **Safety Score Scale Alignment**: Standardized score scales across all metrics so `1.00 = Safe/Clean/Compliant` and pass threshold is `score >= 0.70` for all 25 metric cards (including Toxicity Filter, Bias Filter, and Hallucination Filter).
- **Single-Pass Fast Evaluation Engine**: Fast single-pass structured judge evaluation yielding **20x speedup** with zero rate-limits, featuring robust JSON and regex fallback parsing.
- **Zero-Dependency RAG Knowledge Engine**: Features an in-memory cosine-similarity vector store fallback when ChromaDB is not installed.
- **Live Progress UI**: Real-time evaluation status badges, execution spinners, and token usage meters.

---

## 🚀 How to Run the Project

### Step 1: Install Dependencies

Ensure Python 3.10+ is installed, then install requirements:

```bash
pip install -r 03_DeepEval_Dashboard/requirements.txt
```

---

### Step 2: Start All Subsystems with One Command (Recommended)

Run the master start script, which launches backends first, waits for health checks, seeds the RAG knowledge store, starts the UI dashboard, and opens `http://localhost:8203` in your browser:

```bash
python run_all.py
```
*(On Windows, you can also double-click `run_all.bat`)*

---

### Step 2 (Alternative): Start Subsystems Manually in Separate Terminals

If you prefer starting each service manually:

#### Terminal 1 — Subsystem A (Chatbot on Port 8201)
```bash
cd 01_Chatbot_Shopeasy_chatbot/01_chatbot/backend
python -m uvicorn app:app --port 8201 --reload
```

#### Terminal 2 — Subsystem B (RAG Explorer on Port 8202)
```bash
cd 02_RAG_Explorer/02_rag_explorer
python -m uvicorn app:app --port 8202 --reload
```

#### Terminal 3 — Subsystem C (DeepEval UI Dashboard on Port 8203)
```bash
cd 03_DeepEval_Dashboard
python -m uvicorn dashboard.app:app --port 8203 --reload
```

---

### Step 3: Open the DeepEval Dashboard in Browser

Navigate to:
```text
http://localhost:8203
```

1. **Input API Key**: Enter your **Google Gemini API Key** or **Mistral API Key** in the header configuration bar.
2. **Select Provider & Model**: Choose `Google Gemini` (`gemini-3.6-flash`) or `Mistral AI` (`mistral-small-latest` / `mistral-large-latest`).
3. **Save Keys**: Click **Save Keys**.
4. **Run Evaluation**: Click **▶ Run All 25 Metrics** or test individual metric cards!

---

## 🧪 Running Pytest Automated Tests

To run the automated evaluation suite via terminal CLI:

```bash
cd 03_DeepEval_Dashboard
python -m pytest tests -v
```

---

## 🔑 Environment Variables

Set API keys in `03_DeepEval_Dashboard/.env`:

```ini
GEMINI_API_KEY=your_gemini_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here

EVAL_PROVIDER=gemini
EVAL_MODEL=gemini-3.6-flash
MISTRAL_MODEL=mistral-small-latest
```
