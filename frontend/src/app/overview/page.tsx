"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { listIssues, SCENARIO_LABELS, SCENARIO_ICONS, type Issue } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ConfidenceRing from "@/components/ConfidenceRing";

// ── Helpers ───────────────────────────────────────────────────────────────────

const ISSUE_ORDER = [
  "issue-wire-aml-0001",
  "issue-rrsp-over-0002",
  "issue-unauth-trade-0003",
  "issue-t5-mismatch-0004",
  "issue-etransfer-fail-0005",
  "issue-kyc-frozen-0006",
];

function scoreColor(score: number | null): string {
  if (score === null) return "bg-slate-700";
  if (score >= 0.8) return "bg-emerald-500";
  if (score >= 0.6) return "bg-amber-500";
  return "bg-rose-500";
}

function scoreTextColor(score: number | null): string {
  if (score === null) return "text-slate-500";
  if (score >= 0.8) return "text-emerald-400";
  if (score >= 0.6) return "text-amber-400";
  return "text-rose-400";
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  label, value, sub, accent,
}: {
  label: string; value: React.ReactNode; sub?: string; accent?: string;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ?? "text-slate-100"}`}>{value}</p>
      {sub && <p className="text-xs text-slate-600 mt-1">{sub}</p>}
    </div>
  );
}

// ── Confidence bar row ────────────────────────────────────────────────────────

function ConfidenceRow({ issue }: { issue: Issue }) {
  const label = SCENARIO_LABELS[issue.issue_id] ?? issue.issue_id;
  const icon  = SCENARIO_ICONS[issue.issue_id] ?? "❓";
  const score = issue.confidence_score;
  const pct   = score !== null ? Math.round(score * 100) : null;

  return (
    <div className="flex items-center gap-4 py-3 border-b border-slate-800/60 last:border-0">
      {/* Icon + label */}
      <span className="text-xl w-8 shrink-0 text-center">{icon}</span>
      <div className="w-52 shrink-0">
        <p className="text-sm text-slate-300 truncate">{label}</p>
        <p className="text-[10px] text-slate-600 font-mono mt-0.5">{issue.issue_id}</p>
      </div>

      {/* Bar */}
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
        {pct !== null ? (
          <div
            className={`h-full rounded-full transition-all ${scoreColor(score)}`}
            style={{ width: `${pct}%` }}
          />
        ) : (
          <div className="h-full w-full bg-slate-700/40 animate-pulse rounded-full" />
        )}
      </div>

      {/* Score */}
      <span className={`text-sm font-mono w-10 text-right shrink-0 ${scoreTextColor(score)}`}>
        {pct !== null ? `${pct}%` : "—"}
      </span>

      {/* Badges */}
      <div className="flex items-center gap-2 w-36 shrink-0 justify-end">
        {issue.run_status ? (
          <>
            <StatusBadge value={issue.run_status} type="status" size="sm" />
            {issue.escalate && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                ESC
              </span>
            )}
          </>
        ) : (
          <span className="text-xs text-slate-600">Not run</span>
        )}
      </div>

      {/* Link */}
      {issue.trace_id ? (
        <Link
          href={`/runs/${issue.trace_id}`}
          className="text-xs text-blue-400 hover:text-blue-300 shrink-0"
        >
          View →
        </Link>
      ) : (
        <span className="text-xs text-slate-700 shrink-0">View →</span>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function OverviewPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listIssues()
      .then(setIssues)
      .finally(() => setLoading(false));
  }, []);

  // Order issues by scenario sequence
  const ordered = ISSUE_ORDER.map((id) => issues.find((i) => i.issue_id === id)).filter(Boolean) as Issue[];

  const investigated = ordered.filter((i) => i.run_status !== null);
  const autoResolved = investigated.filter((i) => !i.escalate);
  const escalated    = investigated.filter((i) => i.escalate);
  const avgConf      = investigated.length
    ? investigated.reduce((s, i) => s + (i.confidence_score ?? 0), 0) / investigated.length
    : null;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Stability Overview</h1>
        <p className="text-sm text-slate-500 mt-1">
          Post-investigation confidence and resolution summary across all demo scenarios
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Total scenarios"
          value={ordered.length}
          sub="6 demo cases loaded"
        />
        <StatCard
          label="Investigated"
          value={investigated.length}
          sub={`${ordered.length - investigated.length} pending`}
        />
        <StatCard
          label="Auto-resolved"
          value={autoResolved.length}
          accent="text-emerald-400"
          sub="No human review needed"
        />
        <StatCard
          label="Escalated"
          value={escalated.length}
          accent="text-amber-400"
          sub="Human-in-the-loop required"
        />
      </div>

      {/* Confidence distribution */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
            Confidence Distribution
          </h2>
          {avgConf !== null && (
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">Avg confidence</span>
              <ConfidenceRing score={avgConf} size={52} />
            </div>
          )}
        </div>

        {loading ? (
          <div className="space-y-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="flex items-center gap-4 py-3">
                <div className="w-8 h-5 bg-slate-800 rounded animate-pulse" />
                <div className="w-52 h-4 bg-slate-800 rounded animate-pulse" />
                <div className="flex-1 h-2 bg-slate-800 rounded-full animate-pulse" />
                <div className="w-10 h-4 bg-slate-800 rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : (
          <div>
            {ordered.map((issue) => (
              <ConfidenceRow key={issue.issue_id} issue={issue} />
            ))}
          </div>
        )}
      </div>

      {/* Demo script callout */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
          Demo Script — 3 Minutes
        </h2>
        <div className="space-y-3">
          {[
            ["00:00", "This page", "Show 6 scenarios with mixed confidence scores"],
            ["00:30", "Scenario 4 — T5 Dividends", "Simple auto-resolve • confidence 0.97 • show tool trace"],
            ["01:00", "Scenario 3 — Unauthorized Trade", "High confidence (0.96) → STILL escalated • policy boundary"],
            ["01:45", "Scenario 2 — RRSP Risk", "Agent explicitly states what it doesn't know • confidence 0.54"],
            ["02:15", "Any Run Detail", "Audit trail • tool call timeline • policy flags"],
            ["02:45", "Close", "\"Every decision is traceable. Every boundary is enforced.\""],
          ].map(([time, scene, note]) => (
            <div key={time} className="flex gap-4 text-sm">
              <span className="font-mono text-slate-600 shrink-0 w-14">{time}</span>
              <span className="text-slate-300 shrink-0 w-56">{scene}</span>
              <span className="text-slate-500">{note}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
