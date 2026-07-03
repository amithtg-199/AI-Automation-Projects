# Setup & Deployment Guide

This document covers how to install, configure, and scale the QA Test Case Generation RAG pipeline.

## 1. Project Initialization & Dependency Management

We use **uv** for ultra-fast package installation and dependency resolution using standard PEP 621 `[project]` tables.

### Installing `uv` (First-Time Requirement)
Before running local commands, install `uv` on your operating system:

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
**Or via Python `pip` (Any OS):**
```bash
pip install uv
```

### Initializing the Project
Once `uv` is installed, set up the project dependencies:
```bash
# 1. Create virtual environment and install dependencies natively
uv sync

# Or install dependencies into system/active environment:
uv pip install -r requirements.txt

# 2. Activate virtual environment
# Windows PowerShell:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

---

## 2. Comprehensive First-Time Setup & Configuration (`scripts/config.py`)

All core system configurations are centralized in `scripts/config.py`. The system automatically loads your `.env` file at the root directory and provides fallback defaults if variables are omitted.

### Configurable Project Name (`DEFAULT_PROJECT_NAME`) & Webhook Overrides
The platform never relies on hardcoded project names. You can configure your project dynamically at initialization or during runtime:
1. **Default Environment Configuration (`.env`)**:
   Define `DEFAULT_PROJECT_NAME` in your `.env` file to set the default project name across all evaluation and generation CLI scripts:
   ```env
   DEFAULT_PROJECT_NAME=MyProject
   ```
2. **Dynamic Webhook Trigger Override**:
   Whenever a webhook is triggered (`/webhook/test-case-generation`, `/webhook/human-review`, etc.), any `project_name` sent inside the JSON payload takes absolute precedence over the config default:
   ```json
   {"action": "generate", "project_name": "CustomClientProject"}
   ```
   If omitted from the webhook payload or CLI parameters, scripts automatically reference `DEFAULT_PROJECT_NAME` from `scripts/config.py`.

### A. First-Time Folder & Path Setup (WSL, Windows & Docker Volumes)
When setting up for the first time across different operating systems (Windows, WSL, Linux, macOS), proper path handling is critical:

1. **Local Input Directory (`INPUT_ROOT`)**:
   - By default, the pipeline reads input documents from `<project_root>/input_documents`.
   - If you are developing inside **Windows Subsystem for Linux (WSL)** but storing files on a Windows drive (e.g., `/mnt/d/Projects/...`), `scripts/config.py` automatically detects `/mnt/d/` or `/mnt/c/` prefixes and normalizes them into standard Windows paths (`D:\Projects\...`) when running Python natively on Windows.
   - To use a custom local directory, set `INPUT_ROOT` in your `.env`:
     ```env
     INPUT_ROOT=D:\MyCompany\Automation\test-documents
     ```

2. **Docker Compose Volume Mounts (`docker-compose.yml`)**:
   - When deploying via Docker Compose (`deployment/standalone/docker-compose.yml`), containerized services mount local folders into `/app/...`.
   - Ensure the relative volume paths match your host structure:
     ```yaml
     volumes:
       - ../../scripts:/app/scripts
       - ../../init:/app/init
       - ../../logs:/app/logs
       - ../../output_documents:/app/output_documents
       - ../../input_documents:/app/input_documents
       - ../../eval_datasets:/app/eval_datasets
     ```

---

### B. AI Model & Embedding Provider Configuration
You can switch AI models and embedding providers anytime via `.env` without modifying Python code. `llm_factory.py` dynamically initializes models based on `LLM_PROVIDER` and `EMBEDDING_PROVIDER`.

#### 1. Using Mistral AI (Default)
```env
LLM_PROVIDER=mistral
LLM_MODEL_NAME=mistral-large-latest
LLM_API_KEY=your_mistral_api_key
EMBEDDING_PROVIDER=mistral
EMBEDDING_MODEL=mistral-embed
EMBEDDING_DIMENSION=1024
```

#### 2. Switching to OpenAI (`gpt-4o` & `text-embedding-3-large`)
```env
LLM_PROVIDER=openai
LLM_MODEL_NAME=gpt-4o
LLM_API_KEY=sk-your_openai_api_key
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=3072
```

#### 3. Switching to Anthropic Claude (with OpenAI Embeddings)
```env
LLM_PROVIDER=anthropic
LLM_MODEL_NAME=claude-3-5-sonnet-20241022
LLM_API_KEY=sk-ant-your_anthropic_api_key
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

#### 4. Using Local Open-Source Models via Ollama (100% Offline / Free)
```env
LLM_PROVIDER=ollama
LLM_MODEL_NAME=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=mxbai-embed-large
EMBEDDING_DIMENSION=1024
```

---

### C. Chunking & Segmentation Granularity
The system uses a 3-tier hierarchy to resolve token chunking sizes:
1. **Webhook Payload Override:** Passing `parent_chunk_size` or `child_chunk_size` in the JSON body of `/webhook/test-case-generation` takes highest precedence.
2. **Project-Level YAML Chunking Block (Optional):** Specifying a `chunking:` dictionary block inside `input_documents/<project_name>/config.yaml` (Note: `config.yaml` is primarily used by users to list any number of custom input folders to be pooled and processed by the ingestion flow).
3. **Global Defaults (`.env` / `config.py`):**
   ```env
   PARENT_CHUNK_SIZE=2000
   PARENT_CHUNK_OVERLAP=200
   CHILD_CHUNK_SIZE=400
   CHILD_CHUNK_OVERLAP=50
   ```

