import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.vector_db import get_qdrant_client
from services.llm import get_mistral_client, generate_embeddings

qdrant = get_qdrant_client()
mistral = get_mistral_client()

query = "Can you give me a brief of selenium repo"
query_emb = generate_embeddings(mistral, [query])[0]

search_result = qdrant.query_points(
    collection_name="project_1",
    query=query_emb,
    limit=5
).points

print(f"Number of hits: {len(search_result)}")
for hit in search_result:
    print(f"Score: {hit.score}")
    print(f"Text: {hit.payload.get('text', '')[:100]}...")
    print("-" * 40)
