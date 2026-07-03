import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from scripts.ingestion import IngestionPipeline
from scripts.retrieval import RetrievalPipeline
from scripts.evaluation import RagasEvaluator
from scripts.logger import get_logger, setup_action_logger
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn

logger = get_logger(__name__)
app = FastAPI(title="LangChain RAG API")

# Initialize Prometheus Metrics Exporter
Instrumentator().instrument(app).expose(app)

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from scripts.config import config

class WebhookPayload(BaseModel):
    project_name: str = Field(default_factory=lambda: config.DEFAULT_PROJECT_NAME)
    action: str = "review"
    approve_all: bool = False
    status: Optional[str] = None
    notes: str = ""
    parent_chunk_size: Optional[int] = None
    parent_chunk_overlap: Optional[int] = None
    child_chunk_size: Optional[int] = None
    child_chunk_overlap: Optional[int] = None

class RetrievalPayload(BaseModel):
    project_name: str = Field(default_factory=lambda: config.DEFAULT_PROJECT_NAME)
    query: str
    top_k: int = 5

class EvaluationPayload(BaseModel):
    project_name: str = Field(default_factory=lambda: config.DEFAULT_PROJECT_NAME)
    query: str
    expected_answer: str
    top_k: int = 5

class ReviewPayload(BaseModel):
    feedback_id: Optional[str] = None
    feedback_ids: Optional[List[str]] = None
    project_name: Optional[str] = Field(default_factory=lambda: config.DEFAULT_PROJECT_NAME)
    approve_all: bool = False
    status: str  # APPROVED, REJECTED
    notes: str = ""

class BulkReviewPayload(BaseModel):
    project_name: str = Field(default_factory=lambda: config.DEFAULT_PROJECT_NAME)
    status: str = "APPROVED"  # APPROVED, REJECTED
    notes: str = ""

def run_ingestion(project_name: str, parent_chunk_size: Optional[int] = None, parent_chunk_overlap: Optional[int] = None, child_chunk_size: Optional[int] = None, child_chunk_overlap: Optional[int] = None):
    setup_action_logger("ingestion", clear_old=True)
    logger.info(f"--- Starting Ingestion Iteration for Project: {project_name} ---")
    pipeline = IngestionPipeline(
        project_name=project_name,
        parent_chunk_size=parent_chunk_size,
        parent_chunk_overlap=parent_chunk_overlap,
        child_chunk_size=child_chunk_size,
        child_chunk_overlap=child_chunk_overlap
    )
    pipeline.run()

def run_generation(project_name: str):
    setup_action_logger("generation", clear_old=True)
    logger.info(f"--- Starting Generation Iteration for Project: {project_name} ---")
    pipeline = RetrievalPipeline(project_name)
    try:
        pipeline.generate_test_documents()
    finally:
        pipeline.close()

