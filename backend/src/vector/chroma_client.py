"""
ChromaDB HTTP client wrapper.

Collections:
  - policies       : chunked policy markdown documents
  - case_embeddings: historical resolved cases for similarity search

Usage:
    from src.vector.chroma_client import vector_store
    results = await vector_store.search_policies("AML hold large wire", top_k=3)
    similar = await vector_store.search_cases("wire delay AML", top_k=3)
"""

import asyncio
from dataclasses import dataclass
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings


@dataclass
class SearchResult:
    doc_id: str
    content: str
    metadata: dict  # type: ignore[type-arg]
    distance: float


@lru_cache
def _get_client() -> chromadb.HttpClient:  # type: ignore[type-arg]
    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


class VectorStore:
    def __init__(self) -> None:
        self._client = _get_client()

    def _collection(self, name: str) -> chromadb.Collection:  # type: ignore[type-arg]
        return self._client.get_or_create_collection(name)

    async def search_policies(
        self, query: str, category: str | None = None, top_k: int = 3
    ) -> list[SearchResult]:
        where = {"category": category} if category else None
        return await asyncio.to_thread(
            self._query, settings.chroma_collection_policies, query, top_k, where
        )

    async def search_cases(self, query: str, top_k: int = 3) -> list[SearchResult]:
        return await asyncio.to_thread(
            self._query, settings.chroma_collection_cases, query, top_k, None
        )

    def _query(
        self,
        collection_name: str,
        query: str,
        top_k: int,
        where: dict | None,  # type: ignore[type-arg]
    ) -> list[SearchResult]:
        col = self._collection(collection_name)
        kwargs: dict = {"query_texts": [query], "n_results": min(top_k, col.count() or 1)}
        if where:
            kwargs["where"] = where
        result = col.query(**kwargs)

        output: list[SearchResult] = []
        for i, doc_id in enumerate(result["ids"][0]):
            output.append(
                SearchResult(
                    doc_id=doc_id,
                    content=result["documents"][0][i],
                    metadata=result["metadatas"][0][i] if result["metadatas"] else {},
                    distance=result["distances"][0][i] if result["distances"] else 0.0,
                )
            )
        return output

    def ping(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False


vector_store = VectorStore()
