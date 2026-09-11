# AI Automation Projects

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-Hybrid%20RAG-green.svg)](https://python.langchain.com/)
[![Langflow](https://img.shields.io/badge/Langflow-QA%20Agents-orange.svg)](https://langflow.org/)
[![DeepEval](https://img.shields.io/badge/DeepEval-Framework-purple.svg)](#11-deepeval-quality--security-evaluation-framework-deepeval_framework)
[![Kubernetes](https://img.shields.io/badge/Deploy-Kubernetes%20%7C%20Docker-blueviolet.svg)](#)

Welcome to the **AI Automation Projects** repository. This centralized monorepo houses a suite of state-of-the-art Generative AI pipelines, hybrid Retrieval-Augmented Generation (RAG) architectures, and low-code autonomous agent workflows engineered specifically for **Software Quality Assurance (SQA)**, **Automated Test Generation**, **LLM Evaluation**, and **API Verification**.

---

## Repository Structure & Project Overview

```text
AI-Automation-Projects/
├── Deepeval_Framework/                    # DeepEval Quality & Security Evaluation Framework & UI
├── crewai_projects/                       # CrewAI based Multi-Agent workflows
├── langchain_module_projects/              # LangChain & LangGraph Agents
│   ├── Langchain_content_writer_agent/    # LCEL Content Writer & Research Brief Agent
│   └── langgraph_financial_forecast_analysis/ # LangGraph 3-Stage Financial & Equity Valuation Pipeline
├── langchain-hybrid-rag-bm25/             # Production RAG Pipeline (uv, Qdrant, Postgres, BM25)
├── langchain-rag-test-case-legacy-docs/   # Legacy RAG Implementation (Poetry reference)
├── langflow-agents/                       # Custom Langflow Components & API Contract Validators
├── langflow-qa-agents/                    # Curated Langflow Low-Code Agent Workflows (.json)
├── llm_eval_projects/                     # LLM Evaluation Suite (DeepEval, Confident AI, Gemini Judge)
├── qa-chatbot-RAG/                        # Full Adaptive Qdrant RAG Engine & Vite Glassmorphic UI
├── QA_Mentor_ChatBot/                     # Interactive QA Mentorship System & Architecture
└── stlc-agent-tool/                       # STLC Agentic Platform (LangGraph, FastAPI, React)
```

---

### 1. [DeepEval Quality & Security Evaluation Framework (`Deepeval_Framework`)](./Deepeval_Framework/)

An enterprise-grade **DeepEval Quality & Security Framework and UI Dashboard** designed to evaluate AI Chatbots (**Subsystem A**) and RAG Systems (**Subsystem B**) across **25 evaluation metrics**, powered by **Google Gemini** (`gemini-3.6-flash`) and **Mistral AI** (`mistral-small-latest`, `mistral-large-latest`).

* **Core Highlights**:
  * **25 Comprehensive Quality & Security Metrics**: Evaluates Answer Relevancy, Faithfulness, Hallucination, Toxicity, Bias, PII Leakage, Prompt Injection, Jailbreak Defense, Data Exfiltration, Role Violation, and Domain Misuse.
  * **Unified Safety Score Scale**: Standardized score scales across all 25 metric cards so `1.00 = Safe/Clean/Compliant` and pass condition is `score >= 0.70` (including Toxicity Filter, Bias Filter, and Hallucination Detection).
  * **Single-Pass Fast LLM Judge Evaluation**: High-speed single-pass structured judge evaluation mode yielding **20x speedup** with zero rate-limits and fallback regex/JSON parser resilience.
  * **Interactive Web Dashboard (Port 8203)**: Real-time execution status badges, live step counters, token usage meters, and multi-provider selection.
  * **One-Click Orchestration (`run_all.py`)**: Master start script that launches backends, checks health, seeds knowledge stores, and starts the UI dashboard.

---

### 2. [LangChain & LangGraph Projects (`langchain_module_projects`)](./langchain_module_projects/)

A collection of autonomous agents engineered with **LangChain Expression Language (LCEL)**, **LangGraph state machines**, and dynamic multi-model orchestration.

* **Included Agents**:
  * **[`langgraph_financial_forecast_analysis`](./langchain_module_projects/langgraph_financial_forecast_analysis/)**:
    * **3-Stage LangGraph State Machine**: Orchestrates sequential collaboration across a **Forensic Auditor Node**, an **Independent Verification Officer Node**, and an **Equity Research Director Node**.
    * **Fault-Tolerant Multi-LLM Engine**: Multi-tiered failover across **Mistral AI**, **OpenAI**, **Anthropic Claude**, and **Google Gemini**.
  * **[`Langchain_content_writer_agent`](./langchain_module_projects/Langchain_content_writer_agent/)**:
    * **Veteran Researcher Persona**: Emulates a senior technical researcher to generate in-depth, structured research papers and technical briefs.

---

### 3. [LangChain Hybrid RAG & BM25 Pipeline (`langchain-hybrid-rag-bm25`)](./langchain-hybrid-rag-bm25/)

A production-grade, multi-modal RAG platform built with modern Python (`uv` package manager) that autonomously analyzes software documentation (PRDs, Jira user stories, architecture diagrams) and generates enterprise-ready QA artifacts.

* **Core Highlights**:
  * **Multi-Modal Document Parsing**: Integrates **Docling OCR** to parse complex PDF layouts, Word documents, and visual architecture diagrams.
  * **Advanced Hybrid Retrieval**: Combines **Qdrant** dense vector similarity search with sparse **BM25** lexical search and **FlashRank** cross-encoder reranking.
  * **Continuous Evaluation & Ragas Benchmarking**: Scored via Ragas (Context Precision, Recall, Faithfulness, Answer Relevance).

---

### 4. [LangChain RAG Legacy Implementation (`langchain-rag-test-case-legacy-docs`)](./langchain-rag-test-case-legacy-docs/)

The original, preserved implementation of the QA Test Case Generation RAG pipeline built using **Poetry**. Maintained as a historical reference and architecture benchmark for backward compatibility.

---

### 5. [Langflow Custom Agents & Contract Validators (`langflow-agents`)](./langflow-agents/)

A collection of custom Python utilities and extensions designed to integrate seamlessly into custom pipelines or Langflow environments.

* **Featured Component (`contract-validator`)**:
  * An automated API verification suite (`validator.py`, `cli.py`, and `langflow_component.py`) that checks HTTP requests and responses against formal OpenAPI/Swagger specifications and JSON schemas.

---

### 6. [Langflow QA Agent Workflows (`langflow-qa-agents`)](./langflow-qa-agents/)

A curated collection of low-code, drag-and-drop autonomous agent workflows formatted as importable Langflow JSON blueprints (`*.json`).

* **Included Agent Workflows**: `Test-Case-Generator.json`, `Test-Plan-Creator.json`, `Bug_Triage_Agent.json`, `RCA-Bot.json`, `Flaky_Test_Case_generator.json`, and `JSON-Schema-Validator.json`.

---

### 7. [Enterprise QA-Assistant-Chatbot & Adaptive Qdrant RAG Suite (`qa-chatbot-RAG`)](./qa-chatbot-RAG/)

An end-to-end, hardened enterprise Quality Assurance Retrieval-Augmented Generation ecosystem featuring a **Vite + React Glassmorphic UI** wired directly to **Qdrant Vector Engine** and **Vercel AI Gateway**.

👉 **Access the Verified Live Cloud Application**: **[https://qa-rag.vercel.app/](https://qa-rag.vercel.app/)**

---

### 8. [QA Mentor ChatBot (`QA_Mentor_ChatBot`)](./QA_Mentor_ChatBot/)

An interactive QA mentorship system designed to guide, review, and assist users in Software Quality Assurance practices.

![QA Mentor Architecture](./QA_Mentor_ChatBot/qa_mentor_architecture_1784438683437.png)

---

### 9. [STLC Agentic Platform (`stlc-agent-tool`)](./stlc-agent-tool/)

A centralized, AI-driven automation orchestrator for modern Software Testing Life Cycles (STLC) utilizing LangGraph for multi-agent workflows.

---

### 10. [CrewAI Projects (`crewai_projects`)](./crewai_projects/)

A dedicated workspace for enterprise CrewAI multi-agent automation workflows.

* **Included Projects**:
  * **[`pro1_flaky_testcase_locator_agent`](./crewai_projects/pro1_flaky_testcase_locator_agent/)**: Autonomous Playwright diagnostics and flaky test case locator agent.

---

### 11. [LLM Evaluation Projects (`llm_eval_projects`)](./llm_eval_projects/)

An enterprise-ready LLM evaluation suite leveraging **DeepEval**, **Confident AI**, and **LLM-as-a-Judge** scoring metrics powered by **Google Gemini**.

---

## Quick Start Guide

Each project maintains its own dedicated setup guide and dependencies. To get started:

1. **For DeepEval Quality & Security Framework**:
   Navigate to [`Deepeval_Framework`](./Deepeval_Framework/), configure `03_DeepEval_Dashboard/.env` with your `GEMINI_API_KEY` and `MISTRAL_API_KEY`, and run `python run_all.py`.
2. **For LangGraph Financial Forecast Agent**:
   Navigate to [`langchain_module_projects/langgraph_financial_forecast_analysis`](./langchain_module_projects/langgraph_financial_forecast_analysis/), copy `configs/.env.example` to `configs/.env`, insert API keys, and run `python main.py`.
3. **For Production RAG Generation & Evaluation**:
   Navigate to [`langchain-hybrid-rag-bm25`](./langchain-hybrid-rag-bm25/) and follow the [SETUP.md](./langchain-hybrid-rag-bm25/SETUP.md) instructions using `uv`.
4. **For CrewAI Multi-Agent Workflows**:
   Navigate to [`crewai_projects/pro1_flaky_testcase_locator_agent`](./crewai_projects/pro1_flaky_testcase_locator_agent/), run `uv sync`, copy `config/.env.example` to `config/.env`, and execute `uv run main.py`.
5. **For Langflow Visual Workflows**:
   Launch your local instance of [Langflow](https://github.com/langflow-ai/langflow) (`pip install langflow && langflow run`) and import any JSON workflow from [`langflow-qa-agents`](./langflow-qa-agents/).

---

## License & Contributing

Contributions, issues, and feature requests are welcome! Feel free to open a pull request or discuss enhancements across any of the included pipelines.
