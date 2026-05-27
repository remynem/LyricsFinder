from __future__ import annotations
from functools import lru_cache
from typing import Optional
from app.core.config import settings


class LexicalSearch:
    def __init__(self):
        from elasticsearch import AsyncElasticsearch
        self._es = AsyncElasticsearch(settings.ELASTICSEARCH_URL)
        self._index = settings.ELASTICSEARCH_INDEX

    async def _ensure_index(self):
        if not await self._es.indices.exists(index=self._index):
            await self._es.indices.create(index=self._index, body={
                "mappings": {"properties": {
                    "segment_id":   {"type": "keyword"},
                    "track_id":     {"type": "keyword"},
                    "text":         {"type": "text", "analyzer": "standard"},
                    "title":        {"type": "text"},
                    "artist":       {"type": "keyword"},
                    "language":     {"type": "keyword"},
                    "release_year": {"type": "integer"},
                }}
            })

    async def bulk_index(self, docs: list[dict]) -> None:
        try:
            await self._ensure_index()
            from elasticsearch.helpers import async_bulk
            actions = [{"_index": self._index, "_id": d["segment_id"], **d} for d in docs]
            await async_bulk(self._es, actions)
        except Exception:
            pass

    async def search(self, query: str, limit: int = 50, filter_language: Optional[str] = None) -> list[dict]:
        try:
            from app.services.text import sanitise_es_query
            safe_query = sanitise_es_query(query)
            must = [{"match": {"text": {"query": safe_query, "fuzziness": "AUTO"}}}]
            filter_ = [{"term": {"language": filter_language}}] if filter_language else []
            resp = await self._es.search(
                index=self._index,
                body={"query": {"bool": {"must": must, "filter": filter_}}, "size": limit},
            )
            results = []
            for hit in resp["hits"]["hits"]:
                src = hit["_source"]
                src["segment_id"] = hit["_id"]
                src["score"] = hit["_score"]
                results.append(src)
            return results
        except Exception:
            return []


class NoopLexicalSearch:
    async def bulk_index(self, docs): pass
    async def search(self, query, limit=50, filter_language=None): return []


@lru_cache(maxsize=1)
def get_lexical_search():
    try:
        return LexicalSearch()
    except Exception:
        return NoopLexicalSearch()
