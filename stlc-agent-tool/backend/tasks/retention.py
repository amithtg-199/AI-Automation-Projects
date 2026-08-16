import logging
import psycopg
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from backend.tasks.celery_app import celery_app
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Configurable retention periods
AUDIT_LOG_RETENTION_MONTHS = 3 # Approx 90 days
COST_LOG_RETENTION_MONTHS = 3

@celery_app.task
def drop_old_partitions():
    """
    Drops partitions for audit_logs and token_cost_logs that are older than the retention period.
    We are dropping by month since tables are partitioned by month.
    """
    now = datetime.now()
    
    # Calculate cutoff dates
    audit_cutoff = now - relativedelta(months=AUDIT_LOG_RETENTION_MONTHS)
    cost_cutoff = now - relativedelta(months=COST_LOG_RETENTION_MONTHS)
    
    # Format of partition names: table_name_YYYY_MM
    audit_partition_to_drop = f"audit_logs_{audit_cutoff.strftime('%Y_%m')}"
    cost_partition_to_drop = f"token_cost_logs_{cost_cutoff.strftime('%Y_%m')}"
    
    logger.info(f"Running retention job. Looking to drop partitions older than {audit_cutoff.strftime('%Y_%m')}")
    
    try:
        with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Drop audit log partition
                cur.execute(f"DROP TABLE IF EXISTS {audit_partition_to_drop}")
                logger.info(f"Dropped partition {audit_partition_to_drop} if it existed.")
                
                # Drop cost log partition
                cur.execute(f"DROP TABLE IF EXISTS {cost_partition_to_drop}")
                logger.info(f"Dropped partition {cost_partition_to_drop} if it existed.")
                
                # We can also proactively create next month's partitions here to ensure we never fail
                # if the app restarts aren't frequent enough.
                current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                next_month = (current_month + relativedelta(months=1))
                next_next_month = (next_month + relativedelta(months=1))
                
                for table in ["audit_logs", "token_cost_logs"]:
                    partition_name = f"{table}_{next_month.strftime('%Y_%m')}"
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {partition_name} 
                        PARTITION OF {table} 
                        FOR VALUES FROM ('{next_month.strftime('%Y-%m-%d')}') TO ('{next_next_month.strftime('%Y-%m-%d')}');
                    """)
                    
    except Exception as e:
        logger.error(f"Retention job failed: {e}")
