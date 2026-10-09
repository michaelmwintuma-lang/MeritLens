// What the model looks at overall, across all employees.
import { api } from "../../api";
import { useLoad } from "../../useLoad";
import { percent } from "../../format";
import { Brain } from "lucide-react";
import { LoadError, Loading, PageHeader } from "../../components/ui";

export default function ModelOverview() {
  const { data: data, error, reload: load } = useLoad(() => api("/promotion/importance"), []);

  if (error) return <><PageHeader icon={Brain} title="How the model works" /><LoadError message={error} onRetry={load} /></>;
  if (!data) return <Loading />;
  const rows = data.features;
  const max = rows[0].share;

  return (
    <>
      <PageHeader icon={Brain} title="How the model works" subtitle="What the promotion model looks at, and what it never sees." />
      <div className="card">
        <h2>What it looks at overall</h2>
        <p className="muted">
          How much each factor moves readiness scores on average, across {data.sample_size.toLocaleString()} employees
          from the training data. It shows what the model relies on in general; it says nothing about any one person.
        </p>
        <ul className="importance">
          {rows.map((r) => (
            <li key={r.feature}>
              <span className="importance-name">{r.label}</span>
              <span className="importance-bar"><span style={{ width: `${(r.share / max) * 100}%` }} /></span>
              <span className="importance-value strong">{percent(r.share)}</span>
              <span className="muted small importance-direction">{r.direction}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="card">
        <h2>What it never looks at</h2>
        <p>
          Gender, age and education are used only to check, after training, that every group is recommended at a fair
          rate (the four-fifths rule). Nothing below is ever given to the model:
        </p>
        <div className="table-wrap" tabIndex={0}><table>
          <thead><tr><th>Information</th><th>Why it's left out</th></tr></thead>
          <tbody>{data.never_used.map((n) => <tr key={n.name}><td className="nowrap">{n.name}</td><td>{n.reason}</td></tr>)}</tbody>
        </table></div>
      </div>
    </>
  );
}
