"""
Replay engine — perturbation generation and stability scoring.

Uses Claude Haiku to paraphrase customer messages (cheap, fast).
Falls back to rule-based variants if LLM call fails.
"""

import json
import re

import anthropic
import structlog

from src.config import settings

log = structlog.get_logger()

# Haiku: fast and cheap for paraphrasing (~$0.001 per call)
_PARAPHRASE_MODEL = "claude-haiku-4-5-20251001"


async def generate_perturbations(message: str, n: int) -> list[str]:
    """
    Generate n paraphrased versions of message using Haiku.
    All factual details (amounts, dates, names, account types) are preserved.
    Only wording, tone, and structure vary.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await client.messages.create(
            model=_PARAPHRASE_MODEL,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": (
                    f"Generate exactly {n} paraphrases of this customer support message. "
                    "Rules:\n"
                    "- Keep ALL factual details identical: amounts, dates, account types, names, transaction IDs\n"
                    "- Vary only: wording, sentence structure, tone (formal/casual, brief/detailed, calm/frustrated)\n"
                    "- Each paraphrase must be a complete, natural-sounding message\n"
                    f"- Return ONLY a valid JSON array of {n} strings, no other text\n\n"
                    f"Message:\n{message}"
                ),
            }],
        )

        raw = response.content[0].text.strip()

        # Try direct parse
        parsed = json.loads(raw)
        if isinstance(parsed, list) and len(parsed) >= n:
            return [str(p) for p in parsed[:n]]

    except json.JSONDecodeError:
        # Try to extract JSON array from surrounding text
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, list) and len(parsed) >= n:
                    return [str(p) for p in parsed[:n]]
            except json.JSONDecodeError:
                pass
        log.warning("replay.perturbation_parse_failed", raw_preview=raw[:100])

    except Exception as exc:
        log.warning("replay.perturbation_llm_failed", error=str(exc))

    # Fallback: rule-based variants
    log.info("replay.using_rule_based_fallback")
    return _rule_based_perturbations(message, n)


def _rule_based_perturbations(message: str, n: int) -> list[str]:
    """Simple deterministic fallback variants."""
    variants = [
        f"Hi support team, I need help with the following: {message}",
        f"To whom it may concern — {message} Please advise on next steps.",
        f"Hello, I'm reaching out regarding an issue. {message} Appreciate your assistance.",
        f"I wanted to follow up on this matter urgently. {message}",
        f"Good day. I have a concern I need resolved: {message} Thank you.",
    ]
    return variants[:n]


def compute_stability(
    original_resolution_type: str,
    original_escalate: bool,
    runs: list[dict],
) -> float:
    """
    Fraction of replay runs whose resolution_type AND escalate match the original.
    A score of 1.0 means the agent gave the same verdict on every variation.
    """
    if not runs:
        return 0.0
    matches = sum(
        1 for r in runs
        if r.get("resolution_type") == original_resolution_type
        and r.get("escalate") == original_escalate
    )
    return round(matches / len(runs), 3)
