"""
Investigation runner — Claude + MCP client.

Flow:
  1. Connect to MCP server via SSE
  2. Fetch available tools from MCP server
  3. Build combined tool list (MCP tools + submit_resolution)
  4. Enter agentic loop (up to MAX_TURNS):
       a. Call Claude with current messages + all tool schemas
       b. On submit_resolution: capture structured output, exit loop
       c. On MCP tool: call via session.call_tool(), append result, continue
       d. On end_turn (fallback): exit loop
  5. Return RunResult dict

Design notes:
  - Agent owns NO database — it only calls MCP tools and Claude
  - submit_resolution is NOT in the MCP server; it is defined locally here
  - Cache awareness: latency < 5 ms is used as a proxy for Redis cache hit
  - MAX_TURNS guards against runaway loops
"""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import anthropic
import structlog
from mcp import ClientSession
from mcp.client.sse import sse_client

from src.config import settings
from src.prompts import SYSTEM_PROMPT

log = structlog.get_logger()
UTC = timezone.utc
MAX_TURNS = 15


# ── submit_resolution schema (terminal tool — never sent to MCP) ──────────────

SUBMIT_RESOLUTION: dict[str, Any] = {
    "name": "submit_resolution",
    "description": (
        "Submit the final investigation resolution. Call this ONLY when you have "
        "completed your investigation and are ready to submit your findings. "
        "This closes the investigation. Do not call any other tools after this."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "issue_type": {
                "type": "string",
                "description": (
                    "Classified issue type: WIRE_DELAY, RRSP_OVER, UNAUTH_TRADE, "
                    "TAX_SLIP, ETRANSFER_FAIL, KYC_EXPIRED, ACCOUNT_FROZEN, or GENERAL."
                ),
            },
            "root_cause": {
                "type": "string",
                "description": "A concise explanation of the root cause of the issue.",
            },
            "resolution": {
                "type": "string",
                "description": "What was determined and what happens next.",
            },
            "resolution_type": {
                "type": "string",
                "enum": ["AUTO_RESOLVED", "ESCALATED", "REFUNDED", "CORRECTED"],
                "description": "The resolution outcome category.",
            },
            "next_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of concrete next steps.",
            },
            "confidence_score": {
                "type": "number",
                "description": "Confidence in this resolution, between 0.0 and 1.0.",
            },
            "escalate": {
                "type": "boolean",
                "description": (
                    "True if this issue requires human review. MUST be true for: "
                    "suspected fraud, tax advice, over-contributions, or insufficient data."
                ),
            },
            "escalation_priority": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                "description": "Priority of escalation. Required when escalate=true.",
            },
            "policy_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Policy flag codes triggered during investigation.",
            },
        },
        "required": [
            "issue_type", "root_cause", "resolution", "resolution_type",
            "next_steps", "confidence_score", "escalate", "policy_flags",
        ],
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _digest(args: dict[str, Any]) -> str:
    payload = json.dumps(args, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def _summarise(tool_name: str, result: dict[str, Any]) -> str:
    if "error" in result:
        return f"ERROR: {result['error']}"
    match tool_name:
        case "customer_lookup":
            return f"Customer: {result.get('name')} | KYC: {result.get('kyc_status')}"
        case "account_lookup":
            count = result.get("count", 0)
            statuses = [a.get("status") for a in result.get("accounts", [])]
            return f"{count} account(s) — statuses: {statuses}"
        case "account_login_history":
            countries = result.get("unique_countries", [])
            return f"{result.get('count', 0)} events | countries: {countries}"
        case "account_communication_history":
            return f"{result.get('count', 0)} communication(s)"
        case "transactions_search":
            count = result.get("count", 0)
            filters = result.get("filters", {})
            return (
                f"{count} transaction(s) | "
                f"type={filters.get('transaction_type')} status={filters.get('status')}"
            )
        case "transactions_metadata":
            return (
                f"tx {result.get('transaction_id', '')[:8]}... "
                f"| {result.get('status')} | {result.get('amount')} {result.get('currency')}"
            )
        case "policy_search":
            return f"{result.get('count', 0)} policy chunk(s) for: '{result.get('query', '')[:40]}'"
        case "cases_similar":
            return f"{result.get('count', 0)} similar case(s)"
        case _:
            return f"{len(result)} field(s) returned"


def _mcp_to_anthropic(tool: Any) -> dict[str, Any]:
    """Convert an MCP Tool object to Anthropic tool_use format."""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.inputSchema,
    }


# ── Core runner ───────────────────────────────────────────────────────────────

