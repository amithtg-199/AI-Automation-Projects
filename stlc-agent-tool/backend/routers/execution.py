import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from backend.core.auth.deps import get_current_user, CurrentUser
from backend.core.config import settings
from backend.execution.runner import run_suite
from backend.execution.sync import sync_disconnected_results

router = APIRouter(prefix="/api/execution", tags=["Execution"])

class RunSuiteRequest(BaseModel):
    project_name: str
    suite_id: str
    mode: str = "sync" # sync or parallel
    tests_path: str = "tests/"

@router.get("/config")
def get_execution_config(user: CurrentUser = Depends(get_current_user)):
    return {
        "deployment_mode": settings.STLC_DEPLOYMENT_MODE
    }

@router.get("/results")
def get_execution_results(project_name: str, user: CurrentUser = Depends(get_current_user)):
    """Returns all test execution result JSON files for a project."""
    if project_name not in user.projects and user.role != "Admin":
        raise HTTPException(status_code=403, detail="Not assigned to this project.")
    
    base_dir = Path(__file__).resolve().parent.parent.parent / "projects" / project_name / "test_case_result"
    
    results = []
    if base_dir.exists():
        for f in sorted(base_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                results.append(data)
            except Exception:
                pass
    
    return results

@router.get("/suites")
def get_test_suites(project_name: str, user: CurrentUser = Depends(get_current_user)):
    """Returns available test suites derived from execution results and generated test files."""
    if project_name not in user.projects and user.role != "Admin":
        raise HTTPException(status_code=403, detail="Not assigned to this project.")
    
    base_dir = Path(__file__).resolve().parent.parent.parent / "projects" / project_name
    result_dir = base_dir / "test_case_result"
    tests_dir = base_dir / "tests"
    
    suites = []
    
    # From execution results
    if result_dir.exists():
        for f in sorted(result_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                suites.append({
                    "id": data.get("suite_id", f.stem),
                    "name": data.get("suite_name", f.stem),
                    "type": data.get("suite_type", "API"),
                    "mode": "sync",
                    "endpoints": sum(1 for r in data.get("results", []) if r.get("category") == "positive"),
                    "cases": data.get("summary", {}),
                    "has_results": True
                })
            except Exception:
                pass
    
    # From test directories (generated code without results yet)
    if tests_dir.exists():
        for subdir in ["api", "e2e"]:
            test_subdir = tests_dir / subdir
            if test_subdir.exists():
                test_files = list(test_subdir.glob("test_*.py"))
                if test_files:
                    suite_id = f"suite-{subdir}-generated"
                    # Don't duplicate if already in results
                    if not any(s["id"] == suite_id for s in suites):
                        suites.append({
                            "id": suite_id,
                            "name": f"Generated {subdir.upper()} Tests",
                            "type": "API" if subdir == "api" else "UI",
                            "mode": "sync",
                            "endpoints": len(test_files),
                            "cases": {"total": len(test_files), "passed": 0, "failed": 0, "skipped": 0},
                            "has_results": False
                        })
    
    return suites

@router.post("/run")
def execute_suite(req: RunSuiteRequest, user: CurrentUser = Depends(get_current_user)):
    if req.project_name not in user.projects:
        raise HTTPException(status_code=403, detail="Not assigned to this project.")
        
    result = run_suite(
        project_name=req.project_name, 
        suite_id=req.suite_id,
        mode=req.mode,
        tests_path=req.tests_path
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result)
        
    return result

@router.post("/sync")
def sync_results(user: CurrentUser = Depends(get_current_user)):
    # Explicitly triggered by a user when regaining connectivity in DISCONNECTED mode
    return sync_disconnected_results()

