from __future__ import annotations
import json
from functools import lru_cache
from app.core.config import settings


class RedisCache:
    def __init__(self):
        import redis.asyncio as redis
        self._client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get(self, key: str):
        try:
            val = await self._client.get(key)
            return json.loads(val) if val else None
        except Exception:
            return None

    async def set(self, key: str, value, ttl: int = 300):
        try:
            await self._client.setex(key, ttl, json.dumps(value))
        except Exception:
            pass


class NoopCache:
    async def get(self, key): return None
    async def set(self, key, value, ttl=300): pass


@lru_cache(maxsize=1)
def get_cache():
    try:
        return RedisCache()
    except Exception:
        return NoopCache()
