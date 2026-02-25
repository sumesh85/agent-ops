"""Transaction tools."""

import json
from typing import Any

from src.app import mcp
from src.cache.client import cache_get, cache_set, make_key
from src.config import settings
from src.db.pool import get_pool


def _row(row: object) -> dict:  # type: ignore[type-arg]
    r = dict(row)  # type: ignore[call-overload]
    return {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in r.items()}


@mcp.tool()
async def transactions_search(
    account_id: str,
    transaction_type: str | None = None,
    status: str | None = None,
    days: int = 90,
    year: int | None = None,
) -> str:
    """
    Search an account's transaction history with optional filters.

    transaction_type: deposit | withdrawal | wire_in | wire_out | transfer_in | transfer_out
                      | trade_buy | trade_sell | dividend | drip | etransfer

    status: completed | pending | processing | failed | reversed | pending_reversal
      - Use status=reversed to find completed refund/reversal credits.
      - Use status=pending_reversal to find refunds still in progress.

    days: search window in days (default 90, max 365). Use days=365 to cover a full calendar year.
    year: if provided (e.g. 2024), filters to Jan 1–Dec 31 of that year, ignoring days.

    Returns amount, status, description, counterparty, reference_number, initiated_at.
    """
    key = make_key(
        "transactions_search",
        account_id=account_id, transaction_type=transaction_type,
        status=status, days=days, year=year,
    )
    if hit := await cache_get(key):
        return hit

    params: list[Any] = [account_id]

    if year:
        conditions: list[str] = [
            "account_id = $1",
            f"initiated_at >= '{year}-01-01'::date",
            f"initiated_at < '{year + 1}-01-01'::date",
        ]
    else:
        days = min(days, 365)
        conditions = [
            "account_id = $1",
            f"initiated_at > NOW() - ('{days} days')::interval",
        ]

    if transaction_type:
        params.append(transaction_type)
        conditions.append(f"transaction_type = ${len(params)}")
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT transaction_id, transaction_type, amount::float, currency, status,
                   description, counterparty, reference_number, failure_reason,
                   initiated_at::text, settled_at::text
            FROM transactions
            WHERE {" AND ".join(conditions)}
            ORDER BY initiated_at DESC LIMIT 100
            """,
            *params,
        )

    result = json.dumps({
        "transactions": [_row(r) for r in rows],
        "count": len(rows),
        "filters": {
            "transaction_type": transaction_type,
            "status": status,
            "days": days if not year else None,
            "year": year,
        },
    })
    await cache_set(key, result, ttl=settings.redis_ttl_tool_call)
    return result


@mcp.tool()
async def transactions_metadata(transaction_id: str) -> str:
    """
    Retrieve full metadata for a specific transaction — including device ID, IP country,
    instrument details, and login session ID. Use when a specific transaction needs
    deeper inspection (e.g. to check whether a trade came from a known device and country).
    """
    key = make_key("transactions_metadata", transaction_id=transaction_id)
    if hit := await cache_get(key):
        return hit

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT transaction_id, transaction_type, amount::float, currency, status,
                   description, counterparty, reference_number, failure_reason,
                   initiated_at::text, settled_at::text, metadata
            FROM transactions WHERE transaction_id = $1
            """,
            transaction_id,
        )

    if not row:
        return json.dumps({"error": f"Transaction '{transaction_id}' not found."})

    data = _row(row)
    if isinstance(data.get("metadata"), str):
        data["metadata"] = json.loads(data["metadata"])

    result = json.dumps(data)
    await cache_set(key, result, ttl=settings.redis_ttl_tool_call)
    return result
