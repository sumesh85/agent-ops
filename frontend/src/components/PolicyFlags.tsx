interface Props {
  flags: string[];
}

const FLAG_SEVERITY: Record<string, "critical" | "high" | "medium"> = {
  FRAUD_SUSPECTED:              "critical",
  MANDATORY_ESCALATION:         "critical",
  ACCOUNT_FREEZE_RECOMMENDED:   "critical",
  MAX_TURNS_EXCEEDED:           "critical",
  TAX_ADVICE_REQUIRED:          "high",
  CRA_PENALTY_RISK:             "high",
  AML_REVIEW_TRIGGERED:         "high",
  REGISTERED_ACCOUNT:           "medium",
  KYC_COMPLIANCE:               "medium",
  TAX_RELATED:                  "medium",
};

const SEVERITY_STYLE = {
  critical: "bg-rose-500/15 text-rose-300 border border-rose-500/25",
  high:     "bg-amber-500/15 text-amber-300 border border-amber-500/25",
  medium:   "bg-blue-500/15  text-blue-300  border border-blue-500/25",
};

const SEVERITY_DOT = {
  critical: "bg-rose-400",
  high:     "bg-amber-400",
  medium:   "bg-blue-400",
};

export default function PolicyFlags({ flags }: Props) {
  if (!flags || flags.length === 0) {
    return (
      <p className="text-sm text-slate-500 italic">No policy flags triggered.</p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {flags.map((flag) => {
        const severity = FLAG_SEVERITY[flag] ?? "medium";
        return (
          <span
            key={flag}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium ${SEVERITY_STYLE[severity]}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${SEVERITY_DOT[severity]}`} />
            {flag.replace(/_/g, " ")}
          </span>
        );
      })}
    </div>
  );
}
