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
  critic_agrees: boolean | null;
}

export interface ToolCall {
  tool: string;
  args_digest: string;
  latency_ms: number;
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
  is_replay: boolean;
  // Critic review (Haiku audits Sonnet's verdict)
  critic_agrees: boolean | null;
  critic_notes: string | null;
  critic_model: string | null;
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

export async function triggerReplay(
  traceId: string,
  n: number = 3,
): Promise<ReplaySession> {
  const res = await fetch(`${API_URL}/api/v1/replay/${traceId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Replay failed: ${res.status}`);
  }
  return res.json();
}

export async function getReplaySession(sessionId: string): Promise<ReplaySession> {
  const res = await fetch(`${API_URL}/api/v1/replay/sessions/${sessionId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load replay session: ${res.status}`);
  return res.json();
}

export async function getStability(): Promise<StabilityData> {
  const res = await fetch(`${API_URL}/api/v1/stability`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load stability: ${res.status}`);
  return res.json();
}

export async function getAnalytics(): Promise<AnalyticsData> {
  const res = await fetch(`${API_URL}/api/v1/analytics/summary`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load analytics: ${res.status}`);
  return res.json();
}

export async function listEscalations(): Promise<EscalationRun[]> {
  const res = await fetch(`${API_URL}/api/v1/escalations`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load escalations: ${res.status}`);
  const data = await res.json();
  return data.escalations;
}

export async function submitReview(
  traceId: string,
  decision: "approved" | "overridden" | "rejected",
  notes: string,
): Promise<{ review_id: string; decision: string }> {
  const res = await fetch(`${API_URL}/api/v1/escalations/${traceId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Review failed: ${res.status}`);
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

export interface ReplayRun {
  run_id: string;
  perturbation: string;
  resolution_type: string | null;
  confidence_score: number | null;
  escalate: boolean | null;
  matches_original: boolean;
  replay_trace_id: string | null;
  error?: string;
}

export interface ReplaySession {
  session_id: string;
  trace_id: string;
  issue_id: string;
  n_runs: number;
  matches: number;
  stability_score: number | null;
  status: string;
  original_resolution_type?: string;
  original_escalate?: boolean;
  runs: ReplayRun[];
}

export interface StabilityScenario {
  issue_id: string;
  original_trace_id: string;
  original_status: string;
  original_escalate: boolean;
  original_confidence: number | null;
  original_resolution_type: string | null;
  session_id: string | null;
  n_runs: number | null;
  matches: number | null;
  stability_score: number | null;
  session_status: string | null;
}

export interface StabilityData {
  scenarios: StabilityScenario[];
  overall_stability: number | null;
}

export interface AnalyticsSummary {
  total_runs: number;
  auto_resolved: number;
  escalated: number;
  failed: number;
  avg_confidence: number | null;
  avg_duration_minutes: number | null;
  total_tokens: number | null;
  critic_reviewed: number;
  critic_agreed: number;
}

export interface IssueMetric {
  issue_id: string;
  confidence_score: number | null;
  escalate: boolean;
  status: string;
  critic_agrees: boolean | null;
}

export interface FlagCount {
  flag: string;
  count: number;
}

export interface AnalyticsData {
  summary: AnalyticsSummary;
  by_issue: IssueMetric[];
  policy_flag_frequency: FlagCount[];
}

export interface EscalationRun {
  trace_id: string;
  issue_id: string;
  run_status: string;
  confidence_score: number;
  escalate: boolean;
  policy_flags: string[];
  agent_reasoning: string;
  structured_output: StructuredOutput;
  started_at: string;
  completed_at: string;
  urgency: "low" | "medium" | "high" | "critical";
  channel: string;
  raw_message: string;
  message_preview: string;
  customer_name: string;
  customer_id: string;
  critic_agrees: boolean | null;
  // review (null if not yet reviewed)
  review_id: string | null;
  decision: "approved" | "overridden" | "rejected" | null;
  notes: string | null;
  reviewer: string | null;
  reviewed_at: string | null;
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
