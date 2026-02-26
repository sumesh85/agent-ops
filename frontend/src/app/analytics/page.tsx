"use client";

import { useState, useEffect } from "react";
import {
  getAnalytics,
  SCENARIO_LABELS,
  type AnalyticsData,
  type FlagCount,
  type IssueMetric,
} from "@/lib/api";

// ── Primitives ─────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "green" | "amber" | "blue" | "rose";
}) {
  const colors = {
    green: "text-emerald-400",
    amber: "text-amber-400",
    blue:  "text-blue-400",
    rose:  "text-rose-400",
  };
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ? colors[accent] : "text-slate-100"}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-slate-600 mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Donut chart ────────────────────────────────────────────────────────────────

function ResolutionDonut({
  autoResolved,
  escalated,
  failed,
}: {
  autoResolved: number;
  escalated: number;
  failed: number;
}) {
  const total = autoResolved + escalated + failed;
  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-600 text-sm">
        No runs yet
      </div>
    );
  }

  const r = 52;
  const cx = 70;
  const cy = 70;
  const circumference = 2 * Math.PI * r;

  const segments = [
    { value: autoResolved, color: "#34d399", label: "Auto-resolved" },
    { value: escalated,    color: "#fbbf24", label: "Escalated" },
    { value: failed,       color: "#f87171", label: "Failed" },
  ];

  let offset = 0;
  const arcs = segments.map((seg) => {
    const pct   = seg.value / total;
    const dash  = pct * circumference;
    const arc   = { ...seg, dash, gap: circumference - dash, offset };
    offset += dash;
    return arc;
  });

  const autoResPct = Math.round((autoResolved / total) * 100);

  return (
    <div className="flex items-center gap-8">
      <svg width="140" height="140" viewBox="0 0 140 140">
        {/* Track */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e293b" strokeWidth="14" />
        {arcs.map((arc, i) =>
          arc.value > 0 ? (
            <circle
              key={i}
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={arc.color}
              strokeWidth="14"
              strokeDasharray={`${arc.dash} ${arc.gap}`}
              strokeDashoffset={-arc.offset}
              strokeLinecap="butt"
              transform={`rotate(-90 ${cx} ${cy})`}
            />
          ) : null
        )}
        <text x={cx} y={cy - 6} textAnchor="middle" fill="#34d399"
              fontSize="22" fontWeight="700" fontFamily="ui-monospace, monospace">
          {autoResPct}%
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill="#64748b" fontSize="10">
          auto-resolved
        </text>
      </svg>

      {/* Legend */}
      <div className="space-y-2">
        {segments.map((seg) => (
          <div key={seg.label} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: seg.color }} />
            <span className="text-xs text-slate-400">{seg.label}</span>
            <span className="text-xs font-mono text-slate-200 ml-auto pl-4">{seg.value}</span>
          </div>
        ))}
        <div className="pt-1 border-t border-slate-800 flex justify-between text-xs text-slate-500">
          <span>Total</span>
          <span className="font-mono text-slate-300">{total}</span>
        </div>
      </div>
    </div>
  );
}

// ── Horizontal bar ─────────────────────────────────────────────────────────────

function HBar({
  label,
  value,
  max,
  color = "#6366f1",
  suffix = "",
}: {
  label: string;
  value: number;
  max: number;
  color?: string;
  suffix?: string;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <p className="text-xs text-slate-400 w-44 shrink-0 truncate">{label}</p>
      <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
        <div
          className="h-2 rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-xs font-mono text-slate-300 w-12 text-right shrink-0">
        {typeof value === "number" && !Number.isInteger(value)
          ? value.toFixed(2)
          : value}
        {suffix}
      </span>
    </div>
  );
}

// ── Confidence by scenario ─────────────────────────────────────────────────────

function ConfidenceByScenario({ issues }: { issues: IssueMetric[] }) {
  if (issues.length === 0) {
    return <p className="text-xs text-slate-600 py-4">No runs yet.</p>;
  }
  const max = 1.0;
  return (
    <div className="space-y-3">
      {issues.map((issue) => {
        const score = issue.confidence_score ?? 0;
        const color = score >= 0.8 ? "#34d399" : score >= 0.6 ? "#fbbf24" : "#f87171";
        const label = SCENARIO_LABELS[issue.issue_id] ?? issue.issue_id;
        return (
          <HBar
            key={issue.issue_id}
            label={label}
            value={score}
            max={max}
            color={color}
          />
        );
      })}
    </div>
  );
}

