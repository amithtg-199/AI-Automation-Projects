import logging
from typing import List, Dict, Any, Tuple
from qdrant_client import QdrantClient
from qdrant_client.http import models
from neo4j import GraphDatabase

from fastembed import SparseTextEmbedding
from langchain_openai import OpenAIEmbeddings

from backend.core.config import settings
from backend.utils.resilience import exponential_backoff_with_jitter, wait_for_tokens

logger = logging.getLogger(__name__)

class BGERerankerStub:
    """
    A placeholder for the BGE Cross-Encoder reranker.
    In a real implementation, this would use sentence-transformers CrossEncoder.
    """
    def rerank(self, query: str, documents: List[str]) -> List[Tuple[float, str]]:
        # Mock logic: returns them in the original order with dummy scores
        return [(1.0 - (0.1 * i), doc) for i, doc in enumerate(documents)]

@exponential_backoff_with_jitter(max_retries=settings.MAX_RETRIES, base_delay=settings.FALLBACK_SECONDS)
def execute_rrf_search(query: str, top_k: int) -> List[dict]:
    qdrant = QdrantClient(url=settings.QDRANT_URL)
    
    # Generate Dense Embedding
    dense_vector = [0.0] * 1024
    if settings.LLM_API_KEY:
        try:
            dense_model = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL or "text-embedding-3-small", 
                api_key=settings.LLM_API_KEY
            )
            # Rate limit enforcement
            wait_for_tokens(len(query) // 4)
            dense_vector = dense_model.embed_query(query)
        except Exception as e:
            logger.warning(f"Dense embed failed: {e}")
            
    # Generate Sparse Embedding
    sparse_model = SparseTextEmbedding("Qdrant/bm25")
    embeddings = list(sparse_model.embed([query]))
    sparse_vector = models.SparseVector(indices=[], values=[])
    if embeddings:
        sparse_vector = models.SparseVector(
            indices=embeddings[0].indices.tolist(),
            values=embeddings[0].values.tolist()
        )
        
    prefetch_dense = models.Prefetch(
        query=dense_vector,
        using="dense",
        limit=top_k * 2
    )
    
    prefetch_sparse = models.Prefetch(
        query=sparse_vector,
        using="sparse",
        limit=top_k * 2
    )
    
    # RRF merging
    search_result = qdrant.query_points(
        collection_name=settings.PROJECT_NAME if hasattr(settings, "PROJECT_NAME") else "default", # Need actual project_name parameter passing
        prefetch=[prefetch_dense, prefetch_sparse],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="is_latest",
                    match=models.MatchValue(value=True)
                )
            ]
        ),
        limit=top_k,
        with_payload=True
    )
    return search_result.points

@exponential_backoff_with_jitter(max_retries=settings.MAX_RETRIES, base_delay=settings.FALLBACK_SECONDS)
def execute_neo4j_expansion(hashes: List[str]) -> Dict[str, List[dict]]:
    logger.info(f"Expanding Graph Context for {len(hashes)} chunk hashes")
    graph_context_map = {}
    driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    with driver.session() as session:
        result = session.run('''
            MATCH (c:Chunk)-[r]-(n)
            WHERE c.hashed_value IN $hashes AND c.is_latest = True
            WITH c, n, r
            WITH c, collect(n)[..5] as neighbors
            RETURN c.hashed_value as hash, neighbors
        ''', hashes=hashes)
        for record in result:
            neighbors = [dict(node) for node in record["neighbors"]]
            graph_context_map[record["hash"]] = neighbors
            logger.debug(f"Graph expansion found {len(neighbors)} neighbors for hash {record['hash'][:8]}...")
            
    logger.info(f"Graph expansion complete. Enhanced {len(graph_context_map)} chunks with relationships.")
    return graph_context_map

def retrieve_rag_context(project_name: str, query: str, top_k: int = 5) -> List[str]:
    """
    Executes Dense + Sparse retrieval with RRF merging, filters by is_latest: True,
    pulls bounded graph context from Neo4j, and reranks.
    """
    try:
        # We need to hack QdrantClient to use project_name since execute_rrf_search takes it from settings originally.
        # Let's adjust the implementation to pass project_name to the wrapper.
        pass # implemented in inline scope to support backoff
    except Exception as e:
        logger.error(f"Retrieval wrapper failed: {e}")
        return []
        
    @exponential_backoff_with_jitter(max_retries=settings.MAX_RETRIES, base_delay=settings.FALLBACK_SECONDS)
    def _do_rrf(project_name, query, top_k):
        qdrant = QdrantClient(url=settings.QDRANT_URL)
        dense_vector = [0.0] * 1024
        if settings.LLM_API_KEY:
            try:
                dense_model = OpenAIEmbeddings(
                    model=settings.EMBEDDING_MODEL or "text-embedding-3-small", 
                    api_key=settings.LLM_API_KEY
                )
                wait_for_tokens(len(query) // 4)
                dense_vector = dense_model.embed_query(query)
            except Exception as e:
                logger.warning(f"Dense embed failed: {e}")
                
        sparse_model = SparseTextEmbedding("Qdrant/bm25")
        embeddings = list(sparse_model.embed([query]))
        sparse_vector = models.SparseVector(indices=[], values=[])
        if embeddings:
            sparse_vector = models.SparseVector(
                indices=embeddings[0].indices.tolist(),
                values=embeddings[0].values.tolist()
            )
            
        prefetch_dense = models.Prefetch(query=dense_vector, using="dense", limit=top_k * 2)
        prefetch_sparse = models.Prefetch(query=sparse_vector, using="sparse", limit=top_k * 2)
        
        search_result = qdrant.query_points(
            collection_name=project_name,
            prefetch=[prefetch_dense, prefetch_sparse],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=models.Filter(
                must=[models.FieldCondition(key="is_latest", match=models.MatchValue(value=True))]
            ),
            limit=top_k,
            with_payload=True
        )
        return search_result.points
        
    try:
        logger.info(f"Retrieval initiated for project '{project_name}' with query: '{query[:50]}...'")
        points = _do_rrf(project_name, query, top_k)
        
        logger.info(f"Qdrant RRF returned {len(points)} matching points.")
        
        merged_chunks = []
        hashes = []
        for point in points:
            payload = point.payload or {}
            chunk_text = payload.get("text", "")
            chunk_hash = payload.get("hashed_value", "")
            merged_chunks.append({"text": chunk_text, "hash": chunk_hash})
            if chunk_hash:
                hashes.append(chunk_hash)
                
        graph_context_map = execute_neo4j_expansion(hashes) if hashes else {}
        
        documents_to_rerank = []
        for chunk in merged_chunks:
            text = chunk["text"]
            neighbors = graph_context_map.get(chunk["hash"], [])
            if neighbors:
                context_str = " | ".join([str(n) for n in neighbors])
                text = f"{text}\nGraph Context: {context_str}"
            documents_to_rerank.append(text)
            
        if not documents_to_rerank:
            logger.warning("No documents found to rerank.")
            return []
            
        # Rerank and consume tokens for reranker stub
        logger.info(f"Reranking {len(documents_to_rerank)} documents...")
        wait_for_tokens(len(query) // 4 * len(documents_to_rerank))
        reranker = BGERerankerStub()
        reranked = reranker.rerank(query, documents_to_rerank)
        
        final_docs = [doc for score, doc in reranked if score > 0.5]
        logger.info(f"Reranking complete. Selected {len(final_docs)} final context documents passing threshold.")
        return final_docs[:top_k]
        
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return []
