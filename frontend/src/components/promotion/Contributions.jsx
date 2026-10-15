// What raised and what lowered the score, compared with an average employee: one chart, biggest effect first, with
// bars growing right from the centre line (raises, blue) or left (lowers, orange). Each row also says "raises" or
// "lowers" in words, so colour is never the only signal. `numbers` adds each effect's size in log-odds (left out on
// the employee's own page, where the bars and the plain summary say it more simply). The full table is ExactNumbers,
// under "Show technical details".

function Row({ item, max, numbers }) {
  const raises = item.contribution > 0;
  const width = `${(Math.abs(item.contribution) / max) * 50}%`; // half the track each way
  return (
    <li className="contribution">
      <div className="contribution-text">
        <span className="strong">{item.label}</span>
        <span className="muted small"> · {item.value_display}</span>
        <div className={`effect-word ${raises ? "raises" : "lowers"}`}>{raises ? "▲ raises" : "▼ lowers"}</div>
      </div>
      <div className="diverging" aria-hidden="true"><div className={raises ? "bar-up" : "bar-down"} style={{ width }} /></div>
      {numbers && <div className="contribution-number small muted">{raises ? "+" : "−"}{Math.abs(item.contribution).toFixed(2)}</div>}
    </li>
  );
}

export default function Contributions({ contributions, limit = 8, numbers = true }) {
  // Effects that round to zero are left out of the chart (they're still in the full table)
  const shown = contributions.filter((c) => Math.abs(c.contribution) >= 0.005).slice(0, limit);
  const max = Math.max(...shown.map((c) => Math.abs(c.contribution)), 0.001);
  if (!shown.length) return <p className="muted">Every factor is close to an average employee's.</p>;
  return (
    <>
      <div className={`factor-legend contribution ${numbers ? "" : "no-numbers"}`} aria-hidden="true">
        <span />
        <span className="row spread"><span className="lowers">◀ lowers</span><span className="raises">raises ▶</span></span>
        {numbers && <span />}
      </div>
      <ul className={`contributions ${numbers ? "" : "no-numbers"}`}
        aria-label={`The ${shown.length} factors with the biggest effect, biggest first`}>
        {shown.map((c) => <Row key={c.feature} item={c} max={max} numbers={numbers} />)}
      </ul>
    </>
  );
}

/** Every factor's exact contribution, for "Show technical details". */
export function ExactNumbers({ contributions }) {
  return (
    <>
      <h3>All {contributions.length} factors with exact numbers</h3>
      <p className="muted small">
        Each number is the factor's contribution in log-odds: how far this employee's value moves the score compared
        with an average employee, read from the model's own curve for that factor. Added to the average employee's
        starting point, they give exactly the model's score.
      </p>
      <div className="table-wrap" tabIndex={0}><table>
        <thead><tr><th>Factor</th><th>Value</th><th>Contribution</th><th>Effect</th></tr></thead>
        <tbody>
          {contributions.map((c) => (
            <tr key={c.feature}><td>{c.label}</td><td>{c.value_display}</td><td className="mono">{c.contribution.toFixed(4)}</td><td>{c.effect}</td></tr>
          ))}
        </tbody>
      </table></div>
    </>
  );
}
