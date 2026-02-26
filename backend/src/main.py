"""AgentOps Control Plane — backend API."""

import json
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/analytics/summary", tags=["analytics"])
async def analytics_summary() -> dict:  # type: ignore[type-arg]
    """Aggregated metrics across all completed run traces."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Overall summary
        summary = await conn.fetchrow(
            """
            SELECT
                COUNT(*)                                                    AS total_runs,
                COUNT(*) FILTER (WHERE escalate = FALSE AND status = 'completed') AS auto_resolved,
                COUNT(*) FILTER (WHERE escalate = TRUE)                     AS escalated,
                COUNT(*) FILTER (WHERE status = 'failed')                   AS failed,
                ROUND(AVG(confidence_score)::numeric, 3)                    AS avg_confidence,
                ROUND(AVG(
                    EXTRACT(EPOCH FROM (completed_at - started_at)) / 60.0
                )::numeric, 2)                                              AS avg_duration_minutes,
                SUM(token_count)                                            AS total_tokens
            FROM run_traces
            WHERE status != 'running'
            """
        )

        # Per-issue breakdown
        by_issue_rows = await conn.fetch(
            """
            SELECT issue_id, confidence_score, escalate, status
            FROM run_traces
            WHERE status != 'running'
            ORDER BY started_at DESC
            """
        )

        # Policy flag frequency (unnest JSONB array)
        flag_rows = await conn.fetch(
            """
            SELECT flag, COUNT(*) AS cnt
            FROM run_traces,
                 jsonb_array_elements_text(
                     CASE WHEN jsonb_typeof(policy_flags) = 'array'
                          THEN policy_flags ELSE '[]'::jsonb END
                 ) AS flag
            WHERE status != 'running'
              AND flag != ''
            GROUP BY flag
            ORDER BY cnt DESC
            LIMIT 10
            """
        )

    return {
        "summary": dict(summary) if summary else {},
        "by_issue": [dict(r) for r in by_issue_rows],
        "policy_flag_frequency": [{"flag": r["flag"], "count": r["cnt"]} for r in flag_rows],
    }


# ── Escalation queue ──────────────────────────────────────────────────────────

@app.get("/api/v1/escalations", tags=["escalations"])
async def list_escalations() -> dict:  # type: ignore[type-arg]
    """List all escalated runs with issue context and any existing review."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                t.trace_id, t.issue_id, t.status AS run_status,
                t.confidence_score, t.escalate, t.policy_flags,
                t.agent_reasoning, t.structured_output,
                t.started_at::text, t.completed_at::text,
                i.urgency, i.channel, i.raw_message,
                LEFT(i.raw_message, 160) AS message_preview,
                c.name AS customer_name, c.customer_id,
                r.review_id, r.decision, r.notes,
                r.reviewer, r.reviewed_at::text
            FROM run_traces t
            JOIN issues i     ON i.issue_id = t.issue_id
            JOIN customers c  ON c.customer_id = i.customer_id
            LEFT JOIN escalation_reviews r ON r.trace_id = t.trace_id
            WHERE t.escalate = TRUE
            ORDER BY
                CASE i.urgency WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                               WHEN 'medium' THEN 3 ELSE 4 END,
                t.started_at DESC
            """
        )
    escalations = []
    for r in rows:
        row = dict(r)
        for field in ("policy_flags", "structured_output"):
            if isinstance(row.get(field), str):
                row[field] = json.loads(row[field])
        escalations.append(row)
    return {"escalations": escalations, "count": len(escalations)}


class ReviewRequest(BaseModel):
    decision: str   # approved | overridden | rejected
    notes: str = ""
    reviewer: str = "human_agent"


@app.post("/api/v1/escalations/{trace_id}/review", tags=["escalations"])
async def review_escalation(trace_id: str, body: ReviewRequest) -> dict:  # type: ignore[type-arg]
    """
    Submit a human review decision for an escalated run.

    - approved:   human agrees with escalation, will handle manually
    - overridden: human overrides — issue can be auto-resolved after all
    - rejected:   agent was wrong, re-investigate (future: trigger replay)
    """
    if body.decision not in ("approved", "overridden", "rejected"):
        raise HTTPException(
            status_code=422,
            detail="decision must be one of: approved, overridden, rejected",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        trace = await conn.fetchrow(
            "SELECT trace_id, issue_id, escalate FROM run_traces WHERE trace_id = $1",
            trace_id,
        )
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found.")
        if not trace["escalate"]:
            raise HTTPException(status_code=422, detail="This run was not escalated.")

        # Upsert — one review per trace
        review_id = await conn.fetchval(
            """
            INSERT INTO escalation_reviews (trace_id, issue_id, reviewer, decision, notes)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (trace_id) DO UPDATE
                SET decision    = EXCLUDED.decision,
                    notes       = EXCLUDED.notes,
                    reviewer    = EXCLUDED.reviewer,
                    reviewed_at = NOW()
            RETURNING review_id
            """,
            trace_id,
            trace["issue_id"],
            body.reviewer,
            body.decision,
            body.notes,
        )

        new_status = (
            "resolved"  if body.decision == "overridden" else
            "open"      if body.decision == "rejected"   else
            "escalated"
        )
        await conn.execute(
            "UPDATE issues SET status = $1 WHERE issue_id = $2",
            new_status, trace["issue_id"],
        )

    log.info(
        "backend.escalation_reviewed",
        trace_id=trace_id, decision=body.decision, reviewer=body.reviewer,
    )
    return {"review_id": review_id, "trace_id": trace_id, "decision": body.decision}


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
