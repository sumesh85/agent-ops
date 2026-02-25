# AgentOps Control Plane (MVP Spec)

**Generated on:** 2026-02-25T03:12:58.379751 UTC

------------------------------------------------------------------------

## Goal

Demonstrate an AI-native, technical system that makes *agentic
workflows* measurable, stable, and governable.

This is NOT a chatbot. This is a control plane for agentic AI systems.

Primary demo scenario: - Fintech customer support agent (synthetic
tickets)

Optional secondary scenario: - Internal analyst SQL agent reliability

------------------------------------------------------------------------

# 1. Problem Statement

Agentic LLM systems fail in ways traditional workflow engines don't
measure well:

-   Instability: small prompt/context changes produce materially
    different outputs\
-   Silent drift: behavior changes after prompt/model/tool updates\
-   Tool coupling: tool calls diverge or loop unexpectedly\
-   Hard-to-audit reasoning and decisions

This MVP introduces: - Run trace capture\
- Perturbation-based replay\
- Stability scoring\
- Drift monitoring\
- Optional self-healing loop

------------------------------------------------------------------------

# 2. Target Personas

## AI Platform Engineer

Needs reliability signals, stability metrics, and governance controls.

## Support Operations Lead

Needs consistent and safe responses to customers.

## Compliance / Risk Reviewer

Needs auditability and risk-topic detection.

------------------------------------------------------------------------

# 3. MVP Scope

## Must Have

-   Agent run trace ingestion
-   MCP tool call logging
-   Replay with 3 perturbations
-   Stability score calculation
-   Policy flag detection
-   Control plane dashboard (Runs, Run Detail, Replay, Overview)

## Nice to Have

-   Critic-based self-healing
-   Baseline comparison and regression alerting

## Out of Scope

-   Real customer data
-   Production integrations
-   Complex ML training
-   Full compliance rule engine

------------------------------------------------------------------------

# 4. UX Structure (No Chat UI)

## Page A -- Runs

Columns: - Run ID - Workflow Type - Model - Tool Count - Tokens - Cost -
Loop Depth - Stability Score - Risk Level - Status

Actions: - View Run - Replay - Compare to Baseline

------------------------------------------------------------------------

## Page B -- Run Detail

Sections: - Summary Card (model, stability, risk flags) - Execution
Graph (planner → tools → draft → critic → final) - Tool Trace - Policy
Flags - Final Structured Output

------------------------------------------------------------------------

## Page C -- Replay Comparison

Side-by-side comparison: - Base vs Perturb1 vs Perturb2 vs Perturb3 -
Similarity matrix - Field variance - Tool call diff - Stability
breakdown

------------------------------------------------------------------------

## Page D -- Stability Overview

Charts: - Stability distribution - Stability over time - Drift
indicators - Tool call anomalies - Loop depth histogram

------------------------------------------------------------------------

# 5. Workflow Types

## SupportReply (Primary)

Example Tickets: - Withdrawal delay - Tax question - Account
lock/security - Transfer request

Output Schema Example:

``` json
{
  "category": "WITHDRAWAL|TAX|SECURITY|TRANSFER|GENERAL",
  "answer": "short factual response",
  "next_steps": ["step1", "step2"],
  "disclaimer": "string",
  "needs_human_review": true,
  "citations": [{"source": "policy", "id": "POL-123"}]
}
```

------------------------------------------------------------------------

## SQLAnalysis (Optional)

Input: - Question + Schema

Output: - SQL (read-only) - Explanation - Summary

------------------------------------------------------------------------

# 6. Architecture Overview

Components:

1.  Agent Runner
2.  Trace Collector
3.  Replay Engine
4.  Evaluator
5.  Self-Heal Controller (optional)
6.  Control Plane UI
7.  Storage Layer

------------------------------------------------------------------------

# 7. Data Model

## runs

-   run_id
-   workflow_type
-   created_at
-   model
-   status
-   metrics (json)

## events

-   run_id
-   seq
-   event_type
-   payload

## tool_calls

-   run_id
-   tool_name
-   args_digest
-   latency_ms
-   result_meta

## replays

-   replay_id
-   base_run_id
-   perturbation_type
-   metrics

------------------------------------------------------------------------

# 8. MCP Integration

Example MCP tools: - knowledge.search() - db.query() - account.lookup()

Captured per tool call: - tool name - arguments hash - latency - result
metadata - error status

------------------------------------------------------------------------

# 9. Perturbation Types

P1 -- Instruction paraphrase\
P2 -- Context shuffle\
P3 -- Tool constraint variation

Each replay recomputes stability metrics.

------------------------------------------------------------------------

# 10. Stability Scoring

Stability Score (0--100):

-   Based on embedding similarity across replays
-   Penalizes structured field variance
-   Penalizes tool call divergence

Disagreement Score: - Measures variance across multiple generations

Policy Flags: - Topic detection (TAX, SECURITY, LEGAL) - Disclaimer
enforcement - Prohibited claim detection

------------------------------------------------------------------------

# 11. Self-Healing (Optional)

If stability \< threshold: 1. Trigger critic agent 2. Constrained retry
3. Re-score stability 4. Mark run as SELF_HEALED if improved

------------------------------------------------------------------------

# 12. Demo Flow (2--3 Minutes)

1.  Show Stability Overview dashboard
2.  Run low-risk support ticket → stable
3.  Run tax-related ticket → instability detected
4.  Show replay comparison
5.  Trigger self-heal → stability improves
6.  Show drift/regression detection

Close with: "This platform introduces reliability engineering principles
to agentic AI systems."

------------------------------------------------------------------------

# 13. 1-Week Build Plan

Day 1--2: Agent runner + trace logging\
Day 3: Replay engine\
Day 4: Stability metrics\
Day 5: Dashboard UI\
Day 6--7: Self-heal + polish

------------------------------------------------------------------------

# 14. Value Proposition

This platform enables:

-   Stability measurement
-   Drift detection
-   Tool usage governance
-   Self-healing agent workflows
-   Auditability for regulated environments

It is not an AI feature. It is AI reliability infrastructure.

------------------------------------------------------------------------

# End of Document
