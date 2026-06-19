import psycopg2
from qdrant_client import QdrantClient
from scripts.config import config
import os

print("Starting database cleanup...")

# Postgres
try:
    print(f"Connecting to Postgres at {config.POSTGRES_HOST}:{config.POSTGRES_PORT}...")
    conn = psycopg2.connect(config.get_pg_dsn())
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('TRUNCATE TABLE parent_chunks, documents, projects, versions CASCADE')
    cur.close()
    conn.close()
    print("Postgres Cleaned Successfully!")
except Exception as e:
    print(f"Postgres Error: {e}")

# Qdrant
try:
    print(f"Connecting to Qdrant at {config.QDRANT_HOST}:{config.QDRANT_PORT}...")
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    # Get all collections and delete them, or just delete VDRC_phase2
    # we will just delete the project if it exists, or maybe just blindly try
    try:
        client.delete_collection('VDRC_phase2')
        print("Qdrant collection 'VDRC_phase2' deleted!")
    except Exception as e:
        print(f"Qdrant collection deletion info: {e}")
        
    print("Qdrant Cleaned Successfully!")
except Exception as e:
    print(f"Qdrant Error: {e}")
