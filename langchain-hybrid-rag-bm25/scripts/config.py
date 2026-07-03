import os
from dotenv import load_dotenv
from pathlib import Path

def get_env_var(key, default=""):
    val = os.getenv(key, default)
    if val and val.startswith("ENC:"):
        try:
            from cryptography.fernet import Fernet
            master_key = os.getenv("MASTER_KEY")
            if not master_key:
                print(f"[WARNING] {key} is encrypted but MASTER_KEY is not set!")
                return default
            f = Fernet(master_key.encode())
            encrypted_data = val[4:]  # strip 'ENC:'
            return f.decrypt(encrypted_data.encode()).decode()
        except ImportError:
            print(f"[WARNING] cryptography package is not installed. Cannot decrypt {key}.")
            return default
        except Exception as e:
            print(f"[ERROR] Failed to decrypt {key}: {e}")
            return default
    return val.strip() if isinstance(val, str) else val

# Load .env from the root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = Path(os.path.join(PROJECT_ROOT, ".env"))
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()  # Fallback

class Config:
    # Postgres
    POSTGRES_USER = os.getenv("POSTGRES_USER", "qa_user")
    POSTGRES_PASSWORD = get_env_var("POSTGRES_PASSWORD", "AAbb12#$%")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "qa_rag")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    @classmethod
    def get_pg_dsn(cls):
        from urllib.parse import quote_plus
        user = quote_plus(cls.POSTGRES_USER)
        pwd = quote_plus(cls.POSTGRES_PASSWORD)
        return f"postgresql://{user}:{pwd}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"

    # Qdrant
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

    # JIRA
    JIRA_URL = os.getenv("JIRA_URL", "")
    JIRA_USERNAME = os.getenv("JIRA_USERNAME", "")
    JIRA_API_TOKEN = get_env_var("JIRA_API_TOKEN", "")

    # Extraction Service (Docling)
    _raw_extraction = os.getenv("EXTRACTION_SERVICE_URL", "http://localhost:8000")
    if not os.path.exists("/.dockerenv") and "extraction-service:" in _raw_extraction:
        _raw_extraction = "http://localhost:8000"
    EXTRACTION_SERVICE_URL = _raw_extraction

    # LLM & Embeddings (Universal)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mistral")
    LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "mistral-large-latest")
    EVAL_MODEL_NAME = os.getenv("EVAL_MODEL_NAME", LLM_MODEL_NAME)
    LLM_API_KEY = get_env_var("LLM_API_KEY", get_env_var("MISTRAL_API_KEY", ""))
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "mistral")
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "mistral-embed")
    EMBEDDING_API_KEY = get_env_var("EMBEDDING_API_KEY", "")
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    # Chunking Configuration
    PARENT_CHUNK_SIZE = int(os.getenv("PARENT_CHUNK_SIZE", "2000"))
    PARENT_CHUNK_OVERLAP = int(os.getenv("PARENT_CHUNK_OVERLAP", "200"))
    CHILD_CHUNK_SIZE = int(os.getenv("CHILD_CHUNK_SIZE", "400"))
    CHILD_CHUNK_OVERLAP = int(os.getenv("CHILD_CHUNK_OVERLAP", "50"))

    # Generation / Rate-Limit & Eval Settings
    GENERATION_BATCH_DELAY = float(os.getenv("GENERATION_BATCH_DELAY", "1.0"))
    GENERATION_BATCH_SIZE = int(os.getenv("GENERATION_BATCH_SIZE", "15"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "5"))
    LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "600"))
    EVAL_BATCH_SIZE = int(os.getenv("EVAL_BATCH_SIZE", "5"))
    EVAL_DELAY_SECONDS = int(os.getenv("EVAL_DELAY_SECONDS", "5"))
    DEFAULT_PROJECT_NAME = os.getenv("DEFAULT_PROJECT_NAME", "SampleProject")

    # Folders
    if os.path.exists("/app/input_documents"):
        INPUT_ROOT = "/app/input_documents"
    else:
        local_input_dir = os.path.join(PROJECT_ROOT, "input_documents")
        raw_input = os.getenv("INPUT_ROOT", local_input_dir)
        if raw_input.startswith("/mnt/d/"):
            raw_input = raw_input.replace("/mnt/d/", "d:\\").replace("/", "\\")
        elif raw_input.startswith("/mnt/c/"):
            raw_input = raw_input.replace("/mnt/c/", "c:\\").replace("/", "\\")
        if "n8n-test-case-rag" in raw_input:
            raw_input = local_input_dir
        INPUT_ROOT = raw_input

config = Config()
