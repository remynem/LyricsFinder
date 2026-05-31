from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional
from app.core.config import settings


class VectorDBBase(ABC):
    @abstractmethod
    async def upsert(self, segments: list[dict]) -> None: ...
    @abstractmethod
    async def search(self, embedding: list[float], limit: int = 100,
                     filter_language: Optional[str] = None,
                     filter_year_min: Optional[int] = None,
                     filter_year_max: Optional[int] = None) -> list[dict]: ...


class InMemoryVectorDB(VectorDBBase):
    """
    Simple in-memory vector store using cosine similarity.
    Fast to start, no external dependencies.
    Data is lost on restart — use for prototyping.
    """
    def __init__(self):
        self._segments: list[dict] = []

    async def upsert(self, segments: list[dict]) -> None:
        existing_ids = {s["segment_id"] for s in self._segments}
        for seg in segments:
            if seg["segment_id"] not in existing_ids:
                self._segments.append(seg)

    async def search(self, embedding, limit=100, filter_language=None,
                     filter_year_min=None, filter_year_max=None):
        import math

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb + 1e-9)

        candidates = self._segments
        if filter_language:
            candidates = [s for s in candidates if s.get("language") == filter_language]
        if filter_year_min:
            candidates = [s for s in candidates if (s.get("release_year") or 0) >= filter_year_min]
        if filter_year_max:
            candidates = [s for s in candidates if (s.get("release_year") or 9999) <= filter_year_max]

        scored = []
        for seg in candidates:
            emb = seg.get("embedding")
            if emb:
                score = cosine(embedding, emb)
                result = {k: v for k, v in seg.items() if k != "embedding"}
                result["score"] = score
                scored.append(result)

        return sorted(scored, key=lambda x: x["score"], reverse=True)[:limit]


class QdrantVectorDB(VectorDBBase):
    def __init__(self):
        from qdrant_client import AsyncQdrantClient
        kwargs = {"url": settings.QDRANT_URL}
        if settings.QDRANT_API_KEY:
            kwargs["api_key"] = settings.QDRANT_API_KEY
        self._client = AsyncQdrantClient(**kwargs)
        self._collection = settings.QDRANT_COLLECTION
        self._dim = settings.EMBEDDING_DIM

    async def _collection_exists(self) -> bool:
        try:
            existing = [c.name for c in (await self._client.get_collections()).collections]
            return self._collection in existing
        except Exception:
            return False

    async def _ensure_collection(self):
        from qdrant_client.models import Distance, VectorParams, HnswConfigDiff
        try:
            if not await self._collection_exists():
                await self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
                    hnsw_config=HnswConfigDiff(
                        m=settings.QDRANT_HNSW_M,
                        ef_construct=settings.QDRANT_HNSW_EF_CONSTRUCT,
                    ),
                )
        except Exception:
            pass

    async def upsert(self, segments: list[dict]) -> None:
        from qdrant_client.models import PointStruct
        await self._ensure_collection()
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, seg["segment_id"])),
                vector=seg["embedding"],
                payload={k: seg.get(k, "") for k in
                         ["segment_id", "track_id", "text", "title", "artist",
                          "album", "language", "release_year", "line_offset", "context", "spotify_id"]},
            )
            for seg in segments
        ]
        await self._client.upsert(collection_name=self._collection, points=points)

    async def search(self, embedding, limit=100, filter_language=None,
                     filter_year_min=None, filter_year_max=None):
        if not await self._collection_exists():
            return []
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
            must = []
            if filter_language:
                must.append(FieldCondition(key="language", match=MatchValue(value=filter_language)))
            if filter_year_min or filter_year_max:
                must.append(FieldCondition(
                    key="release_year", range=Range(gte=filter_year_min, lte=filter_year_max)))
            results = await self._client.search(
                collection_name=self._collection, query_vector=embedding, limit=limit,
                query_filter=Filter(must=must) if must else None,
                with_payload=True, search_params={"hnsw_ef": settings.QDRANT_HNSW_EF},
            )
            return [{**r.payload, "score": r.score} for r in results]
        except Exception:
            return []


@lru_cache(maxsize=1)
def get_vector_db() -> VectorDBBase:
    """
    Use VECTOR_DB=memory for prototype (no external deps).
    Use VECTOR_DB=qdrant for production.
    """
    if settings.VECTOR_DB == "memory":
        return InMemoryVectorDB()
    try:
        return QdrantVectorDB()
    except Exception:
        return InMemoryVectorDB()
