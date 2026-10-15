// Readiness on a 0-100% bar, with the threshold marked (dashed) so the score is always read against it. Above the
// threshold the bar is the "raises" blue; below it, a quiet slate: "not yet" is neutral, never an alarm.
import { percent } from "../../format";

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

/** "Recommended" or "Not yet recommended", always in words. The model's view, so a data tag, not a status. */
export function Verdict({ recommended }) {
  return recommended
    ? <span className="tag tag-up">▲ Recommended by the model</span>
    : <span className="tag">Not yet recommended</span>;
}
