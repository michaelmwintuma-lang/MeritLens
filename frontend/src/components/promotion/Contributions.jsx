// What raised and what lowered the score, compared with an average employee. The bars are exact contributions;
// `numbers` shows their size in log-odds next to each bar (left out on the employee's own page, where the bars and
// the plain summary say it more simply). The full table is ExactNumbers, under "Show technical details".

function Row({ item, max, numbers }) {
  const width = `${(Math.abs(item.contribution) / max) * 100}%`;
  return (
    <li className="contribution">
      <div className="contribution-text">
        <span className="strong">{item.label}</span>
        <span className="muted small"> · {item.value_display}</span>
      </div>
      <div className="contribution-bar"><div className={item.contribution > 0 ? "bar-up" : "bar-down"} style={{ width }} /></div>
      {numbers && <div className="contribution-number small muted">{item.contribution > 0 ? "+" : "−"}{Math.abs(item.contribution).toFixed(2)}</div>}
    </li>
  );
}

export default function Contributions({ contributions, limit = 6, numbers = true }) {
  const max = Math.max(...contributions.map((c) => Math.abs(c.contribution)), 0.001);
  // Effects that round to zero are left out of the short lists (they're still in the full table below)
  const raising = contributions.filter((c) => c.contribution >= 0.005).slice(0, limit);
  const lowering = contributions.filter((c) => c.contribution <= -0.005).slice(0, limit);
  return (
    <>
      <div className="two-columns">
        <div>
          <h3>Raises readiness ▲</h3>
          {raising.length ? <ul className={`contributions ${numbers ? "" : "no-numbers"}`}>{raising.map((c) => <Row key={c.feature} item={c} max={max} numbers={numbers} />)}</ul>
            : <p className="muted">Nothing raises it above an average employee.</p>}
        </div>
        <div>
          <h3>Lowers readiness ▼</h3>
          {lowering.length ? <ul className={`contributions ${numbers ? "" : "no-numbers"}`}>{lowering.map((c) => <Row key={c.feature} item={c} max={max} numbers={numbers} />)}</ul>
            : <p className="muted">Nothing lowers it below an average employee.</p>}
        </div>
      </div>
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
