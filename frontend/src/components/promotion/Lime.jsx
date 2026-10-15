// LIME: a second, independent explanation, with how well it fits.
import { Callout } from "../ui";

export default function Lime({ lime, contributions }) {
  if (!lime) return null;
  const topFive = new Set(contributions.slice(0, 5).map((c) => c.label));
  return (
    <>
      <p className="muted">
        LIME tries thousands of slightly different versions of this record, fits a small simple model to the
        answers, and reads rules from it. Rules that name the same factors as above support the explanation.
      </p>
      <ul className="rules">
        {lime.rules.map((r) => (
          <li key={r.rule}>
            <span>{r.rule}</span>
            <span className={r.effect === "raises" ? "effect-raises" : "effect-lowers"}>{r.effect === "raises" ? "▲ raises" : "▼ lowers"}{[...topFive].some((label) => r.rule.includes(label)) && " · also in the top 5 above"}</span>
          </li>
        ))}
      </ul>
      <p>Fit (R²): <strong>{lime.fit_r2.toFixed(2)}</strong> <span className="muted">(1.0 = LIME copies the model perfectly here)</span></p>
      {lime.note && <Callout>{lime.note}</Callout>}
    </>
  );
}
