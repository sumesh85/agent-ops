import type { ToolCall, RunTrace } from "@/lib/api";

// ── Source metadata ────────────────────────────────────────────────────────────

const TOOL_META: Record<string, { source: string; color: string; border: string; bg: string }> = {
  customer_lookup:               { source: "DB",  color: "text-blue-400",   border: "border-blue-600/60",   bg: "bg-blue-950/20" },
  account_lookup:                { source: "DB",  color: "text-blue-400",   border: "border-blue-600/60",   bg: "bg-blue-950/20" },
  account_login_history:         { source: "DB",  color: "text-blue-400",   border: "border-blue-600/60",   bg: "bg-blue-950/20" },
  account_communication_history: { source: "DB",  color: "text-blue-400",   border: "border-blue-600/60",   bg: "bg-blue-950/20" },
  transactions_search:           { source: "DB",  color: "text-blue-400",   border: "border-blue-600/60",   bg: "bg-blue-950/20" },
  transactions_metadata:         { source: "DB",  color: "text-blue-400",   border: "border-blue-600/60",   bg: "bg-blue-950/20" },
  policy_search:                 { source: "VEC", color: "text-purple-400", border: "border-purple-600/60", bg: "bg-purple-950/20" },
  cases_similar:                 { source: "VEC", color: "text-purple-400", border: "border-purple-600/60", bg: "bg-purple-950/20" },
};

const DEFAULT_META = { source: "—", color: "text-slate-400", border: "border-slate-700", bg: "bg-slate-800/20" };

// ── Connector ──────────────────────────────────────────────────────────────────

function Connector() {
  return (
    <div className="flex flex-col items-center" aria-hidden>
      <div className="w-px h-5 bg-slate-700" />
      <svg width="12" height="7" viewBox="0 0 12 7" className="text-slate-700">
        <path d="M0 0L6 7L12 0" fill="currentColor" />
      </svg>
    </div>
  );
}

// ── Start node ─────────────────────────────────────────────────────────────────

function StartNode({ run }: { run: RunTrace }) {
  return (
    <div className="w-full rounded-xl border border-slate-600/50 bg-slate-800/60 overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-700/50">
        <div className="w-6 h-6 rounded-full bg-slate-600 flex items-center justify-center shrink-0">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <polygon points="2,1 9,5 2,9" fill="#94a3b8" />
          </svg>
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-200 uppercase tracking-wide">
            Investigation Start
          </p>
          <p className="text-xs text-slate-500 font-mono mt-0.5">{run.issue_id}</p>
        </div>
      </div>
      <div className="px-4 py-2.5 flex items-center gap-3 text-xs text-slate-400">
        <span>Model: <span className="font-mono text-slate-300">{run.model ?? "—"}</span></span>
        <span className="text-slate-700">·</span>
        <span>Max turns: <span className="font-mono text-slate-300">15</span></span>
        {run.started_at && (
          <>
            <span className="text-slate-700">·</span>
            <span>{new Date(run.started_at).toLocaleTimeString()}</span>
          </>
        )}
      </div>
    </div>
  );
}

// ── Tool node ──────────────────────────────────────────────────────────────────

function ToolNode({ tc, step }: { tc: ToolCall; step: number }) {
  const meta = TOOL_META[tc.tool] ?? DEFAULT_META;
  const latencyColor =
    tc.latency_ms < 20 ? "text-emerald-400"
    : tc.latency_ms < 80 ? "text-amber-400"
    : "text-rose-400";

  return (
    <div className={`w-full rounded-xl border ${meta.border} ${meta.bg} overflow-hidden`}>
      {/* Header row */}
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Step circle */}
        <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-600
                        flex items-center justify-center shrink-0">
          <span className="text-xs font-mono text-slate-400">{step}</span>
        </div>

        {/* Tool name */}
        <span className="font-mono text-sm text-slate-100 flex-1 truncate">{tc.tool}</span>

        {/* Source badge */}
        <span className={`text-xs font-semibold font-mono px-1.5 py-0.5 rounded
                          bg-slate-800/80 ${meta.color}`}>
          {meta.source}
        </span>

        {/* Latency */}
        <span className={`text-xs font-mono tabular-nums ${latencyColor}`}>
          {tc.latency_ms.toFixed(1)}ms
        </span>
      </div>

      {/* Result summary */}
      {tc.result_summary && (
        <div className="px-4 pb-3 pt-0">
          <p className="text-xs text-slate-400 leading-relaxed pl-9">{tc.result_summary}</p>
        </div>
      )}
    </div>
  );
}

