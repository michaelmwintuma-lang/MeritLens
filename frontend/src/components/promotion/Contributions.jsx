// The exact contributions (SHAP): what raised and what lowered the score, compared with an average employee.

function Row({ item, max }) {
  const width = `${(Math.abs(item.contribution) / max) * 100}%`;
  return (
    <li className="contribution">
      <div className="contribution-text">
        <span className="strong">{item.label}</span>
        <span className="muted small"> · {item.value_display}</span>
      </div>
      <div className="contribution-bar"><div className={item.contribution > 0 ? "bar-up" : "bar-down"} style={{ width }} /></div>
      <div className="contribution-number small muted">{item.contribution > 0 ? "+" : "−"}{Math.abs(item.contribution).toFixed(2)}</div>
    </li>
  );
}

export default function Contributions({ contributions, limit = 6 }) {
  const max = Math.max(...contributions.map((c) => Math.abs(c.contribution)), 0.001);
  // Effects that round to zero are left out of the short lists (they're still in the full table below)
  const raising = contributions.filter((c) => c.contribution >= 0.005).slice(0, limit);
  const lowering = contributions.filter((c) => c.contribution <= -0.005).slice(0, limit);
  return (
    <>
      <div className="two-columns">
        <div>
          <h3>Raises readiness ▲</h3>
          {raising.length ? <ul className="contributions">{raising.map((c) => <Row key={c.feature} item={c} max={max} />)}</ul>
            : <p className="muted">Nothing raises it above an average employee.</p>}
        </div>
        <div>
          <h3>Lowers readiness ▼</h3>
          {lowering.length ? <ul className="contributions">{lowering.map((c) => <Row key={c.feature} item={c} max={max} />)}</ul>
            : <p className="muted">Nothing lowers it below an average employee.</p>}
        </div>
      </div>
      <details className="details">
        <summary>All {contributions.length} factors with exact numbers</summary>
        <p className="muted small">
          Each number is the factor's contribution in log-odds: weight × (this employee's value − the average value).
          Added to the average employee's starting point, they give exactly the model's score.
        </p>
        <table>
          <thead><tr><th>Factor</th><th>Value</th><th>Contribution</th><th>Effect</th></tr></thead>
          <tbody>
            {contributions.map((c) => (
              <tr key={c.feature}><td>{c.label}</td><td>{c.value_display}</td><td className="mono">{c.contribution.toFixed(4)}</td><td>{c.effect}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  );
}
