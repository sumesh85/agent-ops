import hashlib
import json
from typing import Any

import redis.asyncio as aioredis
from src.config import settings

_pool = aioredis.ConnectionPool.from_url(
    settings.redis_url, max_connections=10, decode_responses=True
)


def _redis() -> aioredis.Redis:  # type: ignore[type-arg]
    return aioredis.Redis(connection_pool=_pool)


def make_key(tool: str, **kwargs: Any) -> str:
    payload = json.dumps(kwargs, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"tool:{tool}:{digest}"


async def cache_get(key: str) -> str | None:
    return await _redis().get(key)  # type: ignore[return-value]


async def cache_set(key: str, value: str, ttl: int = 60) -> None:
    await _redis().setex(key, ttl, value)
