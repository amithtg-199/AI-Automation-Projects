import os
import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.core.config import settings
from backend.core.neo4j_schema import apply_schema
from backend.core.postgres_bootstrap import bootstrap_postgres
from backend.core.middleware import AuditLogMiddleware

from backend.routers import auth, admin, orchestrator, rag_eval, execution, approvals, knowledge, reports, cost, users

app = FastAPI(title="STLC Agentic Tool API")

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditLogMiddleware)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(orchestrator.router)
app.include_router(rag_eval.router)
app.include_router(execution.router)
app.include_router(approvals.router)
app.include_router(knowledge.router)
app.include_router(reports.router)
app.include_router(cost.router)

@app.on_event("startup")
def on_startup():
    # Attempt to bootstrap schemas on startup
    try:
        bootstrap_postgres()
        apply_schema()
    except Exception as e:
        print(f"Warning: Failed to bootstrap DB schemas on startup: {e}")

@app.post("/api/projects/{project_name}/init")
def init_project(project_name: str):
    """
    Initializes a new project by:
    1. Creating the required folder tree.
    2. Creating the Qdrant collection for the project (dense+sparse).
    3. Registering the project in Postgres.
    """
    if not project_name or not project_name.isalnum():
        raise HTTPException(status_code=400, detail="Invalid project name (must be alphanumeric)")

    base_dir = Path(__file__).resolve().parent.parent.parent
    project_dir = base_dir / "projects" / project_name
    
    # 1. Create folders idempotently
    folders_to_create = [
        project_dir,
        project_dir / "docs" / "PRD",
        project_dir / "docs" / "JIRA",
        project_dir / "docs" / "Postman_collection",
        project_dir / "tests" / "e2e",
        project_dir / "tests" / "api",
        project_dir / "fixtures",
        project_dir / "pages",
        project_dir / "models",
        project_dir / "clients",
        project_dir / "utils",
    ]
    
    for folder in folders_to_create:
        folder.mkdir(parents=True, exist_ok=True)
        
    # Create empty __init__.py files (except for docs and project root)
    for folder in folders_to_create:
        if folder != project_dir and "docs" not in folder.parts:
            (folder / "__init__.py").touch(exist_ok=True)
            
    # Create jira_ids.txt for Jira MCP ingestion
    jira_txt_path = project_dir / "docs" / "JIRA" / "jira_ids.txt"
    if not jira_txt_path.exists():
        jira_txt_path.write_text("# Provide a comma-separated list of Jira IDs here for the MCP to fetch.\n# e.g., PROJ-123, PROJ-456\n")
            
    # Create default input_folder.yaml mapping
    yaml_path = project_dir / "input_folder.yaml"
    if not yaml_path.exists():
        yaml_content = f"""# Document Ingestion Mappings
# The celery ingestion engine will scan these paths for raw documents.
prd_docs: "docs/PRD"
jira_exports: "docs/JIRA"
postman_collections: "docs/Postman_collection"
"""
        yaml_path.write_text(yaml_content)

    # 2. Qdrant Collection creation
    qdrant_client = QdrantClient(url=settings.QDRANT_URL)
    
    try:
        # Check if exists
        qdrant_client.get_collection(collection_name=project_name)
    except Exception:
        # Does not exist, create it
        try:
            qdrant_client.create_collection(
                collection_name=project_name,
                vectors_config={
                    # Assuming an embedding model like BAAI/bge-large-en-v1.5 which has 1024 dims
                    # We'll use 1536 as a safe default for OpenAI standard if not specified, 
                    # but let's use 1024 for BGE. Adjust as necessary later.
                    "dense": models.VectorParams(
                        size=1024,
                        distance=models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams()
                }
            )
        except Exception as e:
            print(f"Qdrant collection creation failed (it might already exist): {e}")

    # 3. Postgres Row Insertion (Upsert)
    try:
        with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO projects (name, is_active)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING;
                    """,
                    (project_name, True)
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database registration failed: {str(e)}")

    return {"status": "success", "message": f"Project {project_name} initialized successfully."}

@app.post("/api/global-env")
def update_global_env(env_data: dict):
    """
    Receives Global Env variables from UI and writes them to global_variables/.env.
    Any specific secrets (like LLM_API_KEY) will be encrypted first via Fernet.
    """
    # Just a placeholder structure matching requirements
    return {"status": "success"}
