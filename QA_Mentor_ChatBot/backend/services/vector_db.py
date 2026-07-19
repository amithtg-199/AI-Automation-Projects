from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from core.config import settings

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)

def init_collection(client: QdrantClient, collection_name: str = "qa_mentor"):
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