---

### D. Complete `config.py` Parameter Reference Table

| Parameter Category | Environment Variable | Default Value | Description |
|---|---|---|---|
| **PostgreSQL** | `POSTGRES_HOST`<br>`POSTGRES_PORT`<br>`POSTGRES_USER`<br>`POSTGRES_PASSWORD`<br>`POSTGRES_DB` | `localhost`<br>`5432`<br>`qa_user`<br>`AAbb12#$%`<br>`qa_rag` | Relational database connection string parameters for parent chunk storage and evaluation logs. |
| **Qdrant Vector DB** | `QDRANT_HOST`<br>`QDRANT_PORT` | `localhost`<br>`6333` | Vector engine parameters for child chunk embeddings. |
| **Extraction Service** | `EXTRACTION_SERVICE_URL` | `http://localhost:8000` | Endpoint for the dedicated Docling/Unstructured layout OCR parsing container. |
| **LLM Configuration** | `LLM_PROVIDER`<br>`LLM_MODEL_NAME`<br>`LLM_API_KEY`<br>`OLLAMA_BASE_URL` | `mistral`<br>`mistral-large-latest`<br>`""`<br>`http://localhost:11434` | Universal LLM routing and authentication credentials. Supports `mistral`, `openai`, `anthropic`, `ollama`, `vertexai`. |
| **Embedding Config** | `EMBEDDING_PROVIDER`<br>`EMBEDDING_MODEL`<br>`EMBEDDING_API_KEY`<br>`EMBEDDING_DIMENSION` | `mistral`<br>`mistral-embed`<br>`""`<br>`1024` | Embedding engine routing and vector dimension matching Qdrant collection size. |
| **Chunking Hierarchy** | `PARENT_CHUNK_SIZE`<br>`PARENT_CHUNK_OVERLAP`<br>`CHILD_CHUNK_SIZE`<br>`CHILD_CHUNK_OVERLAP` | `2000`<br>`200`<br>`400`<br>`50` | Hierarchical chunk token budgets and sliding window overlaps. |
| **Rate Limits & Evals** | `GENERATION_BATCH_SIZE`<br>`GENERATION_BATCH_DELAY`<br>`LLM_MAX_RETRIES`<br>`LLM_REQUEST_TIMEOUT`<br>`EVAL_BATCH_SIZE`<br>`EVAL_DELAY_SECONDS` | `10`<br>`1.0`<br>`5`<br>`120`<br>`5`<br>`5` | Generation API throughput pacing and adaptive RAGAS evaluation batching settings. |
| **Storage Folders** | `INPUT_ROOT` | `<project_root>/input_documents` | Base directory containing project document input folders (`prd/`, `jira/`, `config.yaml`). |

---

### E. Prompt Versioning & CSV Formatting Guardrails (`prompts/vX/`)
All prompt templates used for generating test documentation live in versioned directories under `prompts/vX/` (e.g. `prompts/v1/`, `prompts/v2/`).
1. **Dynamic Version Selection:** When generation (`action=generate`) is triggered, the pipeline scans `prompts/` and selects templates from the highest integer version folder (`prompts/v2`).
2. **Strict CSV Data Quality & Quoting Rules:** To prevent LLMs from corrupting tabular data, all CSV prompt templates (`test_cases.md`, `automation_recommendations.md`, `rtm.md`, `test_data_matrix.md`) enforce explicit data formatting rules:
   - **Single-Line Cell Rule:** LLMs are strictly instructed never to insert newlines (`\n`) inside any CSV cell. Multi-step workflows (like `Test Steps` or `Expected Result`) must use inline numbering separated by semicolons on a single line (`1. Open login page; 2. Enter credentials; 3. Click submit`).
   - **RFC 4180 Compliance:** Any cell containing commas, semicolons, or quotes must be wrapped in double quotes. Internal quotes must be escaped by doubling (`""`).
   - **Exact Column Enforcement:** Every generated row must strictly contain the exact number of columns defined for that document type (`test_cases.csv` $\rightarrow$ 15 columns, `automation_recommendations.csv` $\rightarrow$ 6 columns, `rtm.csv` $\rightarrow$ 6 columns, `test_data_matrix.csv` $\rightarrow$ 7 columns).

---

### F. Checkpoint & Smart Resume Architecture across Workflows
Every operational workflow (`inject`, `generate`, `evaluate`) implements robust checkpointing to ensure zero data loss during interruptions or container restarts:

#### 1. Ingestion Checkpointing (`SHA-256 Hashing`)
When `action=inject` runs, the ingestion service computes a global SHA-256 content hash across all files in `input_documents/<project>/`. If the calculated hash exactly matches the previously ingested version stored in `.last_ingested_hash`, document extraction and vector indexing are skipped automatically, preventing duplicate database records.

#### 2. Generation Checkpointing & Version Folder Lifecycle (`output_documents/<project>/vX`)
When `action=generate` runs, the generation pipeline inspects the latest active version folder (`vX`):
- **Rule 1 (Empty Folder Reuse):** If `vX` contains no completed document files (> 0 bytes), the pipeline reuses `vX` without creating redundant empty folders.
- **Rule 2 (Incomplete Run Checkpoint Resume):** If execution stopped halfway through a previous run (e.g. Phase 1 completed, but only 2 out of 6 Phase 2 downstream documents were written before a crash or timeout), the system detects the existing files, activates **Resume Mode**, logs:
  `[Checkpoint] Execution stopped in middle of previous run in ... Resuming generation workflow from last completed checkpoint.`
  It skips regenerating existing files and resumes execution exactly where it stopped.
