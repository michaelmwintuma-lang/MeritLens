// Tips: the smallest realistic improvements that would reach the threshold (worked out by "Run prediction").
import { midSentence, percent } from "../../format";

export default function Tips({ data, threshold }) {
  if (data.already_recommended) return <p>Already above the threshold: nothing more is needed for the model to recommend promotion.</p>;
  if (!data.tips.length) return <p className="muted">No realistic single improvement moves the score. A conversation with the manager about development goals is the best next step.</p>;

  return (
    <>
      <ol className="tips">
        {data.tips.map((t) => (
          <li key={t.feature}>
            <strong>{t.to > t.from ? "Increase" : "Reduce"} {midSentence(t.label)}</strong> from {t.from_display} to {t.to_display}
          </li>
        ))}
      </ol>
      <p className={data.reaches_threshold ? "alert alert-success" : "alert alert-info"}>
        {data.reaches_threshold
          ? `Doing this would raise readiness from ${percent(data.current_score)} to ${percent(data.projected_score)}, above the ${percent(threshold)} threshold.`
          : `Doing this would raise readiness from ${percent(data.current_score)} to ${percent(data.projected_score)}: real progress, though not yet the ${percent(threshold)} threshold.`}
      </p>
      <p className="muted small">Each suggestion is at most one typical step (one standard deviation) and never beyond what the top 5% of employees achieve.</p>
    </>
  );
}
