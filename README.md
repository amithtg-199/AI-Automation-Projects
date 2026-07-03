# AI Automation Projects

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-Hybrid%20RAG-green.svg)](https://python.langchain.com/)
[![Langflow](https://img.shields.io/badge/Langflow-QA%20Agents-orange.svg)](https://langflow.org/)
[![Kubernetes](https://img.shields.io/badge/Deploy-Kubernetes%20%7C%20Docker-blueviolet.svg)](#)

Welcome to the **AI Automation Projects** repository. This centralized monorepo houses a suite of state-of-the-art Generative AI pipelines, hybrid Retrieval-Augmented Generation (RAG) architectures, and low-code autonomous agent workflows engineered specifically for **Software Quality Assurance (SQA)**, **Automated Test Generation**, and **API Verification**.

---

## Repository Structure & Project Overview

```text
AI-Automation-Projects/
├── langchain-hybrid-rag-bm25/             # Production RAG Pipeline (uv, Qdrant, Postgres, BM25)
├── langchain-rag-test-case-legacy-docs/   # Legacy RAG Implementation (Poetry reference)
├── langflow-agents/                       # Custom Langflow Components & API Contract Validators
└── langflow-qa-agents/                    # Curated Langflow Low-Code Agent Workflows (.json)
```

---

### 1. [LangChain Hybrid RAG & BM25 Pipeline (`langchain-hybrid-rag-bm25`)](./langchain-hybrid-rag-bm25/)

A production-grade, multi-modal RAG platform built with modern Python (`uv` package manager) that autonomously analyzes software documentation (PRDs, Jira user stories, architecture diagrams) and generates enterprise-ready QA artifacts.

* **Core Highlights**:
  * **Multi-Modal Document Parsing**: Integrates **Docling OCR** to parse complex PDF layouts, Word documents, and visual architecture diagrams.
  * **Advanced Hybrid Retrieval**: Combines **Qdrant** dense vector similarity search with sparse **BM25** lexical search and **FlashRank** cross-encoder reranking.
  * **Comprehensive SQA Artifact Generation**: Generates structured Test Strategies, Test Plans, Risk Matrices, Requirement Traceability Matrices (RTM), Test Data Matrices, End-to-End Test Cases, and Automation Framework Recommendations.
  * **Continuous Evaluation & Ragas Benchmarking**: Features built-in synthetic testset generation (`generate_300_qa.py`), automated Ragas scoring (Context Precision, Recall, Faithfulness, Answer Relevance), and PostgreSQL feedback loops.
  * **Cloud-Native Deployment**: Includes complete standalone Docker Compose environments and production Kubernetes Helm charts with Horizontal Pod Autoscaling (HPA) and Prometheus monitoring metrics.

---

### 2. [LangChain RAG Legacy Implementation (`langchain-rag-test-case-legacy-docs`)](./langchain-rag-test-case-legacy-docs/)

The original, preserved implementation of the QA Test Case Generation RAG pipeline built using **Poetry**. Maintained as a historical reference and architecture benchmark for backward compatibility.

---

### 3. [Langflow Custom Agents & Contract Validators (`langflow-agents`)](./langflow-agents/)

A collection of custom Python utilities and extensions designed to integrate seamlessly into custom pipelines or Langflow environments.

* **Featured Component (`contract-validator`)**:
  * An automated API verification suite (`validator.py`, `cli.py`, and `langflow_component.py`) that checks HTTP requests and responses against formal OpenAPI/Swagger specifications and JSON schemas.
  * Prevents schema drift and contract violations within automated integration test flows.

---

### 4. [Langflow QA Agent Workflows (`langflow-qa-agents`)](./langflow-qa-agents/)

A curated collection of low-code, drag-and-drop autonomous agent workflows formatted as importable Langflow JSON blueprints (`*.json`).

* **Included Agent Workflows**:
  * **`Test-Case-Generator.json`**: Translates raw user stories and acceptance criteria into comprehensive, edge-case-aware test scripts.
  * **`Test-Plan-Creator.json`**: Synthesizes master test strategies, resource allocations, and scope definitions.
  * **`Bug_Triage_Agent.json`**: Autonomously analyzes incoming bug reports, classifies defects, deduplicates existing issues, and assigns severity/priority ratings.
  * **`RCA-Bot.json`**: A Root Cause Analysis assistant that investigates CI/CD pipeline failures, stack traces, and system logs to pinpoint underlying defects.
  * **`Flaky_Test_Case_generator.json`**: Identifies non-deterministic test patterns and rewrites tests with robust synchronization and assertion mechanisms.
  * **`JSON-Schema-Validator.json`**: Low-code data validation node for payload verification.

---

## Quick Start Guide

Each project maintains its own dedicated setup guide and dependencies. To get started:

1. **For Production RAG Generation & Evaluation**:
   Navigate to [`langchain-hybrid-rag-bm25`](./langchain-hybrid-rag-bm25/) and follow the [SETUP.md](./langchain-hybrid-rag-bm25/SETUP.md) instructions using `uv`.
2. **For Langflow Visual Workflows**:
   Launch your local instance of [Langflow](https://github.com/langflow-ai/langflow) (`pip install langflow && langflow run`) and import any JSON workflow from [`langflow-qa-agents`](./langflow-qa-agents/).

---

## License & Contributing

Contributions, issues, and feature requests are welcome! Feel free to open a pull request or discuss enhancements across any of the included pipelines.
