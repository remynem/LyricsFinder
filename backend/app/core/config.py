from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEY: str = "dev-key"
    SECRET_KEY: str = "change-me"

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/lyricsfinder"

    VECTOR_DB: Literal["qdrant", "memory"] = "memory"  # default to memory for easy deploy
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "lyric_segments"
    QDRANT_HNSW_M: int = 16
    QDRANT_HNSW_EF_CONSTRUCT: int = 100
    QDRANT_HNSW_EF: int = 128

    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX: str = "lyrics"

    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 300

    EMBEDDING_PROVIDER: Literal["openai", "sentence_transformers"] = "sentence_transformers"
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 384

    RERANKER_MODEL: str = "cross-encoder/msmarco-MiniLM-L6-en-de-v1"
    RERANKER_BATCH_SIZE: int = 32

    DEEPL_API_KEY: str = ""
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    MUSIXMATCH_API_KEY: str = ""

    SEARCH_CANDIDATE_LIMIT: int = 200
    INGEST_BATCH_SIZE: int = 64

    CORS_ORIGINS: list[str] = Field(default=["*"])

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
