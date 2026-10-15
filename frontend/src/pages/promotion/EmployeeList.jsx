// A manager's team, or every employee for HR. "Run predictions for everyone" scores the whole list with the live
// model; the page then shows each person's readiness. Click a name to see why.
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { useLoad } from "../../useLoad";
import { useAuth } from "../../auth";
import { percent } from "../../format";
import ScoreBar, { Verdict } from "../../components/promotion/ScoreBar";
import { useRunAll } from "../../components/promotion/useRunAll";
import { Brain, FileUp, Play, RotateCcw, UserPlus, Users } from "lucide-react";
import { Button, EmptyState, LoadError, Loading, PageHeader } from "../../components/ui";

// Long lists are shown a page at a time: drawing thousands of rows at once makes the page slow to use
const PAGE_SIZE = 50;

function time(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** The card above the list: the button, the run in progress, or what the last run did. */
function RunPanel({ run, start, total, scored }) {
  if (run.status === "running") {
    const pct = Math.round(run.progress * 100);
    return (
      <section className="card run-all running" aria-busy="true">
        <div className="run-all-head">
          <span className="run-all-icon working"><Brain size={22} aria-hidden="true" /></span>
          <div>
            <h2>Running predictions…</h2>
            <p className="muted small">Scoring employee {Math.min(Math.max(scored, 1), total)} of {total}</p>
          </div>
          <strong className="run-all-pct">{pct}%</strong>
        </div>
        <div className="run-all-track" role="progressbar" aria-label="Predictions run" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
          <span style={{ width: `${pct}%` }} />
        </div>
      </section>
    );
  }
  return (
    <section className="card run-all">
      <div className="run-all-head">
        <span className="run-all-icon"><Brain size={22} aria-hidden="true" /></span>
        <div>
          {run.status === "done" ? (
            <>
              <h2>Predictions for {run.result.employees.length} employees</h2>
              <p className="muted small" role="status">
                Worked out at {time(run.result.run_at)} by the live model (version {run.result.model_version}) from
                each current record. Nothing is saved, and the model only advises.
              </p>
            </>
          ) : (
            <>
              <h2>Run the readiness predictions</h2>
              <p className="muted small">The live model scores all {total} employees from their current records. Nothing is saved.</p>
            </>
          )}
        </div>
        <Button onClick={start} icon={run.status === "done" ? RotateCcw : Play} look={run.status === "done" ? "plain" : undefined}>
          {run.status === "done" ? "Run again" : `Run predictions for all ${total}`}
        </Button>
      </div>
      {run.status === "error" && <p className="alert alert-error" role="alert" style={{ marginTop: 14 }}>{run.error}</p>}
    </section>
  );
}

export default function EmployeeList() {
  const { user } = useAuth();
  const isManager = user.role === "manager";
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [onlyRecommended, setOnlyRecommended] = useState(false);
  const [sortBy, setSortBy] = useState("score");
  const [page, setPage] = useState(0);
  // Any new search or filter starts again at the first page
  const filter = (setter) => (e) => { setter(e.target.type === "checkbox" ? e.target.checked : e.target.value); setPage(0); };

  const { data, error, reload: load } = useLoad(() => api("/promotion/employees"), []);
  const [run, start] = useRunAll(user.id);

  if (error) return <LoadError message={error} onRetry={load} />;
  if (!data) return <Loading />;

  const done = run.status === "done";
  // The run works down the list in name order (the order the server sends); each row's place in it
  const people = done ? run.result.employees : data.employees;
  const place = new Map(data.employees.map((e, i) => [e.id, i]));
  const scores = new Map((run.result?.employees || []).map((e) => [e.id, e]));
  const scored = Math.floor(run.progress * data.employees.length);
  const threshold = run.result?.threshold ?? data.threshold;

  const departments = [...new Set(people.map((e) => e.department))].sort();
  const rows = people
    .filter((e) => e.full_name.toLowerCase().includes(search.toLowerCase()))
    .filter((e) => !department || e.department === department)
    .filter((e) => !done || !onlyRecommended || e.recommended)
    .sort((a, b) => (done && sortBy === "score" ? b.score - a.score : a.full_name.localeCompare(b.full_name)));
  const recommendedCount = done ? people.filter((e) => e.recommended).length : null;
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const shown = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  /** The readiness cells of one row: its score once the run has reached it, otherwise a placeholder. */
  function readiness(e) {
    const reached = done || (run.status === "running" && place.get(e.id) < scored);
    const result = scores.get(e.id);
    if (reached && result) {
      const fresh = done ? "" : "just-scored";
      return (
        <>
          <td className={`strong ${fresh}`}>{percent(result.score)}</td>
          <td className={fresh}><ScoreBar score={result.score} threshold={threshold} compact /></td>
          <td className={fresh}><Verdict recommended={result.recommended} /></td>
        </>
      );
    }
    if (run.status === "running") {
      return <><td><span className="score-pending" /></td><td><span className="score-pending wide" /></td><td /></>;
    }
    return <><td className="muted small nowrap">Not run yet</td><td /><td /></>;
  }

  return (
    <>
      <PageHeader icon={Users} title={isManager ? "My team" : "All employees"}
        subtitle={done
          ? `${people.length} employees, ${recommendedCount} above the ${percent(threshold)} threshold`
          : `${data.employees.length} employees. Run the predictions to see each person's readiness.`}
        actions={user.role === "hr" && (
          <>
            <Link to="/employees/import" className="btn btn-plain"><FileUp size={16} aria-hidden="true" />Import</Link>
            <Link to="/employees/new" className="btn btn-primary"><UserPlus size={16} aria-hidden="true" />Add employee</Link>
          </>
        )} />

      {user.role === "admin" && <p className="alert alert-info">You're viewing employee data as an administrator: read-only. Nominations, decisions and feedback stay with managers and HR.</p>}
      <RunPanel run={run} start={start} total={data.employees.length} scored={scored} />
      <div className="card flush">
        <div className="card-head filters">
          <input placeholder="Search by name" value={search} onChange={filter(setSearch)} aria-label="Search by name" />
          {!isManager && (
            <select value={department} onChange={filter(setDepartment)} aria-label="Department">
              <option value="">All departments</option>
              {departments.map((d) => <option key={d}>{d}</option>)}
            </select>
          )}
          {/* Sorting and filtering by readiness only make sense once there are scores */}
          {done && (
            <>
              <select value={sortBy} onChange={filter(setSortBy)} aria-label="Sort">
                <option value="score">Highest readiness first</option>
                <option value="name">By name</option>
              </select>
              <label className="check"><input type="checkbox" checked={onlyRecommended} onChange={filter(setOnlyRecommended)} /> Recommended only</label>
            </>
          )}
        </div>
        <div className="table-wrap" tabIndex={0}><table>
          <thead><tr><th>Name</th><th>Department</th><th>Readiness</th><th style={{ width: "30%" }} /><th>Model's view</th></tr></thead>
          <tbody>
            {shown.map((e) => (
              <tr key={e.id} className={run.status === "running" && place.get(e.id) === scored ? "row-scoring" : ""}>
                <td><Link to={`/employees/${e.id}`}>{e.full_name}</Link></td>
                <td>{e.department}</td>
                {readiness(e)}
              </tr>
            ))}
          </tbody>
        </table></div>
        {rows.length === 0 && <EmptyState icon={Users} title="No one matches" text="Try a different name or filter." />}
        {rows.length > PAGE_SIZE && (
          <nav className="pager" aria-label="Pages of employees">
            <button type="button" className="btn btn-plain" onClick={() => setPage(page - 1)} disabled={page === 0}>Previous</button>
            <span className="muted small" aria-live="polite">
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, rows.length)} of {rows.length}
            </span>
            <button type="button" className="btn btn-plain" onClick={() => setPage(page + 1)} disabled={page >= pages - 1}>Next</button>
          </nav>
        )}
      </div>
    </>
  );
}
