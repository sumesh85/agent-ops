"""Knowledge tools — policy search and historical case similarity."""

import json

from src.app import mcp
from src.cache.client import cache_get, cache_set, make_key
from src.config import settings
from src.vector.client import query_collection


@mcp.tool()
async def policy_search(query: str, category: str | None = None, top_k: int = 3) -> str:
    """
    Semantically search the internal policy knowledge base.
    Use this to look up rules, procedures, and thresholds — AML hold triggers,
    RRSP/TFSA contribution limits, KYC renewal requirements, e-transfer refund timelines,
    T5/DRIP tax rules, and escalation procedures.
    Always search policy before making a resolution decision.
    category filter: WIRE | TAX | SECURITY | PAYMENT | COMPLIANCE | TRADING
    """
    top_k = min(top_k, 5)
    key = make_key("policy_search", query=query, category=category, top_k=top_k)
    if hit := await cache_get(key):
        return hit

    where = {"category": category} if category else None
    hits = query_collection(settings.chroma_collection_policies, query, top_k, where)

    chunks = [
        {
            "content": h.content,
            "source_file": h.metadata.get("source_file", ""),
            "category": h.metadata.get("category", ""),
            "section": h.metadata.get("section", ""),
            "relevance_score": round(1 - h.distance, 3),
        }
        for h in hits
    ]

    result = json.dumps({"policy_chunks": chunks, "count": len(chunks), "query": query})
    await cache_set(key, result, ttl=settings.redis_ttl_policy)
    return result


@mcp.tool()
async def cases_similar(issue_description: str, top_k: int = 3) -> str:
    """
    Search historical resolved cases for similar issues.
    Returns past cases with root cause, resolution, resolution type, and confidence score.
    Use this to calibrate confidence and verify your proposed resolution is consistent
    with how similar cases were handled in the past.
    """
    top_k = min(top_k, 5)
    key = make_key("cases_similar", issue_description=issue_description, top_k=top_k)
    if hit := await cache_get(key):
        return hit

    hits = query_collection(settings.chroma_collection_cases, issue_description, top_k)

    similar = [
        {
            "content": h.content,
            "issue_type": h.metadata.get("issue_type", ""),
            "resolution_type": h.metadata.get("resolution_type", ""),
            "confidence_score": float(h.metadata.get("confidence_score", 0)),
            "similarity": round(1 - h.distance, 3),
        }
        for h in hits
    ]

    result = json.dumps({"similar_cases": similar, "count": len(similar)})
    await cache_set(key, result, ttl=settings.redis_ttl_cases)
    return result
