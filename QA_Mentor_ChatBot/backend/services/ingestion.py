from qdrant_client.models import PointStruct
from services.vector_db import get_qdrant_client, init_collection
from services.llm import get_mistral_client, generate_embeddings
from core.state import progress_store
import uuid
import hashlib
import os

def get_text_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

def map_file_to_category(file_path: str) -> str:
    p = file_path.lower()
    if "selenium" in p: return "selenium"
    if "playwright" in p: return "playwright"
    if "test" in p: return "tests"
    if "jira" in p: return "jira"
    if "prd" in p or "brd" in p or "srs" in p: return "prd"
    if "note" in p: return "notes"
    if "jenkins" in p: return "jenkins"
    if "glossary" in p: return "glossary"
    return "docs"

def ingest_directory(project_name: str):
    qdrant = get_qdrant_client()
    mistral = get_mistral_client()
    collection_name = project_name
    base_dir = os.path.join("input_data", project_name)
    
    init_collection(qdrant, collection_name)
    
    # Initialize Progress State
    progress_store[project_name] = {
        "status": "scanning",
        "total_files": 0,
        "extracted_files": 0,
        "total_chunks": 0,
        "embedded_chunks": 0,
        "category_chunks": {}
    }
    
    # Scan directory
    all_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith((".txt", ".md", ".csv", ".py", ".ts", ".tsx")):
                all_files.append(os.path.join(root, file))
                
    progress_store[project_name]["total_files"] = len(all_files)
    progress_store[project_name]["status"] = "processing"
    
    total_chunks = 0
    # Process files
    for file_path in all_files:
        category = map_file_to_category(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = splitter.split_text(text)
            if not chunks: continue
            
            # Scaffolding for Graph RAG extraction
            from services.graph_db import get_neo4j_driver
            driver = get_neo4j_driver()
            if driver:
                try:
                    with driver.session() as session:
                        session.run(
                            """
                            MERGE (c:Category {name: $category})
                            MERGE (d:Document {path: $source})
                            MERGE (d)-[:BELONGS_TO]->(c)
                            """,
                            category=category,
                            source=file_path
                        )
                except Exception as e:
                    print(f"GraphRAG error: {e}")
            
            progress_store[project_name]["total_chunks"] += len(chunks)
            
            # API Batching (Max 50 per request to avoid Mistral Token Limits)
            BATCH_SIZE = 50
            points = []
            
            for i in range(0, len(chunks), BATCH_SIZE):
                batch_chunks = chunks[i:i+BATCH_SIZE]
                embeddings = generate_embeddings(mistral, batch_chunks)
                
                for j, (chunk, emb) in enumerate(zip(batch_chunks, embeddings)):
                    chunk_idx = i + j
                    chunk_hash = get_text_hash(chunk)
                    points.append(PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_hash)),
                        vector=emb,
                        payload={
                            "text": chunk,
                            "source": file_path,
                            "chunk_index": chunk_idx
                        }
                    ))
                progress_store[project_name]["embedded_chunks"] += len(batch_chunks)
                progress_store[project_name]["category_chunks"][category] = \
                    progress_store[project_name]["category_chunks"].get(category, 0) + len(batch_chunks)
            
            qdrant.upsert(
                collection_name=collection_name,
                points=points
            )
            total_chunks += len(chunks)
            progress_store[project_name]["extracted_files"] += 1
            print(f"Successfully ingested {file_path}")
        except Exception as e:
            print(f"Failed to ingest {file_path}: {e}")
            
    progress_store[project_name]["status"] = "complete"
    print(f"Ingestion complete. Total chunks: {total_chunks}")
    return {"status": "success", "chunks_ingested": total_chunks}
