"""
Shared asyncpg connection pool.

Used by the agent tools layer for fast, direct SQL queries.
Initialised lazily on first use; safe to call from any async context.
"""

import asyncpg

from src.config import settings

_pool: asyncpg.Pool | None = None  # type: ignore[type-arg]


async def get_pool() -> asyncpg.Pool:  # type: ignore[type-arg]
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_dsn,
            min_size=2,
            max_size=10,
            command_timeout=10,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
