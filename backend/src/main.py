"""Casepilot — backend API."""

import json
from datetime import datetime

import httpx
import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings
from src.critic import review_verdict
from src.db.pool import close_pool, get_pool
from src.replay import compute_stability, generate_perturbations

log = structlog.get_logger()

app = FastAPI(
    title="Casepilot",
    description="AI-powered financial issue investigation platform",
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

    # Mark issue as in-progress so refreshes show investigating state
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE issues SET status = 'investigating' WHERE issue_id = $1",
            issue_id,
        )

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

    # Persist run trace — raises 500 if storage fails so the client knows
    try:
        await _persist_trace(result)
    except Exception as exc:
        log.error("backend.persist_failed", issue_id=issue_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Investigation completed but trace could not be saved.")

    # Critic review — Haiku audits the Sonnet verdict (never raises)
    critic = await review_verdict(
        issue_id=issue_id,
        structured_output=result.get("structured_output", {}),
        agent_reasoning=result.get("agent_reasoning", ""),
    )
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE run_traces SET critic_agrees=$1, critic_notes=$2, critic_model=$3 WHERE trace_id=$4",
                critic["agrees"], critic["note"], critic["model"], result["trace_id"],
            )
    except Exception as exc:
        log.warning("backend.critic_persist_failed", error=str(exc))

    return {**result, "critic": critic}


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
                   t.critic_agrees,
                   t.started_at::text AS run_started_at,
                   t.completed_at::text AS run_completed_at
            FROM issues i
            JOIN customers c ON c.customer_id = i.customer_id
            LEFT JOIN LATERAL (
                SELECT * FROM run_traces rt
                WHERE rt.issue_id = i.issue_id AND NOT rt.is_replay
                ORDER BY rt.started_at DESC
                LIMIT 1
            ) t ON true
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
                SUM(token_count)                                            AS total_tokens,
                COUNT(*) FILTER (WHERE critic_agrees IS NOT NULL)           AS critic_reviewed,
                COUNT(*) FILTER (WHERE critic_agrees = TRUE)                AS critic_agreed
            FROM run_traces
            WHERE status != 'running' AND NOT is_replay
            """
        )

        # Per-issue breakdown — one row per issue (most recent primary trace)
        by_issue_rows = await conn.fetch(
            """
            SELECT DISTINCT ON (issue_id) issue_id, confidence_score, escalate, status, critic_agrees
            FROM run_traces
            WHERE status != 'running' AND NOT is_replay
            ORDER BY issue_id, started_at DESC
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
              AND NOT is_replay
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
            WHERE t.escalate = TRUE AND NOT t.is_replay
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


# ── Replay engine ─────────────────────────────────────────────────────────────

class ReplayRequest(BaseModel):
    n: int = 3   # number of perturbation runs (1-5)


async def _run_replay_background(
    session_id: str,
    issue_id: str,
    customer_id: str,
    channel: str,
    urgency: str,
    perturbations: list[str],
    original_resolution_type: str,
    original_escalate: bool,
) -> None:
    """Run replay perturbations in the background, updating the session as we go."""
    pool = await get_pool()
    replay_results: list[dict] = []  # type: ignore[type-arg]

    for i, perturbed_message in enumerate(perturbations):
        log.info("replay.run", session_id=session_id, run=i + 1, of=len(perturbations))
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{settings.agent_url}/run",
                    json={
                        "issue_id":    issue_id,
                        "customer_id": customer_id,
                        "channel":     channel,
                        "urgency":     urgency,
                        "raw_message": perturbed_message,
                    },
                )
                resp.raise_for_status()
                result: dict = resp.json()  # type: ignore[type-arg]

            await _persist_trace(result, is_replay=True)

            run_resolution = (result.get("structured_output") or {}).get("resolution_type")
            run_escalate   = bool(result.get("escalate", False))
            matches        = (
                run_resolution == original_resolution_type
                and run_escalate == original_escalate
            )

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO replay_runs
                        (session_id, replay_trace_id, perturbation,
                         resolution_type, confidence_score, escalate, matches_original)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    session_id,
                    result.get("trace_id"),
                    perturbed_message,
                    run_resolution,
                    float(result.get("confidence_score", 0.0)),
                    run_escalate,
                    matches,
                )

            replay_results.append({
                "resolution_type":  run_resolution,
                "escalate":         run_escalate,
                "matches_original": matches,
            })

        except Exception as exc:
            log.error("replay.run_failed", session_id=session_id, run=i + 1, error=str(exc))
            replay_results.append({"matches_original": False})

    # Finalise session
    stability = compute_stability(original_resolution_type, original_escalate, replay_results)
    matches_count = sum(1 for r in replay_results if r.get("matches_original"))

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE replay_sessions
            SET status = 'completed', stability_score = $1,
                matches = $2, completed_at = NOW()
            WHERE session_id = $3
            """,
            stability, matches_count, session_id,
        )

    log.info("replay.complete", session_id=session_id, stability=stability)


@app.post("/api/v1/replay/{trace_id}", tags=["replay"])
async def trigger_replay(
    trace_id: str,
    body: ReplayRequest,
    background_tasks: BackgroundTasks,
) -> dict:  # type: ignore[type-arg]
    """
    Kick off a background replay with n perturbed message variants.
    Returns immediately with session_id and status='running'.
    Poll GET /api/v1/replay/sessions/{session_id} for results.
    """
    n = max(1, min(5, body.n))
    pool = await get_pool()

    # Load original trace + issue
    async with pool.acquire() as conn:
        trace = await conn.fetchrow(
            """
            SELECT t.trace_id, t.issue_id, t.status, t.escalate,
                   t.structured_output, t.confidence_score,
                   i.customer_id, i.raw_message, i.channel, i.urgency
            FROM run_traces t
            JOIN issues i ON i.issue_id = t.issue_id
            WHERE t.trace_id = $1
            """,
            trace_id,
        )
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found.")

    structured = trace["structured_output"]
    if isinstance(structured, str):
        structured = json.loads(structured)
    original_resolution_type = (structured or {}).get("resolution_type", "UNKNOWN")
    original_escalate = bool(trace["escalate"])

    # Create (or reset) replay session
    async with pool.acquire() as conn:
        session_id = await conn.fetchval(
            """
            INSERT INTO replay_sessions (trace_id, issue_id, n_runs)
            VALUES ($1, $2, $3)
            ON CONFLICT (trace_id) DO UPDATE
                SET n_runs = EXCLUDED.n_runs,
                    status = 'running',
                    matches = 0,
                    stability_score = NULL,
                    completed_at = NULL
            RETURNING session_id
            """,
            trace_id, trace["issue_id"], n,
        )

    log.info("replay.queued", session_id=session_id, trace_id=trace_id, n=n)

    # Generate perturbations synchronously (fast Haiku call, ~1-2s)
    perturbations = await generate_perturbations(trace["raw_message"], n)

    # Dispatch the slow agent loop to the background
    background_tasks.add_task(
        _run_replay_background,
        session_id,
        trace["issue_id"],
        trace["customer_id"],
        trace["channel"],
        trace["urgency"],
        perturbations,
        original_resolution_type,
        original_escalate,
    )

    return {
        "session_id": session_id,
        "trace_id":   trace_id,
        "issue_id":   trace["issue_id"],
        "status":     "running",
        "n_runs":     n,
        "matches":    0,
        "stability_score": None,
        "runs":       [],
    }


@app.get("/api/v1/replay/sessions/{session_id}", tags=["replay"])
async def get_replay_session(session_id: str) -> dict:  # type: ignore[type-arg]
    """Retrieve a completed replay session with all run details."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            "SELECT * FROM replay_sessions WHERE session_id = $1", session_id
        )
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
        runs = await conn.fetch(
            "SELECT * FROM replay_runs WHERE session_id = $1 ORDER BY created_at", session_id
        )

    return {
        **dict(session),
        "created_at":   str(session["created_at"]),
        "completed_at": str(session["completed_at"]) if session["completed_at"] else None,
        "runs": [dict(r) for r in runs],
    }


