// Review cycles: HR opens a cycle (everyone is scored once and the scores are saved), follows its progress, exports
// it and closes it once every nomination is decided. The compliance auditor follows the same pages read-only, with
// totals only. One cycle can be open at a time; the page opens on it, or on the latest cycle.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarRange, CheckCircle2, Download, Lock, Play, Printer, TrendingDown, TrendingUp, UserSearch } from "lucide-react";
import { api, apiBlob } from "../../api";
import { useAuth } from "../../auth";
import { useAction } from "../../useAction";
import { useLoad } from "../../useLoad";
import { percent } from "../../format";
import { Badge, Button, Callout, Card, EmptyState, LoadError, Loading, PageHeader, PageLoading, StatCard } from "../../components/ui";
import { StackedBar } from "../../components/charts/BarList";
import { useConfirm } from "../../components/Overlay";
import { useToast } from "../../components/Toast";
import { StatusTag } from "../governance/LiveFairness";

const inDays = (days) => new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);
const day = (iso) => (iso ? iso.slice(0, 10) : "–");
const signed = (change) => `${change >= 0 ? "+" : "−"}${Math.abs(Math.round(change * 100))} points`;

/** A sensible name for the next cycle: "2026 mid-year" in the first half of the year, "2026 year end" after. */
function suggestedName() {
  const now = new Date();
  return `${now.getFullYear()} ${now.getMonth() < 6 ? "mid-year" : "year end"}`;
}

function CycleStatus({ cycle }) {
  if (cycle.status === "closed") return <Badge icon={Lock}>Closed</Badge>;
  return cycle.nominations_open
    ? <Badge tone="success" icon={CheckCircle2}>Open for nominations</Badge>
    : <Badge tone="warning" icon={CalendarRange}>Nominations closed: deciding</Badge>;
}

