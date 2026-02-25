interface Props {
  value: string;
  type?: "urgency" | "status" | "resolution";
  size?: "sm" | "md";
}

const URGENCY: Record<string, string> = {
  critical: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
  high:     "bg-amber-500/20 text-amber-300 border border-amber-500/30",
  medium:   "bg-blue-500/20  text-blue-300  border border-blue-500/30",
  low:      "bg-slate-500/20 text-slate-400 border border-slate-500/30",
};

const STATUS: Record<string, string> = {
  open:          "bg-slate-700/50 text-slate-400 border border-slate-600",
  investigating: "bg-blue-500/20  text-blue-300  border border-blue-500/30",
  completed:     "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  escalated:     "bg-amber-500/20   text-amber-300   border border-amber-500/30",
  failed:        "bg-rose-500/20    text-rose-300    border border-rose-500/30",
};

const RESOLUTION: Record<string, string> = {
  AUTO_RESOLVED: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  ESCALATED:     "bg-amber-500/20   text-amber-300   border border-amber-500/30",
  REFUNDED:      "bg-blue-500/20    text-blue-300    border border-blue-500/30",
  CORRECTED:     "bg-purple-500/20  text-purple-300  border border-purple-500/30",
};

export default function StatusBadge({ value, type = "status", size = "sm" }: Props) {
  const map = type === "urgency" ? URGENCY : type === "resolution" ? RESOLUTION : STATUS;
  const cls = map[value] ?? "bg-slate-700/50 text-slate-400 border border-slate-600";
  const padding = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";

  return (
    <span className={`inline-flex items-center rounded-md font-medium ${padding} ${cls}`}>
      {value.replace(/_/g, " ")}
    </span>
  );
}
