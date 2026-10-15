// What raised and what lowered the score, compared with an average employee, side by side: the factors that raised
// it on one side (teal), those that lowered it on the other (orange), biggest first, every bar on the same scale.
// Each side is headed in words, so colour is never the only signal. `numbers` adds each effect's size in log-odds
// (left out on the employee's own page, where the bars and the plain summary say it more simply). The full table is
// ExactNumbers, under "Show technical details".
import { TrendingDown, TrendingUp } from "lucide-react";

function Side({ kind, items, max, numbers }) {
  const raises = kind === "raises";
  const Icon = raises ? TrendingUp : TrendingDown;
  return (
    <div className={`factor-side ${kind}`}>
      <h3><Icon size={18} aria-hidden="true" />{raises ? "Raised the score" : "Lowered the score"}</h3>
      {items.length === 0 ? <p className="empty-side">{raises ? "Nothing raised it noticeably." : "Nothing lowered it noticeably."}</p> : (
        <ul className="contributions" aria-label={raises ? "Factors that raised the score, biggest first" : "Factors that lowered the score, biggest first"}>
          {items.map((c) => (
            <li key={c.feature} className="contribution">
              <span className="contribution-text">
                <span><span className="strong">{c.label}</span> <span className="muted">· {c.value_display}</span></span>
                {numbers && <span className="contribution-number">{raises ? "+" : "−"}{Math.abs(c.contribution).toFixed(2)}</span>}
              </span>
              <span className="contribution-bar" aria-hidden="true"><span style={{ width: `${(Math.abs(c.contribution) / max) * 100}%` }} /></span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Contributions({ contributions, limit = 5, numbers = true }) {
  // Effects that round to zero are left out of the chart (they're still in the full table)
  const visible = contributions.filter((c) => Math.abs(c.contribution) >= 0.005);
  const raised = visible.filter((c) => c.contribution > 0).slice(0, limit);
  const lowered = visible.filter((c) => c.contribution < 0).slice(0, limit);
  const max = Math.max(...[...raised, ...lowered].map((c) => Math.abs(c.contribution)), 0.001);
  if (!visible.length) return <p className="muted">Every factor is close to an average employee's.</p>;
  return (
    <div className="factor-sides">
      <Side kind="raises" items={raised} max={max} numbers={numbers} />
      <Side kind="lowers" items={lowered} max={max} numbers={numbers} />
    </div>
  );
}

/** Every factor's exact contribution, for "Show technical details". */
export function ExactNumbers({ contributions }) {
  return (
    <>
      <h3>All {contributions.length} factors with exact numbers</h3>
      <p className="muted">
        Each number is the factor's contribution in log-odds: how far this employee's value moves the score compared
        with an average employee, read from the model's own curve for that factor. Added to the average employee's
        starting point, they give exactly the model's score.
      </p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label="All factors with exact numbers"><table>
        <thead><tr><th>Factor</th><th className="num">Value</th><th className="num">Contribution</th><th>Effect</th></tr></thead>
        <tbody>
          {contributions.map((c) => (
            <tr key={c.feature}><td>{c.label}</td><td className="num">{c.value_display}</td><td className="num mono">{c.contribution.toFixed(4)}</td><td>{c.effect}</td></tr>
          ))}
        </tbody>
      </table></div>
    </>
  );
}
