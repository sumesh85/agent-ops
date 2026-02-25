"""
Redis client with typed helpers.

Usage pattern (FastAPI):
    from src.cache.redis_client import cache
    result = await cache.get_json("key")
    await cache.set_json("key", data, ttl=60)

Cache key conventions:
    tool:{tool_name}:{args_hash}   → tool call result
    policy:{query_hash}            → policy search results
    cases:{query_hash}             → similar case results
"""

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis

from src.config import settings

_pool = aioredis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    decode_responses=True,
)


def get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    return aioredis.Redis(connection_pool=_pool)


class CacheClient:
    def __init__(self) -> None:
        self._r = get_redis()

    def make_key(self, prefix: str, *args: Any) -> str:
        payload = json.dumps(args, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"{prefix}:{digest}"

    async def get_json(self, key: str) -> Any | None:
        raw = await self._r.get(key)
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, value: Any, ttl: int = 60) -> None:
        await self._r.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def ping(self) -> bool:
        try:
            return bool(await self._r.ping())
        except Exception:
            return False


cache = CacheClient()
