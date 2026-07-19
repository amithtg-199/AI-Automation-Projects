from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from services.ingestion import ingest_directory
from services.retrieval import get_answer
from core.config import settings
from core.state import progress_store
import dotenv
import os

router = APIRouter()

class ConfigRequest(BaseModel):
    qdrant_url: str
    mistral_api_key: str
    jira_url: str

@router.post("/config")
async def save_config(request: ConfigRequest):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    # Ensure file exists
    if not os.path.exists(env_path):
        open(env_path, 'a').close()
        
    dotenv.set_key(env_path, "QDRANT_URL", request.qdrant_url)
    dotenv.set_key(env_path, "MISTRAL_API_KEY", request.mistral_api_key)
    
    # Update in memory
    settings.qdrant_url = request.qdrant_url
    settings.mistral_api_key = request.mistral_api_key
    
    return {"status": "success", "message": "Saved to .env globally!"}

class ChatRequest(BaseModel):
    query: str
    project_name: str

class IngestRequest(BaseModel):
    project_name: str

@router.post("/ingest")
async def ingest_documents(request: IngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(ingest_directory, request.project_name)
    return {"status": "success", "message": f"Ingestion for {request.project_name} started."}

@router.get("/progress/{project_name}")
def get_progress(project_name: str):
    # Check if currently ingesting
    if project_name in progress_store and progress_store[project_name]["status"] in ["scanning", "processing"]:
        return progress_store[project_name]
        
    from services.vector_db import get_qdrant_client
    from services.ingestion import map_file_to_category
    qdrant = get_qdrant_client()
    
    try:
        if not qdrant.collection_exists(project_name):
            return {
                "status": "idle",
                "total_files": 0,
                "extracted_files": 0,
                "total_chunks": 0,
                "embedded_chunks": 0,
                "category_chunks": {}
            }
            
        # Realtime fetch from Qdrant
        total_chunks = qdrant.count(project_name).count
        
        category_chunks = {}
        unique_files = set()
        
        offset = None
        while True:
            records, offset = qdrant.scroll(
                collection_name=project_name,
                limit=1000,
                offset=offset,
                with_payload=["source"],
                with_vectors=False
            )
            for record in records:
                source = record.payload.get("source", "")
                if source:
                    unique_files.add(source)
                    cat = map_file_to_category(source)
                    category_chunks[cat] = category_chunks.get(cat, 0) + 1
            if offset is None:
                break
                
        # Cache it in memory so we don't query Qdrant heavily on every poll if completed
        progress_store[project_name] = {
            "status": "complete",
            "total_files": len(unique_files),
            "extracted_files": len(unique_files),
            "total_chunks": total_chunks,
            "embedded_chunks": total_chunks,
            "category_chunks": category_chunks
        }
        return progress_store[project_name]
    except Exception as e:
        print(f"Error fetching progress: {e}")
        return progress_store.get(project_name, {
            "status": "idle",
            "total_files": 0,
            "extracted_files": 0,
            "total_chunks": 0,
            "embedded_chunks": 0,
            "category_chunks": {}
        })

from services.vector_db import get_qdrant_client
@router.get("/chunks/{project_name}")
def get_chunk_count(project_name: str):
    qdrant = get_qdrant_client()
    try:
        if qdrant.collection_exists(project_name):
            count_result = qdrant.count(project_name)
            return {"project_name": project_name, "count": count_result.count}
        return {"project_name": project_name, "count": 0}
    except Exception as e:
        return {"project_name": project_name, "count": 0}

@router.post("/chat")
def chat(request: ChatRequest):
    answer = get_answer(request.query, request.project_name)
    return {"response": answer}

@router.get("/projects")
async def list_projects():
    return {"projects": ["QA_Project_1"]}
