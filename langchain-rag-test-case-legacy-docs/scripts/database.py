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

    def get_connection(self):
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
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO parent_chunks (document_id, project_id, version_id, project_snapshot_id, chunk_index, section_name, content, token_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING parent_id
            """, (doc_id, project_id, version_id, snapshot_id, chunk_index, section_name, content, token_count))
            parent_id = cur.fetchone()[0]
            self.conn.commit()
            return str(parent_id)
    def close(self):
        self.conn.close()
