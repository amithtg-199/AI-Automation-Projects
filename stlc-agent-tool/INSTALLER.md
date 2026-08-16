# Installation Guide

This document covers how to install and run the **STLC Agentic Platform**. You can choose to run it locally via Docker Desktop, on Bare-Metal (Linux/WSL2), or distributed in a Kubernetes cluster.

---

## 1. Local Development (Docker Compose)
*Best for development and Hackathon testing.*

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend)
- Python 3.12+ & `uv` (for backend)

### Steps
1. **Start the Databases**
   Navigate to the root directory and start the foundational databases (Postgres, Neo4j, Qdrant, Redis).
   ```bash
   docker-compose up -d
   ```
   > **Note:** The `vLLM` service is **not started** by default (it requires a GPU and is behind the `self-hosted-llm` profile). This means **port 8000 is free** for the FastAPI backend.

2. **Start the Backend**
   If you don't have `uv` installed, install it first:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source $HOME/.local/bin/env
   ```
   Then start the FastAPI backend (runs on **port 8000**):
   ```bash
   # Run from the PROJECT ROOT (stlc-agentic-tool/), NOT from inside backend/
   cd backend
   uv sync
   cd ..
   backend/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Or equivalently using `uv run` from the project root:
   ```bash
   cd backend && uv sync && cd ..
   uv run --project backend uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   > **Tip:** If you already have something on port 8000 from another project, kill it first:
   > ```bash
   > # Linux/WSL
   > fuser -k 8000/tcp
   > ```

3. **Start the Frontend**
   Open a new terminal. The Vite dev server proxies all `/api/*` calls to `localhost:8000`.
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Access the App**
   Open your browser to `http://localhost:5173`.

5. **First-Time Admin Setup**
   On first launch, you will see the Login screen. Click **"First Time Setup? Bootstrap Admin"** to create your initial Admin account. This only works when the `users` table is empty.

---


## 2. Bare-Metal (Hybrid Approach)
*Best for on-premise VMs (Ubuntu/Debian) or Windows WSL2.*

We recommend running the databases in Docker and the Python/Node applications natively via Systemd to maximize performance while avoiding fragile native DB installations.

Please see the detailed guide at [docs/bare_metal_setup.md](docs/bare_metal_setup.md).

---

## 3. Kubernetes (Helm)
*Best for production enterprise deployments with autoscaling.*

### Prerequisites
- A running Kubernetes Cluster (EKS, GKE, or local Minikube)
- Helm 3 installed

### Steps
1. Install dependencies for the umbrella chart (Bitnami Postgres/Redis):
   ```bash
   cd charts/stlc-agentic-tool
   helm dependency update
   ```
2. Install the platform:
   ```bash
   helm install stlc-platform . --namespace stlc --create-namespace
   ```

---

## Optional: Self-Hosted Inference (vLLM)
To radically reduce API costs, the platform supports routing specific agent tasks to a local, self-hosted LLM via vLLM.
*Note: This requires a CUDA-capable GPU.*

**Using Docker Compose:**
Start the stack with the `self-hosted-llm` profile:
```bash
docker-compose --profile self-hosted-llm up -d
```

**Using Kubernetes (KServe):**
Edit `charts/stlc-agentic-tool/values.yaml` and set:
```yaml
selfHostedLLM:
  enabled: true
  model: "meta-llama/Llama-2-7b-chat-hf"
```
*Note: Knative and KServe CRDs MUST be installed on your cluster for this to work.*