- **Rule 3 (Completed Run Re-Generation):** If all 8 documents exist in `vX` (Phase 1 + Phase 2 completed), triggering generation creates a brand new version folder (`vX+1`) and starts a clean, fresh generation cycle.

#### 3. Evaluation Checkpointing (`retrieval_cache_<project>.json`)
During RAGAS benchmark grading (`action=evaluate`), generated answers are cached to disk every 5 questions. If an evaluation run is interrupted or rate-limited (`HTTP 429`), re-running evaluation loads answers from disk cache instantly without spending redundant LLM tokens.

---

## 3. Deployment Strategies

### Securing Secrets (Optional)
If you don't want plaintext passwords (like `POSTGRES_PASSWORD` or `LLM_API_KEY`) lying around in your `.env` or `values.yaml` files, you can use the built-in symmetric encryption utility.

1. **Generate a Master Key**:
   ```bash
   uv run python scripts/encrypt_secrets.py
   ```
   Select Option `1`. Save the generated `MASTER_KEY` securely.

2. **Encrypt your Passwords**:
   Run the script again and select Option `2`. Provide your `MASTER_KEY` and your plaintext secret. It will return a string like `ENC:gAAAAAB...`.

3. **Update your `.env`**:
   Replace plaintext values in `.env` with the encrypted strings:
   ```env
   POSTGRES_PASSWORD=ENC:gAAAAAB...
   ```

4. **Inject the Master Key**:
   When launching Docker or Helm, pass the master key in the environment:
   ```bash
   # For Docker Compose
   MASTER_KEY="your-master-key" docker-compose up -d
   ```

5. **Deploying to Other Environments (Production/Staging)**:
   Because the `.env` file contains only `ENC:...` strings, it is **100% safe to commit to Git**. When you deploy to other environments:
   - **CI/CD Pipelines (GitHub Actions / Jenkins):** Add the raw `MASTER_KEY` as a protected pipeline Secret. Pass it as an environment variable when building/deploying.
   - **Kubernetes (Helm):** Do not commit the `masterKey` to `values.yaml`. Instead, inject it dynamically during deployment:
     ```bash
     helm install qa-rag-api ./deployment/k8s/chart \
       --set secrets.masterKey="your-master-key"
     ```
   - **Cloud Services (AWS ECS / Azure App Service):** Paste the `MASTER_KEY` into the native Environment Variables configuration panel in your cloud provider's console. The Python container will detect it and decrypt the embedded `.env` values automatically.

### Option A: Standalone Docker Deployment (Recommended for VMs/Local)

The easiest way to launch the entire stack (Main API, Extraction Service, Postgres, Qdrant, Prometheus, Grafana, and optionally Ollama).

1. Navigate to the deployment directory:
   ```bash
   cd deployment/standalone
   ```
2. Start the stack:
   ```bash
   docker-compose up -d
   ```
3. Verify Services:
   - Main API: `http://localhost:5679/docs`
   - Extraction Service: `http://localhost:8000/docs`
   - Grafana Metrics: `http://localhost:3000` (User: `admin`, Pass: `admin`)

> **Volume Mounts:** The Docker Compose setup mounts two host directories:
> - `logs/` → Container logs persist at `langchain_test-gen-docs/logs/`
> - `output_documents/` → Generated artifacts persist at `langchain_test-gen-docs/output_documents/<project>/vX/`

*(Note: If you want to run Ollama inside docker, run `docker-compose --profile local-llm up -d`).*

### Option B: Local Development (`uv`)

If you are a developer testing or debugging Python pipelines directly:

1. **Install `uv` (if not installed yet):**
   - Windows PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - Or via pip: `pip install uv`
2. **Install project dependencies into virtual environment:**
   ```bash
   uv sync
   source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\activate
   ```
3. **Start the Main API server:**
   ```bash
   uv run python init/main.py
   ```
*(Note: You will still need Postgres and Qdrant running somewhere, either locally or via a partial `docker compose up -d postgres qdrant`).*

---

### Option C: Kubernetes Scalable Deployment (Helm / EKS / AKS / Local Bare-Metal)

For production or scalable container orchestration, deploy using our packaged Helm chart (`deployment/k8s/chart`).

#### 1. Understanding Chart Structure (`crds/`, `files/`, `templates/`)
- **`crds/` (Custom Resource Definitions):** In Helm conventions, any YAML files placed in `crds/` are installed before anything else. If you use third-party Kubernetes operators (like KEDA ScaledObjects or Prometheus ServiceMonitors), their CRDs go here. For standard Kubernetes deployments, this directory remains empty.
- **`files/` (Static Configuration Files):** Holds raw non-YAML files. In our chart, `files/schema.sql` contains the PostgreSQL initialization script. `templates/configmap.yaml` reads this file using `{{ .Files.Get "files/schema.sql" }}` so that Postgres initializes tables on startup automatically.
- **`templates/` (Kubernetes Manifests):** Contains dynamic templates (`api.yaml`, `postgres.yaml`, `qdrant.yaml`, `monitoring.yaml`, `configmap.yaml`, `secret.yaml`). These templates substitute parameters defined in `values.yaml`.

