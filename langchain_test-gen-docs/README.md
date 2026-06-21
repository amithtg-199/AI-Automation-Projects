# Enterprise QA Test Case Generation (RAG Pipeline)

An enterprise-grade, scalable, and LLM-agnostic system that extracts knowledge from Product Requirement Documents (PRDs) and Jira issues, builds a robust vectorized knowledge base, and uses Retrieval-Augmented Generation (RAG) to generate comprehensive Test Plans and Test Cases with zero data loss.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Microservices & Scalability](#microservices--scalability)
3. [The Pipeline Flow](#the-pipeline-flow)
4. [Prompt & Output Versioning](#prompt--output-versioning)
5. [Evaluation Framework (RAGAS)](#evaluation-framework-ragas)
6. [Observability & Metrics](#observability--metrics)

---

## Architecture Overview

The system operates as an event-driven FastAPI application backed by a microservices architecture. It parses unstructured inputs, chunks them hierarchically, and stores them in dual databases to support precise generation without context window overflow.

### Core Stack
- **API Orchestrator:** FastAPI + Uvicorn (Python 3.11+)
- **Dependency Management:** Poetry
- **Document Extraction:** Dedicated Extraction Service (Docling + Unstructured OCR)
- **Databases:** PostgreSQL (2000-token Parent Chunks) + Qdrant (400-token Child Vectors)
- **AI/LLM Core:** LangChain with Universal LLM Support (Mistral, OpenAI, Anthropic, Ollama, VertexAI)
- **Observability:** Prometheus + Grafana

---

## Microservices & Scalability

This architecture is completely decoupled for Kubernetes (K8s) cloud-native deployment or standalone Docker deployment.

- **Main RAG API:** Handles webhooks, LangChain workflows, and database routing.
- **Extraction Service:** A separate FastAPI container solely responsible for heavy CPU tasks (OCR, PDF/Docx layout parsing). This decoupling prevents memory spikes from crashing the main API.

Both services are fully containerized and include Kubernetes manifests with Horizontal Pod Autoscalers (HPA) and KEDA scaled objects for dynamic, load-based scaling.

---

## Security & Secrets

To prevent API keys and database passwords from being exposed in plaintext `.env` files, the pipeline includes a built-in **Symmetric Encryption** utility. 
- You can encrypt your sensitive fields using a master key (`ENC:gAAAAAB...`).
- The Python application seamlessly decrypts the secrets in memory dynamically during runtime.
- This allows you to safely commit your `.env` configuration files to source control while keeping secrets locked.

---

## The Pipeline Flow

### 1. Ingestion & Extraction (`ingestion.py`)
Triggered via an API webhook, the ingestion pipeline reads:
- All documents inside `input_documents/<project>/prd/`.
- Jira Tickets listed in `input_documents/<project>/jira/jira_id.txt`.

The Main API forwards these files to the **Extraction Service**, which utilizes deep-learning models to export clean Markdown.

### 2. Hierarchical Storage
- **Parent Chunks:** Large blocks of text (2000 tokens) stored in a relational **PostgreSQL** database.
- **Child Chunks:** Smaller blocks of text (400 tokens) mapped back to Parent Chunks, converted to vectors, and stored in **Qdrant**.

<img width="1537" height="765" alt="1000084252" src="https://github.com/user-attachments/assets/6399ebca-7d80-4e4f-a567-cfb1e3cee3aa" />

### 3. Two-Phase Chained Generation (`retrieval.py`)
To prevent hallucination while maximizing detail, the system uses a chained generation pipeline:
1. **Phase 1 — Test Plan + Test Cases (parallel):** Extracts ALL Parent Chunks from Postgres iteratively (100% coverage, bypassing vector loss) and generates both `test_plan.md` and `test_cases.csv` directly from raw requirements. Both run independently against the full source data so test cases retain maximum granularity (all steps, requirement mappings, edge cases).
2. **Phase 2 — Downstream Artifacts:** The LLM reads the generated Test Plan + Test Cases as its ground-truth context to produce the remaining 6 artifacts (Test Strategy, RTM, Risk Matrix, Test Data Matrix, Automation Recommendations, Estimation Report) without re-parsing the source documents.

#### Resume Mode (Recovery Mechanism)
If a generation run is interrupted or fails during Phase 2, you do not need to restart the entire process. The system automatically detects existing Phase 1 files (`test_cases.csv` and `test_plan.md`) in the latest version directory.
- It enables **Resume Mode**, skipping Phase 1 entirely.
- It loads the existing files as ground-truth context and resumes Phase 2 generation.
- It loops through the 6 downstream artifacts and checks if they exist on disk.
- It **skips** generating any artifact that already exists, and only generates the remaining/missing files.

#### In-Memory Context Compacting
To prevent downstream API timeouts due to massive context size (~500 KB / 125,000+ tokens), Phase 2 uses an intelligent, in-memory compaction strategy that *never* modifies the files stored on disk:
- **CSV Compacting:** Verbose columns (`Test Steps`, `Pre-Condition`, `Expected Result`, `Actual Result`, `Test Data`) are stripped from `test_cases.csv` for retrieval context, reducing size by up to 85%.
- **Markdown Compacting:** Repetitive boilerplate sections (e.g., duplicate structure from batched appends) are stripped from subsequent batches in `test_plan.md` context, keeping only unique tables and sections, reducing size by up to 66%.

#### CSV Output Hardening & Dynamic Repair
To ensure output artifacts load cleanly in tools like Excel or Jira without "column count mismatch" errors from LLM hallucinated commas/newlines:
- **Prompt Hardening**: Prompts explicitly instruct the LLM to follow RFC 4180 rules, enforcing strict double-quoting for complex cells.
- **Dynamic CSV Repair (`repair_csv_content`)**: The post-processor automatically scans for fragmented rows, uses anchor-based heuristics to identify the misaligned text boundaries, and re-merges broken "Test Steps" strings into a single column.
- **Locked File Fallback**: If the CSV file is locked by the OS (e.g., currently open in Excel), the pipeline handles the `PermissionError` safely by saving the repaired file as `[filename].csv.repaired`.

### 4. Adaptive Rate Limiter (`rate_limiter.py`)
All LLM calls are routed through an adaptive rate limiter that:
- Starts with a configurable inter-request delay (`GENERATION_BATCH_DELAY`, default 1s for free tiers).
- On HTTP 429 / rate-limit errors: doubles the delay (capped at 60s) and retries up to `LLM_MAX_RETRIES` times.
- On success: halves the delay back toward the baseline, so paid tiers quickly converge to near-zero wait.
- All pacing decisions are logged transparently to `logs/rag_pipeline.log`.

<img width="1149" height="465" alt="1000084254" src="https://github.com/user-attachments/assets/2b638487-4907-4801-8528-c16c986a29d8" />

<img width="1231" height="224" alt="1000084255" src="https://github.com/user-attachments/assets/6960aebb-a413-4ea0-bcf5-62a3346c01af" />

---

## Evaluation Framework (RAGAS)

The system includes a built-in evaluation framework powered by **RAGAS** to score the quality of retrieved contexts and generated answers. The evaluator lives in `scripts/evaluation.py` and is orchestrated by `init/main.py`.

### How It Works (Design)

1. **Input:** A CSV testset containing `question` and `ground_truth` columns.
2. **Retrieval:** For each question, the RAG pipeline (`RetrievalPipeline.retrieve_and_answer`) retrieves the top-k relevant chunks and generates an answer.
3. **Grading:** RAGAS evaluates **one question at a time** against four metrics. This deliberate one-at-a-time design avoids overwhelming the LLM provider with parallel requests that would trigger HTTP 429 rate-limit errors.
4. **Rate-Limit Throttle (`EVAL_DELAY_SECONDS`):** Between each single-question evaluation, the system sleeps for a configurable number of seconds (default **5**). Set the `EVAL_DELAY_SECONDS` environment variable to increase or decrease this delay depending on your LLM provider's rate limits.
5. **Resilient Fallbacks:** Each evaluation attempt cycles through multiple LLM wrapper strategies (wrapped → raw → no RunConfig) and retries (up to 15) before recording the row as `NaN`.
6. **Output:** Results are saved to `logs/ragas_results_<project_name>.csv` and summary averages are logged to the console.

### RAGAS Metrics

| Metric | What It Measures |
|---|---|
| **Faithfulness** | Is the answer grounded in the retrieved context? (hallucination detection) |
| **Answer Relevancy** | Is the answer actually relevant to the question asked? |
| **Context Precision** | Are the retrieved chunks relevant and ranked correctly? |
| **Context Recall** | Does the retrieved context cover the ground truth? |

All four metrics are also exported as live **Prometheus Gauges** (`rag_evaluation_*_score`) for Grafana dashboards.

### Testset: Questions & Ground Truths

The testset is a simple two-column CSV file:

- **`question`** — The evaluation question to ask the RAG pipeline.
- **`ground_truth`** — The expected/reference answer used by RAGAS to compute Context Recall and Context Precision. If omitted, these metrics will be empty.

```csv
question,ground_truth
"What is the system timeout?","The system timeout is 30 seconds."
"How are documents processed?","Through Docling/Unstructured and saved to Postgres/Qdrant."

<img width="1306" height="210" alt="1000084253" src="https://github.com/user-attachments/assets/a77be0e4-8f70-4340-b419-2726041a5ad1" />
```

### 1. Synthetic Evaluation (Default)
By default, triggering the `evaluate` action will prompt the LLM to generate a synthetic test dataset of questions and ground truths from your ingested document chunks (via `RagasEvaluator.generate_synthetic_dataset`), save it to `logs/testset_<project_name>.csv`, and then run evaluation against them. The system requires **RAGAS >= 0.2.0** and also maintains backward compatibility with 0.1.x APIs for the synthetic testset generator.

### 2. Manual Evaluation (Bypass LLM Generation)
If you encounter LLM API rate limits during synthetic dataset generation, you can provide a manual set of questions and expected answers instead.

- Create a CSV file named `manual_testset_<project_name>.csv` in the `logs/` directory (e.g., `logs/manual_testset_VDRC_phase2.csv`).
- The CSV **must** have a `question` column and an optional `ground_truth` column (see format above).
- Trigger the webhook as usual. The container will detect the manual CSV, bypass the synthetic generator, and proceed directly to grading your pipeline's responses.

---

## Observability & Metrics

The system exposes live, project-level metrics for full transparency:
- **Endpoint:** `GET /metrics`
- **Dashboard:** Grafana (pre-configured in Docker Compose)

**Tracked Metrics include:**
- `rag_ingestion_bytes_extracted_total`: Data throughput per project.
- `rag_ingestion_parent_chunks_total` & `child_chunks`: Database load.
- `rag_generation_tokens_approx`: Cost estimation for generated documents.
- `rag_evaluation_faithfulness_score`: Real-time RAGAS hallucination tracking.

---

## Prompt & Output Versioning

- **Prompts:** Add custom prompts to `prompts/vX/`. The system always uses the highest version folder.
- **Outputs:** Generated artifacts are saved to `output_documents/<project_name>/vX/`. The Docker Compose setup mounts this directory to your host so files persist across rebuilds.

---

## Unified Webhook API

The system provides a single webhook for CI/CD or n8n integration.

**Endpoint:** `POST /webhook/test-case-generation`
```json
{
  "action": "inject",
  "project_name": "MyProject"
}
```
**Actions:** `"inject"`, `"generate"`, `"evaluate"`

---

## Generation Speed Tuning

Set these in your `.env` file before starting the container:

| Variable | Default | Effect |
|---|---|---|
| `GENERATION_BATCH_SIZE` | `10` | Parent chunks per LLM call. Larger = fewer batches but bigger prompts. |
| `GENERATION_BATCH_DELAY` | `1.0` | Seconds between consecutive LLM calls. Set to `0` for paid tiers. |
| `LLM_REQUEST_TIMEOUT` | `120` | Seconds before a single LLM call times out. Increase for slow providers. |
| `LLM_MAX_RETRIES` | `5` | App-level retries on rate-limit/timeout errors. |

With 115 parent chunks and batch size 10, generation runs ~12 batches per document instead of 23 (at size 5).

### Recommended Settings by Provider

| Provider | `LLM_REQUEST_TIMEOUT` | `GENERATION_BATCH_DELAY` | `LLM_MAX_RETRIES` | Reason |
|---|---|---|---|---|
| **Mistral (free tier)** | `180` | `1.0` | `5` | Long responses often hit 120s; free tier throttles |
| **OpenAI / Anthropic (paid)** | `120` | `0` | `3` | Faster responses, higher rate limits |
| **Ollama (local)** | `300` | `0` | `2` | Local model latency depends on your hardware |

For full deployment and execution instructions, please see **[SETUP.md](SETUP.md)**.
