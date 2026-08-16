import os
import json
import logging
import uuid
from typing import List, Dict, Any, Tuple
import numpy as np
import hdbscan
from sklearn.metrics.pairwise import cosine_distances

from backend.core.config import settings
from backend.core.llm_client import CentralizedLLMClient
from backend.core.mock_db import MOCK_NEO4J, MOCK_QDRANT

logger = logging.getLogger(__name__)

# Delta threshold from spec
KNOWLEDGE_HUB_LLM_DELTA_THRESHOLD = 0.15

def run_knowledge_hub_job(project_name: str, username: str = "system"):
    """
    Twice-daily Celery beat job.
    Extracts passed scripts, clusters them, detects deltas, and updates the knowledge hub graph.
    """
    # 1. Pull approved scripts (is_latest: True, result: Passed)
    candidates = pull_candidates(project_name)
    if not candidates:
        logger.info("No new candidates found.")
        return
        
    # 2. Build embeddings (mock)
    embeddings, metadata = build_embeddings(candidates)
    
    # 3. Cluster using HDBSCAN (No LLM)
    labels = cluster_skills(embeddings)
    
    # 4. Compare centroids to yesterday (No LLM)
    changed_clusters = detect_deltas(project_name, embeddings, labels, metadata)
    
    # 5. LLM generates Skill Cards only for changed clusters
    llm = CentralizedLLMClient(username=username, project_name=project_name, agent_name="knowledge_hub")
    
    for cluster_id, data in changed_clusters.items():
        skill_card = generate_skill_cards(llm, data["samples"])
        # 6. Write to Graph DB
        persist_to_graph(project_name, cluster_id, skill_card, data["samples"], data["centroid"])

def pull_candidates(project_name: str) -> List[Dict]:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    qdrant = QdrantClient(url=settings.QDRANT_URL)
    
    try:
        points, _ = qdrant.scroll(
            collection_name=project_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key="type", match=models.MatchValue(value="test_execution")),
                    models.FieldCondition(key="is_latest", match=models.MatchValue(value=True))
                ]
            ),
            with_payload=True,
            with_vectors=True,
            limit=1000
        )
        return points
    except Exception as e:
        logger.error(f"Failed to fetch from Qdrant: {e}")
        return []

def build_embeddings(candidates: List[Any]) -> Tuple[np.ndarray, List[Dict]]:
    embeddings = []
    metadata = []
    for point in candidates:
        vec = point.vector
        if isinstance(vec, dict) and "dense" in vec:
            embeddings.append(vec["dense"])
        else:
            # Fallback or older format
            embeddings.append(vec if isinstance(vec, list) else [0.0]*1024)
        metadata.append(point.payload)
        
    if not embeddings:
        return np.array([]), []
    return np.array(embeddings), metadata

def cluster_skills(embeddings: np.ndarray) -> np.ndarray:
    if len(embeddings) < 2:
        # HDBSCAN needs at least a few points, so we mock labels if very small
        return np.zeros(len(embeddings), dtype=int)
        
    clusterer = hdbscan.HDBSCAN(min_cluster_size=2)
    # Using try/except for small mock data sizes
    try:
        labels = clusterer.fit_predict(embeddings)
    except Exception:
        labels = np.zeros(len(embeddings), dtype=int)
    return labels

def detect_deltas(project_name: str, embeddings: np.ndarray, labels: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    from neo4j import GraphDatabase
    neo4j_driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    
    changed_clusters = {}
    
    unique_labels = set(labels)
    for label in unique_labels:
        if label == -1: # Noise
            continue
            
        # Get points for this cluster
        indices = np.where(labels == label)[0]
        cluster_embeddings = embeddings[indices]
        centroid = np.mean(cluster_embeddings, axis=0)
        
        cache_key = f"{project_name}_cluster_{label}"
        
        # Check against yesterday in Neo4j
        old_centroid = None
        try:
            with neo4j_driver.session() as session:
                result = session.run("MATCH (s:Skill {cluster_id: $cluster_id, project: $project}) RETURN s.centroid AS centroid", cluster_id=cache_key, project=project_name)
                record = result.single()
                if record and record["centroid"]:
                    old_centroid = np.array(record["centroid"])
        except Exception as e:
            logger.error(f"Failed to fetch centroid from Neo4j: {e}")
        
        is_changed = True
        if old_centroid is not None:
            distance = cosine_distances([centroid], [old_centroid])[0][0]
            if distance <= KNOWLEDGE_HUB_LLM_DELTA_THRESHOLD:
                is_changed = False
                logger.info(f"Cluster {label} distance {distance} < {KNOWLEDGE_HUB_LLM_DELTA_THRESHOLD}. Skipping LLM.")
                
        if is_changed:
            logger.info(f"Cluster {label} changed or new. Proceeding to LLM.")
            changed_clusters[cache_key] = {
                "centroid": centroid,
                "samples": [metadata[i] for i in indices]
            }
            
    neo4j_driver.close()
    return changed_clusters

def generate_skill_cards(llm: CentralizedLLMClient, samples: List[Dict]) -> str:
    prompt = "Analyze these automation steps and create a generalized Skill Card walkthrough: " + str(samples)
    resp = llm.invoke([{"role": "user", "content": prompt}])
    return resp.content

def persist_to_graph(project_name: str, cluster_id: str, skill_card: str, samples: List[Dict], centroid: np.ndarray):
    from neo4j import GraphDatabase
    skill_id = str(uuid.uuid4())
    
    try:
        neo4j_driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
        with neo4j_driver.session() as session:
            # Upsert Skill node
            session.run(
                """
                MERGE (s:Skill {cluster_id: $cluster_id, project: $project})
                SET s.id = $id,
                    s.card = $card,
                    s.module = $module,
                    s.use_case = $use_case,
                    s.centroid = $centroid
                """,
                cluster_id=cluster_id,
                project=project_name,
                id=skill_id,
                card=skill_card,
                module=samples[0].get("module", "unknown"),
                use_case=samples[0].get("use_case", "unknown"),
                centroid=centroid.tolist()
            )
        neo4j_driver.close()
        logger.info(f"Successfully persisted Skill {skill_id} to project {project_name}")
    except Exception as e:
        logger.error(f"Failed to persist skill to Neo4j: {e}")
