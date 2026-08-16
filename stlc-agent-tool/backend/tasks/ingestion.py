import os
import yaml
import json
import hashlib
import logging
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from neo4j import GraphDatabase

from backend.core.config import settings
from backend.tasks.celery_app import celery_app
from unstructured.partition.auto import partition
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastembed import SparseTextEmbedding
from langchain_openai import OpenAIEmbeddings

from backend.utils.resilience import exponential_backoff_with_jitter, wait_for_tokens

logger = logging.getLogger(__name__)

def generate_hash(text: str, metadata: dict) -> str:
    """Generate SHA256 hash of chunk content + critical metadata for versioning."""
    hasher = hashlib.sha256()
    hasher.update(text.encode("utf-8"))
    for k in sorted(metadata.keys()):
        hasher.update(str(k).encode("utf-8"))
        hasher.update(str(metadata[k]).encode("utf-8"))
    return hasher.hexdigest()

class AtomicIngester:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.qdrant = QdrantClient(url=settings.QDRANT_URL)
        self.neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        self.sparse_model = SparseTextEmbedding("Qdrant/bm25")
        self.dense_model = None
        if settings.LLM_API_KEY:
            try:
                self.dense_model = OpenAIEmbeddings(
                    model=settings.EMBEDDING_MODEL or "text-embedding-3-small", 
                    api_key=settings.LLM_API_KEY
                )
            except Exception as e:
                logger.warning(f"Could not init dense embedder: {e}")
                
        # Ensure collection exists
        try:
            self.qdrant.get_collection(self.project_name)
        except Exception:
            # Create collection with hybrid search config
            logger.info(f"Creating Qdrant collection {self.project_name}")
            vec_size = 1536
            if self.dense_model:
                try:
                    vec_size = len(self._embed_dense("test initialization"))
                except:
                    pass
            
            self.qdrant.create_collection(
                collection_name=self.project_name,
                vectors_config={
                    "dense": qdrant_models.VectorParams(
                        size=vec_size,
                        distance=qdrant_models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": qdrant_models.SparseVectorParams()
                }
            )
        
    def _embed_dense(self, text: str) -> list:
        if self.dense_model:
            # Consume tokens (approx 1 token per 4 chars)
            tokens_required = len(text) // 4
            wait_for_tokens(tokens_required)
            return self.dense_model.embed_query(text)
        return [0.0] * 1024 # Fallback
        
    def _embed_sparse(self, text: str):
        # SparseTextEmbedding returns an iterable of SparseEmbedding objects
        embeddings = list(self.sparse_model.embed([text]))
        if embeddings:
            return qdrant_models.SparseVector(
                indices=embeddings[0].indices.tolist(),
                values=embeddings[0].values.tolist()
            )
        return qdrant_models.SparseVector(indices=[], values=[])

    @exponential_backoff_with_jitter(max_retries=settings.MAX_RETRIES, base_delay=settings.FALLBACK_SECONDS)
    def ingest_chunk(self, text: str, metadata: dict):
        chunk_hash = generate_hash(text, metadata)
        metadata["hashed_value"] = chunk_hash
        metadata["is_latest"] = True
        
        # 1. Flip old chunks to is_latest=False atomically
        unique_key = metadata.get("requirement-unique-id") or metadata.get("jira-unique-id") or metadata.get("file_name")
        
        q_filter = []
        if unique_key:
            key_name = "requirement-unique-id" if "requirement-unique-id" in metadata else ("jira-unique-id" if "jira-unique-id" in metadata else "file_name")
            q_filter.append(qdrant_models.FieldCondition(
                key=key_name,
                match=qdrant_models.MatchValue(value=unique_key)
            ))
            
        old_point_ids = []
        if q_filter:
            scroll_res = self.qdrant.scroll(
                collection_name=self.project_name,
                scroll_filter=qdrant_models.Filter(must=q_filter),
                with_payload=False,
                limit=100
            )[0]
            old_point_ids = [p.id for p in scroll_res]
            
            if old_point_ids:
                self.qdrant.set_payload(
                    collection_name=self.project_name,
                    payload={"is_latest": False},
                    points=old_point_ids
                )
        
        # 2. Insert new chunk into Qdrant
        import uuid
        point_id = str(uuid.uuid4())
        dense_vec = self._embed_dense(text)
        sparse_vec = self._embed_sparse(text)
        
        self.qdrant.upsert(
            collection_name=self.project_name,
            points=[
                qdrant_models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vec,
                        "sparse": sparse_vec
                    },
                    payload={"text": text, **metadata}
                )
            ]
        )
        
        # 3. Update Neo4j graph
        try:
            with self.neo4j_driver.session() as session:
                if unique_key:
                    session.run(
                        """
                        MATCH (c:Chunk)
                        WHERE c.unique_key = $unique_key
                        SET c.is_latest = False
                        """,
                        unique_key=unique_key
                    )
                
                # Check mapping for Jira to Requirement
                jira_id = metadata.get("jira-unique-id")
                req_id = metadata.get("requirement-unique-id")
                
                session.run(
                    """
                    MERGE (c:Chunk {hashed_value: $hash})
                    SET c.text = $text, c.is_latest = True, c.unique_key = $unique_key, c.jira_id = $jira_id, c.req_id = $req_id
                    """,
                    hash=chunk_hash, text=text, unique_key=unique_key, jira_id=jira_id, req_id=req_id
                )
                
                # Link Jira and Req if both present
                if jira_id and req_id:
                    session.run(
                        """
                        MATCH (j:Chunk {jira_id: $jira_id}), (r:Chunk {req_id: $req_id})
                        MERGE (j)-[:IMPLEMENTS]->(r)
                        """,
                        jira_id=jira_id, req_id=req_id
                    )
                    logger.debug(f"Created Neo4j [:IMPLEMENTS] link for Jira {jira_id} -> Req {req_id}")
            logger.info(f"Ingested chunk [{chunk_hash[:8]}...] (type: {metadata.get('type')}) successfully into Qdrant & Neo4j.")
        except Exception as e:
            logger.error(f"Neo4j transaction failed for {chunk_hash}, rolling back Qdrant insert.")
            self.qdrant.delete(collection_name=self.project_name, points_selector=[point_id])
            if old_point_ids:
                 self.qdrant.set_payload(
                    collection_name=self.project_name,
                    payload={"is_latest": True},
                    points=old_point_ids
                )
            raise e

