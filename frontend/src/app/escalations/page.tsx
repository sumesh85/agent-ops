"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  listEscalations, submitReview,
  SCENARIO_LABELS, SCENARIO_ICONS,
  type EscalationRun,
} from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ConfidenceRing from "@/components/ConfidenceRing";
import PolicyFlags from "@/components/PolicyFlags";

// ── Decision badge ─────────────────────────────────────────────────────────────

const DECISION_STYLES: Record<string, string> = {
  approved:   "bg-amber-900/40 text-amber-300 border border-amber-700/50",
  overridden: "bg-emerald-900/40 text-emerald-300 border border-emerald-700/50",
  rejected:   "bg-rose-900/40 text-rose-300 border border-rose-700/50",
};

const DECISION_LABELS: Record<string, string> = {
  approved:   "✓ Approved — Human handling",
  overridden: "↩ Overridden — Auto-resolved",
  rejected:   "✗ Rejected — Re-investigate",
};

function DecisionBadge({ decision }: { decision: string }) {
  return (
    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${DECISION_STYLES[decision] ?? ""}`}>
      {DECISION_LABELS[decision] ?? decision}
    </span>
  );
}

// ── Review form ───────────────────────────────────────────────────────────────

function ReviewForm({
  traceId,
  onSubmit,
}: {
  traceId: string;
  onSubmit: (decision: "approved" | "overridden" | "rejected", notes: string) => Promise<void>;
}) {
  const [decision, setDecision] = useState<"approved" | "overridden" | "rejected">("approved");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit(decision, notes);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mt-4 pt-4 border-t border-slate-800 space-y-3">
      <p className="text-xs font-medium text-slate-400">Human Review Decision</p>

      {/* Decision selector */}
      <div className="flex gap-2">
        {(["approved", "overridden", "rejected"] as const).map((d) => (
          <button
            key={d}
            onClick={() => setDecision(d)}
            className={`flex-1 text-xs py-2 px-3 rounded-lg border transition-colors ${
              decision === d
                ? d === "approved"   ? "bg-amber-900/50 border-amber-600 text-amber-200"
                : d === "overridden" ? "bg-emerald-900/50 border-emerald-600 text-emerald-200"
                :                     "bg-rose-900/50 border-rose-600 text-rose-200"
                : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
            }`}
          >
            {d === "approved" ? "✓ Approve" : d === "overridden" ? "↩ Override" : "✗ Reject"}
          </button>
        ))}
      </div>

      {/* Decision explanation */}
      <p className="text-xs text-slate-500 italic">
        {decision === "approved"   && "You agree with the agent — you'll handle this manually."}
        {decision === "overridden" && "Agent was too cautious — mark as resolved without escalation."}
        {decision === "rejected"   && "Agent made an error — send back for re-investigation."}
      </p>

      {/* Notes */}
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Add notes (optional)..."
        rows={2}
        className="w-full text-xs bg-slate-800 border border-slate-700 rounded-lg px-3 py-2
                   text-slate-200 placeholder-slate-600 resize-none focus:outline-none
                   focus:border-slate-500"
      />

      <button
        onClick={handleSubmit}
        disabled={submitting}
        className="w-full text-xs py-2 rounded-lg bg-blue-600 text-white font-medium
                   hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed
                   transition-colors"
      >
        {submitting ? "Submitting…" : "Submit Review"}
      </button>
    </div>
  );
}

// ── Escalation card ───────────────────────────────────────────────────────────

function EscalationCard({
  run,
  onReview,
}: {
  run: EscalationRun;
  onReview: (traceId: string, decision: "approved" | "overridden" | "rejected", notes: string) => Promise<void>;
}) {
  const label = SCENARIO_LABELS[run.issue_id] ?? run.issue_id;
  const icon  = SCENARIO_ICONS[run.issue_id]  ?? "❓";
  const [expanded, setExpanded] = useState(false);
  const reviewed = run.decision !== null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors">

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <p className="text-sm font-semibold text-slate-100">{label}</p>
            <p className="text-xs text-slate-600 font-mono mt-0.5">{run.issue_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge value={run.urgency} type="urgency" size="sm" />
          <StatusBadge value="escalated" type="status" size="sm" />
        </div>
      </div>

      {/* Message preview */}
      <p className="text-xs text-slate-500 leading-relaxed mb-4 line-clamp-2">
        {run.message_preview}
      </p>

      {/* Confidence + policy flags */}
      <div className="mb-4 p-3 bg-slate-800/40 rounded-lg flex items-center gap-4">
        <ConfidenceRing score={run.confidence_score} size={52} />
        <div className="flex-1 min-w-0">
          <PolicyFlags flags={run.policy_flags ?? []} />
        </div>
      </div>

      {/* Structured output summary */}
      {run.structured_output && (
        <div className="mb-4 p-3 bg-slate-800/30 rounded-lg space-y-1">
          <p className="text-xs font-medium text-slate-400">Agent verdict</p>
          <p className="text-xs text-slate-300">{run.structured_output.root_cause}</p>
          {run.structured_output.escalation_priority && (
            <p className="text-xs text-amber-400 font-medium">
              Priority: {run.structured_output.escalation_priority}
            </p>
          )}
        </div>
      )}

      {/* Reasoning toggle */}
      {run.agent_reasoning && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-slate-500 hover:text-slate-300 transition-colors mb-3"
        >
          {expanded ? "▲ Hide reasoning" : "▼ Show agent reasoning"}
        </button>
      )}
      {expanded && run.agent_reasoning && (
        <div className="mb-4 p-3 bg-slate-950 rounded-lg border border-slate-800 max-h-40 overflow-y-auto">
          <p className="text-xs text-slate-400 whitespace-pre-wrap leading-relaxed font-mono">
            {run.agent_reasoning.slice(0, 1500)}
            {run.agent_reasoning.length > 1500 && "…"}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mb-2">
        <Link
          href={`/runs/${run.trace_id}`}
          className="flex-1 text-center text-xs py-2 rounded-lg bg-slate-800
                     text-slate-300 hover:bg-slate-700 transition-colors"
        >
          View Full Trace →
        </Link>
      </div>

      {/* Review status or form */}
      {reviewed ? (
        <div className="mt-4 pt-4 border-t border-slate-800 space-y-2">
          <p className="text-xs text-slate-500">
            Reviewed by <span className="text-slate-400">{run.reviewer}</span>
            {run.reviewed_at && (
              <span> · {new Date(run.reviewed_at).toLocaleString()}</span>
            )}
          </p>
          <DecisionBadge decision={run.decision!} />
          {run.notes && (
            <p className="text-xs text-slate-400 italic">"{run.notes}"</p>
          )}
        </div>
      ) : (
        <ReviewForm
          traceId={run.trace_id}
          onSubmit={(decision, notes) => onReview(run.trace_id, decision, notes)}
        />
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function EscalationsPage() {
  const [runs, setRuns]       = useState<EscalationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const fetchEscalations = useCallback(async () => {
    try {
      setRuns(await listEscalations());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchEscalations(); }, [fetchEscalations]);

  const handleReview = async (
    traceId: string,
    decision: "approved" | "overridden" | "rejected",
    notes: string,
  ) => {
    await submitReview(traceId, decision, notes);
    await fetchEscalations();
  };

  const pending  = runs.filter((r) => r.decision === null).length;
  const reviewed = runs.filter((r) => r.decision !== null).length;
  const critical = runs.filter((r) => r.urgency === "critical").length;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Escalation Queue</h1>
        <p className="text-sm text-slate-500 mt-1">
          Issues the agent escalated for human review — approve, override, or reject
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Escalated", value: runs.length },
          { label: "Pending Review",  value: pending,  accent: pending > 0 },
          { label: "Reviewed",        value: reviewed },
          { label: "Critical",        value: critical, accent: critical > 0 },
        ].map(({ label, value, accent }) => (
          <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-4">
            <p className="text-xs text-slate-500 mb-1">{label}</p>
            <p className={`text-2xl font-bold ${accent ? "text-amber-400" : "text-slate-100"}`}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-rose-900/30 border border-rose-800 rounded-xl text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && runs.length === 0 && (
        <div className="text-center py-20 text-slate-600">
          <p className="text-4xl mb-3">🎉</p>
          <p className="text-sm">No escalations yet.</p>
          <p className="text-xs mt-1">
            Investigate issues on the{" "}
            <Link href="/issues" className="text-blue-400 hover:underline">Issues</Link> page.
          </p>
        </div>
      )}

      {/* Cards */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-64 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {runs.map((run) => (
            <EscalationCard
              key={run.trace_id}
              run={run}
              onReview={handleReview}
            />
          ))}
        </div>
      )}
    </div>
  );
}
