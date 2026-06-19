import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB", "test_gen_db"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", "5432")
)

cur = conn.cursor()

print("--- Checking Missing Tracking Tables Parity ---")
tables = ["requirements", "artifact_runs", "generated_artifacts", "token_usage", "token_analytics", "validation_results"]

for t in tables:
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);", (t,))
    exists = cur.fetchone()[0]
    print(f"Table '{t}': {'Found' if exists else 'MISSING'}")

cur.close()
conn.close()
print("--- Check Complete ---")
