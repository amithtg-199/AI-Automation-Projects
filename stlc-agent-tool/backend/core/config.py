import os
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine the absolute path to the global_variables folder
BASE_DIR = Path(__file__).resolve().parent.parent.parent
GLOBAL_ENV_FILE = BASE_DIR / "global_variables" / ".env"

class Settings(BaseSettings):
    # App Settings
    HOSTNAME: str = "http://localhost:8000"
    
    # Deployment mode (connected vs disconnected for Batch 07)
    STLC_DEPLOYMENT_MODE: str = "connected"
    
    # LLM Settings
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_EMBEDDING_MODEL: str = "text-embedding-3-small"
    # LLM_API_KEY can be a single string, or a JSON map {"openai": ["key1", "key2"]}
    LLM_API_KEY: Optional[str] = None
    OLLAMA_ENDPOINT: str = "http://localhost:11434"
    
    # DB Settings
    QDRANT_URL: str = "http://localhost:6333"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    REDIS_URL: str = "redis://localhost:6379"
    POSTGRES_URL: str = "postgresql://postgres:postgres@localhost:5432/stlc_db"
    
    # System Settings
    MAX_RETRIES: int = 3
    MAX_BATCHES: int = 10
    FALLBACK_SECONDS: int = 10
    CELERY_WORKERS: int = 4
    
    # API Auth tokens
    API_AUTH_TOKEN: Optional[str] = None
    TOKEN_VALIDITY_SECONDS: int = 3600
    JIRA_URL: Optional[str] = None
    JIRA_EMAIL: Optional[str] = None
    JIRA_API_KEY: Optional[str] = None
    
    # Audit & Tracking
    AUDIT_LOG_RETENTION_DAYS: int = 30
    COST_LOG_RETENTION_DAYS: int = 90
    
    # Knowledge Hub
    KNOWLEDGE_HUB_CRON: str = "0 */12 * * *"
    
    # Encryption Key Path
    SECRET_KEY_PATH: str = str(BASE_DIR / "global_variables" / "secret.key")

    model_config = SettingsConfigDict(
        env_file=str(GLOBAL_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

def get_fernet() -> Fernet:
    key_path = Path(settings.SECRET_KEY_PATH)
    if not key_path.exists():
        # Auto-generate a key if it doesn't exist for ease of setup
        key = Fernet.generate_key()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
    else:
        key = key_path.read_bytes()
    return Fernet(key)

def encrypt_secret(plain_text: str) -> str:
    if not plain_text:
        return plain_text
    f = get_fernet()
    return f.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_secret(cipher_text: str) -> str:
    if not cipher_text:
        return cipher_text
    f = get_fernet()
    return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
