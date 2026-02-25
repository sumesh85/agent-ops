import asyncpg
from src.config import settings

_pool: asyncpg.Pool | None = None  # type: ignore[type-arg]


async def get_pool() -> asyncpg.Pool:  # type: ignore[type-arg]
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_dsn,
            min_size=2,
            max_size=8,
            command_timeout=10,
        )
    return _pool
