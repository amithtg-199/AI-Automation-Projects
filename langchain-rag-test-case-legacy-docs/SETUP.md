# Setup & Deployment Guide

This document covers how to install, configure, and scale the QA Test Case Generation RAG pipeline.

## 1. Environment Configuration

Regardless of your deployment method, you must define your environment variables.
1. Copy `.env.example` to `.env` in the root directory.
2. Fill in the required fields:
   - `LLM_PROVIDER`: `mistral`, `openai`, `anthropic`, or `ollama`.
   - `LLM_API_KEY`: Your primary API key.
   - `OLLAMA_BASE_URL`: (Optional) If using Ollama, set this to your local instance (e.g. `http://localhost:11434` or `http://host.docker.internal:11434`).
   - `EVAL_DELAY_SECONDS`: (Optional, default `5`) Seconds to sleep between each RAGAS evaluation question. Increase this value if your LLM provider throttles requests (HTTP 429). Set to `0` for local/Ollama providers with no rate limits.

### Generation & Rate-Limit Settings
These control the test document generation pipeline speed and resilience:

| Variable | Default | Description |
|---|---|---|
| `GENERATION_BATCH_SIZE` | `10` | Number of parent chunks sent per LLM call. Increase for fewer, larger batches. |
| `GENERATION_BATCH_DELAY` | `1.0` | Seconds between consecutive LLM calls. Set to `0` for paid tiers with no rate limits. |
| `LLM_MAX_RETRIES` | `5` | Application-level retries on 429/rate-limit errors (on top of SDK retries). |
| `LLM_REQUEST_TIMEOUT` | `120` | Seconds before a single LLM request times out. Increase for slow free-tier providers. |

> **Tip:** On Mistral free tier, keep `GENERATION_BATCH_DELAY=1.0` and `LLM_REQUEST_TIMEOUT=180`. For paid tiers, set `GENERATION_BATCH_DELAY=0` for maximum throughput. For Ollama, set `LLM_REQUEST_TIMEOUT=300` and `GENERATION_BATCH_DELAY=0`.

**Example `.env` section:**
```env
# Mistral (free tier)
LLM_REQUEST_TIMEOUT=180
GENERATION_BATCH_DELAY=1.0
LLM_MAX_RETRIES=5

# OpenAI / Anthropic (paid)
# LLM_REQUEST_TIMEOUT=120
# GENERATION_BATCH_DELAY=0
# LLM_MAX_RETRIES=3

# Ollama (local)
# LLM_REQUEST_TIMEOUT=300
# GENERATION_BATCH_DELAY=0
# LLM_MAX_RETRIES=2
```

## 2. Deployment Strategies

### Securing Secrets (Optional)
If you don't want plaintext passwords (like `POSTGRES_PASSWORD` or `LLM_API_KEY`) lying around in your `.env` or `values.yaml` files, you can use the built-in symmetric encryption utility.

1. **Generate a Master Key**:
   ```bash
   poetry run python scripts/encrypt_secrets.py
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

### Option B: Local Development (Poetry)

If you are a developer testing the python scripts directly:

1. Install Poetry (if not installed):
   ```bash
   pip install poetry
   ```
2. Install Main App Dependencies:
   ```bash
   poetry install
   ```
3. Start the Main API:
   ```bash
   poetry run python init/main.py
   ```
*(Note: You will still need Postgres and Qdrant running somewhere, either locally or via a partial `docker-compose up postgres qdrant`).*

### Option C: Kubernetes Scalable Deployment (Helm / EKS / AKS)

For enterprise-scale, load-based horizontal scaling, deploy using the included Helm chart.

#### Assumptions & Prerequisites
- **Volumes/Storage**: The Helm chart uses dynamic volume provisioning for Postgres and Qdrant via PersistentVolumeClaims (PVCs). It assumes your cluster has a default `StorageClass` installed (e.g., `gp2` on EKS or `managed-csi` on AKS). If you want to use a specific storage class, you must define it under `persistence.storageClass` in `values.yaml`.
- **Docker Registry**: You must have access to a container registry (e.g., AWS ECR, Azure ACR, Google GCR, or Docker Hub) to host the custom images built for this pipeline.
- **Scaling**: The cluster must have the Metrics Server installed to support standard Horizontal Pod Autoscalers (HPA) based on CPU/Memory usage.

#### 1. Build and Push Custom Images
Before installing the Helm chart, you must build the API and Extraction microservices and upload them to your registry.

**Example using AWS ECR / Azure ACR:**
```bash
# 1. Authenticate with your registry (Skip if using Docker Hub)
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <your-registry-url>
# OR: az acr login --name <your-registry-name>

