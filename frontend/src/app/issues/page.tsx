"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  listIssues, triggerInvestigation,
  SCENARIO_LABELS, SCENARIO_ICONS,
  type Issue,
} from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ConfidenceRing from "@/components/ConfidenceRing";
import PolicyFlags from "@/components/PolicyFlags";

// ── Issue Card ────────────────────────────────────────────────────────────────

function IssueCard({
  issue,
  onInvestigate,
  loading,
}: {
  issue: Issue;
  onInvestigate: (id: string) => Promise<void>;
  loading: boolean;
}) {
  const label = SCENARIO_LABELS[issue.issue_id] ?? issue.issue_id;
  const icon  = SCENARIO_ICONS[issue.issue_id]  ?? "❓";
  const investigated = issue.run_status !== null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700
                    transition-colors">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <p className="text-sm font-semibold text-slate-100">{label}</p>
            <p className="text-xs text-slate-600 font-mono mt-0.5">{issue.issue_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge value={issue.urgency} type="urgency" size="sm" />
          {investigated && (
            <StatusBadge
              value={issue.escalate ? "escalated" : "completed"}
              type="status"
              size="sm"
            />
          )}
        </div>
      </div>

      {/* Message preview */}
      <p className="text-xs text-slate-500 leading-relaxed mb-4 line-clamp-2">
        {issue.message_preview}
      </p>

      {/* Post-investigation view */}
      {investigated && issue.confidence_score !== null && (
        <div className="mb-4 p-3 bg-slate-800/40 rounded-lg flex items-center gap-4">
          <ConfidenceRing score={issue.confidence_score} size={52} />
          <div className="flex-1 min-w-0">
            <PolicyFlags flags={issue.policy_flags ?? []} />
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {investigated && issue.trace_id ? (
          <Link
            href={`/runs/${issue.trace_id}`}
            className="flex-1 text-center text-xs py-2 rounded-lg bg-slate-800
                       text-slate-300 hover:bg-slate-700 transition-colors"
          >
            View Run Detail →
          </Link>
        ) : (
          <button
            onClick={() => onInvestigate(issue.issue_id)}
            disabled={loading}
            className="flex-1 text-xs py-2 rounded-lg bg-blue-600 text-white font-medium
                       hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor"
                          strokeWidth="3" strokeOpacity="0.25"/>
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor"
                        strokeWidth="3" strokeLinecap="round"/>
                </svg>
                Investigating…
              </>
            ) : "Investigate"}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function IssuesPage() {
  const [issues, setIssues]     = useState<Issue[]>([]);
  const [loading, setLoading]   = useState(true);
  const [running, setRunning]   = useState<string | null>(null);
  const [error, setError]       = useState<string | null>(null);

  const fetchIssues = useCallback(async () => {
    try {
      setIssues(await listIssues());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchIssues(); }, [fetchIssues]);

  const handleInvestigate = async (issueId: string) => {
    setRunning(issueId);
    setError(null);
    try {
      await triggerInvestigation(issueId);
      await fetchIssues();
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(null);
    }
  };

  const investigated = issues.filter((i) => i.run_status !== null);
  const autoResolved = investigated.filter((i) => !i.escalate).length;
  const escalated    = investigated.filter((i) => i.escalate).length;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Issues</h1>
        <p className="text-sm text-slate-500 mt-1">
          Trigger investigations and view results for each demo scenario
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total", value: issues.length },
          { label: "Investigated", value: investigated.length },
          { label: "Auto-resolved", value: autoResolved },
          { label: "Escalated", value: escalated },
        ].map(({ label, value }) => (
          <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-4">
            <p className="text-xs text-slate-500 mb-1">{label}</p>
            <p className="text-2xl font-bold text-slate-100">{value}</p>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-rose-900/30 border border-rose-800 rounded-xl text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* Issue grid */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-slate-900 border border-slate-800 rounded-xl
                                    animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {issues.map((issue) => (
            <IssueCard
              key={issue.issue_id}
              issue={issue}
              onInvestigate={handleInvestigate}
              loading={running === issue.issue_id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
