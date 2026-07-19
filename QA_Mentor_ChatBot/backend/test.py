from qdrant_client import QdrantClient
print([method for method in dir(QdrantClient) if not method.startswith('_')])
