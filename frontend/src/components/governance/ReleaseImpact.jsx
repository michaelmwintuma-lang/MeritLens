// Before a release: both this version and the live model score today's employees, so the HR person can see what
// would change: how many each recommends, who would gain or lose a recommendation, and per department.
import { api } from "../../api";
import { useLoad } from "../../useLoad";
import { percent } from "../../format";
import { Callout, LoadError, Loading } from "../ui";

function People({ title, people }) {
  if (people.length === 0) return null;
  return (
    <details className="details">
      <summary>{title} ({people.length})</summary>
      <ul className="plain-list">{people.map((p) => (
        <li key={p.employee_id}>{p.full_name} <span className="muted">({p.department}): {percent(p.live_score)} → {percent(p.new_score)}</span></li>
      ))}</ul>
    </details>
  );
}

export default function ReleaseImpact({ version }) {
  const { data, error, reload } = useLoad(() => api(`/governance/models/${version}/compare`), [version]);
  if (error) return <LoadError message={error} onRetry={reload} />;
  if (!data) return <Loading label="Scoring today's employees with both models…" />;
  const unchanged = data.gained.length === 0 && data.lost.length === 0;

  return (
    <section className="section-gap" aria-labelledby="impact-title">
      <h3 id="impact-title">What would change for today's {data.employees} employees</h3>
      <dl className="rec-facts">
        <div><dt>Recommended now ({data.live_version})</dt><dd className="num">{data.live_recommends}</dd></div>
        <div><dt>Recommended by {data.version}</dt><dd className="num">{data.new_recommends}</dd></div>
        <div><dt>Average score move</dt><dd className="num">{(data.average_change * 100).toFixed(1)} points</dd></div>
      </dl>
      {unchanged
        ? <Callout tone="success">Nobody would gain or lose a recommendation.</Callout>
        : <Callout tone="warning" title={`${data.gained.length + data.lost.length} people would move across the threshold`}>
            Check these before releasing: their managers and they themselves will see a different recommendation.
          </Callout>}
      <People title="Would gain a recommendation" people={data.gained} />
      <People title="Would lose a recommendation" people={data.lost} />
      <details className="details">
        <summary>Per department</summary>
        <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Recommendations per department"><table>
          <thead><tr><th>Department</th><th className="num">Employees</th><th className="num">Recommended now</th><th className="num">With this version</th></tr></thead>
          <tbody>{data.by_department.map((d) => (
            <tr key={d.department}><td>{d.department}</td><td className="num">{d.employees}</td>
              <td className="num">{d.live_recommends}</td><td className="num">{d.new_recommends}</td></tr>
          ))}</tbody>
        </table></div>
      </details>
    </section>
  );
}
