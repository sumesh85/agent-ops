const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Issue {
  issue_id: string;
  customer_id: string;
  customer_name: string;
  urgency: "low" | "medium" | "high" | "critical";
  status: "open" | "investigating" | "resolved" | "escalated";
  channel: string;
  created_at: string;
  message_preview: string;
  trace_id: string | null;
  run_status: string | null;
  confidence_score: number | null;
  escalate: boolean | null;
  policy_flags: string[] | null;
  run_started_at: string | null;
  run_completed_at: string | null;
}

export interface ToolCall {
  tool: string;
  args_digest: string;
  latency_ms: number;
  cache_hit: boolean;
  result_summary: string;
}

export interface StructuredOutput {
  issue_type: string;
  root_cause: string;
  resolution: string;
  resolution_type: "AUTO_RESOLVED" | "ESCALATED" | "REFUNDED" | "CORRECTED";
  next_steps: string[];
  confidence_score: number;
  escalate: boolean;
  escalation_priority?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  policy_flags: string[];
  // Scenario-specific extra fields (evidence_summary, security_signals, breakdown, etc.)
  [key: string]: unknown;
}

export interface RunTrace {
  trace_id: string;
  issue_id: string;
  started_at: string;
  completed_at: string;
  status: string;
  tool_calls: ToolCall[];
  agent_reasoning: string;
  structured_output: StructuredOutput;
  confidence_score: number;
  escalate: boolean;
  policy_flags: string[];
  token_count: number;
  model: string;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function listIssues(): Promise<Issue[]> {
  const res = await fetch(`${API_URL}/api/v1/issues`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load issues: ${res.status}`);
  const data = await res.json();
  return data.issues;
}

export async function triggerInvestigation(issueId: string): Promise<RunTrace> {
  const res = await fetch(`${API_URL}/api/v1/investigate/${issueId}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Investigation failed: ${res.status}`);
  }
  return res.json();
}

export async function getRun(traceId: string): Promise<RunTrace> {
  const res = await fetch(`${API_URL}/api/v1/runs/${traceId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load run: ${res.status}`);
  return res.json();
}

// ── Scenario labels ────────────────────────────────────────────────────────────

export const SCENARIO_LABELS: Record<string, string> = {
  "issue-wire-aml-0001":      "Wire Transfer + AML Hold",
  "issue-rrsp-over-0002":     "RRSP Over-contribution Risk",
  "issue-unauth-trade-0003":  "Unauthorized Trade",
  "issue-t5-mismatch-0004":   "T5 Dividend Discrepancy",
  "issue-etransfer-fail-0005": "Failed E-Transfer Refund",
  "issue-kyc-frozen-0006":    "KYC Expired — Account Frozen",
};

export const SCENARIO_ICONS: Record<string, string> = {
  "issue-wire-aml-0001":       "🏦",
  "issue-rrsp-over-0002":      "📊",
  "issue-unauth-trade-0003":   "🚨",
  "issue-t5-mismatch-0004":    "📋",
  "issue-etransfer-fail-0005": "💸",
  "issue-kyc-frozen-0006":     "🔒",
};
