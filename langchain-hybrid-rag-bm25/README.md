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
- **Dependency Management:** `uv` (Ultra-fast Python package installer & resolver)
- **Document Extraction:** Dedicated Extraction Service (Docling + Unstructured OCR)
- **Databases:** PostgreSQL (2000-token Parent Chunks) + Qdrant (400-token Child Vectors)
- **AI/LLM Core:** LangChain with Universal LLM Support (Mistral, OpenAI, Anthropic, Ollama, VertexAI)
- **Observability:** Prometheus + Grafana (Full storage & scrape parity across Docker Compose & K8s Helm charts)

---

## Microservices & Scalability

This architecture is completely decoupled for Kubernetes (K8s) cloud-native deployment or standalone Docker deployment.

- **Main RAG API:** Handles webhooks, LangChain workflows, and database routing.
- **Extraction Service:** A separate FastAPI container solely responsible for heavy CPU tasks (OCR, PDF/Docx layout parsing). This decoupling prevents memory spikes from crashing the main API.

Both services are fully containerized and include Kubernetes Helm chart manifests (`deployment/k8s/chart`) with Horizontal Pod Autoscalers (HPA) and dynamic volume claims (`api-logs`, `api-outputs`, `api-inputs`).
For local bare-metal K8s deployments (WSL / Minikube / Docker Desktop), sample StorageClass and PersistentVolume definitions are provided in `deployment/k8s/sample-storage/`.

---

## Security & Secrets

To prevent API keys and database passwords from being exposed in plaintext `.env` files, the pipeline includes a built-in **Symmetric Encryption** utility. 
- You can encrypt your sensitive fields using a master key (`ENC:gAAAAAB...`).
- The Python application seamlessly decrypts the secrets in memory dynamically during runtime.
- This allows you to safely commit your `.env` configuration files to source control while keeping secrets locked.

## First-Time Setup & Customization Reference (`scripts/config.py`)

All system variables, database connections, AI model selections, and directory paths are governed by `scripts/config.py` and loaded dynamically from your root `.env` file.

