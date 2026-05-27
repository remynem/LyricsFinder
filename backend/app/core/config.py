"""Application configuration — reads from environment / .env file."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Auth
    SECRET_KEY: str = "change-me-in-production"
    API_KEY: str = "dev-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lyricfinder:lyricfinder@localhost:5432/lyricfinder"

    # Vector DB
    VECTOR_DB: Literal["qdrant", "pinecone"] = "qdrant"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "lyric_segments"
    QDRANT_HNSW_M: int = 16
    QDRANT_HNSW_EF_CONSTRUCT: int = 100
    QDRANT_HNSW_EF: int = 128
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "lyricfinder"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX: str = "lyrics"

    # Redis cache
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 300

    # Embeddings
    EMBEDDING_PROVIDER: Literal["openai", "sentence_transformers"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 3072  # text-embedding-3-large; 384 for MiniLM

    # Reranker
    RERANKER_MODEL: str = "cross-encoder/msmarco-MiniLM-L6-en-de-v1"
    RERANKER_BATCH_SIZE: int = 32

    # Translation
    DEEPL_API_KEY: str = ""
    GOOGLE_TRANSLATE_KEY: str = ""

    # External APIs
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    MUSIXMATCH_API_KEY: str = ""
    LYRICFIND_API_KEY: str = ""

    # Search params
    SEARCH_CANDIDATE_LIMIT: int = 200
    INGEST_BATCH_SIZE: int = 64
    INGEST_WORKERS: int = 4

    # Monitoring
    SENTRY_DSN: str = ""

    # Storage
    S3_BUCKET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-west-1"

    # CORS
    CORS_ORIGINS: list[str] = Field(default=["*"])

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
