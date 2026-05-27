"""Cross-encoder reranker — multilingual XLM-R or OpenAI LLM rerank."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings


class RerankerBase(ABC):
    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: list[dict],
        batch_size: int = 32,
    ) -> list[dict]:
        """Return candidates sorted by cross-encoder score (descending)."""


class CrossEncoderReranker(RerankerBase):
    """Uses sentence-transformers CrossEncoder (runs locally)."""

    def __init__(self):
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder(
            settings.RERANKER_MODEL,
            max_length=512,
        )

    async def rerank(
        self,
        query: str,
        candidates: list[dict],
        batch_size: int = 32,
    ) -> list[dict]:
        if not candidates:
            return []

        pairs = [(query, c["text"]) for c in candidates]
        loop = asyncio.get_event_loop()

        all_scores = []
        for i in range(0, len(pairs), batch_size):
            chunk = pairs[i : i + batch_size]
            scores = await loop.run_in_executor(
                None,
                lambda c=chunk: self._model.predict(c).tolist(),
            )
            all_scores.extend(scores)

        for candidate, score in zip(candidates, all_scores):
            candidate["score"] = float(score)

        return sorted(candidates, key=lambda x: x["score"], reverse=True)


class PassthroughReranker(RerankerBase):
    """No reranking — returns candidates sorted by existing score. Use as fallback."""

    async def rerank(
        self,
        query: str,
        candidates: list[dict],
        batch_size: int = 32,
    ) -> list[dict]:
        return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)


@lru_cache(maxsize=1)
def get_reranker() -> RerankerBase:
    try:
        return CrossEncoderReranker()
    except Exception:
        # Fallback if model not available
        return PassthroughReranker()
