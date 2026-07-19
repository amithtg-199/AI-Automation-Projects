from services.vector_db import get_qdrant_client
from services.ingestion import map_file_to_category
import sys

qdrant = get_qdrant_client()
project_name = "project_1"

if not qdrant.collection_exists(project_name):
    print("Collection does not exist")
    sys.exit(1)

collection_info = qdrant.get_collection(collection_name=project_name)
print(f"Points count from get_collection: {collection_info.points_count}")
print("Trying count()...")
offset = None
count = 0
total_records = 0
while True:
    records, next_offset = qdrant.scroll(
        collection_name=project_name,
        limit=1000,
        offset=offset,
        with_payload=["source"],
        with_vectors=False
    )
    total_records += len(records)
    print(f"Fetched {len(records)} records. Next offset: {next_offset}")
    if next_offset is None:
        break
    offset = next_offset
    count += 1
    if count > 10:
        print("INFINITE LOOP DETECTED")
        break

print(f"Total fetched: {total_records}")