async def run_investigation(
    issue_id: str,
    customer_id: str,
    channel: str,
    urgency: str,
    raw_message: str,
) -> dict[str, Any]:
    """
    Run a full investigation and return a RunResult dict.
    The caller (backend) is responsible for persisting the trace.
    """
    trace_id = str(uuid.uuid4())
    started_at = datetime.now(UTC)

    log.info("runner.start", trace_id=trace_id, issue_id=issue_id, customer_id=customer_id)

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"Please investigate the following customer issue:\n\n"
                f"Issue ID:    {issue_id}\n"
                f"Customer ID: {customer_id}\n"
                f"Channel:     {channel}\n"
                f"Urgency:     {urgency}\n\n"
                f"Customer message:\n\"{raw_message}\"\n\n"
                f"Start by looking up the customer profile and their accounts, "
                f"then investigate the specific issue based on what you find."
            ),
        }
    ]

    tool_call_logs: list[dict[str, Any]] = []
    reasoning_parts: list[str] = []
    total_tokens: int = 0
    structured_output: dict[str, Any] = {}
    investigation_complete = False

    try:
        async with sse_client(settings.mcp_server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Fetch tool list from MCP server and add submit_resolution locally
                tools_result = await session.list_tools()
                mcp_tools = [_mcp_to_anthropic(t) for t in tools_result.tools]
                all_tools = mcp_tools + [SUBMIT_RESOLUTION]

                log.info(
                    "runner.tools_loaded",
                    mcp_tool_count=len(mcp_tools),
                    total=len(all_tools),
                )

                client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

                for turn in range(MAX_TURNS):
                    log.debug("runner.turn", trace_id=trace_id, turn=turn)

                    response = await client.messages.create(
                        model=settings.anthropic_model,
                        max_tokens=4096,
                        system=SYSTEM_PROMPT,
                        tools=all_tools,  # type: ignore[arg-type]
                        messages=messages,
                    )

                    total_tokens += response.usage.input_tokens + response.usage.output_tokens

                    for block in response.content:
                        if hasattr(block, "text") and block.text:
                            reasoning_parts.append(block.text.strip())

                    if response.stop_reason == "end_turn":
                        log.warning("runner.end_turn_without_resolution", trace_id=trace_id, turn=turn)
                        break

                    if response.stop_reason != "tool_use":
                        log.warning("runner.unexpected_stop", reason=response.stop_reason)
                        break

                    messages.append({"role": "assistant", "content": response.content})
                    tool_results: list[dict[str, Any]] = []

                    for block in response.content:
                        if not hasattr(block, "type") or block.type != "tool_use":
                            continue

                        tool_name: str = block.name
                        tool_args: dict[str, Any] = block.input

                        # Terminal tool — capture and exit
                        if tool_name == "submit_resolution":
                            structured_output = tool_args
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": "Resolution recorded. Investigation complete.",
                            })
                            investigation_complete = True
                            log.info("runner.resolution_submitted", trace_id=trace_id, turn=turn)
                            break

                        # MCP tool call
                        t0 = time.monotonic()
                        mcp_result = await session.call_tool(tool_name, arguments=tool_args)
                        latency_ms = (time.monotonic() - t0) * 1000

                        # Extract text content from MCP result
                        raw_text = ""
                        if mcp_result.content:
                            first = mcp_result.content[0]
                            raw_text = first.text if hasattr(first, "text") else str(first)

                        try:
                            parsed: dict[str, Any] = json.loads(raw_text) if raw_text else {}
                        except json.JSONDecodeError:
                            parsed = {"raw": raw_text}

                        # Use latency as a proxy for cache hit (< 5 ms = Redis hit)
                        cache_hit = latency_ms < 5.0

                        tool_call_logs.append({
                            "tool": tool_name,
                            "args_digest": _digest(tool_args),
                            "latency_ms": round(latency_ms, 2),
                            "cache_hit": cache_hit,
                            "result_summary": _summarise(tool_name, parsed),
                        })

                        log.debug(
                            "runner.tool_called",
                            tool=tool_name,
                            latency_ms=round(latency_ms, 1),
                            cache_hit=cache_hit,
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": raw_text or "{}",
                        })

                    if tool_results:
                        messages.append({"role": "user", "content": tool_results})

                    if investigation_complete:
                        break

    except Exception as exc:
        log.exception("runner.error", trace_id=trace_id, error=str(exc))
        duration_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000
        return {
            "trace_id": trace_id,
            "issue_id": issue_id,
            "customer_id": customer_id,
            "status": "failed",
            "tool_calls": tool_call_logs,
            "structured_output": {},
            "confidence_score": 0.0,
            "escalate": True,
            "escalation_priority": "HIGH",
            "policy_flags": [],
            "agent_reasoning": "",
            "token_count": total_tokens,
            "duration_ms": round(duration_ms, 2),
            "error": str(exc),
        }

    # Guard: max turns reached without resolution
    if not investigation_complete and not structured_output:
        log.warning("runner.max_turns_reached", trace_id=trace_id)
        structured_output = {
            "issue_type": "GENERAL",
            "root_cause": "Investigation did not reach a conclusion within the allowed turns.",
            "resolution": "Escalating for human review.",
            "resolution_type": "ESCALATED",
            "next_steps": ["Human agent to review investigation trace and complete manually."],
            "confidence_score": 0.0,
            "escalate": True,
            "escalation_priority": "MEDIUM",
            "policy_flags": ["MAX_TURNS_EXCEEDED"],
        }

    duration_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000
    escalate: bool = structured_output.get("escalate", False)
    turns_taken = len([m for m in messages if m["role"] == "assistant"])

    log.info(
        "runner.complete",
        trace_id=trace_id,
        status="escalated" if escalate else "completed",
        confidence=structured_output.get("confidence_score", 0),
        turns=turns_taken,
        tool_calls=len(tool_call_logs),
        tokens=total_tokens,
        duration_ms=round(duration_ms),
    )

    return {
        "trace_id": trace_id,
        "issue_id": issue_id,
        "customer_id": customer_id,
        "status": "escalated" if escalate else "completed",
        "tool_calls": tool_call_logs,
        "structured_output": structured_output,
        "confidence_score": float(structured_output.get("confidence_score", 0.0)),
        "escalate": escalate,
        "escalation_priority": structured_output.get("escalation_priority", "LOW"),
        "policy_flags": structured_output.get("policy_flags", []),
        "agent_reasoning": "\n\n".join(reasoning_parts),
        "token_count": total_tokens,
        "duration_ms": round(duration_ms, 2),
        "error": None,
    }
