// Calibration (a reliability diagram): for ten equal-sized groups of employees, ordered by score, the average score
// against the share actually promoted, with 95% intervals. Points on the dashed diagonal mean "a score of 30% means
// about 30%". One series, so no legend: the title names it. Each point has a hover/keyboard tooltip, and the same
// numbers are in a table underneath, so nothing depends on seeing the chart.
import { useState } from "react";
import { percent } from "../../format";

const W = 440, H = 300, PAD = { left: 48, right: 16, top: 14, bottom: 42 };
const pct1 = (v) => `${(v * 100).toFixed(1)}%`;

export function CalibrationSummary({ calibration: c }) {
  const tag = { "well calibrated": "tag tag-yes", "roughly calibrated": "tag tag-info" }[c.verdict] || "tag tag-warn";
  return (
    <p className="calibration-summary">
      <span className={tag}>{c.verdict.charAt(0).toUpperCase() + c.verdict.slice(1)}</span>
      <span className="small muted">
        Average gap {(c.ece * 100).toFixed(1)} percentage points · slope {c.slope.toFixed(2)} (1 is perfect) ·
        Brier {c.brier.toFixed(3)} against {c.brier_baseline.toFixed(3)} for always guessing {percent(c.base_rate)} ·
        {" "}{c.groups_within_interval} of {c.bins.length} groups within their 95% interval
      </span>
    </p>
  );
}

export default function CalibrationChart({ calibration: c }) {
  const [active, setActive] = useState(null);
  const rows = c.bins;
  // Both axes on the same scale, so the diagonal is the 45° "perfect" line; rounded up to the next 10%
  const top = Math.ceil(Math.max(...rows.map((r) => Math.max(r.mean_score, r.promoted_high))) * 10 + 0.0001) / 10;
  const x = (v) => PAD.left + (v / top) * (W - PAD.left - PAD.right);
  const y = (v) => H - PAD.bottom - (v / top) * (H - PAD.top - PAD.bottom);
  const ticks = Array.from({ length: Math.round(top * 10) + 1 }, (_, i) => i / 10);
  const point = active != null ? rows[active] : null;

  return (
    <div className="calibration">
      <div className="calibration-plot" onMouseLeave={() => setActive(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="group"
          aria-label={`Calibration chart: ten score groups from ${pct1(rows[0].mean_score)} to ${pct1(rows[rows.length - 1].mean_score)}; average gap ${(c.ece * 100).toFixed(1)} percentage points. The table below has every value.`}>
          {/* Recessive grid and axes */}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={x(0)} x2={x(top)} y1={y(t)} y2={y(t)} className="cal-grid" />
              <text x={PAD.left - 8} y={y(t)} className="cal-tick" textAnchor="end" dominantBaseline="middle">{Math.round(t * 100)}%</text>
              <text x={x(t)} y={H - PAD.bottom + 16} className="cal-tick" textAnchor="middle">{Math.round(t * 100)}%</text>
            </g>
          ))}
          <text x={(x(0) + x(top)) / 2} y={H - 6} className="cal-axis" textAnchor="middle">Average readiness score in the group</text>
          <text transform={`translate(12 ${(y(0) + y(top)) / 2}) rotate(-90)`} className="cal-axis" textAnchor="middle">Share actually promoted</text>
          {/* Perfect calibration (named in the caption above the chart, where it can't collide with a point) */}
          <line x1={x(0)} y1={y(0)} x2={x(top)} y2={y(top)} className="cal-diagonal" />
          {/* 95% intervals, the series line, then the points with a surface ring */}
          {rows.map((r, i) => <line key={`e${i}`} x1={x(r.mean_score)} x2={x(r.mean_score)} y1={y(r.promoted_low)} y2={y(r.promoted_high)} className="cal-interval" />)}
          <polyline points={rows.map((r) => `${x(r.mean_score)},${y(r.promoted)}`).join(" ")} className="cal-line" />
          {rows.map((r, i) => (
            <g key={`p${i}`} tabIndex={0} role="img" aria-label={describe(r, i)}
              onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onBlur={() => setActive(null)}>
              <circle cx={x(r.mean_score)} cy={y(r.promoted)} r={14} className="cal-hit" />
              <circle cx={x(r.mean_score)} cy={y(r.promoted)} r={active === i ? 6 : 5} className="cal-point" />
            </g>
          ))}
        </svg>
        {point && (
          <div className="cal-tooltip" role="status"
            style={{ left: `${(x(point.mean_score) / W) * 100}%`, top: `${(y(point.promoted) / H) * 100}%` }}>
            <strong>Scores {pct1(point.from)}–{pct1(point.to)}</strong>
            <span>Average score {pct1(point.mean_score)}</span>
            <span>Promoted {pct1(point.promoted)} <span className="muted">(95%: {pct1(point.promoted_low)}–{pct1(point.promoted_high)})</span></span>
            <span className="muted">{point.count.toLocaleString()} employees</span>
          </div>
        )}
      </div>
      <details className="details">
        <summary>Show the numbers as a table</summary>
        <div className="table-wrap" tabIndex={0}><table>
          <thead><tr><th>Score group</th><th>Employees</th><th>Average score</th><th>Actually promoted</th><th>95% interval</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.from}><td>{pct1(r.from)}–{pct1(r.to)}</td><td>{r.count.toLocaleString()}</td><td>{pct1(r.mean_score)}</td>
              <td className="strong">{pct1(r.promoted)}</td><td>{pct1(r.promoted_low)}–{pct1(r.promoted_high)}</td></tr>
          ))}</tbody>
        </table></div>
      </details>
    </div>
  );
}

function describe(r, i) {
  return `Group ${i + 1}: scores ${pct1(r.from)} to ${pct1(r.to)}, average ${pct1(r.mean_score)}; ${pct1(r.promoted)} promoted ` +
    `(95% interval ${pct1(r.promoted_low)} to ${pct1(r.promoted_high)}), ${r.count} employees`;
}
