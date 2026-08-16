import logging
import psycopg
from datetime import datetime, timedelta
from backend.core.config import settings

logger = logging.getLogger(__name__)

def bootstrap_postgres():
    """
    Connects to Postgres and creates the full IAM & Auditing schema.
    """
    conninfo = settings.POSTGRES_URL
    
    logger.info("Bootstrapping Postgres database schema for Batch 02...")
    
    try:
        # connect using autocommit to allow creating tables/partitions easily
        with psycopg.connect(conninfo, autocommit=True) as conn:
            with conn.cursor() as cur:
                # 1. Base projects table (from Batch 01)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    name TEXT PRIMARY KEY,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE
                );
                """)
                
                # 2. Roles
                cur.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    role_name TEXT PRIMARY KEY,
                    permissions JSONB DEFAULT '{}'::jsonb
                );
                """)
                # Pre-populate roles
                cur.execute("""
                INSERT INTO roles (role_name, permissions) 
                VALUES 
                    ('Admin', '{"all": true}'), 
                    ('Tester', '{"execute": true, "generate": true, "approve": true}'), 
                    ('Viewer', '{"read_only": true}')
                ON CONFLICT (role_name) DO NOTHING;
                """)

                # 3. Users
                cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role_name TEXT REFERENCES roles(role_name),
                    must_reset_password BOOLEAN DEFAULT TRUE,
                    password_set_at TIMESTAMPTZ DEFAULT NOW(),
                    failed_attempts INT DEFAULT 0,
                    locked_until TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """)

                # 4. User Projects (Join Table)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS user_projects (
                    username TEXT REFERENCES users(username) ON DELETE CASCADE,
                    project_name TEXT REFERENCES projects(name) ON DELETE CASCADE,
                    PRIMARY KEY(username, project_name)
                );
                """)

                # 5. Login Attempts (for IP rate limiting)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    username TEXT,
                    ip_address TEXT,
                    attempted_at TIMESTAMPTZ DEFAULT NOW(),
                    success BOOLEAN
                );
                CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip_address, attempted_at);
                """)

                # 6. Chat Messages (Durable store)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    thread_id TEXT,
                    project_name TEXT REFERENCES projects(name),
                    username TEXT REFERENCES users(username),
                    role TEXT,
                    content TEXT,
                    initiator TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY(thread_id, created_at)
                );
                """)

                # 7. Audit Logs (Partitioned by Month)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL,
                    username TEXT,
                    project_name TEXT,
                    action TEXT,
                    details JSONB,
                    ip_address TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY(id, created_at)
                ) PARTITION BY RANGE (created_at);
                """)

                # Pending approvals (Batch 08 / Flow B)
                cur.execute('''
                CREATE TABLE IF NOT EXISTS pending_approvals (
                    id VARCHAR(255) PRIMARY KEY,
                    thread_id VARCHAR(255),
                    project_name VARCHAR(100),
                    agent_name VARCHAR(100),
                    proposal_data JSONB,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')

                # Debugging cache (Batch 09)
                cur.execute('''
                CREATE TABLE IF NOT EXISTS debug_cache (
                    cache_key VARCHAR(64) PRIMARY KEY,
                    proposal_data JSONB,
                    seen_count INT DEFAULT 1,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')

                # 8. Token Cost Logs (Partitioned by Month)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS token_cost_logs (
                    id SERIAL,
                    username TEXT,
                    project_name TEXT,
                    agent_name TEXT,
                    provider TEXT,
                    model TEXT,
                    input_tokens INT,
                    output_tokens INT,
                    cost_usd NUMERIC(10, 6),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY(id, created_at)
                ) PARTITION BY RANGE (created_at);
                """)

                # Create partitions for the current and next month for safety
                now = datetime.now()
                current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                next_month = (current_month + timedelta(days=32)).replace(day=1)
                next_next_month = (next_month + timedelta(days=32)).replace(day=1)

                def create_partition(table_name, dt_start, dt_end):
                    partition_name = f"{table_name}_{dt_start.strftime('%Y_%m')}"
                    cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {partition_name} 
                    PARTITION OF {table_name} 
                    FOR VALUES FROM ('{dt_start.strftime('%Y-%m-%d')}') TO ('{dt_end.strftime('%Y-%m-%d')}');
                    """)

                create_partition("audit_logs", current_month, next_month)
                create_partition("audit_logs", next_month, next_next_month)
                
                create_partition("token_cost_logs", current_month, next_month)
                create_partition("token_cost_logs", next_month, next_next_month)

                # 9. RAG Eval Datasets (Batch 04)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS rag_eval_datasets (
                    dataset_id SERIAL PRIMARY KEY,
                    project_name TEXT REFERENCES projects(name),
                    created_by TEXT,
                    status TEXT DEFAULT 'pending_review',
                    is_canary BOOLEAN DEFAULT FALSE,
                    qa_pairs JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    accepted_at TIMESTAMPTZ
                );
                """)

                # 10. RAG Eval Results (Batch 04)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS rag_eval_results (
                    result_id SERIAL PRIMARY KEY,
                    dataset_id INT REFERENCES rag_eval_datasets(dataset_id),
                    project_name TEXT REFERENCES projects(name),
                    run_type TEXT, -- 'manual' or 'canary'
                    context_precision NUMERIC,
                    context_recall NUMERIC,
                    context_entities_recall NUMERIC,
                    faithfulness NUMERIC,
                    answer_relevancy NUMERIC,
                    details JSONB, -- per-question details
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """)

                logger.info("IAM & Audit schema initialized successfully.")

    except Exception as e:
        logger.error(f"Failed to bootstrap Postgres schema: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bootstrap_postgres()
