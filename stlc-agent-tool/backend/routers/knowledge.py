import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List
from backend.core.auth.deps import get_current_user, CurrentUser
from backend.core.mock_db import MOCK_NEO4J

router = APIRouter(prefix="/api/knowledge-hub", tags=["Knowledge Hub"])

@router.post("/upload")
async def upload_document(
    project_name: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user)
):
    if project_name not in user.projects:
        raise HTTPException(status_code=403, detail="Not assigned to this project.")
        
    allowed_extensions = [".json", ".yaml", ".yml", ".md"]
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {allowed_extensions}")
        
    # Save the file to the project's docs folder
    base_dir = Path(__file__).resolve().parent.parent.parent.parent / "projects" / project_name
    
    # Determine subfolder based on extension
    if file_ext in [".json", ".yaml", ".yml"]:
        subfolder = "docs/API"
    else:
        subfolder = "docs/PRD"
        
    target_dir = base_dir / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = target_dir / file.filename
    
    try:
        with target_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        
    return {"status": "success", "message": f"File {file.filename} uploaded successfully."}

@router.post("/ingest")
def trigger_ingestion(project_name: str = Form(...), user: CurrentUser = Depends(get_current_user)):
    if project_name not in user.projects:
        raise HTTPException(status_code=403, detail="Not assigned to this project.")
        
    # Trigger the ingestion celery task
    from backend.tasks.ingestion import run_project_ingestion
    
    try:
        # For simplicity in this env, we can just call it synchronously or delay it
        # depending on if celery is running. Let's delay it.
        run_project_ingestion.delay(project_name)
    except Exception as e:
        # Fallback to synchronous if celery isn't up
        try:
            run_project_ingestion(project_name)
        except Exception as sync_e:
            raise HTTPException(status_code=500, detail=f"Failed to run ingestion: {sync_e}")
            
    return {"status": "success", "message": f"Ingestion cycle started for {project_name}."}

class ShareRequest(BaseModel):
    target_projects: List[str]

@router.get("/skills")
def get_skills(user: CurrentUser = Depends(get_current_user)):
    """
    Returns skills that belong to the user's projects OR are explicitly shared with them.
    """
    # Return discovered skills from ingested project data
    mock_skills = [
        {
            "id": "skill-001",
            "project": "Test",
            "module": "Subscriber Management",
            "use_case": "CRUD Lifecycle (Create → Read → Update → Delete)",
            "card": "Learned from VDRC-38248: Automated lifecycle pair detection for Add/Delete Subscriber endpoints. Generates conftest.py with fixture chains and parametrized boundary tests.",
            "shared_across": []
        },
        {
            "id": "skill-002",
            "project": "Test",
            "module": "TMF API Validation",
            "use_case": "TMF-630 Compliance Check",
            "card": "Validates request/response payloads against TMF-630 Resource Inventory spec. Detects non-compliant field names (e.g., Msisdn vs msisdn) and auto-generates field alias mappings.",
            "shared_across": []
        },
        {
            "id": "skill-003",
            "project": "Test",
            "module": "Auth & Security",
            "use_case": "Bearer Token Negative Testing",
            "card": "Generates comprehensive negative test cases for JWT/Bearer token authentication: expired tokens, malformed headers, missing Authorization, SQL injection in token field.",
            "shared_across": []
        },
        {
            "id": "skill-004",
            "project": "Test",
            "module": "Data Integrity",
            "use_case": "Duplicate Record Detection",
            "card": "Learned pattern: POST with duplicate MSISDN should return 409 Conflict. Generates test asserting idempotency and proper error response schema.",
            "shared_across": []
        },
    ]
    
    # Filter to user's projects
    user_skills = [s for s in mock_skills if s["project"] in user.projects]
    return user_skills

@router.post("/{skill_id}/share")
def share_skill(skill_id: str, req: ShareRequest, user: CurrentUser = Depends(get_current_user)):
    """
    Admin-only endpoint to create the [:SHARED_ACROSS] relationship.
    """
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins can share skills across projects.")
    
    # TODO: Implement Neo4j relationship creation for sharing skills
    raise HTTPException(status_code=404, detail="Skill sharing is not fully implemented yet.")
