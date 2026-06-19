import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from scripts.ingestion import IngestionPipeline
from scripts.retrieval import RetrievalPipeline
from scripts.evaluation import RagasEvaluator
from scripts.logger import get_logger
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn

logger = get_logger(__name__)
app = FastAPI(title="LangChain RAG API")

# Initialize Prometheus Metrics Exporter
Instrumentator().instrument(app).expose(app)

class WebhookPayload(BaseModel):
    project_name: str
    action: str

class RetrievalPayload(BaseModel):
    project_name: str
    query: str
    top_k: int = 5

class EvaluationPayload(BaseModel):
    project_name: str
    query: str
    expected_answer: str
    top_k: int = 5

def run_ingestion(project_name: str):
    pipeline = IngestionPipeline(project_name)
    pipeline.run()

def run_generation(project_name: str):
    pipeline = RetrievalPipeline(project_name)
    pipeline.generate_test_documents()

def run_evaluation(project_name: str):
    evaluator = RagasEvaluator(project_name)
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    manual_testset_file = os.path.join(logs_dir, f"manual_testset_{project_name}.csv")
    testset_file = os.path.join(logs_dir, f"testset_{project_name}.csv")
    results_file = os.path.join(logs_dir, f"ragas_results_{project_name}.csv")
    
    if os.path.exists(manual_testset_file):
        logger.info(f"Found manual testset at {manual_testset_file}. Bypassing synthetic dataset generation.")
        logger.info(f"Running evaluation for {project_name} using manual testset...")
        evaluator.run_evaluation(testset_csv=manual_testset_file, output_csv=results_file)
    else:
        logger.info(f"No manual testset found at {manual_testset_file}. Generating synthetic dataset for {project_name}...")
        evaluator.generate_synthetic_dataset(num_questions=5, output_file=testset_file)
        logger.info(f"Running evaluation for {project_name}...")
        evaluator.run_evaluation(testset_csv=testset_file, output_csv=results_file)

@app.post("/webhook/test-case-generation")
async def handle_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    if payload.action == "inject":
        # Clear old logs upon new ingestion run
        log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "rag_pipeline.log")
        if os.path.exists(log_file):
            with open(log_file, "w") as f:
                f.truncate()
                
    logger.info(f"Received webhook: project={payload.project_name}, action={payload.action}")
    if payload.action == "inject":
        background_tasks.add_task(run_ingestion, payload.project_name)
        return {"status": "success", "message": f"Started ingestion for {payload.project_name} in background."}
    elif payload.action == "generate":
        background_tasks.add_task(run_generation, payload.project_name)
        return {"status": "success", "message": f"Started document generation for {payload.project_name} in background."}
    elif payload.action == "evaluate":
        background_tasks.add_task(run_evaluation, payload.project_name)
        return {"status": "success", "message": f"Started Ragas evaluation for {payload.project_name} in background."}
    else:
        logger.warning(f"Unhandled action: {payload.action}")
        return {"status": "ignored", "message": f"Action '{payload.action}' not recognized. Use 'inject', 'generate', or 'evaluate'."}

@app.post("/webhook/retrieve")
async def retrieve_endpoint(payload: RetrievalPayload):
    logger.info(f"Received retrieve request for project {payload.project_name}")
    try:
        pipeline = RetrievalPipeline(payload.project_name)
        result = pipeline.retrieve_and_answer(payload.query, payload.top_k)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Retrieve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5679)
