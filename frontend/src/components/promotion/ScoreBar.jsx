// The readiness score, always read against the threshold: as a large gauge (the explanation pages) or a thin bar
// (tables). At or above the threshold it is the "raises" teal; below it, a neutral grey: "not yet" is never an alarm.
// It is a readiness score, never called a probability or a chance.
import { CheckCircle2, Clock } from "lucide-react";
import { percent } from "../../format";
import { Badge } from "../ui";

export default function ScoreBar({ score, threshold, compact = false }) {
  const above = score >= threshold;
  return (
    <div className={`scorebar ${compact ? "compact" : ""}`}
      role="img" aria-label={`Readiness ${percent(score)}, threshold ${percent(threshold)}`}>
      {!compact && <div className="scorebar-label" style={{ left: percent(threshold) }}>Threshold {percent(threshold)}</div>}
      <div className="scorebar-track">
        <div className={`scorebar-fill ${above ? "above" : ""}`} style={{ width: percent(score) }} />
        <div className="scorebar-line" style={{ left: percent(threshold) }} />
      </div>
    </div>
  );
}

// A half circle from 0% (left) to 100% (right)
const R = 80, CX = 100, CY = 96, WIDTH = 16;
const point = (share, radius = R) => {
  const angle = Math.PI * (1 - share);
  return [CX + radius * Math.cos(angle), CY - radius * Math.sin(angle)];
};
const arc = (share) => {
  const [x, y] = point(Math.min(Math.max(share, 0.004), 1));
  return `M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${x.toFixed(2)} ${y.toFixed(2)}`;
};

/** The large gauge: the score in the middle, the threshold as a dark tick on the arc. */
export function Gauge({ score, threshold, recommended }) {
  const [x1, y1] = point(threshold, R - WIDTH / 2 - 6);
  const [x2, y2] = point(threshold, R + WIDTH / 2 + 6);
  const [lx, ly] = point(threshold, R + WIDTH / 2 + 12);
  return (
    <div className="gauge" role="img"
      aria-label={`Readiness score ${percent(score)}. Threshold ${percent(threshold)}. ${recommended ? "Recommended" : "Not yet recommended"}.`}>
      <svg viewBox="0 0 200 112" aria-hidden="true">
        <path d={arc(1)} className="gauge-track" fill="none" strokeWidth={WIDTH} strokeLinecap="round" />
        <path d={arc(score)} className={`gauge-fill ${score >= threshold ? "above" : ""}`} fill="none" strokeWidth={WIDTH} strokeLinecap="round" />
        <line x1={x1} y1={y1} x2={x2} y2={y2} className="gauge-threshold" strokeLinecap="round" />
        <text x={lx} y={ly} className="gauge-threshold-label" textAnchor={threshold < 0.45 ? "end" : threshold > 0.55 ? "start" : "middle"}>
          {percent(threshold)}
        </text>
      </svg>
      <div className="gauge-readout" aria-hidden="true">
        <span className="gauge-value">{percent(score)}</span>
        <span className="gauge-caption">Readiness score</span>
      </div>
    </div>
  );
}

/** "Recommended" or "Not yet recommended", always in words with an icon. The model's view, so a data badge. */
export function Verdict({ recommended, large = false }) {
  return recommended
    ? <Badge tone="up" icon={CheckCircle2} className={large ? "verdict" : ""}>Recommended</Badge>
    : <Badge icon={Clock} className={large ? "verdict" : ""}>Not yet recommended</Badge>;
}
