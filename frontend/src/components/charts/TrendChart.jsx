// Readiness over time: one point per review cycle, joined by a line, with the threshold drawn as a dashed line.
// Each point is labelled with its score, a hover or keyboard focus shows the cycle, and the same numbers are listed
// underneath, so nothing depends on seeing the chart.
import { useState } from "react";
import { percent } from "../../format";

const W = 560, H = 200, PAD = { left: 44, right: 16, top: 24, bottom: 36 };
// Near either side, the tooltip opens inwards so it stays on a narrow screen
const edge = (share) => (share < 0.3 ? " edge-start" : share > 0.7 ? " edge-end" : "");

export default function TrendChart({ points }) {
  const [active, setActive] = useState(null);
  const top = Math.min(1, Math.ceil(Math.max(...points.map((p) => Math.max(p.score, p.threshold))) * 10 + 1) / 10);
  const x = (i) => PAD.left + (points.length === 1 ? (W - PAD.left - PAD.right) / 2 : (i / (points.length - 1)) * (W - PAD.left - PAD.right));
  const y = (v) => H - PAD.bottom - (v / top) * (H - PAD.top - PAD.bottom);
  const ticks = [0, top / 2, top];
  const threshold = points[points.length - 1].threshold;
  const point = active != null ? points[active] : null;

  return (
    <div className="trend">
      <div className="calibration-plot trend-plot" onMouseLeave={() => setActive(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="group" aria-label={`Readiness in ${points.length} review cycle${points.length === 1 ? "" : "s"}, from ${percent(points[0].score)} to ${percent(points[points.length - 1].score)}. The list below has every value.`}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="cal-grid" />
              <text x={PAD.left - 8} y={y(t)} className="cal-tick" textAnchor="end" dominantBaseline="middle">{Math.round(t * 100)}%</text>
            </g>
          ))}
          <line x1={PAD.left} x2={W - PAD.right} y1={y(threshold)} y2={y(threshold)} className="cal-diagonal" />
          <text x={W - PAD.right} y={y(threshold) - 6} className="cal-tick" textAnchor="end">Threshold {percent(threshold)}</text>
          {points.length > 1 && <polyline points={points.map((p, i) => `${x(i)},${y(p.score)}`).join(" ")} className="cal-line" />}
          {points.map((p, i) => (
            <g key={p.cycle_id} tabIndex={0} role="img" aria-label={`${p.name}: ${percent(p.score)}${p.recommended ? ", recommended" : ""}`}
              onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onBlur={() => setActive(null)}>
              <circle cx={x(i)} cy={y(p.score)} r={14} className="cal-hit" />
              <circle cx={x(i)} cy={y(p.score)} r={active === i ? 6 : 5} className="cal-point" />
              <text x={x(i)} y={H - PAD.bottom + 18} className="cal-tick" textAnchor="middle">{p.name}</text>
            </g>
          ))}
        </svg>
        {point && (
          <div className={`cal-tooltip${edge(x(active) / W)}`} role="status" style={{ left: `${(x(active) / W) * 100}%`, top: `${(y(point.score) / H) * 100}%` }}>
            <strong>{point.name}</strong>
            <span>Readiness {percent(point.score)}{point.recommended ? " · recommended" : ""}</span>
            {point.rescored && <span className="muted">Updated after a record change (was {percent(point.score_at_opening)})</span>}
          </div>
        )}
      </div>
      <ul className="plain-list trend-list">
        {points.map((p) => (
          <li key={p.cycle_id}><strong>{p.name}</strong>: {percent(p.score)}{p.recommended ? ", recommended" : ""}
            {p.status === "open" && <span className="muted"> (open now)</span>}
            {p.rescored && <span className="muted"> · updated after a record change, from {percent(p.score_at_opening)}</span>}</li>
        ))}
      </ul>
    </div>
  );
}
