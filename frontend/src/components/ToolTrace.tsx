import type { ToolCall } from "@/lib/api";

interface Props {
  toolCalls: ToolCall[];
}

const TOOL_SOURCE: Record<string, { label: string; color: string }> = {
  customer_lookup:               { label: "DB",  color: "text-blue-400" },
  account_lookup:                { label: "DB",  color: "text-blue-400" },
  account_login_history:         { label: "DB",  color: "text-blue-400" },
  account_communication_history: { label: "DB",  color: "text-blue-400" },
  transactions_search:           { label: "DB",  color: "text-blue-400" },
  transactions_metadata:         { label: "DB",  color: "text-blue-400" },
  policy_search:                 { label: "VEC", color: "text-purple-400" },
  cases_similar:                 { label: "VEC", color: "text-purple-400" },
};

function LatencyBar({ ms }: { ms: number }) {
  // max bar = 100ms; anything above is capped visually
  const pct = Math.min(100, (ms / 100) * 100);
  const color =
    ms < 20 ? "bg-emerald-500"
    : ms < 60 ? "bg-amber-500"
    : "bg-rose-500";

  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-slate-400 w-14 text-right">
        {ms.toFixed(1)}ms
      </span>
    </div>
  );
}

export default function ToolTrace({ toolCalls }: Props) {
  if (!toolCalls || toolCalls.length === 0) {
    return <p className="text-sm text-slate-500 italic">No tool calls recorded.</p>;
  }

  const cached = toolCalls.filter((t) => t.cache_hit).length;
  const totalMs = toolCalls.reduce((s, t) => s + t.latency_ms, 0);

  return (
    <div>
      {/* Summary bar */}
      <div className="flex items-center gap-4 mb-4 text-xs text-slate-500">
        <span>{toolCalls.length} calls</span>
        <span className="text-slate-700">•</span>
        <span>{cached} cached</span>
        <span className="text-slate-700">•</span>
        <span>{totalMs.toFixed(0)}ms total</span>
      </div>

      {/* Timeline */}
      <div className="space-y-px">
        {toolCalls.map((tc, i) => {
          const src = TOOL_SOURCE[tc.tool] ?? { label: "??", color: "text-slate-400" };
          return (
            <div
              key={i}
              className="grid grid-cols-[24px_180px_36px_1fr_140px] gap-3 items-center
                         px-3 py-2 rounded-lg hover:bg-slate-800/60 transition-colors group"
            >
              {/* Step number */}
              <span className="text-xs font-mono text-slate-600 group-hover:text-slate-400">
                {i + 1}
              </span>

              {/* Tool name */}
              <span className="font-mono text-sm text-slate-200 truncate">
                {tc.tool}
              </span>

              {/* Source badge */}
              <span className={`text-xs font-mono font-semibold ${src.color}`}>
                {src.label}
              </span>

              {/* Result summary */}
              <span className="text-xs text-slate-500 truncate">
                {tc.result_summary}
              </span>

              {/* Latency + cache */}
              <div className="flex items-center gap-2">
                {tc.cache_hit ? (
                  <span className="text-xs text-emerald-500 font-mono">●&nbsp;cache</span>
                ) : (
                  <LatencyBar ms={tc.latency_ms} />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
