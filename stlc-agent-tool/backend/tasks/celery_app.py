import os
from celery import Celery
from backend.core.config import settings

# Initialize Celery using Redis Database 0 as broker per strict conventions
celery_app = Celery(
    "stlc_agentic_tasks",
    broker=f"{settings.REDIS_URL}/0",
    backend=f"{settings.REDIS_URL}/0",
    include=["backend.tasks.retention", "backend.tasks.eval_tasks", "backend.tasks.ingestion"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Periodic tasks schedule
    beat_schedule={
        "drop-old-audit-partitions": {
            "task": "backend.tasks.retention.drop_old_partitions",
            "schedule": 86400.0, # Run every day
        },
        "weekly-canary-eval": {
            "task": "backend.tasks.eval_tasks.run_canary_eval",
            "schedule": 604800.0, # Run every week (7 days)
        },
        "hourly-ingestion": {
            "task": "backend.tasks.ingestion.run_project_ingestion",
            "schedule": 3600.0, # Run every 1 hour
            "args": ("Test",) # Hardcoded project name for the default periodic task for now
        }
    }
)
