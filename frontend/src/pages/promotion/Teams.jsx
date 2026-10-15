// HR: teams and reporting lines. Everyone without a manager first (nobody can recommend them until they have one),
// then every manager in reporting-line order with their team, who they report to and any cover; and cover while a
// manager is away. A reporting line can never loop back on itself (the server refuses it).
import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRightLeft, CheckCircle2, Network, UserMinus, Users } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { useLoad } from "../../useLoad";
import { Badge, Button, Callout, Card, EmptyState, LoadError, PageHeader, PageLoading, Pager, StatCard } from "../../components/ui";
import { Drawer } from "../../components/Overlay";
import { useToast } from "../../components/Toast";
import Cover from "../../components/promotion/Cover";

const PAGE_SIZE = 25;

/** Choose a manager and move the ticked people to them (or to nobody). */
function MoveBar({ managers, count, onMove, allowNone = false, label = "Assign" }) {
  const [to, setTo] = useState("");
  const [working, withWorking] = useAction();
  return (
    <div className="inline-form">
      <label className="field">Manager
        <select value={to} onChange={(e) => setTo(e.target.value)}>
          <option value="">Choose a manager</option>
          {allowNone && <option value="none">No manager</option>}
          {managers.map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name}</option>)}
        </select>
      </label>
      <Button icon={ArrowRightLeft} busy={working} busyText="Saving…" disabled={!count || !to}
        onClick={() => withWorking(() => onMove(to === "none" ? null : Number(to)))}>
        {label} {count || ""} {count === 1 ? "person" : "people"}
      </Button>
    </div>
  );
}

/** A table of people with a tick box each, and "tick everyone on this page". */
function PickTable({ people, picked, setPicked, label }) {
  const [page, setPage] = useState(0);
  const shown = people.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const allShown = shown.length > 0 && shown.every((p) => picked.has(p.id));
  const toggle = (id) => { const next = new Set(picked); next.has(id) ? next.delete(id) : next.add(id); setPicked(next); };
  const toggleAll = () => { const next = new Set(picked); shown.forEach((p) => (allShown ? next.delete(p.id) : next.add(p.id))); setPicked(next); };
  return (
    <>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={label}><table>
        <thead><tr>
          <th><input type="checkbox" checked={allShown} onChange={toggleAll} aria-label="Tick everyone on this page" /></th>
          <th>Name</th><th>Department</th><th className="num">Number</th>
        </tr></thead>
        <tbody>{shown.map((p) => (
          <tr key={p.id}>
            <td><input type="checkbox" checked={picked.has(p.id)} onChange={() => toggle(p.id)} aria-label={`Tick ${p.full_name}`} /></td>
            <td><Link to={`/employees/${p.id}`}>{p.full_name}</Link></td><td>{p.department}</td><td className="num muted">{p.id}</td>
          </tr>
        ))}</tbody>
      </table></div>
      <Pager page={page} size={PAGE_SIZE} total={people.length} onPage={setPage} label={`Pages of ${label}`} />
    </>
  );
}

