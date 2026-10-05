// What the model looks at overall, across all employees.
import { useEffect, useState } from "react";
import { api } from "../../api";
import { percent } from "../../format";
import { Brain } from "lucide-react";
import { PageHeader } from "../../components/ui";

export default function ModelOverview() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/promotion/importance").then((d) => setRows(d.features)).catch((err) => setError(err.message)); }, []);

  if (error) return <p className="alert alert-error">{error}</p>;
  if (!rows) return <p className="muted">Loading…</p>;
  const max = rows[0].share;

  return (
    <>
      <PageHeader icon={Brain} title="How the model works" subtitle="What the promotion model looks at, and what it never sees." />
      <div className="card">
        <h2>What it looks at overall</h2>
        <p className="muted">
          How much each factor moves readiness scores on average, across 2,000 employees. It shows what the model
          relies on in general; it says nothing about any one person.
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
          Gender, age, education, marital status and pay are never used by the model. Gender, age and education are
          used only to check, after training, that every group is recommended at a fair rate (the four-fifths rule).
        </p>
      </div>
    </>
  );
}
