# Bare Metal Deployment

This document describes how to deploy the STLC Agentic Platform on bare-metal systems (e.g., EC2 instances, on-prem VMs).

## Supported Platforms
- **Linux (Primary):** Ubuntu 22.04 LTS / Debian 11+
- **Windows:** Supported **only via WSL2**. Native Windows deployment of dependencies like Qdrant and Redis is not officially supported and is highly prone to errors. We strongly recommend running the Linux instructions inside a WSL2 environment.

## Deployment Strategy: Hybrid (Recommended)

While it is possible to install every dependency (Postgres, Redis, Neo4j, Qdrant) via `apt` or native binaries, this is often fragile and difficult to upgrade.
**We strongly recommend a hybrid deployment:**
1. Use Docker to run the database dependencies.
2. Run the application logic (Python backend, Celery workers, Node/Nginx frontend) natively via Systemd.

### 1. Database Dependencies (via Docker)
Start the foundational databases using the provided stripped-down compose file:
```bash
# Example subset of docker-compose.yml for DBs only
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
docker run -d -p 6379:6379 redis:7-alpine
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
docker run -d -p 7474:7474 -p 7687:7687 --env NEO4J_AUTH=neo4j/password neo4j:5
```

### 2. Backend API & Celery (Systemd)
Install `uv` and python dependencies:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cd backend
uv sync
```

Create a systemd service file at `/etc/systemd/system/stlc-backend.service`:
```ini
[Unit]
Description=STLC Agentic Backend FastAPI
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/stlc-agentic-tool
ExecStart=/home/ubuntu/.local/bin/uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
EnvironmentFile=/path/to/stlc-agentic-tool/.env
Restart=always

[Install]
WantedBy=multi-user.target
```
Enable and start the service: `sudo systemctl enable --now stlc-backend`

Repeat this pattern for the `celery worker` and `celery beat` processes.
_Security Warning: Never place raw API keys inside the `.service` file. Always use an `EnvironmentFile` that has restricted `chmod 600` permissions._

### 3. Frontend UI (Nginx)
Build the static assets:
```bash
cd frontend
npm install
npm run build
```
Copy the contents of `dist/` to `/var/www/html` and configure Nginx to route `/api/*` to your backend on `localhost:8000`.

## Self-Hosted Inference (vLLM)
If you have a CUDA-capable GPU and have `SELF_HOSTED_LLM_ENABLED=true`, you can run vLLM natively.
**Windows Note:** vLLM natively requires Linux. To run on Windows, you must use WSL2 with NVIDIA CUDA passthrough drivers installed on the host. Do not attempt to pip install vLLM on raw Windows.
```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-2-7b-chat-hf
```
Then point `SELF_HOSTED_LLM_BASE_URL` in your `.env` to `http://localhost:8000/v1`.
