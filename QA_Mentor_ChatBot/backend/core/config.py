from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mistral_api_key: str = ""
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379/0"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    class Config:
        env_file = ".env"

settings = Settings()