export default function Teams() {
  const { data, error, reload } = useLoad(() => api("/promotion/teams"), []);
  const [picked, setPicked] = useState(new Set());
  const [department, setDepartment] = useState("");
  const [open, setOpen] = useState(null);        // the manager whose team is open in the drawer
  const [teamPicked, setTeamPicked] = useState(new Set());
  const [problem, setProblem] = useState("");
  const toast = useToast();

  const header = <PageHeader title="Teams" subtitle="Who manages whom. Every employee needs a manager to be recommended for promotion; managers see their own team, and read-only everyone further down their reporting line." />;
  if (error) return <>{header}<LoadError message={error} onRetry={reload} /></>;
  if (!data) return <>{header}<PageLoading /></>;

  const managers = data.managers.map((m) => ({ user_id: m.user_id, full_name: m.full_name }));
  const departments = [...new Set(data.unassigned.map((p) => p.department))].sort();
  const unassigned = data.unassigned.filter((p) => !department || p.department === department);
  const openManager = data.managers.find((m) => m.user_id === open);

  async function move(ids, managerId, done) {
    setProblem("");
    try {
      const res = await api("/promotion/teams/assign", { method: "PUT", body: { employee_ids: [...ids], manager_user_id: managerId } });
      const name = managerId == null ? "no manager" : managers.find((m) => m.user_id === managerId)?.full_name;
      toast(`${res.moved} ${res.moved === 1 ? "person" : "people"} moved to ${name}.`);
      done();
      reload();
    } catch (err) {
      setProblem(err.message);
    }
  }

  return (
    <>
      {header}
      {problem && <Callout tone="error">{problem}</Callout>}
      <div className="stat-grid">
        <StatCard label="Managers" value={data.managers.length} note="Active manager accounts" />
        <StatCard label="With a manager" value={data.employees - data.unassigned.length} note={`of ${data.employees} employees`} />
        <StatCard label="Without a manager" value={data.unassigned.length} note="Nobody can recommend them yet" />
      </div>

      <Card flush id="unassigned" title={`Without a manager (${data.unassigned.length})`}
        subtitle="Tick people, choose their manager, and assign them. The manager is emailed the names of the people who join."
        actions={departments.length > 1 && (
          <label className="field filter-field"><span className="visually-hidden">Department</span>
            <select value={department} onChange={(e) => setDepartment(e.target.value)} aria-label="Department">
              <option value="">All departments</option>
              {departments.map((d) => <option key={d}>{d}</option>)}
            </select></label>)}>
        {data.unassigned.length === 0 ? <EmptyState icon={CheckCircle2} title="Everyone has a manager" text="People added later without a manager appear here." /> : (
          <>
            <div className="card-inset"><MoveBar managers={managers} count={picked.size} onMove={(to) => move(picked, to, () => setPicked(new Set()))} /></div>
            <PickTable people={unassigned} picked={picked} setPicked={setPicked} label="people without a manager" />
          </>
        )}
      </Card>

      <Card flush id="lines" title="Reporting lines" subtitle="Each manager under the manager they report to. A manager reports to someone when their own employee record has a manager.">
        {data.managers.length === 0 ? <EmptyState icon={Network} title="No managers yet" text="The admin creates manager accounts on the Users page." /> : (
          <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Reporting lines"><table>
            <thead><tr><th>Manager</th><th>Reports to</th><th className="num">Own team</th><th className="num">Further down</th><th>Cover</th><th><span className="visually-hidden">Team</span></th></tr></thead>
            <tbody>{data.managers.map((m) => (
              <tr key={m.user_id}>
                <td><span className={`org-name level-${Math.min(m.level, 3)}`}><span className="strong">{m.full_name}</span>
                  {m.job_title && <span className="cell-sub"> · {m.job_title}</span>}</span>
                  {!m.employee_id && <div className="cell-sub">Account not linked to an employee record</div>}</td>
                <td>{m.reports_to || <span className="muted">Top of the line</span>}</td>
                <td className="num">{m.direct}</td><td className="num">{m.branch}</td>
                <td>{m.cover ? <Badge tone={m.cover.status === "active" ? "success" : "info"}>{m.cover.cover}, to {m.cover.ends}</Badge> : <span className="muted">–</span>}</td>
                <td><div className="actions"><button type="button" className="btn btn-secondary btn-sm" onClick={() => { setOpen(m.user_id); setTeamPicked(new Set()); }}>
                  Team<span className="visually-hidden"> of {m.full_name}</span></button></div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </Card>

      <Cover onChanged={reload} />

      <Drawer open={Boolean(openManager)} onClose={() => setOpen(null)} title={openManager ? `${openManager.full_name}'s team` : ""}
        subtitle={openManager ? `${openManager.direct} ${openManager.direct === 1 ? "person" : "people"}${openManager.reports_to ? ` · reports to ${openManager.reports_to}` : ""}` : null}>
        {openManager && (openManager.team.length === 0
          ? <EmptyState compact icon={Users} title="No one on this team yet" text="Assign people from “Without a manager” above." />
          : <>
              <p className="muted">Tick people to move them to another manager, or to no manager.</p>
              <MoveBar managers={managers.filter((m) => m.user_id !== openManager.user_id)} count={teamPicked.size} allowNone label="Move"
                onMove={(to) => move(teamPicked, to, () => setTeamPicked(new Set()))} />
              <div className="section-gap"><PickTable people={openManager.team} picked={teamPicked} setPicked={setTeamPicked} label={`${openManager.full_name}'s team`} /></div>
            </>)}
        {openManager && <p className="section-gap"><UserMinus size={16} aria-hidden="true" className="icon-inline" /> <span className="muted">Moving someone takes them off this team at once; the new manager is emailed.</span></p>}
      </Drawer>
    </>
  );
}
