"""AgentOps Control Plane — backend API."""

import json
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.db.pool import close_pool, get_pool

log = structlog.get_logger()
UTC = timezone.utc

app = FastAPI(
    title="AgentOps Control Plane",
    description="Observability and governance layer for agentic AI workflows",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


# ── Investigation endpoint ────────────────────────────────────────────────────

@app.post("/api/v1/investigate/{issue_id}", tags=["agent"])
async def investigate(issue_id: str) -> dict:  # type: ignore[type-arg]
    """
    Trigger an investigation for a known issue_id.
    Loads the issue from DB, delegates to the agent service, persists the trace.
    """
    pool = await get_pool()

    # Load issue
    async with pool.acquire() as conn:
        issue = await conn.fetchrow(
            "SELECT issue_id, customer_id, raw_message, channel, urgency FROM issues WHERE issue_id = $1",
            issue_id,
        )

    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found.")

    # Delegate to agent service
    payload = {
        "issue_id":    str(issue["issue_id"]),
        "customer_id": str(issue["customer_id"]),
        "channel":     issue["channel"],
        "urgency":     issue["urgency"],
        "raw_message": issue["raw_message"],
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{settings.agent_url}/run", json=payload)
            resp.raise_for_status()
            result: dict = resp.json()  # type: ignore[type-arg]
    except httpx.HTTPStatusError as exc:
        log.error("backend.agent_error", issue_id=issue_id, status=exc.response.status_code)
        raise HTTPException(status_code=502, detail=f"Agent service error: {exc.response.text}")
    except httpx.RequestError as exc:
        log.error("backend.agent_unreachable", issue_id=issue_id, error=str(exc))
        raise HTTPException(status_code=503, detail="Agent service unreachable.")

    # Persist run trace
    await _persist_trace(result)

    return result


# ── Issues list ───────────────────────────────────────────────────────────────

@app.get("/api/v1/issues", tags=["issues"])
async def list_issues() -> dict:  # type: ignore[type-arg]
    """List all demo issues with their current status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT i.issue_id, i.customer_id, i.urgency, i.status, i.channel,
                   i.created_at::text,
                   LEFT(i.raw_message, 160) AS message_preview,
                   c.name AS customer_name,
                   t.trace_id, t.status AS run_status,
                   t.confidence_score, t.escalate, t.policy_flags,
                   t.started_at::text AS run_started_at,
                   t.completed_at::text AS run_completed_at
            FROM issues i
            JOIN customers c ON c.customer_id = i.customer_id
            LEFT JOIN run_traces t ON t.issue_id = i.issue_id
            ORDER BY
                CASE i.urgency WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                               WHEN 'medium' THEN 3 ELSE 4 END,
                i.created_at DESC
            """
        )
    issues = []
    for r in rows:
        row = dict(r)
        if isinstance(row.get("policy_flags"), str):
            row["policy_flags"] = json.loads(row["policy_flags"])
        issues.append(row)
    return {"issues": issues, "count": len(issues)}


# ── Run trace detail ──────────────────────────────────────────────────────────

@app.get("/api/v1/runs/{trace_id}", tags=["runs"])
async def get_run(trace_id: str) -> dict:  # type: ignore[type-arg]
    """Retrieve a full run trace by trace_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM run_traces WHERE trace_id = $1", trace_id
        )
    if not row:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found.")

    result = dict(row)
    for field in ("tool_calls", "structured_output", "policy_flags"):
        if isinstance(result.get(field), str):
            result[field] = json.loads(result[field])
    result["started_at"]   = str(result["started_at"])
    result["completed_at"] = str(result.get("completed_at", ""))
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _persist_trace(result: dict) -> None:  # type: ignore[type-arg]
    """Write a RunResult dict to run_traces. Non-fatal on error."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO run_traces (
                    trace_id, issue_id, started_at, completed_at, status,
                    tool_calls, agent_reasoning, structured_output,
                    confidence_score, escalate, policy_flags,
                    token_count, model
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (trace_id) DO NOTHING
                """,
                result["trace_id"],
                result["issue_id"],
                datetime.now(UTC),          # started_at approximation from backend side
                datetime.now(UTC),
                result["status"],
                json.dumps(result.get("tool_calls", [])),
                (result.get("agent_reasoning") or "")[:10_000],
                json.dumps(result.get("structured_output", {}), default=str),
                float(result.get("confidence_score", 0.0)),
                bool(result.get("escalate", False)),
                json.dumps(result.get("policy_flags", [])),
                int(result.get("token_count", 0)),
                settings.anthropic_model,
            )
    except Exception as exc:
        log.error("backend.persist_failed", error=str(exc))


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup() -> None:
    log.info("agentops.startup", env=settings.app_env, agent_url=settings.agent_url)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_pool()
    log.info("agentops.shutdown")