// ── Policy flag frequency ──────────────────────────────────────────────────────

function FlagFrequency({ flags }: { flags: FlagCount[] }) {
  if (flags.length === 0) {
    return <p className="text-xs text-slate-600 py-4">No policy flags yet.</p>;
  }
  const max = flags[0]?.count ?? 1;
  return (
    <div className="space-y-3">
      {flags.map((f) => (
        <HBar
          key={f.flag}
          label={f.flag}
          value={f.count}
          max={max}
          color="#f59e0b"
        />
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [data, setData]     = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const s = data?.summary;

  const resolutionPct =
    s && s.total_runs > 0
      ? Math.round((s.auto_resolved / s.total_runs) * 100)
      : null;

  // Approx cost: claude-sonnet-4-6 blended ~$5 / MTok
  const costUsd =
    s?.total_tokens != null
      ? ((s.total_tokens / 1_000_000) * 5).toFixed(4)
      : null;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Analytics</h1>
        <p className="text-sm text-slate-500 mt-1">
          Aggregated metrics across all completed agent runs
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-rose-900/30 border border-rose-800 rounded-xl text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* Stat cards */}
      {loading ? (
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : s ? (
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            label="Total Runs"
            value={s.total_runs}
            sub={`${s.auto_resolved} auto · ${s.escalated} escalated`}
          />
          <StatCard
            label="Resolution Rate"
            value={resolutionPct !== null ? `${resolutionPct}%` : "—"}
            sub="auto-resolved"
            accent={resolutionPct !== null && resolutionPct >= 60 ? "green" : "amber"}
          />
          <StatCard
            label="Avg Confidence"
            value={s.avg_confidence != null ? `${Math.round(s.avg_confidence * 100)}%` : "—"}
            sub="across all runs"
            accent={
              s.avg_confidence != null
                ? s.avg_confidence >= 0.8 ? "green"
                : s.avg_confidence >= 0.6 ? "amber"
                : "rose"
                : undefined
            }
          />
          <StatCard
            label="Est. API Cost"
            value={costUsd !== null ? `$${costUsd}` : "—"}
            sub={s.total_tokens != null ? `${s.total_tokens.toLocaleString()} tokens` : ""}
            accent="blue"
          />
        </div>
      ) : null}

      {/* Charts row */}
      {!loading && data && (
        <div className="grid grid-cols-2 gap-6">

          {/* Resolution donut */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-sm font-medium text-slate-300 mb-5">Resolution Breakdown</h2>
            <ResolutionDonut
              autoResolved={s?.auto_resolved ?? 0}
              escalated={s?.escalated ?? 0}
              failed={s?.failed ?? 0}
            />
          </div>

          {/* Avg duration card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-between">
            <h2 className="text-sm font-medium text-slate-300 mb-5">Performance</h2>
            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-500 mb-1">Avg time to resolve</p>
                <p className="text-3xl font-bold text-slate-100">
                  {s?.avg_duration_minutes != null
                    ? `${s.avg_duration_minutes} min`
                    : "—"}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800">
                <div>
                  <p className="text-xs text-slate-500">Auto-resolved</p>
                  <p className="text-xl font-bold text-emerald-400">{s?.auto_resolved ?? 0}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Escalated</p>
                  <p className="text-xl font-bold text-amber-400">{s?.escalated ?? 0}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confidence by scenario */}
      {!loading && data && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-sm font-medium text-slate-300 mb-5">Confidence by Scenario</h2>
          <ConfidenceByScenario issues={data.by_issue} />
        </div>
      )}

      {/* Policy flag frequency */}
      {!loading && data && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-sm font-medium text-slate-300 mb-5">
            Policy Flag Frequency
            <span className="ml-2 text-xs text-slate-600 font-normal">top 10</span>
          </h2>
          <FlagFrequency flags={data.policy_flag_frequency} />
        </div>
      )}
    </div>
  );
}
