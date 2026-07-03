import psycopg2
from psycopg2.extras import RealDictCursor
from scripts.config import config
import uuid

class PostgresDB:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT
        )
        self.conn.autocommit = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def ensure_connection(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
        except Exception:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = psycopg2.connect(
                dbname=config.POSTGRES_DB,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD,
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT
            )
            self.conn.autocommit = False

    def get_connection(self):
        self.ensure_connection()
        return self.conn

    def get_or_create_project(self, project_name: str) -> str:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT project_id FROM projects WHERE project_name = %s", (project_name,))
            res = cur.fetchone()
            if res:
                return str(res["project_id"])
            
            cur.execute(
                "INSERT INTO projects (project_name) VALUES (%s) RETURNING project_id",
                (project_name,)
            )
            project_id = cur.fetchone()["project_id"]
            self.conn.commit()
            return str(project_id)

    def create_version(self, project_id: str) -> dict:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Demote old latest
            cur.execute("UPDATE versions SET is_latest = FALSE WHERE project_id = %s", (project_id,))
            
            # Get next version number
            cur.execute("SELECT COALESCE(MAX(version_number), 0) + 1 as next_v FROM versions WHERE project_id = %s", (project_id,))
            next_v = cur.fetchone()["next_v"]
            
            snapshot_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO versions (project_id, version_number, project_snapshot_id, is_latest)
                VALUES (%s, %s, %s, TRUE)
                RETURNING version_id, version_number, project_snapshot_id
            """, (project_id, next_v, snapshot_id))
            
            ver = cur.fetchone()
            self.conn.commit()
            return dict(ver)

    def insert_document(self, project_id: str, version_id: str, snapshot_id: str, file_name: str, doc_type: str) -> str:
        self.ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents (project_id, version_id, project_snapshot_id, file_name, document_type)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING document_id
            """, (project_id, version_id, snapshot_id, file_name, doc_type))
            doc_id = cur.fetchone()[0]
            self.conn.commit()
            return str(doc_id)

    def insert_parent_chunk(self, doc_id: str, project_id: str, version_id: str, snapshot_id: str, chunk_index: int, section_name: str, content: str, token_count: int) -> str:
        self.ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO parent_chunks (document_id, project_id, version_id, project_snapshot_id, chunk_index, section_name, content, search_vector, token_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, to_tsvector('english', %s), %s)
                RETURNING parent_id
            """, (doc_id, project_id, version_id, snapshot_id, chunk_index, section_name, content, content, token_count))
            parent_id = cur.fetchone()[0]
            self.conn.commit()
            return str(parent_id)

    def get_latest_version(self, project_id: str) -> dict:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT version_id, version_number, project_snapshot_id FROM versions WHERE project_id = %s AND is_latest = TRUE LIMIT 1", (project_id,))
            res = cur.fetchone()
            return dict(res) if res else {}

    def search_parent_chunks_bm25(self, project_id: str, query: str, limit: int = 20) -> list:
        """
        Performs BM25 exact keyword ranking using PostgreSQL full-text search (ts_rank_cd).
        Returns a list of dicts with parent_id, content, section_name, and score from the latest active version.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT parent_id, content, section_name,
                       ts_rank_cd(search_vector, websearch_to_tsquery('english', %s)) AS bm25_score
                FROM parent_chunks
                WHERE project_id = %s 
                  AND version_id = (SELECT version_id FROM versions WHERE project_id = %s AND is_latest = TRUE LIMIT 1)
                  AND search_vector @@ websearch_to_tsquery('english', %s)
                ORDER BY bm25_score DESC
                LIMIT %s
            """, (query, project_id, project_id, query, limit))
            results = cur.fetchall()
            return [dict(r) for r in results]

    def insert_evaluation_feedback(self, project_name: str, question: str, answer: str, contexts: list, ground_truth: str, faithfulness: float, answer_relevancy: float, context_precision: float, context_recall: float) -> str:
        import json
        import math
        def _clean_float(f):
            if f is None or not isinstance(f, (int, float)) or math.isnan(f) or math.isinf(f):
                return None
            return float(f)
        self.ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO evaluation_feedback (project_name, question, answer, contexts, ground_truth, faithfulness, answer_relevancy, context_precision, context_recall)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING feedback_id
            """, (project_name, question, answer, json.dumps(contexts), ground_truth, _clean_float(faithfulness), _clean_float(answer_relevancy), _clean_float(context_precision), _clean_float(context_recall)))
            fid = cur.fetchone()[0]
            self.conn.commit()
            return str(fid)

    def get_pending_feedback(self, project_name: str) -> list:
        import math
        def sanitize_val(val):
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return None
            if hasattr(val, "isoformat"):
                return val.isoformat()
            if isinstance(val, uuid.UUID):
                return str(val)
            if isinstance(val, dict):
                return {k: sanitize_val(v) for k, v in val.items()}
            if isinstance(val, list):
                return [sanitize_val(v) for v in val]
            return val

        self.ensure_connection()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM evaluation_feedback WHERE project_name = %s AND human_status = 'PENDING' ORDER BY created_at DESC
            """, (project_name,))
            return [sanitize_val(dict(r)) for r in cur.fetchall()]

    def submit_human_review(self, feedback_id: str, status: str, notes: str = "") -> bool:
        self.ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE evaluation_feedback SET human_status = %s, reviewer_notes = %s, updated_at = NOW() WHERE feedback_id = %s
            """, (status, notes, feedback_id))
            self.conn.commit()
            return cur.rowcount > 0

    def submit_human_review_all(self, project_name: str, status: str, notes: str = "") -> int:
        self.ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE evaluation_feedback SET human_status = %s, reviewer_notes = %s, updated_at = NOW() WHERE project_name = %s AND human_status = 'PENDING'
            """, (status, notes, project_name))
            updated_count = cur.rowcount
            self.conn.commit()
            return updated_count

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
