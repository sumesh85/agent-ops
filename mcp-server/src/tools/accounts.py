"""Account and customer tools."""

import json
from src.app import mcp
from src.cache.client import cache_get, cache_set, make_key
from src.config import settings
from src.db.pool import get_pool


def _row(row: object) -> dict:  # type: ignore[type-arg]
    return {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in dict(row).items()}  # type: ignore[call-overload]


@mcp.tool()
async def customer_lookup(customer_id: str) -> str:
    """
    Look up a customer's profile: name, province, KYC status, KYC expiry date, risk profile.
    Call this first to understand who the customer is and whether their identity verification
    is current.
    """
    key = make_key("customer_lookup", customer_id=customer_id)
    if hit := await cache_get(key):
        return hit

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT customer_id, name, email, province, date_of_birth::text,
                   kyc_status, kyc_verified_at::text, kyc_expires_at::text,
                   risk_profile, created_at::text
            FROM customers WHERE customer_id = $1
            """,
            customer_id,
        )

    result = json.dumps(_row(row) if row else {"error": f"Customer '{customer_id}' not found."})
    await cache_set(key, result, ttl=settings.redis_ttl_tool_call)
    return result


@mcp.tool()
async def account_lookup(customer_id: str) -> str:
    """
    Retrieve all accounts held by a customer. Returns account type (TFSA, RRSP, Cash, Crypto),
    status (active/frozen/restricted), freeze_reason if frozen, balance, available_balance,
    and YTD RRSP/TFSA contributions. Call this early to understand the account landscape.
    """
    key = make_key("account_lookup", customer_id=customer_id)
    if hit := await cache_get(key):
        return hit

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT account_id, account_type, account_number, status, freeze_reason,
                   balance::float, available_balance::float, currency,
                   rrsp_contribution_ytd::float, tfsa_contribution_ytd::float,
                   created_at::text
            FROM accounts WHERE customer_id = $1 ORDER BY account_type
            """,
            customer_id,
        )

    result = json.dumps({"accounts": [_row(r) for r in rows], "count": len(rows)})
    await cache_set(key, result, ttl=settings.redis_ttl_tool_call)
    return result


@mcp.tool()
async def account_login_history(customer_id: str, days: int = 30) -> str:
    """
    Retrieve recent login events: device ID, IP address, country, timestamp.
    Use when investigating suspected unauthorized access — look for logins from
    unfamiliar countries or unknown devices. Returns unique_countries and unique_devices
    as summary fields to make anomaly detection easier.
    """
    days = min(days, 90)
    key = make_key("account_login_history", customer_id=customer_id, days=days)
    if hit := await cache_get(key):
        return hit

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT event_id, event_type, device_id, ip_address, ip_country,
                   user_agent, occurred_at::text
            FROM login_events
            WHERE customer_id = $1
              AND occurred_at > NOW() - ($2 || ' days')::interval
            ORDER BY occurred_at DESC LIMIT 50
            """,
            customer_id, str(days),
        )

    events = [_row(r) for r in rows]
    countries = sorted({e.get("ip_country", "") for e in events if e.get("ip_country")})
    devices   = sorted({e.get("device_id", "")   for e in events if e.get("device_id")})
    result = json.dumps({
        "login_events": events, "count": len(events),
        "unique_countries": countries, "unique_devices": devices, "period_days": days,
    })
    await cache_set(key, result, ttl=settings.redis_ttl_tool_call)
    return result


@mcp.tool()
async def account_communication_history(customer_id: str) -> str:
    """
    Retrieve recent outbound communications sent to the customer: emails, SMS, push
    notifications — subject and summary. Useful for confirming whether the customer
    was notified about KYC expiry, account freeze, or other events.
    """
    key = make_key("account_communication_history", customer_id=customer_id)
    if hit := await cache_get(key):
        return hit

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT comm_id, direction, channel, subject, body_summary, sent_at::text
            FROM communications WHERE customer_id = $1 ORDER BY sent_at DESC LIMIT 20
            """,
            customer_id,
        )

    result = json.dumps({"communications": [_row(r) for r in rows], "count": len(rows)})
    await cache_set(key, result, ttl=settings.redis_ttl_tool_call)
    return result