#### 2. Configuring Folder & File Paths (`templates/` & `values.yaml`)
Inside `templates/api.yaml`, container storage paths are mapped to Kubernetes volume claims via `volumeMounts`:
```yaml
volumeMounts:
  - name: api-logs
    mountPath: /app/logs
  - name: api-outputs
    mountPath: /app/output_documents
  - name: api-inputs
    mountPath: /app/input_documents
```
You configure the sizing and storage class of these volumes directly in `values.yaml` under `persistence`:
```yaml
persistence:
  storageClass: ""        # Storage class name (e.g. gp2, managed-csi, or manual-local)
  postgresSize: "10Gi"
  qdrantSize: "10Gi"
  apiLogsSize: "5Gi"
  apiOutputsSize: "10Gi"
  apiInputsSize: "10Gi"
```

#### 3. Configuring Storage Classes & Persistent Volumes (PVs)
When deploying PersistentVolumeClaims (PVCs), Kubernetes requires a volume provisioner:

- **Cloud Providers (AWS EKS, Azure AKS, Google GKE):**
  Cloud clusters come with dynamic provisioners. Leaving `storageClass: ""` (or setting `storageClass: "gp2"`) in `values.yaml` prompts the cloud provider to automatically create and attach physical disks. No manual PersistentVolume (PV) files are needed!

- **Local / Bare-Metal Clusters (WSL, Minikube, Docker Desktop, k3s):**
  On local bare-metal clusters without cloud disk provisioners, PVCs will stay in a `Pending` state unless you define a local StorageClass and PersistentVolumes.
  We have provided sample configurations in `deployment/k8s/sample-storage/`:
  1. **Apply the Sample StorageClass & PVs:**
     ```bash
     kubectl apply -f deployment/k8s/sample-storage/local-storage-class.yaml
     kubectl apply -f deployment/k8s/sample-storage/sample-pvs.yaml
     ```
     *(This creates `manual-local` storage mapping `/mnt/k8s-storage/...` host paths to Kubernetes volumes).*
  2. **Set StorageClass in `values.yaml`:**
     Update `values.yaml`:
     ```yaml
     persistence:
       storageClass: "manual-local"
     ```

#### 4. Initializing & Installing the Project on K8s
1. **Build and push your container images** to your container registry (or load them locally into minikube/kind):
   ```bash
   docker build -t your-registry.com/qa_rag_api:latest .
   docker build -t your-registry.com/qa_rag_extraction:latest ./extraction-service
   docker push your-registry.com/qa_rag_api:latest
   docker push your-registry.com/qa_rag_extraction:latest
   ```
2. **Lint the Helm chart** to verify template syntax:
   ```bash
   helm lint deployment/k8s/chart
   ```
3. **Install or Upgrade the release:**
   ```bash
   helm upgrade --install qa-rag-pipeline deployment/k8s/chart --namespace qa-rag --create-namespace
   ```
4. **Verify running Pods and Volumes:**
   ```bash
   kubectl get pods -n qa-rag
   kubectl get pvc -n qa-rag
   kubectl get svc -n qa-rag
   ```

---

## 4. Project Document Inputs & Custom Rules

To parse a project, place your documents in the root `input_documents/<project_name>/` folder.

You can explicitly control extraction behavior by creating a `config.yaml` file inside your project folder:
```yaml
- name: PRD
  folder: prd
  action: extract_to_md

- name: JIRA
  folder: jira
  action: fetch_jira_then_md
```

If no `config.yaml` is provided, the tool defaults to reading `/prd/` for documents and `/jira/jira_id.txt` for Jira IDs.

---

## 5. Triggering the Workflow

The system operates entirely via asynchronous webhooks. You can trigger it via cURL, Postman, or n8n.

**Base URL:** `http://localhost:5679/webhook/test-case-generation`
*(If using K8s, use your LoadBalancer/Ingress IP).*

### Step 1: Ingestion
Injects data from your `input_documents` to Qdrant/Postgres.
```bash
curl -X POST http://localhost:5679/webhook/test-case-generation \
     -H "Content-Type: application/json" \
     -d '{"action": "inject", "project_name": "MyProject"}'
```

### Step 2: Generation
Triggers the two-phase LLM generation pipeline:
- **Phase 1:** Test Plan + Test Cases (both from raw ingested data, parallel)
- **Phase 2:** 6 downstream artifacts (from generated Test Plan + Test Cases)

Output files are saved to `output_documents/MyProject/vX/` (mounted to host).
```bash
curl -X POST http://localhost:5679/webhook/test-case-generation \
     -H "Content-Type: application/json" \
     -d '{"action": "generate", "project_name": "MyProject"}'
```

#### Resume Mode & Fault Tolerance
If a run is interrupted or fails during Phase 2, you do not need to delete anything or restart from scratch. 
Simply re-run the same `generate` webhook. The pipeline will:
1. Detect that Phase 1 files (`test_cases.csv` and `test_plan.md`) already exist in the latest version directory (`vX`).
2. Automatically enable **Resume Mode** and bypass Phase 1 generation entirely.
3. For Phase 2, verify which of the 6 downstream artifacts already exist on disk.
4. **Skip** generating any existing files (e.g. `test_strategy.md`, `rtm.csv`), and only generate the missing ones.
5. Once all missing files are generated, the run will successfully conclude.

This design is fully robust against transient API errors, docker restarts, or rate limits.

