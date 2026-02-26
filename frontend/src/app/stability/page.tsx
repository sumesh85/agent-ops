"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getStability, SCENARIO_LABELS, SCENARIO_ICONS, type StabilityScenario, type StabilityData } from "@/lib/api";

// ── Stability ring ─────────────────────────────────────────────────────────────

function StabilityRing({ score, size = 72 }: { score: number; size?: number }) {
  const r = 28;
  const cx = 36;
  const cy = 36;
  const circ = 2 * Math.PI * r;
  const filled = circ * Math.min(1, Math.max(0, score));
  const color = score >= 0.8 ? "#34d399" : score >= 0.6 ? "#fbbf24" : "#f87171";
  const pct = Math.round(score * 100);

  return (
    <svg width={size} height={size} viewBox="0 0 72 72" aria-label={`Stability ${pct}%`}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e293b" strokeWidth="6" />
      <circle
        cx={cx} cy={cy} r={r} fill="none"
        stroke={color} strokeWidth="6"
        strokeDasharray={`${filled} ${circ}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dasharray 0.6s ease" }}
      />
      <text x={cx} y={cy - 4} textAnchor="middle" fill={color}
            fontSize="14" fontWeight="700" fontFamily="ui-monospace, monospace">
        {pct}%
      </text>
      <text x={cx} y={cy + 10} textAnchor="middle" fill="#64748b" fontSize="8">
        stable
      </text>
    </svg>
  );
}

// ── Scenario card ──────────────────────────────────────────────────────────────

function ScenarioCard({ s }: { s: StabilityScenario }) {
  const label = SCENARIO_LABELS[s.issue_id] ?? s.issue_id;
  const icon  = SCENARIO_ICONS[s.issue_id] ?? "❓";
  const replayed  = s.stability_score !== null;
  const running   = s.session_status === "running";

  const resColor =
    s.original_resolution_type === "AUTO_RESOLVED" ? "text-emerald-400"
    : s.original_resolution_type === "ESCALATED"   ? "text-amber-400"
    : "text-slate-400";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <span className="text-xl">{icon}</span>
          <div>
            <p className="text-sm font-semibold text-slate-100">{label}</p>
            <p className="text-xs text-slate-600 font-mono mt-0.5">{s.issue_id}</p>
          </div>
        </div>
        {replayed && !running && (
          <StabilityRing score={Number(s.stability_score)} size={64} />
        )}
        {running && (
          <div className="flex items-center gap-2 text-xs text-amber-400">
            <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
            </svg>
            Running…
          </div>
        )}
      </div>

      {/* Original verdict */}
      {s.original_resolution_type && (
        <div className="mb-3 text-xs text-slate-500">
          Original verdict:{" "}
          <span className={`font-semibold ${resColor}`}>{s.original_resolution_type}</span>
          {s.original_confidence != null && (
            <span className="ml-2 text-slate-600">
              ({Math.round(Number(s.original_confidence) * 100)}% confidence)
            </span>
          )}
        </div>
      )}

      {/* Replay results */}
      {replayed && !running && s.matches !== null && s.n_runs !== null && (
        <div className="space-y-2">
          {/* Match bar */}
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-2 rounded-full transition-all duration-700"
                style={{
                  width: `${(s.matches / s.n_runs) * 100}%`,
                  background:
                    Number(s.stability_score) >= 0.8 ? "#34d399"
                    : Number(s.stability_score) >= 0.6 ? "#fbbf24"
                    : "#f87171",
                }}
              />
            </div>
            <span className="text-xs text-slate-400 font-mono shrink-0">
              {s.matches}/{s.n_runs} matched
            </span>
          </div>
          <p className="text-xs text-slate-600">
            {s.matches === s.n_runs
              ? "Agent gave identical verdict on all variations"
              : s.matches === 0
              ? "Agent verdict changed on every variation"
              : `Agent verdict changed on ${s.n_runs - s.matches} of ${s.n_runs} variations`}
          </p>
        </div>
      )}

      {/* Not yet replayed */}
      {!replayed && !running && s.original_trace_id && (
        <div className="mt-2">
          <Link
            href={`/runs/${s.original_trace_id}`}
            className="text-xs text-blue-400 hover:underline"
          >
            View run → trigger replay from run detail
          </Link>
        </div>
      )}

      {/* Not yet investigated */}
      {!s.original_trace_id && (
        <p className="text-xs text-slate-600 mt-2">Not investigated yet</p>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function StabilityPage() {
  const [data, setData]       = useState<StabilityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    getStability()
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const replayed = data?.scenarios.filter((s) => s.stability_score !== null) ?? [];
  const overall  = data?.overall_stability;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Stability</h1>
          <p className="text-sm text-slate-500 mt-1">
            How consistently does the agent reach the same verdict under varied message wording?
          </p>
        </div>
        {overall != null && (
          <div className="text-center">
            <StabilityRing score={overall} size={80} />
            <p className="text-xs text-slate-500 mt-1">Overall</p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-rose-900/30 border border-rose-800 rounded-xl text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* Stats */}
      {!loading && data && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Scenarios replayed", value: replayed.length },
            {
              label: "Fully stable",
              value: replayed.filter((s) => Number(s.stability_score) === 1.0).length,
            },
            {
              label: "Needs attention",
              value: replayed.filter((s) => Number(s.stability_score) < 0.8).length,
            },
          ].map(({ label, value }) => (
            <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-4">
              <p className="text-xs text-slate-500 mb-1">{label}</p>
              <p className="text-2xl font-bold text-slate-100">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* How it works callout */}
      <div className="p-4 bg-slate-800/40 border border-slate-700/50 rounded-xl text-xs text-slate-400 leading-relaxed">
        <span className="text-slate-300 font-medium">How it works: </span>
        The replay engine takes a completed investigation, generates {3} paraphrased versions
        of the original customer message (same facts, different wording), and re-runs the full
        agent loop on each. Stability = % of runs where the agent reaches the same
        resolution type and escalation decision as the original.
      </div>

      {/* Scenario grid */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-40 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {(data?.scenarios ?? []).filter((s, idx, arr) => arr.findIndex(x => x.issue_id === s.issue_id) === idx).map((s) => (
            <ScenarioCard key={s.issue_id} s={s} />
          ))}
        </div>
      )}
    </div>
  );
}
