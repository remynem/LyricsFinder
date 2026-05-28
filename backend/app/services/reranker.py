from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache
from app.core.config import settings


class RerankerBase(ABC):
    @abstractmethod
    async def rerank(self, query: str, candidates: list[dict], batch_size: int = 32) -> list[dict]: ...


class CrossEncoderReranker(RerankerBase):
    def __init__(self):
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder(settings.RERANKER_MODEL, max_length=512)

    async def rerank(self, query: str, candidates: list[dict], batch_size: int = 32) -> list[dict]:
        if not candidates:
            return []
        pairs = [(query, c["text"]) for c in candidates]
        loop = asyncio.get_event_loop()
        all_scores = []
        for i in range(0, len(pairs), batch_size):
            scores = await loop.run_in_executor(
                None, lambda c=pairs[i:i + batch_size]: self._model.predict(c).tolist())
            all_scores.extend(scores)
        for candidate, score in zip(candidates, all_scores):
            candidate["score"] = float(score)
        return sorted(candidates, key=lambda x: x["score"], reverse=True)


class PassthroughReranker(RerankerBase):
    async def rerank(self, query, candidates, batch_size=32):
        return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)


@lru_cache(maxsize=1)
def get_reranker() -> RerankerBase:
    try:
        return CrossEncoderReranker()
    except Exception:
        return PassthroughReranker()