# 2. Build the images locally
docker build -t <your-registry-url>/qa_rag_api:latest .
docker build -t <your-registry-url>/qa_rag_extraction:latest ./extraction-service

# 3. Push the images to the cloud
docker push <your-registry-url>/qa_rag_api:latest
docker push <your-registry-url>/qa_rag_extraction:latest
```

2. Navigate to the Helm chart directory:
   ```bash
   cd deployment/k8s/chart
   ```

3. Update the `values.yaml` file with your specific image registry paths and API keys (Mistral/OpenAI).

4. Install the Helm chart:
   ```bash
   helm install qa-rag-pipeline . --namespace qa-rag --create-namespace
   ```

5. Verify Deployment:
   ```bash
   kubectl get pods -n qa-rag
   kubectl get svc -n qa-rag
   ```

This deploys the Main API, Extraction Service, Postgres, Qdrant, and Monitoring stack. It also automatically configures Horizontal Pod Autoscalers (HPA) to dynamically scale based on CPU usage.

---

## 3. Project Configuration (Dynamic Inputs)

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

## 4. Triggering the Workflow

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
2. The system looks for `logs/manual_testset_<project_name>.csv`. If found, it skips synthetic generation and uses the manual file directly.
3. If no manual file exists, `RagasEvaluator.generate_synthetic_dataset()` uses the LLM to auto-generate questions and ground truths from your ingested parent chunks, saving them to `logs/testset_<project_name>.csv`.
4. For each question in the testset, the RAG retrieval pipeline fetches the top-5 chunks and generates an answer.
5. RAGAS then grades **one question at a time** against four metrics: Faithfulness, Answer Relevancy, Context Precision, and Context Recall.
6. Between each evaluation, the system sleeps for `EVAL_DELAY_SECONDS` (default `5`) to avoid 429 rate-limit errors from the LLM provider.
7. Final results (per-question scores + averages) are saved to `logs/ragas_results_<project_name>.csv`.

#### Setting Questions & Ground Truths (Manual Testset)

To provide your own evaluation questions, create a CSV file at:
```
logs/manual_testset_<project_name>.csv
```

The CSV requires a `question` column and an optional `ground_truth` column:
```csv
question,ground_truth
"What is the system timeout?","The system timeout is 30 seconds."
"How are documents processed?","Through Docling/Unstructured and saved to Postgres/Qdrant."
```

- **`question`** — The query to evaluate against your RAG pipeline.
- **`ground_truth`** — The expected/reference answer. RAGAS uses this to compute Context Recall and Context Precision. If left empty, those two metrics will return `NaN`.

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

#### Option 2: Manual Dataset (Workaround for Rate Limits)
To bypass automatic question generation and avoid hitting API rate limits:
1. Create the file `logs/manual_testset_MyProject.csv` with your questions and ground truths (see format above).
2. Trigger the webhook action `"evaluate"` as normal.
3. The RAG pipeline will detect the manual CSV, skip synthetic generation, retrieve chunks for each question, and grade the output.

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

## 5. Grafana Observability & Metrics

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

---

## 6. Database Cleanup

To purge databases completely (e.g. after a bad run):

**Wipe Postgres:**
```bash
docker exec qa_rag_postgres psql -U qa_user -d qa_rag -c "TRUNCATE TABLE projects CASCADE;"
```

**Wipe Qdrant Collection:**
```bash
curl -X DELETE http://localhost:6333/collections/<project_name>
```
