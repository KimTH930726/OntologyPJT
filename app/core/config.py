from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "local"
    log_level: str = "INFO"
    admin_token: str = "dev-admin-token"

    # Postgres
    database_url: str = "postgresql+psycopg://ontology_user:ontology_password@localhost:5432/ontology_rag"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "chunks"


@lru_cache
def get_settings() -> Settings:
    return Settings()
