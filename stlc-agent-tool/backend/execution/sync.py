import os
import glob
import logging
import json
from backend.execution.runner import get_result_dir, push_to_central_queue

logger = logging.getLogger(__name__)

def sync_disconnected_results():
    """
    Sweeps the local test_case_result directory for disconnected runs 
    and manually pushes them to the central queue.
    """
    base_projects_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "projects"))
    
    if not os.path.exists(base_projects_dir):
        return {"status": "success", "synced_files": 0, "message": "No projects directory found."}
        
    synced = 0
    for project_name in os.listdir(base_projects_dir):
        project_dir = os.path.join(base_projects_dir, project_name)
        if not os.path.isdir(project_dir):
            continue
            
        result_dir = get_result_dir(project_name)
        if not os.path.exists(result_dir):
            continue
            
        # Find all json files
        search_pattern = os.path.join(result_dir, "**", "*.json")
        json_files = glob.glob(search_pattern, recursive=True)
        
        for file_path in json_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                filename = os.path.basename(file_path)
                push_to_central_queue(project_name, "unknown_suite", data, file_path)
                synced += 1
                logger.info(f"Successfully synced: {filename} from {project_name}")
            except Exception as e:
                logger.error(f"Failed to sync {file_path}: {str(e)}")
                
    return {"status": "success", "synced_files": synced}
