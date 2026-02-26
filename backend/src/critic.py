"""
Critic pattern — Haiku reviews Sonnet's investigation verdict.

Validates resolution logic, confidence calibration, and escalation decision.
Never raises — returns a safe fallback on any error so it can never block
investigation persistence.
"""

import json

import anthropic
import structlog

from src.config import settings

log = structlog.get_logger()

_CRITIC_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM = """You are a senior compliance reviewer auditing an AI agent's investigation verdict.

Review the structured output and assess:
1. Is resolution_type correct for the stated root_cause?
2. Does confidence_score seem appropriate (not too high/low)?
3. Is the escalation decision sound? (escalate=true is required for: suspected fraud,
   tax/regulatory advice, over-contributions, AML flags, insufficient data to decide)
4. Are policy_flags comprehensive given the described root_cause?

Respond with ONLY a valid JSON object — no markdown, no extra text:
{"agrees": true, "note": "One or two sentence explanation."}

Set agrees=false only for meaningful concerns (wrong resolution type, clearly wrong
escalation decision, dangerously overconfident score). Minor stylistic differences
are not a concern."""


async def review_verdict(
    issue_id: str,
    structured_output: dict,  # type: ignore[type-arg]
    agent_reasoning: str,
) -> dict:  # type: ignore[type-arg]
    """
    Haiku reviews Sonnet's structured output.
    Returns {"agrees": bool, "note": str, "model": str}.
    Never raises.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    context = (
        f"Issue ID: {issue_id}\n\n"
        f"Agent verdict:\n{json.dumps(structured_output, indent=2)}\n\n"
        f"Agent reasoning (excerpt):\n{agent_reasoning[:600]}"
    )

    raw = ""
    try:
        response = await client.messages.create(
            model=_CRITIC_MODEL,
            max_tokens=300,
            system=_SYSTEM,
            messages=[{"role": "user", "content": context}],
        )
        raw = response.content[0].text.strip()
        parsed = json.loads(raw)
        return {
            "agrees": bool(parsed.get("agrees", True)),
            "note":   str(parsed.get("note", "")),
            "model":  _CRITIC_MODEL,
        }
    except json.JSONDecodeError:
        log.warning("critic.parse_failed", raw_preview=raw[:120])
    except Exception as exc:
        log.warning("critic.failed", issue_id=issue_id, error=str(exc))

    # Safe fallback — don't block trace persistence
    return {"agrees": True, "note": "Critic review unavailable.", "model": _CRITIC_MODEL}
