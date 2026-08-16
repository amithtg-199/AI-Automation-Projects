import os
import datetime
import subprocess
import json
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Base output directory
def get_result_dir(project_name: str) -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "projects", project_name, "test_case_result"))
    return base_dir

def run_suite(project_name: str, suite_id: str, mode: str = "sync", tests_path: str = "tests/") -> dict:
    """
    Executes a pytest suite honoring the exact execution_mode.
    No LLM, RAG, or Graph dependencies.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_dir = get_result_dir(project_name)
    output_folder = os.path.join(result_dir, timestamp)
    os.makedirs(output_folder, exist_ok=True)
    
    json_report_path = os.path.join(output_folder, f"{project_name}_test_result_{timestamp}.json")
    
    # Resolve tests_path inside project folder
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "projects", project_name))
    resolved_tests_path = os.path.join(project_root, tests_path)
    
    cmd = ["uv", "run", "pytest", resolved_tests_path, "--json-report", f"--json-report-file={json_report_path}"]
    
    # Enforce Guardrail 19
    if mode == "parallel":
        cmd.extend(["-n", "auto"])
        
    logger.info(f"Executing: {' '.join(cmd)}")
    
    # Run the test
    # In a real app we might run this asynchronously or via Celery.
    # For MVP we use subprocess.run
    process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    
    # Check if report was generated
    if not os.path.exists(json_report_path):
        return {"status": "error", "message": "Failed to generate JSON report", "logs": process.stderr}
        
    with open(json_report_path, "r") as f:
        report_data = json.load(f)
        
    summary = report_data.get("summary", {})
    
    # Handle routing based on deployment mode
    if settings.STLC_DEPLOYMENT_MODE == "connected":
        push_to_central_queue(project_name, suite_id, report_data, json_report_path)
    else:
        logger.info(f"DISCONNECTED MODE: Result saved locally to {json_report_path} only.")
        
    return {
        "status": "success",
        "timestamp": timestamp,
        "summary": summary,
        "report_file": json_report_path
    }

def push_to_central_queue(project_name: str, suite_id: str, report_data: dict, file_path: str):
    """
    Push to the central RAG ingestion queue.
    """
    from backend.tasks.ingestion import run_project_ingestion
    logger.info(f"CONNECTED MODE: Pushed {file_path} to central queue for RAG ingestion.")
    run_project_ingestion.delay(project_name)