/** HR, when no cycle is open: name it, set the nomination deadline, and start it. */
function StartCycle({ onStarted }) {
  const [form, setForm] = useState({ name: suggestedName(), nominations_close: inDays(21), note: "" });
  const [error, setError] = useState("");
  const [working, withWorking] = useAction();
  const toast = useToast();
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function start(e) {
    e.preventDefault();
    setError("");
    try {
      const report = await api("/promotion/cycles", { method: "POST", body: {
        name: form.name.trim(), nominations_close: form.nominations_close || null, note: form.note.trim() || null } });
      toast(`“${report.cycle.name}” is open: ${report.totals.people} people scored and saved. Managers have been emailed.`);
      onStarted(report.cycle.id);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card id="start" title="Start a review cycle" icon={Play}
      subtitle="The live model scores everyone once, and the scores are saved for the whole cycle. Managers nominate against them until the deadline; you decide; then you close the cycle.">
      {error && <Callout tone="error">{error}</Callout>}
      <form onSubmit={(e) => withWorking(() => start(e))}>
        <div className="form-row">
          <label className="field">Name<input value={form.name} onChange={set("name")} required minLength={3} maxLength={80} placeholder="e.g. 2026 mid-year" /></label>
          <label className="field">Nominations close
            <input type="date" value={form.nominations_close} onChange={set("nominations_close")} min={inDays(0)} max={inDays(365)} />
            <span className="field-hint">The last day managers can recommend someone. Leave empty for no deadline.</span>
          </label>
        </div>
        <label className="field"><span>Note for the record <span className="muted">(optional)</span></span>
          <textarea rows={2} value={form.note} onChange={set("note")} maxLength={2000} placeholder="e.g. Annual round, after the year-end reviews were entered." />
        </label>
        <ul className="steps-list muted">
          <li>Everyone's score, its inputs and the model version are saved, so what the model said can always be reproduced.</li>
          <li>During the cycle a score changes only when a record changes (your edit, or a correction you confirm), and that is logged.</li>
          <li>No new model can be released until the cycle is closed, so everyone in it is scored by the same model.</li>
        </ul>
        <div className="form-actions section-gap">
          <Button icon={Play} busy={working} busyText="Scoring everyone…">Start the cycle and score everyone</Button>
        </div>
      </form>
    </Card>
  );
}

function Movement({ movement }) {
  if (!movement.previous) return <p className="muted">This is the first cycle, so there is nothing to compare with yet.</p>;
  const people = (rows, Icon) => (rows?.length ? (
    <ul className="plain-list">
      {rows.map((r) => (
        <li key={r.employee_id} className="row spread">
          <span><Icon size={16} aria-hidden="true" className="icon-inline" /> <Link to={`/employees/${r.employee_id}`}>{r.full_name}</Link> <span className="muted">· {r.department}</span></span>
          <span className="num">{percent(r.before)} → <strong>{percent(r.now)}</strong> <span className="muted">({signed(r.change)})</span></span>
        </li>
      ))}
    </ul>
  ) : <p className="muted">Nobody.</p>);
  return (
    <>
      <div className="stat-grid compact">
        <StatCard label="Compared" value={movement.compared} note={`People in both cycles`} />
        <StatCard label="Now recommended" value={movement.crossed_up} note="Crossed the threshold upwards" />
        <StatCard label="No longer recommended" value={movement.crossed_down} note="Fell below the threshold" />
        <StatCard label="Average change" value={movement.average_change == null ? "–" : signed(movement.average_change)} note="Across everyone compared" />
      </div>
      {movement.risers && (
        <div className="two-columns">
          <div><h3>Rose the most</h3>{people(movement.risers, TrendingUp)}</div>
          <div><h3>Fell the most</h3>{people(movement.fallers, TrendingDown)}</div>
        </div>
      )}
    </>
  );
}

function CycleFairness({ cycleId }) {
  const { data, error, reload } = useLoad(() => api(`/governance/fairness?cycle_id=${cycleId}`), [cycleId]);
  if (error) return <LoadError message={error} onRetry={reload} />;
  if (!data) return <Loading label="Checking fairness for this cycle…" />;
  return (
    <>
      <p className="row"><StatusTag status={data.overall} /> <span className="muted">The four-fifths rule on this cycle's saved scores, and its nominations and decisions.</span></p>
      <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Fairness in this cycle"><table>
        <thead><tr><th>Characteristic</th>{data.checks[0]?.stages.map((s) => <th key={s.stage}>{s.stage}</th>)}</tr></thead>
        <tbody>{data.checks.map((c) => (
          <tr key={c.characteristic}><td>{c.label}</td>{c.stages.map((s) => <td key={s.stage}><StatusTag status={s.status} />
            {s.ratio != null && <div className="cell-sub">ratio {s.ratio.toFixed(2)}</div>}</td>)}</tr>
        ))}</tbody>
      </table></div>
      <p className="section-gap"><Link className="text-link" to="/fairness">How the check works, and today's live view</Link></p>
    </>
  );
}

/** One cycle's progress: totals, the nomination pipeline, departments, who isn't nominated, movement, fairness. */
function CycleReport({ id, isHr, onChanged }) {
  const { data, error, reload } = useLoad(() => api(`/promotion/cycles/${id}`), [id]);
  const [confirm, dialog] = useConfirm();
  const [closing, withClosing] = useAction();
  const [problem, setProblem] = useState("");
  const toast = useToast();
  if (error) return <LoadError message={error} onRetry={reload} />;
  if (!data) return <PageLoading />;
  const { cycle, totals } = data;
  const open = cycle.status === "open";

  async function exportCsv() {
    try {
      const url = URL.createObjectURL(await apiBlob(`/promotion/cycles/${id}/export.csv`));
      Object.assign(document.createElement("a"), { href: url, download: `review-cycle-${cycle.name}.csv` }).click();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (err) {
      setProblem(err.message);
    }
  }

  async function close() {
    if (!(await confirm({ title: `Close “${cycle.name}”?`, action: "Close the cycle",
      text: "The saved scores stay as they are, and scores go back to being worked out on demand. A new model can be released again, and you can open the next cycle." }))) return;
    setProblem("");
    try {
      await api(`/promotion/cycles/${id}/close`, { method: "POST" });
      toast(`“${cycle.name}” is closed.`);
      onChanged();
      reload();
    } catch (err) {
      setProblem(err.message);
    }
  }

  return (
    <>
      {dialog}
      <Card id="cycle" title={cycle.name} actions={<CycleStatus cycle={cycle} />}
        subtitle={`Opened ${day(cycle.opened_at)} by ${cycle.opened_by}${cycle.closed_at ? ` · closed ${day(cycle.closed_at)} by ${cycle.closed_by}` : ""} · model ${cycle.model_version}, threshold ${percent(cycle.threshold)}`}>
        {cycle.note && <p className="quote">{cycle.note}</p>}
        <p className="muted">
          {cycle.nominations_close
            ? open && cycle.nominations_open
              ? `Nominations close on ${cycle.nominations_close} (${cycle.days_left === 0 ? "today" : `${cycle.days_left} day${cycle.days_left === 1 ? "" : "s"} left`}).`
              : `Nominations closed on ${cycle.nominations_close}.`
            : "No nomination deadline."}
          {totals.rescored > 0 && ` ${totals.rescored} score${totals.rescored === 1 ? " was" : "s were"} updated after a record change.`}
          {totals.added_late > 0 && ` ${totals.added_late} ${totals.added_late === 1 ? "person was" : "people were"} added after the cycle opened.`}
        </p>
        {problem && <Callout tone="error">{problem}</Callout>}
        <div className="form-actions">
          {isHr && open && <Button icon={Lock} busy={closing} busyText="Closing…" disabled={!data.can_close} onClick={() => withClosing(close)}>Close the cycle</Button>}
          {isHr && <Button look="secondary" icon={Download} onClick={exportCsv}>Export CSV</Button>}
          <Link className="btn btn-secondary" to={`/cycles/${id}/report`}><Printer size={16} aria-hidden="true" />Printable report</Link>
        </div>
        {open && data.close_blocker && <Callout className="section-gap">{data.close_blocker} The cycle can be closed once they are decided.</Callout>}
        {isHr && totals.recommended_no_manager > 0 && (
          <Callout tone="warning" className="section-gap" title={`${totals.recommended_no_manager} ${totals.recommended_no_manager === 1 ? "person" : "people"} the model recommends ${totals.recommended_no_manager === 1 ? "has" : "have"} no manager`}>
            Nobody can recommend them until they have one. <Link to="/teams">Give them a manager</Link>
          </Callout>
        )}
      </Card>

      <div className="stat-grid">
        <StatCard label="People scored" value={totals.people} note="Scores saved for this cycle" />
        <StatCard label="Recommended" value={totals.recommended} note={totals.people ? `${percent(totals.recommended / totals.people)} of everyone` : "–"} />
        <StatCard label="Nominated" value={totals.nominated} note={`${totals.recommended_not_nominated} recommended, not nominated`} />
        <StatCard label="Decided" value={totals.approved + totals.rejected} note={`${totals.approved} approved · ${totals.against_model} against the model`} />
      </div>

      <Card title="Nominations" subtitle="Where every nomination in this cycle stands.">
        {totals.nominated === 0 ? <EmptyState compact icon={UserSearch} title="No nominations yet" text="Managers' recommendations in this cycle appear here." /> : (
          <StackedBar label="Nominations by stage" parts={[
            { key: "approved", label: "Approved", value: totals.approved, slot: 3 },
            { key: "rejected", label: "Not approved", value: totals.rejected, slot: 4 },
            { key: "waiting", label: "Waiting for HR", value: totals.waiting, slot: 1 },
            { key: "held", label: "On hold", value: totals.on_hold, slot: 2 },
          ]} />
        )}
      </Card>
      <Card title="By department">
        <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Cycle by department"><table>
          <thead><tr><th>Department</th><th className="num">People</th><th className="num">Recommended</th><th className="num">Nominated</th><th className="num">Approved</th></tr></thead>
          <tbody>{data.by_department.map((d) => (
            <tr key={d.department}><td>{d.department}</td><td className="num">{d.people}</td><td className="num">{d.recommended || 0}</td>
              <td className="num">{d.nominated || 0}</td><td className="num">{d.approved || 0}</td></tr>
          ))}</tbody>
        </table></div>
      </Card>

      {isHr && (
        <Card flush title="Recommended, not nominated" subtitle="The model recommends them, but no manager has recommended them in this cycle. The model only advises: this is a prompt to check, not a to-do list.">
          {data.not_nominated.length === 0 ? <EmptyState compact icon={CheckCircle2} title="Nobody" text="Everyone the model recommends has been nominated." /> : (
            <div className="table-wrap" tabIndex={0} role="region" aria-label="Recommended, not nominated"><table>
              <thead><tr><th>Name</th><th>Department</th><th>Manager</th><th className="num">Readiness</th></tr></thead>
              <tbody>{data.not_nominated.map((r) => (
                <tr key={r.employee_id}><td><Link to={`/employees/${r.employee_id}`}>{r.full_name}</Link></td><td>{r.department}</td>
                  <td>{r.manager || <span className="muted">No manager</span>}</td><td className="num strong">{percent(r.score)}</td></tr>
              ))}</tbody>
            </table></div>
          )}
        </Card>
      )}

      <Card title={data.movement.previous ? `Since “${data.movement.previous.name}”` : "Since the last cycle"}
        subtitle="How saved scores moved between cycles, for the people in both.">
        <Movement movement={data.movement} />
      </Card>

      <Card title="Fairness in this cycle">
        <CycleFairness cycleId={id} />
      </Card>
    </>
  );
}

export default function ReviewCycles() {
  const { user } = useAuth();
  const isHr = user.role === "hr";
  const { data: rows, error, reload } = useLoad(() => api("/promotion/cycles"), []);
  const [chosen, setChosen] = useState(null);
  const openOne = rows?.find((r) => r.status === "open");
  useEffect(() => { if (rows && chosen == null && rows.length) setChosen((openOne || rows[0]).id); }, [rows]); // eslint-disable-line react-hooks/exhaustive-deps

  const header = <PageHeader title="Review cycles"
    subtitle={isHr ? "Score everyone once, keep the scores, and run a promotion round against them." : "Each promotion round's saved scores, progress and fairness. Read-only: totals only."} />;
  if (error) return <>{header}<LoadError message={error} onRetry={reload} /></>;
  if (!rows) return <>{header}<PageLoading /></>;
  return (
    <>
      {header}
      {isHr && !openOne && <StartCycle onStarted={(id) => { setChosen(id); reload(); }} />}
      {!isHr && rows.length === 0 && <Card><EmptyState icon={CalendarRange} title="No review cycles yet" text="When HR starts one, its progress and fairness appear here." /></Card>}
      {chosen != null && <CycleReport key={chosen} id={chosen} isHr={isHr} onChanged={reload} />}
      {rows.length > 0 && (
        <Card flush title="All cycles" subtitle="Newest first.">
          <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="All review cycles"><table>
            <thead><tr><th>Cycle</th><th>Status</th><th>Opened</th><th className="num">People</th><th className="num">Recommended</th><th className="num">Nominated</th><th className="num">Approved</th><th><span className="visually-hidden">Open</span></th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} className={r.id === chosen ? "row-open" : ""}>
                <td className="strong">{r.name}</td><td><CycleStatus cycle={r} /></td><td className="num">{day(r.opened_at)}</td>
                <td className="num">{r.people}</td><td className="num">{r.recommended}</td><td className="num">{r.nominated}</td><td className="num">{r.approved}</td>
                <td><div className="actions"><button type="button" className="btn btn-secondary btn-sm" aria-pressed={r.id === chosen}
                  onClick={() => setChosen(r.id)}>{r.id === chosen ? "Shown" : "Show"}<span className="visually-hidden"> {r.name}</span></button></div></td>
              </tr>
            ))}</tbody>
          </table></div>
        </Card>
      )}
    </>
  );
}