// ── End node ───────────────────────────────────────────────────────────────────

function EndNode({ run }: { run: RunTrace }) {
  const out = run.structured_output;
  const escalated = run.escalate;
  const failed = run.status === "failed";

  const border = failed    ? "border-rose-600/60"
               : escalated ? "border-amber-500/60"
               :             "border-emerald-600/60";

  const bg = failed    ? "bg-rose-950/20"
           : escalated ? "bg-amber-950/20"
           :             "bg-emerald-950/20";

  const iconColor = failed ? "text-rose-400" : escalated ? "text-amber-400" : "text-emerald-400";
  const icon = failed ? "✕" : escalated ? "⚠" : "✓";

  return (
    <div className={`w-full rounded-xl border ${border} ${bg} overflow-hidden`}>
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-700/40">
        <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0
                         border ${border}`}>
          <span className={`text-xs font-bold ${iconColor}`}>{icon}</span>
        </div>
        <div className="flex-1">
          <p className={`text-xs font-semibold uppercase tracking-wide ${iconColor}`}>
            {out?.resolution_type ?? run.status}
          </p>
          {out?.escalation_priority && escalated && (
            <p className="text-xs text-amber-400/70 mt-0.5">
              Priority: {out.escalation_priority}
            </p>
          )}
        </div>
        {/* Confidence */}
        <div className="text-right">
          <p className="text-xs text-slate-500">Confidence</p>
          <p className={`text-sm font-bold font-mono ${iconColor}`}>
            {Math.round(run.confidence_score * 100)}%
          </p>
        </div>
      </div>

      {/* Root cause */}
      {out?.root_cause && (
        <div className="px-4 py-3">
          <p className="text-xs text-slate-400 leading-relaxed">{out.root_cause}</p>
        </div>
      )}

      {/* Footer stats */}
      <div className="px-4 py-2.5 bg-slate-900/40 border-t border-slate-700/30
                      flex items-center gap-4 text-xs text-slate-500">
        <span>
          <span className="text-slate-400">{run.tool_calls?.length ?? 0}</span> tool calls
        </span>
        <span className="text-slate-700">·</span>
        <span>
          <span className="text-slate-400">{run.token_count?.toLocaleString() ?? "—"}</span> tokens
        </span>
        {run.started_at && run.completed_at && (
          <>
            <span className="text-slate-700">·</span>
            <span>
              <span className="text-slate-400">
                {((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000).toFixed(1)}s
              </span> total
            </span>
          </>
        )}
      </div>
    </div>
  );
}

// ── Diagram ────────────────────────────────────────────────────────────────────

export default function WorkflowDiagram({ run }: { run: RunTrace }) {
  const toolCalls = run.tool_calls ?? [];

  if (toolCalls.length === 0 && !run.structured_output) {
    return <p className="text-sm text-slate-500 italic">No workflow data available.</p>;
  }

  return (
    <div className="flex flex-col items-stretch max-w-xl mx-auto">
      <StartNode run={run} />

      {toolCalls.map((tc, i) => (
        <div key={i}>
          <Connector />
          <ToolNode tc={tc} step={i + 1} />
        </div>
      ))}

      <Connector />
      <EndNode run={run} />
    </div>
  );
}
