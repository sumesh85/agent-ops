"""Agent service — FastAPI wrapper around the investigation runner."""

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings
from src.runner import run_investigation

log = structlog.get_logger()

app = FastAPI(
    title="Casepilot Investigation Agent",
    description="Claude + MCP investigation runner",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    issue_id:    str
    customer_id: str
    channel:     str
    urgency:     str
    raw_message: str


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.anthropic_model}


@app.post("/run", tags=["agent"])
async def run(req: RunRequest) -> dict:  # type: ignore[type-arg]
    """
    Run a full investigation for a given issue.
    Returns a RunResult dict. The caller (backend) persists the trace.
    """
    result = await run_investigation(
        issue_id=req.issue_id,
        customer_id=req.customer_id,
        channel=req.channel,
        urgency=req.urgency,
        raw_message=req.raw_message,
    )
    if result.get("status") == "failed" and result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.on_event("startup")
async def on_startup() -> None:
    log.info(
        "agent.startup",
        model=settings.anthropic_model,
        mcp_url=settings.mcp_server_url,
    )