#### CSV Auto-Repair & Locked Files
During CSV generation, the pipeline employs a robust auto-repair algorithm to automatically fix common LLM formatting errors like "column count mismatches". 
- If you have an output CSV file actively open in Excel while the pipeline is attempting to run, Excel will lock the file. 
- The pipeline will gracefully catch this `PermissionError`, wait briefly, and if still locked, will save the fixed content to a `.repaired` file (e.g., `test_cases.csv.repaired`) to ensure zero data loss.


### Step 3: Evaluation (Optional)
Uses RAGAS to grade the hallucination levels and retrieval accuracy of the pipeline.

#### How Evaluation Executes
1. The webhook triggers `run_evaluation()` in `init/main.py`.
2. The system checks for your dedicated benchmark file at `eval_datasets/<project_name>/questions_ground_truth.csv`. If found, it skips synthetic generation and evaluates your pipeline against this benchmark immediately.
3. If not found, it checks for `logs/manual_testset_<project_name>.csv`. If found, it uses this fallback manual file.
4. If neither file exists, `RagasEvaluator.generate_synthetic_dataset()` uses the LLM to auto-generate questions and ground truths from your ingested parent chunks, saving them to `logs/testset_<project_name>.csv`.
5. For each question in the testset, the RAG retrieval pipeline fetches the top-5 chunks and generates an answer.
6. RAGAS then grades **one question at a time** against four metrics: Faithfulness, Answer Relevancy, Context Precision, and Context Recall.
7. Between each evaluation, the system sleeps for `EVAL_DELAY_SECONDS` (default `5`) to avoid 429 rate-limit errors from the LLM provider.
8. Final results (per-question scores + averages) are saved to `logs/ragas_results_<project_name>.csv`.

#### Setting Questions & Ground Truths (Dedicated Benchmark Dataset)

To provide your own evaluation questions, create a CSV file at:
```
eval_datasets/<project_name>/questions_ground_truth.csv
```

The CSV requires a `question` column and an optional `ground_truth` column:
```csv
question,ground_truth
"What is the system timeout?","The system timeout is 30 seconds."
"How are documents processed?","Through Docling/Unstructured and saved to Postgres/Qdrant."
```

- **`question`** — The query to evaluate against your RAG pipeline.
- **`ground_truth`** — The expected/reference answer. RAGAS uses this to compute Context Recall and Context Precision. If left empty, those two metrics will return `NaN`.

#### Generating Evaluation Questions from Chunks

The system provides a dedicated script to generate 300-500 evaluation Q&A pairs from your ingested parent chunks. This script supports both automatic LLM generation and interactive manual mode.

**Script Location:** `scripts/evaluation/generate_300_qa.py`

**Features:**
- Randomly samples chunks to ensure broad coverage across all document types (pdf, docx, md, jpeg, png, etc.) including Jira
- Automatic rate-limit detection with exponential backoff retry (2s, 4s, 8s, 16s, 32s)
- Resume capability to continue from an existing CSV
- Auto-saves every 50 chunks to prevent data loss
- Deduplicates questions before final output

##### Auto Mode (LLM Generates All)

Let the LLM automatically generate Q&A pairs from random chunks:

```bash
# Generate 300 questions (default)
uv run python -m scripts.evaluation.generate_300_qa <project_name> --mode auto

# Generate 500 questions with custom settings
uv run python -m scripts.evaluation.generate_300_qa <project_name> \
    --mode auto \
    --num-questions 500 \
    --pairs-per-chunk 3 \
    --delay 2.0

# Resume from existing CSV (continues until target is reached)
uv run python -m scripts.evaluation.generate_300_qa <project_name> \
    --mode auto \
    --num-questions 500 \
    --resume
```

**Auto Mode Arguments:**
- `--mode auto` — LLM generates all Q&A pairs automatically
- `--num-questions` — Target number of Q&A pairs (default: 300, range: 300-500)
- `--pairs-per-chunk` — Q&A pairs to generate per chunk (default: 3)
- `--delay` — Seconds between LLM calls for rate limiting (default: 2.0)
- `--resume` — Continue from existing CSV instead of overwriting

##### Manual Mode (Interactive)

For manual control over question quality, use interactive mode:

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

**Example Manual Session:**
```
MANUAL Q&A GENERATION MODE
 Target: 500 pairs | Current: 0 pairs
 Total available chunks: 210

Commands:
  [Enter]     - Submit question & answer for this chunk
  'skip'      - Skip to next random chunk
  'done'      - Save and exit
  'status'    - Show current progress
  'bulk N'    - Generate N pairs from current chunk using LLM

CHUNK #1 | Source: HLD_V4.6.docx
  [chunk content preview...]
Progress: 0/500 pairs

Enter command (or type question): What is the authentication timeout?
Ground truth answer: The system timeout is 30 seconds.
  Added! Total: 1/500
  Add another for this chunk? (y/n): n
```

##### Output Location

Generated Q&A pairs are saved to:
```
eval_datasets/<project_name>/questions_ground_truth.csv
```

This is the same file used by the evaluation webhook (`action: "evaluate"`). Once generated, you can trigger evaluation to grade your RAG pipeline against these questions.

#### Controlling Rate-Limit Delay (`EVAL_DELAY_SECONDS`)

The `EVAL_DELAY_SECONDS` environment variable controls the pause (in seconds) between each individual RAGAS evaluation call. This exists because RAGAS makes multiple LLM calls per question (one per metric), and cloud LLM providers often enforce rate limits.