def run_evaluation(project_name: str):
    setup_action_logger("evals", clear_old=True)
    logger.info(f"--- Starting Evaluation Iteration for Project: {project_name} ---")
    evaluator = RagasEvaluator(project_name)
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(root_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        eval_results_dir = os.path.join(root_dir, "eval_datasets", project_name, "results")
        os.makedirs(eval_results_dir, exist_ok=True)
        
        existing_v = [int(f.split("_")[0][1:]) for f in os.listdir(eval_results_dir) if f.startswith("v") and "_" in f and f.split("_")[0][1:].isdigit()]
        next_eval_v = max(existing_v) + 1 if existing_v else 1
        results_file = os.path.join(eval_results_dir, f"v{next_eval_v}_ragas_results.csv")
        latest_results_file = os.path.join(eval_results_dir, "latest_ragas_results.csv")
        
        eval_folder_file = os.path.join(root_dir, "eval_datasets", project_name, "questions_ground_truth.csv")
        manual_testset_file = os.path.join(logs_dir, f"manual_testset_{project_name}.csv")
        testset_file = os.path.join(logs_dir, f"testset_{project_name}.csv")
        
        if os.path.exists(eval_folder_file):
            logger.info(f"Found dedicated RAGAS evaluation dataset at {eval_folder_file}. Running evaluation (v{next_eval_v})...")
            evaluator.run_evaluation(testset_csv=eval_folder_file, output_csv=results_file)
        elif os.path.exists(manual_testset_file):
            logger.info(f"Found manual testset at {manual_testset_file}. Running evaluation (v{next_eval_v})...")
            evaluator.run_evaluation(testset_csv=manual_testset_file, output_csv=results_file)
        else:
            logger.info(f"No manual testset found. Generating synthetic dataset for {project_name}...")
            evaluator.generate_synthetic_dataset(num_questions=5, output_file=testset_file)
            logger.info(f"Running evaluation for {project_name} (v{next_eval_v})...")
            evaluator.run_evaluation(testset_csv=testset_file, output_csv=results_file)

        import shutil
        if os.path.exists(results_file):
            shutil.copyfile(results_file, latest_results_file)
            logger.info(f"Saved copy to {latest_results_file}")
    finally:
        evaluator.close()

@app.post("/webhook/test-case-generation")
async def handle_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    logger.info(f"Received webhook: project={payload.project_name}, action={payload.action}")
    if payload.action == "inject":
        background_tasks.add_task(
            run_ingestion,
            payload.project_name,
            payload.parent_chunk_size,
            payload.parent_chunk_overlap,
            payload.child_chunk_size,
            payload.child_chunk_overlap
        )
        return {"status": "success", "message": f"Started ingestion for {payload.project_name} in background."}
    elif payload.action == "generate":
        background_tasks.add_task(run_generation, payload.project_name)
        return {"status": "success", "message": f"Started document generation for {payload.project_name} in background."}
    elif payload.action == "evaluate":
        background_tasks.add_task(run_evaluation, payload.project_name)
        return {"status": "success", "message": f"Started Ragas evaluation for {payload.project_name} in background."}
    elif payload.action == "review" or payload.approve_all:
        setup_action_logger("human_loop_reviews", clear_old=False)
        if payload.approve_all or payload.status:
            status_val = payload.status or "APPROVED"
            from scripts.database import PostgresDB
            with PostgresDB() as db:
                count = db.submit_human_review_all(payload.project_name, status_val, payload.notes)
                logger.info(f"[Human Review Acceptance Logs] Successfully recorded bulk decision '{status_val}' via webhook for all {count} pending reviews in project {payload.project_name}.")
                return {"status": "success", "updated_count": count, "message": f"Updated all {count} pending reviews for {payload.project_name} to {status_val}."}
        logger.info(f"[Human Review Acceptance Logs] Initiated human review loop for project: {payload.project_name}.")
        return {"status": "success", "message": f"Human review loop initiated for {payload.project_name}. Check /feedback/pending/{payload.project_name}."}
    else:
        logger.warning(f"Unhandled action: {payload.action}")
        return {"status": "ignored", "message": f"Action '{payload.action}' not recognized. Use 'inject', 'generate', 'evaluate', or 'review'."}

@app.post("/webhook/human-review")
async def trigger_human_review(payload: WebhookPayload):
    setup_action_logger("human_loop_reviews", clear_old=False)
    if payload.approve_all or payload.status:
        status_val = payload.status or "APPROVED"
        from scripts.database import PostgresDB
        with PostgresDB() as db:
            count = db.submit_human_review_all(payload.project_name, status_val, payload.notes)
            logger.info(f"[Human Review Acceptance Logs] Successfully recorded bulk decision '{status_val}' via webhook for all {count} pending reviews in project {payload.project_name}.")
            return {"status": "success", "updated_count": count, "message": f"Updated all {count} pending reviews for {payload.project_name} to {status_val}."}
    logger.info(f"[Human Review Acceptance Logs] Webhook triggered for project {payload.project_name}. Ready for human review and final approval.")
    return {"status": "success", "message": f"Human review step triggered for project {payload.project_name}. Users can now approve recommendations."}

@app.post("/webhook/retrieve")
async def retrieve_endpoint(payload: RetrievalPayload):
    setup_action_logger("retrieval", clear_old=False)
    logger.info(f"Received retrieve request for project {payload.project_name}")
    pipeline = RetrievalPipeline(payload.project_name)
    try:
        result = pipeline.retrieve_and_answer(payload.query, payload.top_k)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Retrieve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pipeline.close()

@app.get("/feedback/pending/{project_name}")
async def get_pending_feedback(project_name: str):
    setup_action_logger("human_loop_reviews", clear_old=False)
    logger.info(f"Fetching pending feedback reviews for project: {project_name}")
    from scripts.database import PostgresDB
    with PostgresDB() as db:
        items = db.get_pending_feedback(project_name)
        pending_uuids = [item["feedback_id"] for item in items if "feedback_id" in item]
        return {
            "status": "success",
            "count": len(pending_uuids),
            "pending_feedback_ids": pending_uuids
        }

@app.post("/feedback/review")
async def submit_feedback_review(payload: ReviewPayload):
    setup_action_logger("human_loop_reviews", clear_old=False)
    from scripts.database import PostgresDB
    with PostgresDB() as db:
        if payload.approve_all and payload.project_name:
            count = db.submit_human_review_all(payload.project_name, payload.status, payload.notes)
            logger.info(f"[Human Review Acceptance Logs] Successfully recorded bulk decision '{payload.status}' for all {count} pending reviews in project {payload.project_name}.")
            return {"status": "success", "updated_count": count, "message": f"Updated all {count} pending reviews for {payload.project_name} to {payload.status}."}
        elif payload.feedback_ids:
            updated = 0
            for fid in payload.feedback_ids:
                if db.submit_human_review(fid, payload.status, payload.notes):
                    updated += 1
            logger.info(f"[Human Review Acceptance Logs] Successfully recorded decision '{payload.status}' for {updated}/{len(payload.feedback_ids)} feedback IDs.")
            return {"status": "success", "updated_count": updated, "message": f"Updated {updated} feedback IDs to {payload.status}."}
        elif payload.feedback_id:
            success = db.submit_human_review(payload.feedback_id, payload.status, payload.notes)
            if success:
                logger.info(f"[Human Review Acceptance Logs] Successfully recorded decision '{payload.status}' for feedback ID {payload.feedback_id}. Notes: '{payload.notes}'")
                return {"status": "success", "message": f"Feedback {payload.feedback_id} updated to {payload.status}."}
            logger.error(f"[Human Review Acceptance Logs] Failed to record decision: Feedback ID {payload.feedback_id} not found.")
            raise HTTPException(status_code=404, detail="Feedback ID not found.")
        else:
            raise HTTPException(status_code=400, detail="Must provide either feedback_id, feedback_ids list, or (project_name + approve_all=True).")

@app.post("/feedback/review/all")
async def submit_bulk_feedback_review(payload: BulkReviewPayload):
    setup_action_logger("human_loop_reviews", clear_old=False)
    logger.info(f"[Human Review Acceptance Logs] Processing bulk human review decision for project: {payload.project_name} with status: {payload.status}")
    from scripts.database import PostgresDB
    with PostgresDB() as db:
        count = db.submit_human_review_all(payload.project_name, payload.status, payload.notes)
        logger.info(f"[Human Review Acceptance Logs] Successfully recorded bulk decision '{payload.status}' for all {count} pending reviews in project {payload.project_name}. Notes: '{payload.notes}'")
        return {"status": "success", "updated_count": count, "message": f"Updated all {count} pending reviews for {payload.project_name} to {payload.status}."}

class MetricsEndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/metrics" not in record.getMessage()

if __name__ == "__main__":
    logging.getLogger("uvicorn.access").addFilter(MetricsEndpointFilter())
    uvicorn.run(app, host="0.0.0.0", port=5679)
