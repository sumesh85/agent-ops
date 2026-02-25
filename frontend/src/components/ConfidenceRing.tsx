interface Props {
  score: number;   // 0.0 – 1.0
  size?: number;   // px, default 88
}

export default function ConfidenceRing({ score, size = 88 }: Props) {
  const r = 32;
  const cx = 44;
  const cy = 44;
  const circumference = 2 * Math.PI * r;
  const filled = circumference * Math.min(1, Math.max(0, score));

  const color =
    score >= 0.8 ? "#34d399"   // emerald
    : score >= 0.6 ? "#fbbf24" // amber
    : "#f87171";               // red

  const pct = Math.round(score * 100);

  return (
    <svg width={size} height={size} viewBox="0 0 88 88" aria-label={`Confidence ${pct}%`}>
      {/* Track */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke="#1e293b"
        strokeWidth="7"
      />
      {/* Arc */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={color}
        strokeWidth="7"
        strokeDasharray={`${filled} ${circumference}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dasharray 0.6s ease" }}
      />
      {/* Label */}
      <text
        x={cx} y={cy - 5}
        textAnchor="middle"
        fill={color}
        fontSize="16"
        fontWeight="700"
        fontFamily="ui-monospace, monospace"
      >
        {pct}%
      </text>
      <text
        x={cx} y={cy + 11}
        textAnchor="middle"
        fill="#64748b"
        fontSize="9"
        fontWeight="500"
      >
        confidence
      </text>
    </svg>
  );
}