### 1. Local Directory & Volume Paths (WSL & Windows Support)
- **Local Input Path (`INPUT_ROOT`)**: Defaults to `<project_root>/input_documents`. If developing on Windows Subsystem for Linux (WSL) with files stored on Windows drives (`/mnt/c/` or `/mnt/d/`), `config.py` automatically normalizes prefixes into native Windows drive paths (`C:\` / `D:\`) when executed on Windows.
- **Docker Compose Volumes**: In `deployment/standalone/docker-compose.yml`, host directories are mounted relatively (`../../logs:/app/logs`, `../../output_documents:/app/output_documents`). Ensure local directories exist prior to container launch.

### 2. Switching AI Models & Providers
You can swap LLM and Embedding models instantly via `.env` variables without altering source code:
- **Mistral AI (Default):** `LLM_PROVIDER=mistral`, `LLM_MODEL_NAME=mistral-large-latest`, `EMBEDDING_PROVIDER=mistral`, `EMBEDDING_MODEL=mistral-embed`, `EMBEDDING_DIMENSION=1024`
- **OpenAI:** `LLM_PROVIDER=openai`, `LLM_MODEL_NAME=gpt-4o`, `EMBEDDING_PROVIDER=openai`, `EMBEDDING_MODEL=text-embedding-3-large`, `EMBEDDING_DIMENSION=3072`
- **Anthropic Claude:** `LLM_PROVIDER=anthropic`, `LLM_MODEL_NAME=claude-3-5-sonnet-20241022`
- **Ollama (Local / Free):** `LLM_PROVIDER=ollama`, `LLM_MODEL_NAME=llama3.1`, `OLLAMA_BASE_URL=http://localhost:11434`, `EMBEDDING_PROVIDER=ollama`, `EMBEDDING_MODEL=mxbai-embed-large`

### 3. Chunking Granularity Hierarchy
1. **API Webhook Body:** Passing `parent_chunk_size` or `child_chunk_size` in POST JSON payloads overrides all defaults.
2. **Project Config:** `input_documents/<project_name>/config.yaml`.
3. **Global Defaults:** `.env` settings (`PARENT_CHUNK_SIZE=2000`, `CHILD_CHUNK_SIZE=400`).

*(See [SETUP.md](SETUP.md) Section 2 for the complete parameter reference table).*

---

## The Pipeline Flow

### 1. Ingestion & Extraction (`scripts/ingestion/pipeline.py`)
Triggered via an API webhook, the ingestion pipeline reads documents from the project's input directory structure:

#### Dynamic Input Folder Structure & `config.yaml`
> [!IMPORTANT]
> **Replacing `SampleProject` with Actual Webhook `project_name`**
> The repository ships with skeleton template directories under `input_documents/SampleProject/` and `eval_datasets/SampleProject/`. When running ingestion or triggering API webhooks for your real project, you **must replace `SampleProject` (or `<project_name>`) with your exact project name** matching the `"project_name"` sent in your API/webhook payload (or your `DEFAULT_PROJECT_NAME` in `.env`). For example, if your webhook triggers `"project_name": "BillingModule"`, create and place your input files under `input_documents/BillingModule/`.

Users can create any number of custom input folders under `input_documents/<project_name>/`. The ingestion pipeline dynamically pools and processes all documents inside folders listed in `config.yaml`:
```text
input_documents/
└── <project_name>/ (e.g. BillingModule or SampleProject)
    ├── prd/
    │   ├── architecture_spec.pdf
    │   └── system_requirements.docx
    ├── jira/
    │   └── jira_ids.txt
    ├── templates/
    │   └── custom_spec.md
    └── config.yaml (Dynamic folder pooling & extraction rules)
```

**Example `input_documents/<project_name>/config.yaml`:**
```yaml
- name: PRD
  folder: prd
  glob: "**/*.{pdf,docx,txt,md}"
  action: extract_to_md

- name: TMPL
  folder: templates
  glob: "**/*"
  action: pass_through

- name: JIRA
  folder: jira
  file: jira_ids.txt
  format: comma-separated list
  action: fetch_jira_then_md
```
*(Note: Token chunking sizes like `PARENT_CHUNK_SIZE=2000` and `CHILD_CHUNK_SIZE=400` are managed centrally in `scripts/config.py` and `.env`, or overridden via webhook payload parameters).*

#### SHA-256 Content Hashing Optimization
Before creating database versions or triggering document extraction, the pipeline computes a full **SHA-256 content hash** across all input files (`.last_ingested_hash`). If the hash exactly matches the previously ingested version, ingestion is skipped entirely, saving processing time and avoiding redundant vector/db rows. If any file changes or is added/removed, a new version is created (`is_latest = TRUE`).

The Main API forwards new files to the **Extraction Service**, which utilizes deep-learning models to export clean Markdown.

### 2. Hierarchical Storage & Strict Version Isolation
- **Parent Chunks:** Large blocks of text (2000 tokens) stored in a relational **PostgreSQL** database.
- **Child Chunks:** Smaller blocks of text (400 tokens) mapped back to Parent Chunks, converted to vectors, and stored in **Qdrant**.
- **Version Isolation:** Both PostgreSQL BM25 keyword queries and Qdrant dense vector search strictly filter by `version_id = latest_version_id`, ensuring downstream retrieval only queries the most up-to-date document version.

### 3. Hybrid Retrieval & Re-Ranking Engine (`scripts/retrieval/pipeline.py`)
To prevent hallucination while maximizing retrieval precision and recall, the system uses a state-of-the-art Hybrid RAG architecture:
1. **Dense Vector Search (Qdrant):** Retrieves Top 20 semantic candidate chunks using cosine similarity.
2. **Sparse Keyword Search (PostgreSQL Full-Text BM25):** Retrieves Top 20 exact keyword match chunks using `to_tsvector` and `ts_rank_cd`.
3. **Reciprocal Rank Fusion (RRF):** Merges dense and sparse candidates using reciprocal rank scoring ($k=60$) to identify the Top 20 hybrid candidates.
4. **Cross-Encoder Re-ranking (BGE):** Passes the 20 candidate chunks through a `sentence-transformers` CrossEncoder (`BAAI/bge-reranker-base`) to score pairs directly against the query, outputting the Top 5 highest-precision chunks to the LLM.

#### Standalone Image OCR via Docling
In addition to Word/PDF layouts, the pipeline directly ingests standalone architectural diagrams, UI mockups, and flowcharts (`.png`, `.jpg`, `.jpeg`), applying Docling OCR to convert visual data into searchable Markdown chunks.

#### Human-in-the-Loop Feedback & Loop Engineering
Every RAGAS evaluation run and generation output is logged to PostgreSQL (`evaluation_feedback` table). Reviewers can query pending reviews via `GET /feedback/pending/{project}` and promote or reject test cases and prompt versions via `POST /feedback/review`.

---

## Evaluation Framework (RAGAS)

The system includes a built-in evaluation framework powered by **RAGAS** to score the quality of retrieved contexts and generated answers. The evaluator lives in `scripts/evaluation/pipeline.py` and is orchestrated by `init/main.py`.

### How It Works (Adaptive Batching Design & Scaling)

1. **Input:** A CSV testset containing `question` and `ground_truth` columns.
2. **Retrieval:** For each question, the RAG pipeline (`RetrievalPipeline.retrieve_and_answer`) retrieves top-k relevant chunks from the **latest active version** (`is_latest = TRUE`) across Qdrant and PostgreSQL and generates an answer.
3. **Adaptive Batch Grading (`EVAL_BATCH_SIZE`):** By default, RAGAS evaluates questions in batches of **5** (configurable via `EVAL_BATCH_SIZE=5` in `.env`). When using high-throughput or paid LLM tiers (OpenAI, Claude, Mistral Tier 2+), increase `EVAL_BATCH_SIZE` (e.g. `20` or `50`) and decrease `EVAL_DELAY_SECONDS` (e.g. `0`) to drastically accelerate grading.
4. **Automatic Gradual Step-Down (429 Rate-Limit Protection):** If an API rate limit (`429` / `Too Many Requests`) is intercepted during batch grading, the evaluator does not drop straight to 1. Instead, it dynamically steps down the batch size by 1 (`5 -> 4 -> 3 -> 2 -> 1`), pauses for `EVAL_DELAY_SECONDS`, and loops until throughput stabilizes at your LLM tier's exact rate ceiling.
5. **Automatic Checkpointing & Cache Recovery:** During the retrieval phase, answers are cached to disk every 5 questions (`retrieval_cache_<project_name>.json`). If an evaluation run is interrupted or rate-limited, re-running the evaluation resumes immediately from cached answers without re-querying previous items.
6. **Versioned Output & Database Logging:** Evaluation results are automatically versioned and stored inside `eval_datasets/<project_name>/results/vX_ragas_results.csv` (with a copy maintained at `latest_ragas_results.csv`), recorded directly into the PostgreSQL `evaluation_feedback` table, and exported as live Prometheus Gauges (`rag_evaluation_*_score`).

### RAGAS Metrics

| Metric | What It Measures |
|---|---|
| **Faithfulness** | Is the answer grounded in the retrieved context? (hallucination detection) |
| **Answer Relevancy** | Is the answer actually relevant to the question asked? |
| **Context Precision** | Are the retrieved chunks relevant and ranked correctly? |
| **Context Recall** | Does the retrieved context cover the ground truth? |

All four metrics are also exported as live **Prometheus Gauges** (`rag_evaluation_*_score`) for Grafana dashboards. Persistent Docker volumes (`prometheus_data` and `grafana_data`) ensure that metric time series and custom dashboards persist across system restarts.

### Testset: Questions & Ground Truths

The testset is a simple two-column CSV file:

- **`question`** — The evaluation question to ask the RAG pipeline.
- **`ground_truth`** — The expected/reference answer used by RAGAS to compute Context Recall and Context Precision. If omitted, these metrics will be empty.

```csv
question,ground_truth
"What is the system timeout?","The system timeout is 30 seconds."
"How are documents processed?","Through Docling/Unstructured and saved to Postgres/Qdrant."
```

### Generating Evaluation Questions from Chunks

The system provides a dedicated script to generate 300-500 evaluation Q&A pairs from your ingested parent chunks. This script supports both automatic LLM generation and interactive manual mode.

**Script Location:** `scripts/evaluation/generate_300_qa.py`

**Features:**
- Randomly samples chunks to ensure broad coverage across all document types (pdf, docx, md, jpeg, png, etc.) including Jira
- Automatic rate-limit detection with exponential backoff retry (2s, 4s, 8s, 16s, 32s)
- Resume capability to continue from an existing CSV
- Auto-saves every 50 chunks to prevent data loss
- Deduplicates questions before final output

#### Auto Mode (LLM Generates All)

```bash
# Generate 300 questions (default)
uv run python -m scripts.evaluation.generate_300_qa <project_name> --mode auto

# Generate 500 questions with custom settings
uv run python -m scripts.evaluation.generate_300_qa <project_name> \
    --mode auto \
    --num-questions 500 \
    --pairs-per-chunk 3 \
    --delay 2.0

# Resume from existing CSV
uv run python -m scripts.evaluation.generate_300_qa <project_name> \
    --mode auto \
    --num-questions 500 \
    --resume
```

#### Manual Mode (Interactive)

```bash
# Start manual mode with 500 target questions
uv run python -m scripts.evaluation.generate_300_qa <project_name> \
    --mode manual \
    --num-questions 500
```

**Manual Mode Commands:**
- `[Enter]` — Type a question, then provide the ground truth answer
- `skip` — Skip to next random chunk
- `done` — Save and exit
- `status` — Show current progress
- `bulk N` — Generate N pairs from current chunk using LLM (then review/accept/pick)

**Output:** `eval_datasets/<project_name>/questions_ground_truth.csv`

### 1. Dedicated Evaluation Dataset (Highest Priority)
Our code checks for a dedicated evaluation dataset first! If you place your test questions and expected answers at:
`eval_datasets/<project_name>/questions_ground_truth.csv`
The evaluation pipeline will immediately load this file, bypass synthetic dataset generation entirely, and grade your pipeline against your exact benchmark questions.

### 2. Manual Testset Fallback
If no file exists in `eval_datasets/`, the system checks for `logs/manual_testset_<project_name>.csv`. If found, it bypasses synthetic generation and uses this CSV directly.

### 3. Synthetic Evaluation (Auto-Generated Default)
If neither dedicated nor manual CSV files exist, the system automatically prompts the LLM (`RagasEvaluator.generate_synthetic_dataset`) to generate synthetic test questions from your ingested document chunks, saves them to `logs/testset_<project_name>.csv`, and runs evaluation against them.

---

## Observability & Metrics

### 1. Prometheus Metrics & Grafana Integration
The API Orchestrator automatically tracks and exposes live Prometheus metrics at `GET /metrics` (scraped every 15s by Prometheus and visualized in Grafana):
- **Ingestion Metrics:** `rag_ingestion_documents_processed_total`, `rag_ingestion_bytes_extracted_total`, `rag_ingestion_parent_chunks_total`, `rag_ingestion_child_chunks_total`
- **Generation Metrics:** `rag_generation_documents_created_total`, `rag_generation_tokens_approx`
- **Token Utilization & Cost Metrics:** `rag_llm_prompt_tokens_total`, `rag_llm_completion_tokens_total`, `rag_llm_cost_usd_total`
- **Evaluation Metrics:** `rag_evaluation_questions_generated_total`, `rag_evaluation_faithfulness_score`, `rag_evaluation_answer_relevancy_score`, `rag_evaluation_context_precision_score`, `rag_evaluation_context_recall_score`

### 2. Comprehensive Action Logging
The pipeline outputs clear, structured logs at every step:
- **BM-25 Indexing:** Explicit log confirming when each Parent Chunk is indexed into PostgreSQL full-text `search_vector` (`to_tsvector`).
- **Hybrid Retrieval & RRF:** Logs showing exact candidate counts retrieved via dense vector search (Qdrant) and exact keyword search (Postgres BM-25), along with Reciprocal Rank Fusion (RRF `k=60`) score merging.
- **Generation Loop Engineering:** Banner outputting recommendations when test cases and plans finish generating.
- **Eval Optimization Loop Engineering:** Checkpoint outputting review recommendations upon completion of RAGAS grading runs.
- **Human Review Acceptance Logs:** Formal tracking log (`[Human Review Acceptance Logs]`) when human engineers submit feedback decisions (`APPROVED` or `REJECTED`).

---

## Prompt & Output Versioning & Checkpoint Resuming

### 1. Prompt Versioning & Guardrails (`prompts/vX/`)
- **Version Discovery:** Place your custom prompt templates inside `prompts/vX/` (e.g. `prompts/v1/`, `prompts/v2/`). The pipeline automatically scans the folder structure and loads templates from the highest numbered directory (`v2`).
- **Strict CSV Guardrails:** All CSV generation prompts (`test_cases.md`, `automation_recommendations.md`, `rtm.md`, `test_data_matrix.md`) enforce strict formatting guardrails to ensure zero syntax corruption:
  - **Single-Line Cell Rule:** LLMs are explicitly forbidden from outputting newlines (`\n`) inside cells. Multi-step workflows (like `Test Steps` or `Expected Result`) must use inline numbering separated by semicolons on a single line (`1. Open page; 2. Click submit`).
  - **RFC 4180 Quoting:** Delimiters and internal double quotes must be properly escaped (`"Verify ""Error"" modal"`).
  - **Exact Column Enforcement:** Every row must strictly match the required column count (`test_cases.csv` $\rightarrow$ 15 cols, `automation_recommendations.csv` $\rightarrow$ 6 cols, `rtm.csv` $\rightarrow$ 6 cols, `test_data_matrix.csv` $\rightarrow$ 7 cols).

### 2. Checkpoint & Smart Resume Architecture
The workflow features granular checkpointing across all execution phases so interruption never causes data loss:
1. **Ingestion Checkpoint (`SHA-256 Hashing`):** The ingestion engine hashes all files inside `input_documents/<project>/`. If files haven't changed since the last execution (`.last_ingested_hash`), ingestion skips automatically without creating redundant database records.
2. **Generation Folder Lifecycle & Checkpoints (`output_documents/<project>/vX`):**
   - **Empty Folder Reuse:** If `vX` contains no completed document files, running generation reuses `vX` without creating unnecessary version folders.
   - **Incomplete Run Checkpointing (Resume Mode):** If execution stops halfway through (e.g. Phase 1 completed, but only 2 out of 6 Phase 2 downstream documents were generated before an interruption or restart), the system detects the existing files, logs `[Checkpoint] Execution stopped in middle of previous run... Resuming workflow from last completed checkpoint`, skips generating existing files, and completes only the missing artifacts.
   - **Completed Run Re-Generation:** If all 8 documents exist in `vX` (Phase 1 + Phase 2 completed), triggering generation creates a brand new version folder (`vX+1`) for a clean, fresh re-generation run.
3. **Evaluation Checkpoint (`retrieval_cache_<project>.json`):** During RAGAS grading, generated answers are cached to disk every 5 items. If evaluation is interrupted or rate-limited (`429`), re-running evaluation resumes immediately from disk cache.

---

## Database Schemas & Persistent Volumes

### 1. What Data the Database Tables Hold
The system utilizes two persistent database engines:
- **PostgreSQL (`parent_chunks` Table):** Stores primary document blocks (up to 2000 tokens), file metadata, SHA-256 hashes, and precomputed `search_vector` (`to_tsvector`) indices for exact keyword BM25 full-text search.
- **PostgreSQL (`evaluation_feedback` Table):** Stores RAGAS benchmark scores (`faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`) and human review workflow states (`PENDING`, `APPROVED`, `REJECTED`) along with reviewer notes.
- **Qdrant (`child_chunks` Collection):** Stores dense vector embeddings (1024 dimensions for Mistral, 3072 for OpenAI) of smaller 400-token child chunks mapped directly back to their PostgreSQL parent chunk IDs.

### 2. How Persistent Volumes Are Setup
Whether deployed on Docker Compose or Kubernetes, all storage volumes ensure permanent persistence:
- **Docker Compose Volumes (`docker-compose.yml`):** Mounted relatively to the host filesystem:
  - `../../output_documents:/app/output_documents` (generated test plans & cases)
  - `../../logs:/app/logs` (execution and audit logs)
  - `../../eval_datasets:/app/eval_datasets` (RAGAS evaluation Q&A pairs)
  - `../../prompts:/app/prompts` (versioned prompt templates)
- **Kubernetes PVCs (`deployment/k8s/chart`):** Managed via dynamic storage claims (`api-outputs`, `api-logs`, `api-inputs`). On bare-metal or local clusters (WSL/Minikube), sample `manual-local` StorageClass definitions map PVCs directly to local storage disks (`deployment/k8s/sample-storage/`).

---

## Unified Webhook API

The system provides a single webhook for CI/CD or n8n integration that dynamically routes project pipelines and configures chunking parameters on the fly.

**Endpoint:** `POST /webhook/test-case-generation`
```json
{
  "action": "inject",
  "project_name": "MyProject",
  "parent_chunk_size": 2000,
  "parent_chunk_overlap": 200,
  "child_chunk_size": 400,
  "child_chunk_overlap": 50
}
```
**Actions:** `"inject"`, `"generate"`, `"evaluate"`, `"review"`

You can also trigger dedicated Loop Engineering human review & approval via:
**Endpoint:** `POST /webhook/human-review`
*(Note: Loop Engineering & Evaluation Review recommendations are automatically logged at the completion of both document generation and RAGAS benchmark evaluation).*

You can also specify per-project chunking sizes inside `input_documents/<project_name>/config.yaml`.

---

## Maintenance Scripts & Per-Action Logs

- **Per-Action Iteration Logs:** Stored in `logs/` (`ingestion.log`, `generation.log`, `evals.log`, `human_loop_reviews.log`). Old logs are automatically truncated/cleared before each iteration run.
- **Unified OS-Aware Cleanup (`scripts/` and `scripts/cleanup/`):**
  - **Linux / macOS:** `./scripts/cleanup.sh [flags]` (or `./scripts/cleanup/cleanup.sh`)
  - **Windows PowerShell:** `.\scripts\cleanup.ps1 [flags]` (or `.\scripts\cleanup\cleanup.ps1`)
  - **Direct Python:** `uv run python scripts/cleanup/cleanup.py [flags]`
  - *Flags:* `--system` (clean cache/Docker), `--db [ProjectName|--all]` (purge database records), `--all` (clean both).
- **Database Connection Resilience:** The PostgreSQL database engine (`PostgresDB`) features automatic connection health checks (`ensure_connection()`), automatically reconnecting dropped database sockets during long-running embedding loops.

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
