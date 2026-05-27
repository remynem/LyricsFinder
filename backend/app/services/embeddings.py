"""Embeddings service — abstracts OpenAI and sentence-transformers providers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

from app.core.config import settings

if TYPE_CHECKING:
    pass


class EmbedderBase(ABC):
    """Interface for embedding providers. Swap by setting EMBEDDING_PROVIDER."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return list of embedding vectors, one per input text."""


class OpenAIEmbedder(EmbedderBase):
    def __init__(self):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_EMBEDDING_MODEL

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # OpenAI supports up to 2048 inputs per call; chunk if needed
        results: list[list[float]] = []
        chunk_size = 256
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i : i + chunk_size]
            response = await self._client.embeddings.create(
                model=self._model,
                input=chunk,
                encoding_format="float",
            )
            results.extend([item.embedding for item in response.data])
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
            None,
            lambda: self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
        )
        return embeddings.tolist()


@lru_cache(maxsize=1)
def get_embedder() -> EmbedderBase:
    """Return the configured embedder (cached singleton)."""
    provider = settings.EMBEDDING_PROVIDER
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return OpenAIEmbedder()
    elif provider == "sentence_transformers":
        return SentenceTransformersEmbedder()
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")
