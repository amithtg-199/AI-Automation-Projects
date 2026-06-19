import os
import glob
import uuid
import requests
from requests.auth import HTTPBasicAuth
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http import models
from langchain_text_splitters import TokenTextSplitter

from scripts.config import config
from scripts.database import PostgresDB
from scripts.logger import get_logger
from scripts.llm_factory import get_embeddings
from scripts.metrics import INGESTION_DOCUMENTS_PROCESSED, INGESTION_BYTES_EXTRACTED, INGESTION_PARENT_CHUNKS, INGESTION_CHILD_CHUNKS

logger = get_logger(__name__)

class IngestionPipeline:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.db = PostgresDB()
        
        self.qdrant = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
        self.embeddings = get_embeddings()
        
        # Ensure collection exists
        self._ensure_qdrant_collection()

        # Exact token sizes requested: 2000 + 200 overlap for parent, 400 + 50 overlap for child
        self.parent_splitter = TokenTextSplitter(chunk_size=2000, chunk_overlap=200)
        self.child_splitter = TokenTextSplitter(chunk_size=400, chunk_overlap=50)

    def _ensure_qdrant_collection(self):
        try:
            self.qdrant.get_collection(self.project_name)
        except Exception:
            self.qdrant.create_collection(
                collection_name=self.project_name,
                vectors_config=models.VectorParams(
                    size=1024, # Mistral embedding size is 1024
                    distance=models.Distance.COSINE
                )
            )

    def run(self):
        logger.info(f"Starting ingestion for project: {self.project_name}")
        
        # 1. Setup DB Versioning
        project_id = self.db.get_or_create_project(self.project_name)
        version_data = self.db.create_version(project_id)
        version_id = version_data["version_id"]
        snapshot_id = version_data["project_snapshot_id"]
        
        logger.info(f"Created version {version_data['version_number']} (snapshot: {snapshot_id})")

        # 2. Process Dynamic Input Folders (via config.yaml)
        config_yaml_path = os.path.join(config.INPUT_ROOT, self.project_name, "config.yaml")
        if os.path.exists(config_yaml_path):
            import yaml
            with open(config_yaml_path, "r") as f:
                rules = yaml.safe_load(f) or []
            
            for rule in rules:
                folder_name = rule.get("folder", "")
                action = rule.get("action", "")
                
                if action == "extract_to_md":
                    folder_path = os.path.join(config.INPUT_ROOT, self.project_name, folder_name)
                    if os.path.exists(folder_path):
                        files = glob.glob(os.path.join(folder_path, "**", "*.*"), recursive=True)
                        for f in files:
                            ext = f.split('.')[-1].lower()
                            if ext in ['docx', 'pdf', 'md', 'txt', 'csv']:
                                logger.info(f"Processing {rule.get('name', 'File')}: {os.path.basename(f)}")
                                try:
                                    with open(f, "rb") as file_data:
                                        res = requests.post(
                                            f"{config.EXTRACTION_SERVICE_URL}/extract",
                                            files={"file": (os.path.basename(f), file_data)}
                                        )
                                    if res.status_code == 200:
                                        md_text = res.json().get("markdown", "")
                                        self._process_document(
                                        project_id=project_id,
                                        version_id=version_id,
                                        snapshot_id=snapshot_id,
                                        file_name=os.path.basename(f),
                                        doc_type=rule.get("name", "DOC"),
                                        markdown_content=md_text
                                    )
                                    else:
                                        logger.error(f"Extraction service failed for {f}: {res.status_code} - {res.text}")
                                except Exception as e:
                                    logger.error(f"Failed to process {f}: {e}")
                elif action == "fetch_jira_then_md":
                    self._process_jira(project_id, version_id, snapshot_id)
        else:
            # Fallback to hardcoded PRD/Jira processing if config.yaml is missing
            prd_folder = os.path.join(config.INPUT_ROOT, self.project_name, "prd")
            if os.path.exists(prd_folder):
                files = glob.glob(os.path.join(prd_folder, "**", "*.*"), recursive=True)
                for f in files:
                    ext = f.split('.')[-1].lower()
                    if ext in ['docx', 'pdf', 'md', 'txt', 'csv']:
                        logger.info(f"Processing PRD: {os.path.basename(f)}")
                        try:
                            with open(f, "rb") as file_data:
                                res = requests.post(
                                    f"{config.EXTRACTION_SERVICE_URL}/extract",
                                    files={"file": (os.path.basename(f), file_data)}
                                )
                            if res.status_code == 200:
                                md_text = res.json().get("markdown", "")
                                self._process_document(
                                project_id=project_id,
                                version_id=version_id,
                                snapshot_id=snapshot_id,
                                file_name=os.path.basename(f),
                                doc_type="PRD",
                                markdown_content=md_text
                            )
                            else:
                                logger.error(f"Extraction service failed for {f}: {res.status_code} - {res.text}")
                        except Exception as e:
                            logger.error(f"Failed to process {f}: {e}")
            
            # 3. Process JIRA Issues (Fallback)
            self._process_jira(project_id, version_id, snapshot_id)
        
        self.db.close()
        logger.info("Ingestion complete.")

    def _process_jira(self, project_id, version_id, snapshot_id):
        if not config.JIRA_URL or not config.JIRA_USERNAME:
            logger.warning("Jira credentials not set, skipping Jira ingestion.")
            return

        logger.info("Fetching Jira issues...")
        url = f"{config.JIRA_URL}/rest/api/3/search/jql"
        auth = HTTPBasicAuth(config.JIRA_USERNAME, config.JIRA_API_TOKEN)
        
        # Read Jira IDs from jira_id.txt
        jira_file_path = os.path.join(config.INPUT_ROOT, self.project_name, "jira", "jira_id.txt")
        jira_ids = []
        if os.path.exists(jira_file_path):
            with open(jira_file_path, "r") as f:
                content = f.read().strip()
                if content:
                    # Handle both comma separated and newline separated
                    content = content.replace('\\n', ',')
                    jira_ids = [j.strip() for j in content.split(',') if j.strip()]
                    
        if not jira_ids:
            logger.info(f"No Jira IDs found in {jira_file_path}. Skipping Jira extraction.")
            return
            
        # The new JIRA API expects POST to /rest/api/3/search or /rest/api/3/search/jql
        jql = f"key IN ({','.join(jira_ids)})"
        
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        payload = {
            "jql": jql, 
            "maxResults": 100,
            "fields": ["key", "summary", "description", "attachment"]
        }
        
        try:
            res = requests.post(url, auth=auth, headers=headers, json=payload)
        except Exception as e:
            logger.error(f"Failed to connect to Jira API: {e}")
            return
            
        if res.status_code == 200:
            data = res.json()
            issues = data.get("issues", [])
            for issue in issues:
                if not isinstance(issue, dict) or "key" not in issue:
                    logger.warning(f"Unexpected issue format received from Jira: {issue}")
                    continue
                    
                key = issue["key"]
                
                # In Jira v3, fields.description is an Atlassian Document Format (ADF) object, not a string.
                fields = issue.get("fields", {})
                summary = fields.get("summary", "")
                desc_obj = fields.get("description")
                desc = ""
                if isinstance(desc_obj, str):
                    desc = desc_obj
                elif isinstance(desc_obj, dict):
                    # Extremely basic ADF text extraction
                    try:
                        texts = []
                        for block in desc_obj.get("content", []):
                            for node in block.get("content", []):
                                if node.get("type") == "text":
                                    texts.append(node.get("text", ""))
                        desc = "\n".join(texts)
                    except:
                        pass
                
                md_text = f"# {key}: {summary}\n\n{desc}\n"
                
                # Process Attachments
                attachments = fields.get("attachment", [])
                if attachments:
                    temp_dir = os.path.join(os.path.dirname(__file__), "temp_attachments")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    for att in attachments:
                        filename = att.get("filename", "")
                        content_url = att.get("content", "")
                        ext = filename.split('.')[-1].lower() if '.' in filename else ""
                        
                        # Docling supports a wide variety of formats including office documents
                        if ext in ['docx', 'pdf', 'md', 'txt', 'xlsx', 'csv', 'pptx'] and content_url:
                            logger.info(f"Downloading Jira attachment: {filename} for {key}")
                            try:
                                att_res = requests.get(content_url, auth=auth, stream=True)
                                if att_res.status_code == 200:
                                    tmp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")
                                    with open(tmp_path, 'wb') as f:
                                        for chunk in att_res.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                            
                                    logger.info(f"Extracting text from attachment: {filename}")
                                    with open(tmp_path, "rb") as file_data:
                                        ext_res = requests.post(
                                            f"{config.EXTRACTION_SERVICE_URL}/extract",
                                            files={"file": (filename, file_data)}
                                        )
                                    if ext_res.status_code == 200:
                                        att_md = ext_res.json().get("markdown", "")
                                        md_text += f"\n\n## Attachment: {filename}\n\n{att_md}\n"
                                    else:
                                        logger.error(f"Extraction service failed for {filename}: {ext_res.status_code} - {ext_res.text}")
                                    
                                    # Cleanup
                                    os.remove(tmp_path)
                                else:
                                    logger.error(f"Failed to download attachment {filename}: {att_res.status_code}")
                            except Exception as e:
                                logger.error(f"Error processing attachment {filename}: {e}")
                                
                logger.info(f"Processing JIRA: {key}")
                self._process_document(
                    project_id=project_id,
                    version_id=version_id,
                    snapshot_id=snapshot_id,
                    file_name=key,
                    doc_type="JIRA",
                    markdown_content=md_text
                )
        else:
            logger.error(f"Jira API error: {res.status_code} - {res.text}")

    def _process_document(self, project_id, version_id, snapshot_id, file_name, doc_type, markdown_content):
        if not markdown_content.strip():
            return
            
        doc_id = self.db.insert_document(project_id, version_id, snapshot_id, file_name, doc_type)
        
        docling_chars = len(markdown_content)
        
        # 1. Parent Chunking (2000 tokens)
        parent_chunks = self.parent_splitter.split_text(markdown_content)
        total_parents_extracted = len(parent_chunks)
        parent_chars_total = sum(len(p) for p in parent_chunks)
        
        qdrant_points = []
        total_parents_stored = 0
        total_children_stored = 0
        
        for p_idx, p_text in enumerate(parent_chunks):
            # Insert Parent Chunk into Postgres
            parent_id = self.db.insert_parent_chunk(
                doc_id=doc_id,
                project_id=project_id,
                version_id=version_id,
                snapshot_id=snapshot_id,
                chunk_index=p_idx,
                section_name=f"Section {p_idx+1}",
                content=p_text,
                token_count=len(p_text) // 4  # Approximation
            )
            total_parents_stored += 1
            
            # 2. Child Chunking (400 tokens)
            child_texts = self.child_splitter.split_text(p_text)
            
            if child_texts:
                # Embed all child chunks for this parent at once
                child_embeddings = self.embeddings.embed_documents(child_texts)
                
                for c_idx, (c_text, emb) in enumerate(zip(child_texts, child_embeddings)):
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{parent_id}-{c_idx}"))
                    
                    qdrant_points.append(
                        models.PointStruct(
                            id=point_id,
                            vector=emb,
                            payload={
                                "parent_id": parent_id,
                                "document_id": doc_id,
                                "project_id": project_id,
                                "version_id": version_id,
                                "project_snapshot_id": snapshot_id,
                                "file_name": file_name,
                                "document_type": doc_type,
                                "chunk_index": c_idx,
                                "content": c_text
                            }
                        )
                    )
        
        if qdrant_points:
            # Upsert in batches to Qdrant
            batch_size = 100
            for i in range(0, len(qdrant_points), batch_size):
                batch = qdrant_points[i:i+batch_size]
                self.qdrant.upsert(
                    collection_name=self.project_name,
                    points=batch
                )
                total_children_stored += len(batch)
                
        # Detailed Logging to Ensure No Data Loss
        logger.info(f"--- Document Processing Complete for: {file_name} ---")
        logger.info(f"Docling extracted exact characters: {docling_chars}")
        logger.info(f"Total characters across parent chunks: {parent_chars_total} (Greater than raw docling because of 200 token overlap!)")
        logger.info(f"Total Parent Chunks Extracted (Docling/LangChain): {total_parents_extracted}")
        logger.info(f"Total Parent Chunks Stored in Postgres: {total_parents_stored}")
        logger.info(f"Total Child Chunks Stored in Qdrant: {total_children_stored}")
        logger.info(f"---------------------------------------------------")
        
        INGESTION_DOCUMENTS_PROCESSED.labels(project_name=self.project_name, doc_type=doc_type).inc()
        INGESTION_BYTES_EXTRACTED.labels(project_name=self.project_name).inc(docling_chars)
        INGESTION_PARENT_CHUNKS.labels(project_name=self.project_name).inc(total_parents_stored)
        INGESTION_CHILD_CHUNKS.labels(project_name=self.project_name).inc(total_children_stored)

if __name__ == "__main__":
    import uuid
    pipeline = IngestionPipeline("VDRC_phase2")
    pipeline.run()