@app.get("/api/v1/stability", tags=["replay"])
async def get_stability() -> dict:  # type: ignore[type-arg]
    """Per-scenario stability summary across all completed replay sessions."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                i.issue_id,
                t.trace_id          AS original_trace_id,
                t.status            AS original_status,
                t.escalate          AS original_escalate,
                t.confidence_score  AS original_confidence,
                t.structured_output,
                rs.session_id,
                rs.n_runs,
                rs.matches,
                rs.stability_score,
                rs.status           AS session_status,
                rs.created_at::text AS session_created_at
            FROM issues i
            JOIN LATERAL (
                SELECT * FROM run_traces rt
                WHERE rt.issue_id = i.issue_id AND NOT rt.is_replay
                ORDER BY rt.started_at DESC
                LIMIT 1
            ) t ON true
            LEFT JOIN replay_sessions rs ON rs.trace_id = t.trace_id
            ORDER BY i.created_at
            """
        )

    scenarios = []
    for r in rows:
        row = dict(r)
        structured = row.pop("structured_output", None)
        if isinstance(structured, str):
            structured = json.loads(structured)
        row["original_resolution_type"] = (structured or {}).get("resolution_type")
        scenarios.append(row)

    replayed = [s for s in scenarios if s.get("stability_score") is not None]
    overall = (
        round(sum(float(s["stability_score"]) for s in replayed) / len(replayed), 3)
        if replayed else None
    )

    return {"scenarios": scenarios, "overall_stability": overall}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _persist_trace(result: dict, is_replay: bool = False) -> None:  # type: ignore[type-arg]
    """Write a RunResult dict to run_traces. Raises on error — callers must handle."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO run_traces (
                trace_id, issue_id, started_at, completed_at, status,
                tool_calls, agent_reasoning, structured_output,
                confidence_score, escalate, policy_flags,
                token_count, model, is_replay
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
            ON CONFLICT (trace_id) DO NOTHING
            """,
            result["trace_id"],
            result["issue_id"],
            datetime.fromisoformat(result["started_at"]),
            datetime.fromisoformat(result["completed_at"]),
            result["status"],
            json.dumps(result.get("tool_calls", [])),
            (result.get("agent_reasoning") or "")[:10_000],
            json.dumps(result.get("structured_output", {}), default=str),
            float(result.get("confidence_score", 0.0)),
            bool(result.get("escalate", False)),
            json.dumps(result.get("policy_flags", [])),
            int(result.get("token_count", 0)),
            settings.anthropic_model,
            is_replay,
        )
        # Sync issues.status so page refreshes reflect the final state
        if not is_replay:
            issue_status = "escalated" if result.get("escalate") else "resolved"
            await conn.execute(
                "UPDATE issues SET status = $1 WHERE issue_id = $2",
                issue_status, result["issue_id"],
            )


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup() -> None:
    log.info("casepilot.startup", env=settings.app_env, agent_url=settings.agent_url)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_pool()
    log.info("casepilot.shutdown")