| Provider | Recommended Value |
|---|---|
| Mistral / OpenAI (free tier) | `10` – `15` |
| OpenAI (paid tier) | `3` – `5` |
| Ollama (local) | `0` |

Set it in your `.env` file or export it before launching:
```bash
export EVAL_DELAY_SECONDS=10
```

#### Option 1: Synthetic Dataset (Default)
Generates questions using the LLM automatically.
```bash
curl -X POST http://localhost:5679/webhook/test-case-generation \
     -H "Content-Type: application/json" \
     -d '{"action": "evaluate", "project_name": "MyProject"}'
```

#### Option 2: Dedicated Benchmark Dataset (Highest Priority)
To bypass automatic question generation and evaluate against exact benchmark questions:
1. Create the file `eval_datasets/MyProject/questions_ground_truth.csv` with your questions and ground truths.
2. Trigger the webhook action `"evaluate"` as normal.
3. The RAG pipeline will detect this CSV first, skip synthetic generation, retrieve chunks for each question, and grade your pipeline's output.

#### Interpreting Results

After evaluation completes, open `logs/ragas_results_<project_name>.csv`. Each row contains:

| Column | Description |
|---|---|
| `question` | The evaluation question |
| `answer` | The RAG pipeline's generated answer |
| `contexts` | The retrieved chunks used as context |
| `ground_truth` | The reference answer from the testset |
| `faithfulness` | Score 0–1 (higher = less hallucination) |
| `answer_relevancy` | Score 0–1 (higher = more relevant answer) |
| `context_precision` | Score 0–1 (higher = better ranked retrieval) |
| `context_recall` | Score 0–1 (higher = better coverage of ground truth) |

The console log also prints per-metric averages at the end of the run.

---

## 6. End-to-End Execution & Human-in-the-Loop Guide

Here is the exact workflow for initializing the environment, structuring input folders, triggering ingestion/retrieval/evaluations, and conducting human review:

### Step 1: Initialize Project & Start Services
```bash
# 1. Install dependencies natively using uv
uv sync
# Activate virtual environment
source .venv/bin/activate  # Or Windows: .venv\Scripts\activate

# 2. Launch persistent microservice stack
cd deployment/standalone
docker compose up -d
```

### Step 2: Place Source Documents & Jira IDs
Create a folder inside `input_documents/` named after your project (e.g. `MyProject`):
- **PRDs & Diagrams:** Place all PDF, DOCX, PNG, JPG, or JPEG requirement documents inside `input_documents/MyProject/prd/`. Docling OCR automatically parses both text layouts and visual architecture diagrams.
- **Jira Tickets:** Place your target Jira ticket IDs (one per line) inside `input_documents/MyProject/jira/jira_id.txt`:
  ```text
  PROJ-101
  PROJ-102
  ```

### Step 3: Execute Ingestion Workflow
Trigger the ingestion webhook to extract, chunk, and index your documents into PostgreSQL (BM25) and Qdrant (Vector):
```bash
curl -X POST http://localhost:5679/webhook/test-case-generation \
     -H "Content-Type: application/json" \
     -d '{"project_name": "MyProject", "action": "inject"}'
```

### Step 4: Invoke Direct Retrieval & Question Answering
To query the Hybrid RAG engine (BM25 + Qdrant Vector + RRF Fusion + BGE Re-ranker) directly without generating full test plans:
```bash
curl -X POST http://localhost:5679/webhook/retrieve \
     -H "Content-Type: application/json" \
     -d '{"project_name": "MyProject", "query": "What is the login authentication timeout?", "top_k": 5}'
```

### Step 5: Run Adaptive RAGAS Evaluations & Dataset Generation
To benchmark retrieval and generation quality against ground-truth Q&A pairs:

1. **Generate Evaluation Dataset (Optional):**
   Use the built-in dataset generator to sample ingested parent chunks and build 300-500 Q&A pairs automatically or manually:
   ```bash
   # Auto LLM mode with rate-limit retries and caching:
   uv run python -m scripts.evaluation.generate_300_qa MyProject --mode auto --num-questions 300
   ```
   *(Saves to `eval_datasets/MyProject/questions_ground_truth.csv`).*

2. **Trigger RAGAS Benchmark Evaluation:**
   ```bash
   curl -X POST http://localhost:5679/webhook/test-case-generation \
        -H "Content-Type: application/json" \
        -d '{"project_name": "MyProject", "action": "evaluate"}'
   ```
   - **Adaptive Step-Down & Scaling for Paid LLM Tiers:** By default, evaluation processes questions in batches of `EVAL_BATCH_SIZE=5`. If an HTTP 429 rate limit occurs, it dynamically steps down batch size by 1 (`5 -> 4 -> 3...`) with `EVAL_DELAY_SECONDS=5` pacing until throughput stabilizes. If connected to high-throughput paid LLMs (OpenAI `gpt-4o`, Anthropic Claude, or Mistral Commercial), increase `EVAL_BATCH_SIZE=25` and set `EVAL_DELAY_SECONDS=0` in `.env` for rapid evaluation speed.
   - **Outputs:** Evaluation results are versioned inside `eval_datasets/MyProject/results/vX_ragas_results.csv` (with `latest_ragas_results.csv` updated automatically) and logged to the PostgreSQL `evaluation_feedback` table.

### Step 6: Human Review for Loop Engineering
All RAGAS evaluation runs and retrieval outputs are persisted in PostgreSQL (`evaluation_feedback` table) with a `PENDING` status. Reviewers can validate or correct outputs to engineer continuous feedback loops:

1. **View Pending Reviews:**
   ```bash
   curl -X GET http://localhost:5679/feedback/pending/MyProject
   ```
2. **Submit Human Review Decision (Individual, Multi-Select, or All at Once):**
   * **Individual Review:**
     ```bash
     curl -X POST http://localhost:5679/feedback/review \
          -H "Content-Type: application/json" \
          -d '{"feedback_id": "<UUID_FROM_PENDING>", "status": "APPROVED", "notes": "Accurate grounding."}'
     ```
   * **Multi-Select Review (Multiple IDs):**
     ```bash
     curl -X POST http://localhost:5679/feedback/review \
          -H "Content-Type: application/json" \
          -d '{"feedback_ids": ["<UUID_1>", "<UUID_2>"], "status": "APPROVED"}'
     ```
   * **Approve Everything at Once (Bulk Review):**
     ```bash
     curl -X POST http://localhost:5679/feedback/review/all \
          -H "Content-Type: application/json" \
          -d '{"project_name": "<Project_name>", "status": "APPROVED", "notes": "Approved all pending items."}'
     ```
   *(Valid statuses: `APPROVED` or `REJECTED`). Approved outputs can be used to fine-tune future prompt versions.*

---

## 7. Grafana Observability & Metrics

The system is instrumented with Prometheus and exports custom metrics for every phase of the pipeline. You can query these in Grafana (`http://localhost:3000`) to build custom dashboards.

> **Note on Metric Visibility:** Prometheus Python clients do not expose labeled metrics until they are recorded at least once. If you just restarted the container, extraction metrics won't appear until you run an `inject` job, and evaluation metrics won't appear until you run an `evaluate` job.

### Ingestion Metrics
- `rag_ingestion_documents_processed_total`: Total documents processed (`Counter` by `project_name`, `doc_type`)
- `rag_ingestion_bytes_extracted_total`: Total bytes extracted by Docling/Unstructured (`Counter` by `project_name`)
- `rag_ingestion_parent_chunks_total`: Total parent chunks stored in Postgres (`Counter` by `project_name`)
- `rag_ingestion_child_chunks_total`: Total child vectors stored in Qdrant (`Counter` by `project_name`)

### Generation & LLM Costing Metrics
- `rag_generation_documents_created_total`: Total test documents created (`Counter` by `project_name`, `document_type`)
- `rag_generation_tokens_approx`: Histogram of approximate tokens generated (`Histogram` by `project_name`, `document_type`)
- `rag_llm_prompt_tokens_total`: Total prompt tokens sent to the LLM (`Counter` by `project_name`, `agent_name`, `model_name`)
- `rag_llm_completion_tokens_total`: Total completion tokens received from the LLM (`Counter` by `project_name`, `agent_name`, `model_name`)
- `rag_llm_cost_usd_total`: Total estimated LLM cost in USD (`Counter` by `project_name`, `agent_name`, `model_name`)

### Evaluation (RAGAS) Metrics
- `rag_evaluation_questions_generated_total`: Total synthetic questions generated (`Counter` by `project_name`)
- `rag_evaluation_faithfulness_score`: Average Ragas Faithfulness score (`Gauge` by `project_name`)
- `rag_evaluation_answer_relevancy_score`: Average Ragas Answer Relevancy score (`Gauge` by `project_name`)
- `rag_evaluation_context_precision_score`: Average Ragas Context Precision score (`Gauge` by `project_name`)
- `rag_evaluation_context_recall_score`: Average Ragas Context Recall score (`Gauge` by `project_name`)

### PostgreSQL Database Monitoring Queries across All Flows
In addition to live Prometheus metrics in Grafana, database administrators and QA engineers can run direct SQL validation queries against PostgreSQL to inspect workflow execution health:

#### 1. Ingestion Flow Monitoring (`parent_chunks` Table)
```sql
-- Check active parent chunks ingested per document type:
SELECT doc_type, count(*) AS active_chunks 
FROM parent_chunks 
WHERE project_name = '<Project_name>' AND is_latest = TRUE 
GROUP BY doc_type;

-- Check SHA-256 document version history:
SELECT version_id, file_path, doc_hash, created_at 
FROM parent_chunks 
WHERE project_name = '<Project_name>' 
ORDER BY created_at DESC LIMIT 10;
```

#### 2. Retrieval & Keyword Search Flow (`to_tsvector` BM25 Engine)
```sql
-- Test full-text BM25 keyword matching vector:
SELECT chunk_id, left(content, 80) AS snippet, ts_rank_cd(search_vector, query) AS bm25_rank
FROM parent_chunks, to_tsquery('english', 'timeout & login') query
WHERE search_vector @@ query AND project_name = '<Project_name>' AND is_latest = TRUE
ORDER BY bm25_rank DESC LIMIT 5;
```

#### 3. Evaluation & Human Review Loop Flow (`evaluation_feedback` Table)
```sql
-- Monitor status distribution of RAGAS evaluation and generation reviews:
SELECT human_status, count(*) AS review_count 
FROM evaluation_feedback 
WHERE project_name = '<Project_name>' 
GROUP BY human_status;

-- Inspect average RAGAS quality benchmark scores recorded in DB:
SELECT round(avg(faithfulness)::numeric, 3) AS avg_faithfulness,
       round(avg(answer_relevancy)::numeric, 3) AS avg_relevancy,
       round(avg(context_precision)::numeric, 3) AS avg_precision,
       round(avg(context_recall)::numeric, 3) AS avg_recall
FROM evaluation_feedback 
WHERE project_name = '<Project_name>';
```