@celery_app.task
def run_project_ingestion(project_name: str):
    """
    Scans the input_folder.yaml mappings, test cases, and jiras, extracting and chunking them.
    Uses a Redis lock to prevent overlapping ingestion cycles.
    """
    logger.info(f"Starting ingestion for project: {project_name}")
    
    lock_id = f"stlc:lock:ingestion:{project_name}"
    from backend.utils.resilience import redis_client
    
    if redis_client:
        # Try to acquire a lock with a 55 minute timeout (since schedule is 60 mins)
        lock = redis_client.lock(lock_id, timeout=3300, blocking=False)
        if not lock.acquire():
            logger.warning(f"Ingestion for {project_name} is already running. Skipping this cycle.")
            return
            
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent.parent / "projects" / project_name
        yaml_path = base_dir / "input_folder.yaml"
        
        ingester = AtomicIngester(project_name)
        splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=100)
        
        all_chunks = []

        # 1. Standard docs
        if yaml_path.exists():
            with open(yaml_path, "r") as f:
                mappings = yaml.safe_load(f)
                
            for doc_type, rel_path in mappings.items():
                doc_dir = base_dir / rel_path
                if not doc_dir.exists():
                    continue
                    
                for file in doc_dir.glob("*"):
                    if file.is_file() and file.name != "jira_ids.txt":
                        try:
                            logger.info(f"Parsing PRD/Swagger document '{file.name}' with unstructured.io...")
                            elements = partition(filename=str(file))
                            full_text = "\n\n".join([str(el) for el in elements if str(el).strip()])
                            
                            split_texts = splitter.split_text(full_text)
                            logger.debug(f"Document '{file.name}' chunked into {len(split_texts)} text blocks.")
                            req_id = f"req-{file.stem}"
                            for idx, txt in enumerate(split_texts):
                                all_chunks.append({
                                    "text": txt,
                                    "metadata": {
                                        "file_name": file.name, 
                                        "type": doc_type, 
                                        "version": "1.0",
                                        "requirement-unique-id": req_id,
                                        "chunk_index": idx
                                    }
                                })
                        except Exception as e:
                            logger.error(f"Failed to process {file.name}: {e}")

        # 2. Jira IDs
        jira_txt = base_dir / "docs" / "JIRA" / "jira_ids.txt"
        if jira_txt.exists():
            content = jira_txt.read_text()
            ids = [i.strip() for i in content.split(",") if i.strip() and not i.startswith("#")]
            logger.info(f"Found {len(ids)} Jira stories for ingestion.")
            for jid in ids:
                jira_text = f"Jira Ticket Content for {jid}"
                split_texts = splitter.split_text(jira_text)
                for idx, txt in enumerate(split_texts):
                    all_chunks.append({
                        "text": txt, 
                        "metadata": {
                            "jira-unique-id": jid, 
                            "description": jira_text,
                            "type": "jira_exports", 
                            "version": "1.0",
                            "chunk_index": idx
                        }
                    })

        # 3. Test Cases / Executions
        test_results_dir = base_dir / "test_case_result"
        if test_results_dir.exists():
            for dt_folder in test_results_dir.iterdir():
                if dt_folder.is_dir():
                    for json_file in dt_folder.glob("*.json"):
                        try:
                            with open(json_file, 'r') as jf:
                                data = json.load(jf)
                            txt = json.dumps(data, indent=2)
                            split_texts = splitter.split_text(txt)
                            for idx, txt in enumerate(split_texts):
                                all_chunks.append({
                                    "text": txt,
                                    "metadata": {
                                        "file_name": json_file.name,
                                        "type": "test_execution",
                                        "execution_datetime": dt_folder.name,
                                        "version": "1.0",
                                        "chunk_index": idx
                                    }
                                })
                        except Exception as e:
                            logger.error(f"Failed to process test result {json_file.name}: {e}")

        # Batch and ingest
        max_batches = settings.MAX_BATCHES
        batch_size = max(1, len(all_chunks) // max_batches) if max_batches > 0 else len(all_chunks)
        
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            logger.info(f"Ingesting batch {i//batch_size + 1}...")
            
            for chunk in batch:
                try:
                    ingester.ingest_chunk(chunk["text"], chunk["metadata"])
                except Exception as e:
                    logger.error(f"Final ingest failure for chunk: {e}")
                        
        logger.info(f"Ingestion completed for project: {project_name}")
    finally:
        if redis_client and 'lock' in locals() and lock.owned():
            lock.release()
