"""Vector DB service — abstracts Qdrant and Pinecone. Swap via VECTOR_DB env var."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional

from app.core.config import settings


class VectorDBBase(ABC):
    """Interface for vector database providers."""

    @abstractmethod
    async def upsert(self, segments: list[dict]) -> None:
        """Upsert segments with embeddings."""

    @abstractmethod
    async def search(
        self,
        embedding: list[float],
        limit: int = 100,
        filter_language: Optional[str] = None,
        filter_year_min: Optional[int] = None,
        filter_year_max: Optional[int] = None,
    ) -> list[dict]:
        """ANN search; return candidate dicts with score."""


class QdrantVectorDB(VectorDBBase):
    def __init__(self):
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, VectorParams
        self._client = AsyncQdrantClient(url=settings.QDRANT_URL)
        self._collection = settings.QDRANT_COLLECTION
        self._dim = settings.EMBEDDING_DIM

    async def _ensure_collection(self):
        from qdrant_client.models import Distance, VectorParams, HnswConfigDiff
        existing = [c.name for c in (await self._client.get_collections()).collections]
        if self._collection not in existing:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._dim,
                    distance=Distance.COSINE,
                ),
                hnsw_config=HnswConfigDiff(
                    m=settings.QDRANT_HNSW_M,
                    ef_construct=settings.QDRANT_HNSW_EF_CONSTRUCT,
                ),
            )

    async def upsert(self, segments: list[dict]) -> None:
        from qdrant_client.models import PointStruct
        await self._ensure_collection()

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, seg["segment_id"])),
                vector=seg["embedding"],
                payload={
                    "segment_id": seg["segment_id"],
                    "track_id": seg["track_id"],
                    "text": seg["text"],
                    "title": seg.get("title", ""),
                    "artist": seg.get("artist", ""),
                    "album": seg.get("album", ""),
                    "language": seg.get("language", ""),
                    "release_year": seg.get("release_year"),
                    "line_offset": seg.get("line_offset", 0),
                    "context": seg.get("context", ""),
                    "spotify_id": seg.get("spotify_id", ""),
                },
            )
            for seg in segments
        ]

        await self._client.upsert(
            collection_name=self._collection,
            points=points,
        )

    async def search(
        self,
        embedding: list[float],
        limit: int = 100,
        filter_language: Optional[str] = None,
        filter_year_min: Optional[int] = None,
        filter_year_max: Optional[int] = None,
    ) -> list[dict]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

        must = []
        if filter_language:
            must.append(FieldCondition(key="language", match=MatchValue(value=filter_language)))
        if filter_year_min or filter_year_max:
            must.append(FieldCondition(
                key="release_year",
                range=Range(gte=filter_year_min, lte=filter_year_max),
            ))

        results = await self._client.search(
            collection_name=self._collection,
            query_vector=embedding,
            limit=limit,
            query_filter=Filter(must=must) if must else None,
            with_payload=True,
            search_params={"hnsw_ef": settings.QDRANT_HNSW_EF},
        )

        return [
            {
                **r.payload,
                "score": r.score,
            }
            for r in results
        ]


class PineconeVectorDB(VectorDBBase):
    def __init__(self):
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self._index = pc.Index(settings.PINECONE_INDEX)

    async def upsert(self, segments: list[dict]) -> None:
        import asyncio
        vectors = [
            {
                "id": seg["segment_id"],
                "values": seg["embedding"],
                "metadata": {
                    "track_id": seg["track_id"],
                    "text": seg["text"][:500],
                    "title": seg.get("title", ""),
                    "artist": seg.get("artist", ""),
                    "language": seg.get("language", ""),
                    "release_year": seg.get("release_year") or 0,
                    "line_offset": seg.get("line_offset", 0),
                    "context": seg.get("context", "")[:500],
                },
            }
            for seg in segments
        ]
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._index.upsert(vectors=vectors))

    async def search(
        self,
        embedding: list[float],
        limit: int = 100,
        filter_language: Optional[str] = None,
        filter_year_min: Optional[int] = None,
        filter_year_max: Optional[int] = None,
    ) -> list[dict]:
        import asyncio
        pinecone_filter = {}
        if filter_language:
            pinecone_filter["language"] = {"$eq": filter_language}
        if filter_year_min:
            pinecone_filter.setdefault("release_year", {})["$gte"] = filter_year_min
        if filter_year_max:
            pinecone_filter.setdefault("release_year", {})["$lte"] = filter_year_max

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._index.query(
                vector=embedding,
                top_k=limit,
                filter=pinecone_filter or None,
                include_metadata=True,
            ),
        )

        return [
            {
                "segment_id": m.id,
                **m.metadata,
                "score": m.score,
            }
            for m in result.matches
        ]


@lru_cache(maxsize=1)
def get_vector_db() -> VectorDBBase:
    if settings.VECTOR_DB == "pinecone":
        return PineconeVectorDB()
    return QdrantVectorDB()
