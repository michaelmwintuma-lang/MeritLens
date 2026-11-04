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
import { Brain, CalendarRange, FileUp, Play, RotateCcw, UserPlus, Users } from "lucide-react";
import { Badge, Button, Callout, EmptyState, LoadError, PageHeader, PageLoading, Pager, SortHeader, sortRows } from "../../components/ui";
import Cover from "../../components/promotion/Cover";

// Long lists are shown a page at a time: drawing thousands of rows at once makes the page slow to use
const PAGE_SIZE = 50;

function time(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** During a review cycle: the scores below are the cycle's saved ones, and when nominations close. */
function CyclePanel({ cycle, total, isHr }) {
  const deadline = cycle.nominations_close
    ? cycle.nominations_open ? `Nominations close on ${cycle.nominations_close}.` : `Nominations closed on ${cycle.nominations_close}.`
    : "No nomination deadline.";
  return (
    <section className="card run-all" aria-labelledby="cycle-panel">
      <div className="run-all-head">
        <span className="run-all-icon"><CalendarRange size={22} aria-hidden="true" /></span>
        <div>
          <h2 id="cycle-panel">Review cycle: {cycle.name}</h2>
          <p className="muted" role="status">
            Scores for all {total} saved on {cycle.opened_at.slice(0, 10)} by model {cycle.model_version}. They change only
            when a record changes. {deadline} The model only advises.
          </p>
        </div>
        {isHr && <Link className="btn btn-secondary" to="/cycles">Cycle progress</Link>}
      </div>
    </section>
  );
}

/** The card above the list (no review cycle open): shows automatic scoring status, with quick action to re-calculate or start a cycle. */
function RunPanel({ run, start, total, scored, isHr, modelVersion, lastRunAt }) {
  if (run.status === "running") {
    const pct = Math.round(run.progress * 100);
    return (
      <section className="card run-all running" aria-busy="true">
        <div className="run-all-head">
          <span className="run-all-icon working"><Brain size={22} aria-hidden="true" /></span>
          <div>
            <h2>Re-scoring predictions…</h2>
            <p className="muted">Scoring employee {Math.min(Math.max(scored, 1), total)} of {total}</p>
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
          <h2>System-wide readiness predictions</h2>
          <p className="muted" role="status">
            All {total} employees are automatically scored by live model ({modelVersion ? `v${modelVersion}` : ""}) from their latest records.
            {lastRunAt ? ` Re-calculated at ${time(lastRunAt)}.` : " Scores are live and ready."}
          </p>
        </div>
        <div className="form-actions" style={{ margin: 0, gap: 8 }}>
          {isHr && (
            <Link to="/cycles" className="btn btn-primary">
              <CalendarRange size={16} aria-hidden="true" /> Start promotion round
            </Link>
          )}
          <Button onClick={start} icon={RotateCcw} look="secondary">
            Re-calculate all
          </Button>
        </div>
      </div>
      {run.status === "error" && <Callout tone="error" className="section-gap">{run.error}</Callout>}
    </section>
  );
}

export default function EmployeeList() {
  const { user } = useAuth();
  const isManager = user.role === "manager";
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [onlyRecommended, setOnlyRecommended] = useState(false);
  const [scope, setScope] = useState("all"); // a manager: everyone they see, or only their own team
  const [sort, setSort] = useState({ by: "score", dir: "desc" }); // highest readiness first, once there are scores
  const [page, setPage] = useState(0);
  // Any new search or filter starts again at the first page
  const filter = (setter) => (e) => { setter(e.target.type === "checkbox" ? e.target.checked : e.target.value); setPage(0); };

  const { data, error, reload: load } = useLoad(() => api("/promotion/employees"), []);
  const [run, start] = useRunAll(user.id);

  if (error) return <LoadError message={error} onRetry={load} />;
  if (!data) return <PageLoading />;

  // When a review cycle is open, scores are the cycle's snapshot; otherwise live predictions returned by server
  const cycle = data.cycle;
  const done = true;
  const people = run.result?.employees || data.employees;
  const place = new Map(data.employees.map((e, i) => [e.id, i]));
  const scores = new Map(people.map((e) => [e.id, e]));
  const scored = Math.floor(run.progress * data.employees.length);
  const threshold = cycle ? data.threshold : (run.result?.threshold ?? data.threshold);
  const modelVersion = cycle ? cycle.model_version : (run.result?.model_version ?? data.model_version);

  const departments = [...new Set(people.map((e) => e.department))].sort();
  const hasBranch = isManager && data.employees.some((e) => e.relation !== "direct");
  const relation = new Map(data.employees.map((e) => [e.id, e]));
  const rows = people
    .filter((e) => scope === "all" || relation.get(e.id)?.relation !== "branch")
    .filter((e) => e.full_name.toLowerCase().includes(search.toLowerCase()))
    .filter((e) => !department || e.department === department)
    .filter((e) => !onlyRecommended || e.recommended);
  const sorted = sortRows(rows, sort);
  const recommendedCount = people.filter((e) => e.recommended).length;
  const shown = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  /** The readiness cells of one row: its score and verdict. */
  function readiness(e) {
    const result = scores.get(e.id);
    if (result && result.score != null) {
      const fresh = run.status === "running" && place.get(e.id) < scored ? "just-scored" : "";
      return (
        <>
          <td className={`num strong ${fresh}`}>{percent(result.score)}</td>
          <td className={fresh}><ScoreBar score={result.score} threshold={threshold} compact /></td>
          <td className={fresh}><Verdict recommended={result.recommended} /></td>
        </>
      );
    }
    if (run.status === "running") {
      return <><td className="num"><span className="score-pending" /></td><td><span className="score-pending wide" /></td><td /></>;
    }
    return <><td className="num muted">Calculating…</td><td /><td /></>;
  }

  return (
    <>
      <PageHeader title={isManager ? "My team" : "All employees"}
        subtitle={done
          ? `${people.length} employees, ${recommendedCount} above the ${percent(threshold)} threshold`
          : `${data.employees.length} employees. Run the predictions to see each person's readiness.`}
        actions={user.role === "hr" && (
          <>
            <Link to="/employees/import" className="btn btn-secondary"><FileUp size={16} aria-hidden="true" />Import</Link>
            <Link to="/employees/new" className="btn btn-primary"><UserPlus size={16} aria-hidden="true" />Add employee</Link>
          </>
        )} />

      {user.role === "admin" && <Callout>You're viewing employee data as an administrator: read-only. Nominations, decisions and feedback stay with managers and HR.</Callout>}
      {cycle
        ? <CyclePanel cycle={cycle} total={data.employees.length} isHr={user.role === "hr"} />
        : <RunPanel run={run} start={start} total={data.employees.length} scored={scored}
            isHr={user.role === "hr"} modelVersion={modelVersion} lastRunAt={run.result?.run_at} />}
      <div className="card flush">
        <div className="card-head filters">
          <input placeholder="Search by name" value={search} onChange={filter(setSearch)} aria-label="Search by name" />
          {hasBranch && (
            <select value={scope} onChange={filter(setScope)} aria-label="Who to show">
              <option value="all">My team and everyone below</option>
              <option value="mine">Only people I can recommend</option>
            </select>
          )}
          {!isManager && (
            <select value={department} onChange={filter(setDepartment)} aria-label="Department">
              <option value="">All departments</option>
              {departments.map((d) => <option key={d}>{d}</option>)}
            </select>
          )}
          {/* Filtering by readiness only makes sense once there are scores */}
          {done && <label className="check"><input type="checkbox" checked={onlyRecommended} onChange={filter(setOnlyRecommended)} /> Recommended only</label>}
        </div>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={isManager ? "My team" : "All employees"}><table>
          <thead><tr>
            <SortHeader label="Name" by="full_name" sort={sort} onSort={(s) => { setSort(s); setPage(0); }} />
            <SortHeader label="Department" by="department" sort={sort} onSort={(s) => { setSort(s); setPage(0); }} />
            {done ? <SortHeader label="Readiness" by="score" sort={sort} onSort={(s) => { setSort(s); setPage(0); }} numeric /> : <th className="num">Readiness</th>}
            <th className="wide-col"><span className="visually-hidden">Readiness against the threshold</span></th>
            <th>Model's view</th>
          </tr></thead>
          <tbody>
            {shown.map((e) => (
              <tr key={e.id} className={run.status === "running" && place.get(e.id) === scored ? "row-scoring" : ""}>
                <td><Link to={`/employees/${e.id}`}>{e.full_name}</Link>
                  {relation.get(e.id)?.relation === "branch" && <div className="cell-sub">Reports to {relation.get(e.id).manager}</div>}
                  {relation.get(e.id)?.relation === "cover" && <div><Badge tone="info">Covering for {relation.get(e.id).manager}</Badge></div>}</td>
                <td>{e.department}</td>
                {readiness(e)}
              </tr>
            ))}
          </tbody>
        </table></div>
        {rows.length === 0 && <EmptyState icon={Users} title="No one matches" text="Try a different name or filter." />}
        <Pager page={page} size={PAGE_SIZE} total={rows.length} onPage={setPage} label="Pages of employees" />
      </div>
      {isManager && <Cover onChanged={load} />}
    </>
  );
}