---

## 8. Observability Persistence (Grafana & Prometheus Volumes)

Both Prometheus and Grafana store historical metrics and dashboards in persistent volumes across deployment environments:
- **Standalone Docker Compose:** Uses persistent Docker volumes (`prometheus_data` and `grafana_data`) and file bind-mounts for `prometheus.yml`.
- **Kubernetes Helm Chart:** Uses dedicated Kubernetes `StatefulSet` resources with Persistent Volume Claims (`prometheus-data`, `grafana-data`) and ConfigMaps (`qa-rag-pipeline-prometheus-config`) for scrape configs.

Even when containers or pods are restarted or rescheduled, your custom dashboards, data sources, and metric time-series history remain fully intact.

---

## 9. Unified OS-Aware Maintenance & Cleanup (`scripts/cleanup/`)

All maintenance utilities are consolidated under the `scripts/cleanup/` directory into a single OS-aware Python engine (`cleanup.py`) with streamlined root and folder OS entrypoints:
- **Linux / macOS Wrapper:** `./scripts/cleanup.sh` (or `scripts/cleanup/cleanup.sh`)
- **Windows PowerShell Wrapper:** `.\scripts\cleanup.ps1` (or `scripts\cleanup\cleanup.ps1`)

### Execution Flags & Options
The script automatically detects your operating system (`Windows`, `Linux`, or `Darwin`) to execute OS-specific file deletions and Docker commands:

```bash
# 1. Clean system build artifacts only (__pycache__, temp CSVs, Docker build cache):
uv run python scripts/cleanup/cleanup.py --system
# Or via shell wrapper:
./scripts/cleanup.sh --system

# 2. Purge database records only (Postgres & Qdrant):
# Purge all projects:
uv run python scripts/cleanup/cleanup.py --db --all
# Purge specific project:
uv run python scripts/cleanup/cleanup.py --db MyProject

# 3. Full purge (system artifacts + all databases):
uv run python scripts/cleanup/cleanup.py --all
```
*(Windows PowerShell users can invoke `.\scripts\cleanup.ps1 --all`)*

---

## 10. Per-Action Iteration Logging & Observability
Each pipeline action records logs to a dedicated file in the `logs/` folder. Before a new iteration begins, its previous log file is automatically cleared so you get fresh logs per run:
- **Ingestion (`logs/ingestion.log`):** Logs document character counts, chunk generation, and explicit **BM-25 Indexing** statements confirming when each Parent Chunk is stored in PostgreSQL full-text `search_vector` (`to_tsvector`).
- **Retrieval Queries (`logs/retrieval.log`):** Logs hybrid retrieval steps including **Dense Vector Search** hits from Qdrant, **BM-25 Keyword Retrieval** hits from PostgreSQL, and **Reciprocal Rank Fusion (RRF `k=60`)** merging scores.
- **Generation (`logs/generation.log`):** Tracks batch generation and outputs **Generation Loop Engineering** review banners.
- **Evaluation (`logs/evals.log`):** Tracks RAGAS grading runs and outputs **Eval Optimization Loop Engineering** checkpoints.
- **Human Loop & Reviews (`logs/human_loop_reviews.log`):** Records **Human Review Acceptance Logs** whenever engineers submit review decisions via `/feedback/review`.

### Prometheus Metrics & Grafana Integration
The API service automatically exposes live metrics at `GET /metrics`, scraped by Prometheus (`qa_rag_prometheus` container on port 9090) and visualized in Grafana (`qa_rag_grafana` container on port 3000):
- **Ingestion:** `rag_ingestion_documents_processed_total`, `rag_ingestion_bytes_extracted_total`, `rag_ingestion_parent_chunks_total`, `rag_ingestion_child_chunks_total`
- **Generation:** `rag_generation_documents_created_total`, `rag_generation_tokens_approx`
- **LLM Token Utilization & Cost:** `rag_llm_prompt_tokens_total`, `rag_llm_completion_tokens_total`, `rag_llm_cost_usd_total`
- **Evaluation:** `rag_evaluation_questions_generated_total`, `rag_evaluation_faithfulness_score`, `rag_evaluation_answer_relevancy_score`, `rag_evaluation_context_precision_score`, `rag_evaluation_context_recall_score`

---

## 11. Human-in-the-Loop Review & Approval Webhooks
When generation finishes (`action="generate"`) or when RAGAS evaluation completes (`action="evaluate"`), Loop Engineering recommendations and action banners are automatically logged. Recommendations are also written to `output_documents/<project_name>/vX/automation_recommendations.csv`. You can trigger human review workflows via the REST API:

```powershell
# Trigger human review step via webhook:
Invoke-RestMethod -Uri "http://localhost:5679/webhook/human-review" -Method Post -ContentType "application/json" -Body '{"project_name": "<Project_name>"}'

# Or via the unified webhook action:
Invoke-RestMethod -Uri "http://localhost:5679/webhook/test-case-generation" -Method Post -ContentType "application/json" -Body '{"project_name": "<Project_name>", "action": "review"}'
```
You can view pending review items at `GET http://localhost:5679/feedback/pending/<project_name>` and submit approval/rejection individually or in multi-select via `POST http://localhost:5679/feedback/review`, or approve everything at once via `POST http://localhost:5679/feedback/review/all`.
