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
        return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"

    # Qdrant
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

    # JIRA
    JIRA_URL = os.getenv("JIRA_URL", "")
    JIRA_USERNAME = os.getenv("JIRA_USERNAME", "")
    JIRA_API_TOKEN = get_env_var("JIRA_API_TOKEN", "")

    # Extraction Service (Docling)
    EXTRACTION_SERVICE_URL = os.getenv("EXTRACTION_SERVICE_URL", "http://localhost:8000")

    # LLM & Embeddings (Universal)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mistral")
    LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "mistral-large-latest")
    LLM_API_KEY = get_env_var("LLM_API_KEY", get_env_var("MISTRAL_API_KEY", ""))
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "mistral")
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "mistral-embed")
    EMBEDDING_API_KEY = get_env_var("EMBEDDING_API_KEY", "")

    # Generation / Rate-Limit Settings
    # Delay (seconds) between consecutive LLM calls.  Set to 0 for paid tiers.
    GENERATION_BATCH_DELAY = float(os.getenv("GENERATION_BATCH_DELAY", "1.0"))
    # Batch size: number of parent chunks per LLM call
    GENERATION_BATCH_SIZE = int(os.getenv("GENERATION_BATCH_SIZE", "10"))
    # Max retries at the application level (on top of SDK-level retries)
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "5"))
    # Request timeout in seconds (0 = no timeout)
    LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "120"))

    # Folders
    local_input_dir = os.path.join(PROJECT_ROOT, "input_documents")
    raw_input = os.getenv("INPUT_ROOT", local_input_dir)
    if raw_input.startswith("/mnt/d/"):
        raw_input = raw_input.replace("/mnt/d/", "d:\\").replace("/", "\\")
    elif raw_input.startswith("/mnt/c/"):
        raw_input = raw_input.replace("/mnt/c/", "c:\\").replace("/", "\\")
    
    # Force use of local directory if the env variable points to the old n8n path
    if "n8n-test-case-rag" in raw_input:
        raw_input = local_input_dir
        
    INPUT_ROOT = raw_input

config = Config()
