from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache
from app.core.config import settings


class EmbedderBase(ABC):
    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder(EmbedderBase):
    def __init__(self):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_EMBEDDING_MODEL

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results = []
        for i in range(0, len(texts), 256):
            resp = await self._client.embeddings.create(
                model=self._model, input=texts[i:i + 256], encoding_format="float")
            results.extend([item.embedding for item in resp.data])
        return results


class SentenceTransformersEmbedder(EmbedderBase):
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(settings.SENTENCE_TRANSFORMERS_MODEL)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False))
        return embeddings.tolist()


@lru_cache(maxsize=1)
def get_embedder() -> EmbedderBase:
    if settings.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbedder()
    return SentenceTransformersEmbedder()
