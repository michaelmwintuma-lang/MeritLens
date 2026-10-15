// Tips: the smallest realistic improvements that would reach the threshold (worked out by "Run prediction"), as a
// checklist of steps.
import { CircleCheck } from "lucide-react";
import { midSentence, percent } from "../../format";
import { Callout } from "../ui";

export default function Tips({ data, threshold }) {
  if (data.already_recommended) return <p>Already above the threshold: nothing more is needed for the model to recommend promotion.</p>;
  if (!data.tips.length) return <p className="muted">No realistic single improvement moves the score. A conversation with the manager about development goals is the best next step.</p>;

  return (
    <>
      <ul className="checklist">
        {data.tips.map((t) => (
          <li key={t.feature}>
            <CircleCheck size={18} aria-hidden="true" />
            <span><strong>{t.to > t.from ? "Increase" : "Reduce"} {midSentence(t.label)}</strong> from {t.from_display} to {t.to_display}</span>
          </li>
        ))}
      </ul>
      <Callout tone={data.reaches_threshold ? "success" : "info"}>
        {data.reaches_threshold
          ? `Doing this would raise readiness from ${percent(data.current_score)} to ${percent(data.projected_score)}, above the ${percent(threshold)} threshold.`
          : `Doing this would raise readiness from ${percent(data.current_score)} to ${percent(data.projected_score)}: real progress, though not yet the ${percent(threshold)} threshold.`}
      </Callout>
      <p className="muted">Each suggestion is at most one typical step (one standard deviation) and never beyond what the top 5% of employees achieve.</p>
    </>
  );
}
