"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getRun, triggerReplay, getReplaySession, SCENARIO_LABELS, type RunTrace, type ReplaySession } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ConfidenceRing from "@/components/ConfidenceRing";
import PolicyFlags from "@/components/PolicyFlags";
import WorkflowDiagram from "@/components/WorkflowDiagram";

// ── Helpers ───────────────────────────────────────────────────────────────────

function duration(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  return `${(ms / 1000).toFixed(1)}s`;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-slate-900 border border-slate-800 rounded-xl p-6">
      <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="bg-slate-800/60 rounded-lg px-4 py-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-sm font-semibold text-slate-100">{value}</p>
      {sub && <p className="text-xs text-slate-600 mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Reasoning accordion ───────────────────────────────────────────────────────

function ReasoningBlock({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;

  const preview = text.slice(0, 200).replace(/\n/g, " ");

  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left
                   hover:bg-slate-800/60 transition-colors"
      >
        <span className="text-xs font-medium text-slate-400">Agent reasoning</span>
        <svg
          className={`w-4 h-4 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 16 16" fill="none"
        >
          <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5"
                strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {!open && (
        <p className="px-4 pb-3 text-xs text-slate-600 truncate">{preview}…</p>
      )}
      {open && (
        <div className="px-4 pb-4 text-xs text-slate-400 leading-relaxed whitespace-pre-wrap
                        font-mono max-h-80 overflow-y-auto border-t border-slate-700/50 pt-3">
          {text}
        </div>
      )}
    </div>
  );
}

// ── Extra fields renderer (evidence_summary, security_signals, breakdown, etc.) ──

const STANDARD_FIELDS = new Set([
  "issue_type", "root_cause", "resolution", "resolution_type",
  "next_steps", "confidence_score", "escalate", "escalation_priority", "policy_flags",
]);

function ExtraFields({ out }: { out: Record<string, unknown> }) {
  const extras = Object.entries(out).filter(([k]) => !STANDARD_FIELDS.has(k));
  if (extras.length === 0) return null;

  return (
    <div className="space-y-4">
      {extras.map(([key, value]) => (
        <div key={key}>
          <p className="text-xs text-slate-500 mb-1.5 capitalize">
            {key.replace(/_/g, " ")}
          </p>
          <ExtraValue value={value} />
        </div>
      ))}
    </div>
  );
}

function ExtraValue({ value }: { value: unknown }) {
  // Array of objects → card list
  if (Array.isArray(value) && value.length > 0 && typeof value[0] === "object") {
    return (
      <div className="space-y-2">
        {(value as Record<string, unknown>[]).map((item, i) => (
          <div key={i} className="bg-slate-800/50 rounded-lg px-3 py-2 flex flex-wrap gap-x-4 gap-y-1">
            {Object.entries(item).map(([k, v]) => (
              <span key={k} className="text-xs">
                <span className="text-slate-500">{k}: </span>
                <span className={`font-mono ${
                  String(v) === "HIGH" || String(v) === "CRITICAL" ? "text-rose-400" :
                  String(v) === "MEDIUM" ? "text-amber-400" : "text-slate-300"
                }`}>{String(v)}</span>
              </span>
            ))}
          </div>
        ))}
      </div>
    );
  }

  // Plain object → key-value grid
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return (
      <div className="bg-slate-800/50 rounded-lg px-3 py-2.5 grid grid-cols-2 gap-x-6 gap-y-1.5">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k} className="flex justify-between gap-2">
            <span className="text-xs text-slate-500 capitalize">{k.replace(/_/g, " ")}</span>
            <span className="text-xs font-mono text-slate-300">
              {typeof v === "number" ? v.toLocaleString() : String(v)}
            </span>
          </div>
        ))}
      </div>
    );
  }

  // Fallback
  return (
    <p className="text-sm text-slate-300 font-mono bg-slate-800/50 px-3 py-2 rounded-lg">
      {String(value)}
    </p>
  );
}

// ── Resolution card ───────────────────────────────────────────────────────────

function ResolutionCard({ run }: { run: RunTrace }) {
  const out = run.structured_output;
  if (!out) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-slate-500 mb-1">Issue type</p>
          <p className="text-sm font-mono text-slate-200">{out.issue_type}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-1">Resolution type</p>
          <StatusBadge value={out.resolution_type} type="resolution" size="md" />
        </div>
      </div>

      <div>
        <p className="text-xs text-slate-500 mb-1.5">Root cause</p>
        <p className="text-sm text-slate-300 leading-relaxed bg-slate-800/50 px-3 py-2.5 rounded-lg">
          {out.root_cause}
        </p>
      </div>

      <div>
        <p className="text-xs text-slate-500 mb-1.5">Resolution</p>
        <p className="text-sm text-slate-300 leading-relaxed bg-slate-800/50 px-3 py-2.5 rounded-lg">
          {out.resolution}
        </p>
      </div>

      {out.next_steps && out.next_steps.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 mb-1.5">Next steps</p>
          <ol className="space-y-1.5">
            {out.next_steps.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-300">
                <span className="text-slate-600 font-mono shrink-0 w-4">{i + 1}.</span>
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}

      {out.escalate && out.escalation_priority && (
        <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20
                        rounded-lg">
          <span className="text-amber-400 text-base">⚠</span>
          <div>
            <p className="text-xs font-semibold text-amber-400">
              Escalation required — {out.escalation_priority} priority
            </p>
            <p className="text-xs text-amber-400/70 mt-0.5">
              This issue requires human review before any action is taken.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Critic review ─────────────────────────────────────────────────────────────

function CriticPanel({ run }: { run: RunTrace }) {
  if (run.critic_agrees === null || run.critic_agrees === undefined) {
    return (
      <p className="text-xs text-slate-500 italic">
        No critic review yet — trigger an investigation to see the Haiku audit.
      </p>
    );
  }

  const agrees = run.critic_agrees;
  const border = agrees ? "border-emerald-700/40 bg-emerald-950/10" : "border-rose-700/40 bg-rose-950/10";
  const iconColor = agrees ? "text-emerald-400" : "text-rose-400";
  const icon = agrees ? "✓" : "✗";
  const label = agrees ? "Agrees with verdict" : "Flags a concern";

  return (
    <div className={`rounded-xl border ${border} overflow-hidden`}>
      <div className="flex items-center gap-3 px-4 py-3">
        <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0
                         border ${agrees ? "border-emerald-600/60" : "border-rose-600/60"}`}>
          <span className={`text-xs font-bold ${iconColor}`}>{icon}</span>
        </div>
        <div className="flex-1">
          <p className={`text-xs font-semibold ${iconColor}`}>{label}</p>
          {run.critic_model && (
            <p className="text-xs text-slate-600 font-mono mt-0.5">{run.critic_model}</p>
          )}
        </div>
      </div>
      {run.critic_notes && (
        <div className="px-4 pb-3 border-t border-slate-700/30 pt-3">
          <p className="text-xs text-slate-400 leading-relaxed">{run.critic_notes}</p>
        </div>
      )}
    </div>
  );
}

// ── Replay panel ──────────────────────────────────────────────────────────────

function StabilityBar({ score, matches, n }: { score: number; matches: number; n: number }) {
  const color = score >= 0.8 ? "#34d399" : score >= 0.6 ? "#fbbf24" : "#f87171";
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">Stability score</span>
        <span className="font-mono font-bold" style={{ color }}>
          {Math.round(score * 100)}% ({matches}/{n} matched)
        </span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-2 rounded-full transition-all duration-700"
          style={{ width: `${score * 100}%`, background: color }}
        />
      </div>
    </div>
  );
}

function ReplayPanel({ traceId }: { traceId: string }) {
  const [session, setSession]   = useState<ReplaySession | null>(null);
  const [running, setRunning]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const handleReplay = async () => {
    setRunning(true);
    setError(null);
    try {
      // Returns immediately — session is in 'running' state
      const initial = await triggerReplay(traceId, 3);

      // Poll until complete (max ~5 min, every 5s)
      let current = initial;
      for (let i = 0; i < 60 && current.status === "running"; i++) {
        await new Promise((r) => setTimeout(r, 5000));
        if (!mountedRef.current) return;
        current = await getReplaySession(current.session_id);
      }

      if (mountedRef.current) setSession(current);
    } catch (e) {
      if (mountedRef.current) setError(String(e));
    } finally {
      if (mountedRef.current) setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      {!session && !running && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500 leading-relaxed max-w-md">
            Re-run this investigation with 3 paraphrased variants of the customer message.
            Measures whether the agent reaches the same verdict under different wording.
          </p>
          <button
            onClick={handleReplay}
            className="shrink-0 text-xs px-4 py-2 rounded-lg bg-indigo-600 text-white
                       font-medium hover:bg-indigo-500 transition-colors"
          >
            Run Replay (3×)
          </button>
        </div>
      )}

      {running && (
        <div className="flex items-center gap-3 p-4 bg-slate-800/40 rounded-lg">
          <svg className="animate-spin w-4 h-4 text-indigo-400 shrink-0" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25"/>
            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
          </svg>
          <div>
            <p className="text-xs font-medium text-slate-200">Running 3 replay variations…</p>
            <p className="text-xs text-slate-500 mt-0.5">Polling for results every 5s — safe to wait here.</p>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-900/30 border border-rose-800 rounded-lg text-xs text-rose-300">
          {error}
        </div>
      )}

      {session && (
        <div className="space-y-4">
          <StabilityBar
            score={Number(session.stability_score ?? 0)}
            matches={session.matches}
            n={session.n_runs}
          />

          <div className="space-y-2">
            {session.runs.map((run, i) => {
              const matches = run.matches_original;
              const isOpen = expanded === i;
              return (
                <div
                  key={i}
                  className={`rounded-lg border overflow-hidden ${
                    matches ? "border-emerald-700/40 bg-emerald-950/10"
                    : "border-rose-700/40 bg-rose-950/10"
                  }`}
                >
                  <button
                    onClick={() => setExpanded(isOpen ? null : i)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left"
                  >
                    <span className={`text-sm font-bold shrink-0 ${matches ? "text-emerald-400" : "text-rose-400"}`}>
                      {matches ? "✓" : "✗"}
                    </span>
                    <span className="text-xs text-slate-400 flex-1 truncate">
                      Variant {i + 1}
                      {run.resolution_type && (
                        <span className="ml-2 font-mono text-slate-300">{run.resolution_type}</span>
                      )}
                      {run.confidence_score != null && (
                        <span className="ml-2 text-slate-500">
                          {Math.round(Number(run.confidence_score) * 100)}%
                        </span>
                      )}
                    </span>
                    <svg
                      className={`w-3.5 h-3.5 text-slate-600 transition-transform ${isOpen ? "rotate-180" : ""}`}
                      viewBox="0 0 16 16" fill="none"
                    >
                      <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5"
                            strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                  {isOpen && (
                    <div className="px-4 pb-3 border-t border-slate-700/30 pt-3 space-y-2">
                      <p className="text-xs text-slate-500 font-medium">Paraphrased message:</p>
                      <p className="text-xs text-slate-400 leading-relaxed bg-slate-900/50
                                    px-3 py-2 rounded-lg italic">
                        &ldquo;{run.perturbation}&rdquo;
                      </p>
                      {run.replay_trace_id && (
                        <Link
                          href={`/runs/${run.replay_trace_id}`}
                          className="text-xs text-blue-400 hover:underline"
                        >
                          View full replay trace →
                        </Link>
                      )}
                      {run.error && (
                        <p className="text-xs text-rose-400">{run.error}</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex justify-end">
            <Link href="/stability" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
              View all scenarios on Stability page →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RunDetailPage() {
  const { traceId } = useParams<{ traceId: string }>();
  const [run, setRun]     = useState<RunTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    getRun(traceId)
      .then(setRun)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [traceId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <svg className="animate-spin w-6 h-6 text-slate-600" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3"
                strokeLinecap="round"/>
        </svg>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="p-8">
        <Link href="/issues" className="text-sm text-slate-500 hover:text-slate-300 mb-6 inline-block">
          ← Back
        </Link>
        <div className="p-4 bg-rose-900/30 border border-rose-800 rounded-xl text-sm text-rose-300">
          {error ?? "Run not found."}
        </div>
      </div>
    );
  }

  const label = SCENARIO_LABELS[run.issue_id] ?? run.issue_id;
  const dur   = run.started_at && run.completed_at
    ? duration(run.started_at, run.completed_at) : "—";
  const out   = run.structured_output;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">

      {/* Replay banner */}
      {run.is_replay && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-indigo-950/50 border
                        border-indigo-700/40 rounded-xl text-xs text-indigo-300">
          <span>🔁</span>
          <span>
            This is a <span className="font-semibold">replay trace</span> — generated from a
            paraphrased variant of the original customer message. Not a primary investigation.
          </span>
        </div>
      )}

      {/* Back */}
      <Link href="/issues"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500
                       hover:text-slate-300 transition-colors">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M8 2L4 6l4 4" stroke="currentColor" strokeWidth="1.5"
                strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back to Issues
      </Link>

      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <StatusBadge value={run.status} type="status" size="md" />
            {out?.escalation_priority && run.escalate && (
              <StatusBadge value={out.escalation_priority} type="urgency" size="md" />
            )}
          </div>
          <h1 className="text-lg font-semibold text-slate-100">{label}</h1>
          <p className="text-xs text-slate-500 mt-1 font-mono">{run.trace_id}</p>
        </div>
        <ConfidenceRing score={run.confidence_score} size={84} />
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-4 gap-3">
        <Stat label="Duration"   value={dur} />
        <Stat label="Tool calls" value={run.tool_calls?.length ?? 0} />
        <Stat label="Tokens"     value={run.token_count?.toLocaleString()} sub={run.model} />
        <Stat label="Escalated"  value={run.escalate ? "Yes ⚠" : "No ✓"}
              sub={out?.escalation_priority} />
      </div>

      {/* Policy flags */}
      <Section title="Policy Flags">
        <PolicyFlags flags={run.policy_flags ?? []} />
      </Section>

      {/* Investigation workflow */}
      <Section title="Investigation Workflow">
        <WorkflowDiagram run={run} />
      </Section>

      {/* Agent reasoning */}
      {run.agent_reasoning && (
        <Section title="Agent Reasoning">
          <ReasoningBlock text={run.agent_reasoning} />
        </Section>
      )}

      {/* Resolution */}
      <Section title="Resolution">
        <ResolutionCard run={run} />
      </Section>

      {/* Evidence details — scenario-specific extra fields */}
      {out && Object.keys(out).some((k) => !STANDARD_FIELDS.has(k)) && (
        <Section title="Evidence Details">
          <ExtraFields out={out as Record<string, unknown>} />
        </Section>
      )}

      {/* Critic review */}
      <Section title="Critic Review">
        <CriticPanel run={run} />
      </Section>

      {/* Replay engine — only for primary investigations */}
      {!run.is_replay && (
        <Section title="Replay & Stability">
          <ReplayPanel traceId={run.trace_id} />
        </Section>
      )}

    </div>
  );
}
