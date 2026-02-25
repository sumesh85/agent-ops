from dataclasses import dataclass
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings
from src.config import settings


@dataclass
class Hit:
    content: str
    metadata: dict  # type: ignore[type-arg]
    distance: float


@lru_cache
def _client() -> chromadb.HttpClient:  # type: ignore[type-arg]
    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def query_collection(name: str, query: str, top_k: int, where: dict | None = None) -> list[Hit]:  # type: ignore[type-arg]
    col = _client().get_or_create_collection(name)
    count = col.count()
    if count == 0:
        return []
    kwargs: dict = {"query_texts": [query], "n_results": min(top_k, count)}
    if where:
        kwargs["where"] = where
    res = col.query(**kwargs)
    return [
        Hit(
            content=res["documents"][0][i],
            metadata=(res["metadatas"][0][i] if res["metadatas"] else {}),
            distance=(res["distances"][0][i] if res["distances"] else 0.0),
        )
        for i in range(len(res["ids"][0]))
    ]
