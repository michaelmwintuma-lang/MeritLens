// Finance: sign off the pay rise that comes with each approved promotion, or send it back to HR with a reason; sign
// off several within-policy rises at once; see how long each has waited; filter by review cycle; and hand signed-off
// rises to payroll. Finance sees only what a pay decision needs: not the model's score, nor the reasons for the promotion.
import { useEffect, useState } from "react";
import { CheckCircle2, Clock, CornerUpLeft, Download, Send, Wallet } from "lucide-react";
import { api, apiBlob } from "../../api";
import { Badge, Button, Callout, Card, EmptyState, LoadError, PageHeader, PageLoading, Segmented, StatCard } from "../../components/ui";
import BarList from "../../components/charts/BarList";
import { Drawer, useConfirm } from "../../components/Overlay";
import { useToast } from "../../components/Toast";
import { PayStatus, PayTimeline } from "../../components/promotion/PayStatus";
import { useAction } from "../../useAction";

const MIN_NOTE = 20;
const VIEWS = [
  { value: "awaiting_finance", label: "Waiting" },
  { value: "returned", label: "Sent back" },
  { value: "signed_off", label: "Signed off" },
  { value: "all", label: "All" },
];

/** The review of one pay rise, in a drawer: what is being signed off, its history, and sign off or send back. */
function ReviewRow({ row, policy, onDone }) {
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [signing, withSigning] = useAction();
  const [returning, withReturning] = useAction();
  const waiting = row.status === "awaiting_finance";

  async function act(action) {
    setError("");
    try {
      onDone(await api(`/finance/pay-reviews/${row.id}/${action}`, { method: "POST", body: { note: note.trim() || null } }),
        action === "sign-off" ? `Signed off ${row.raise}% for ${row.employee.full_name}. The manager and employee have been told.`
          : `Sent back to HR. Nobody else has been told.`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="review-panel">
      <div className="review-grid">
        <div>
          <h3>What's being signed off</h3>
          <dl className="details-list">
            <div><dt>Employee</dt><dd>{row.employee.full_name}</dd></div>
            <div><dt>New role</dt><dd>{row.new_title || "–"}</dd></div>
            <div><dt>Starting</dt><dd>{row.start || "–"}</dd></div>
            <div><dt>Pay rise approved by HR</dt><dd>{row.raise}%</dd></div>
            <div><dt>Manager proposed</dt><dd>{row.proposed_raise != null ? `${row.proposed_raise}%` : "–"}</dd></div>
            <div><dt>Pay policy</dt><dd>{policy.min_raise}% to {policy.max_raise}%</dd></div>
          </dl>
          {!row.within_policy && (
            <Callout tone="warning" title="Outside the pay policy" className="section-gap">HR's reason: {row.raise_reason}</Callout>
          )}
        </div>
        <div>
          <h3>History</h3>
          <PayTimeline history={row.history} />
        </div>
      </div>
      {waiting && (
        <div className="review-actions">
          {error && <Callout tone="error">{error}</Callout>}
          <label className="field"><span>Note <span className="muted">(optional to sign off; at least {MIN_NOTE} characters to send back, {note.trim().length} so far)</span></span>
            <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000}
              placeholder="e.g. Within this quarter's budget, or why HR should look at it again" />
          </label>
          <div className="form-actions">
            <Button icon={CheckCircle2} busy={signing} busyText="Signing off…" disabled={returning} onClick={() => withSigning(() => act("sign-off"))}>
              Sign off {row.raise}%
            </Button>
            <Button look="secondary" icon={CornerUpLeft} busy={returning} busyText="Sending back…" disabled={signing || note.trim().length < MIN_NOTE}
              onClick={() => withReturning(() => act("return"))}>Send back to HR</Button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Signed-off rises not yet handed to payroll: download them as a CSV, then mark them as sent (once each). */
function Payroll({ rows, onChanged }) {
  const [problem, setProblem] = useState("");
  const [confirm, dialog] = useConfirm();
  const [marking, withMarking] = useAction();
  const toast = useToast();
  const due = rows.filter((r) => r.status === "signed_off" && !r.payroll_sent_at);

  async function download() {
    setProblem("");
    try {
      const url = URL.createObjectURL(await apiBlob("/finance/payroll.csv"));
      Object.assign(document.createElement("a"), { href: url, download: `payroll-${new Date().toISOString().slice(0, 10)}.csv` }).click();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (err) {
      setProblem(err.message);
    }
  }

  async function markSent() {
    if (!(await confirm({ title: `Mark ${due.length} pay rise${due.length === 1 ? "" : "s"} as sent to payroll?`, action: "Mark as sent",
      text: "Do this once payroll has the file. They then leave this list, so nothing is applied twice; the payroll file with everything is still available." }))) return;
    setProblem("");
    try {
      const res = await api("/finance/payroll/mark-sent", { method: "POST", body: { ids: due.map((r) => r.id) } });
      toast(`${res.marked} pay rise${res.marked === 1 ? "" : "s"} marked as sent to payroll.`);
      onChanged();
    } catch (err) {
      setProblem(err.message);
    }
  }

  return (
    <Card id="payroll" icon={Send} title="Hand-over to payroll"
      subtitle="Signed-off rises payroll hasn't had yet: download them, give the file to payroll, then mark them as sent.">
      {dialog}
      {problem && <Callout tone="error">{problem}</Callout>}
      {due.length === 0 ? <EmptyState compact icon={CheckCircle2} title="Nothing waiting for payroll" text="Signed-off pay rises appear here until they're marked as sent." /> : (
        <>
          <ul className="plain-list">{due.map((r) => (
            <li key={r.id} className="row spread"><span><strong>{r.employee.full_name}</strong> <span className="muted">· {r.new_title || "promotion"}{r.start ? `, from ${r.start}` : ""}</span></span>
              <span className="num strong">{r.raise}%</span></li>
          ))}</ul>
          <div className="form-actions section-gap">
            <Button icon={Download} look="secondary" onClick={download}>Download payroll file (CSV)</Button>
            <Button icon={Send} busy={marking} busyText="Saving…" onClick={() => withMarking(markSent)}>Mark {due.length} as sent to payroll</Button>
          </div>
        </>
      )}
    </Card>
  );
}

export default function PaySignOff() {
  const [data, setData] = useState(null);
  const [view, setView] = useState("awaiting_finance");
  const [cycle, setCycle] = useState("");
  const [open, setOpen] = useState(null);
  const [picked, setPicked] = useState(new Set());
  const [confirm, dialog] = useConfirm();
  const [signing, withSigning] = useAction();
  const toast = useToast();
  const [error, setError] = useState("");

  const load = () => api(`/finance/pay-reviews${cycle ? `?cycle_id=${cycle}` : ""}`).then((d) => { setData(d); setPicked(new Set()); })
    .catch((err) => setError(err.message));
  useEffect(() => { load(); }, [cycle]); // eslint-disable-line react-hooks/exhaustive-deps

  const header = <PageHeader title="Pay sign-off" subtitle="Approved promotions whose pay rise needs confirming. Only percentages are used here, never salaries." />;
  if (error && !data) return <>{header}<LoadError message={error} onRetry={load} /></>;
  if (!data) return <>{header}<PageLoading /></>;
  const { summary, policy } = data;
  const rows = data.reviews.filter((r) => view === "all" || r.status === view);
  const opened = data.reviews.find((r) => r.id === open);
  const bulkable = rows.filter((r) => r.status === "awaiting_finance" && r.within_policy);
  const toggle = (id) => { const next = new Set(picked); next.has(id) ? next.delete(id) : next.add(id); setPicked(next); };
  const allPicked = bulkable.length > 0 && bulkable.every((r) => picked.has(r.id));

  async function signOffPicked() {
    const ids = [...picked];
    if (!(await confirm({ title: `Sign off ${ids.length} pay rise${ids.length === 1 ? "" : "s"}?`, action: `Sign off ${ids.length}`,
      text: "Each is within the pay policy. Each is signed off and logged on its own, and each manager and employee is told." }))) return;
    try {
      const res = await api("/finance/pay-reviews/sign-off-many", { method: "POST", body: { ids } });
      toast(`Signed off ${res.signed_off} pay rise${res.signed_off === 1 ? "" : "s"}. The managers and employees have been told.`);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      {header}
      {dialog}
      {error && <Callout tone="error">{error}</Callout>}
      <div className="stat-grid">
        <StatCard label="Waiting for you" value={summary.awaiting}
          note={summary.waiting_longest ? `The oldest has waited ${summary.waiting_longest} working day${summary.waiting_longest === 1 ? "" : "s"}` : "Pay rises to sign off"} />
        <StatCard label="Sent back to HR" value={summary.returned} note="Waiting for HR to revise" />
        <StatCard label="Signed off this year" value={summary.signed_off_this_year}
          note={summary.outside_policy_this_year ? `${summary.outside_policy_this_year} outside the policy` : "All within the policy"} />
        <StatCard label="For payroll" value={summary.payroll_waiting} note="Signed off, not yet sent to payroll" />
      </div>

      <Card flush title="Sign-off queue"
        subtitle={`Open a pay rise to review it, or tick several within the policy (${policy.min_raise}% to ${policy.max_raise}%) to sign them off together.`}
        actions={<div className="row">
          {data.cycles.length > 0 && (
            <label className="field filter-field"><span className="visually-hidden">Review cycle</span>
              <select value={cycle} onChange={(e) => setCycle(e.target.value)} aria-label="Review cycle">
                <option value="">Every review cycle</option>
                {data.cycles.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select></label>)}
          <Segmented label="Show" options={VIEWS} value={view} onChange={(v) => { setView(v); setPicked(new Set()); }} />
        </div>}>
        {picked.size > 0 && (
          <div className="card-inset">
            <div className="bulk-bar">
              <span className="strong">{picked.size} ticked</span>
              <Button icon={CheckCircle2} busy={signing} busyText="Signing off…" onClick={() => withSigning(signOffPicked)}>Sign off {picked.size}</Button>
              <button type="button" className="btn btn-ghost" onClick={() => setPicked(new Set())}>Clear</button>
            </div>
          </div>
        )}
        {rows.length === 0 ? (
          <EmptyState icon={Wallet} title={view === "awaiting_finance" ? "Nothing waiting for sign-off" : "Nothing here yet"}
            text={view === "awaiting_finance" ? "When HR approves a promotion, its pay rise appears here." : "Pay rises will appear here as they move through sign-off."} />
        ) : (
          <div className="table-wrap" tabIndex={0} role="region" aria-label="Sign-off queue">
            <table>
              <thead><tr>
                <th>{bulkable.length > 0 && <input type="checkbox" checked={allPicked} aria-label="Tick every pay rise within the policy"
                  onChange={() => setPicked(allPicked ? new Set() : new Set(bulkable.map((r) => r.id)))} />}</th>
                <th>Employee</th><th>New role</th><th className="num">Pay rise</th><th>Approved by HR</th><th className="num">Waiting</th><th>Status</th><th className="num">Actions</th>
              </tr></thead>
              <tbody>
                {rows.map((r) => {
                  const canTick = r.status === "awaiting_finance" && r.within_policy;
                  return (
                    <tr key={r.id} className={picked.has(r.id) ? "row-open" : ""}>
                      <td>{canTick && <input type="checkbox" checked={picked.has(r.id)} onChange={() => toggle(r.id)} aria-label={`Tick ${r.employee.full_name}'s pay rise`} />}</td>
                      <td><span className="strong">{r.employee.full_name}</span><div className="cell-sub">{r.employee.department}{r.cycle ? ` · ${r.cycle.name}` : ""}</div></td>
                      <td>{r.new_title || "–"}{r.start && <div className="cell-sub">from {r.start}</div>}</td>
                      <td className="num"><span className="strong">{r.raise}%</span>
                        <div className="cell-sub">{r.within_policy ? "Within policy" : <span className="field-unusual strong">Outside policy</span>}</div></td>
                      <td>{r.approved_by}<div className="cell-sub">{r.approved_on}</div></td>
                      <td className="num">{r.waiting_days == null ? <span className="muted">–</span>
                        : r.waiting_days > 2 ? <Badge tone="warning" icon={Clock}>{r.waiting_days} days</Badge>
                          : <span>{r.waiting_days === 0 ? "Today" : `${r.waiting_days} day${r.waiting_days === 1 ? "" : "s"}`}</span>}</td>
                      <td><div className="tag-stack"><PayStatus status={r.status} />{r.payroll_sent_at && <Badge icon={Send}>Sent to payroll</Badge>}</div></td>
                      <td className="num">
                        <button type="button" className={`btn btn-sm ${r.status === "awaiting_finance" ? "btn-primary" : "btn-secondary"}`} onClick={() => setOpen(r.id)}>
                          {r.status === "awaiting_finance" ? "Review" : "Details"}<span className="visually-hidden"> {r.employee.full_name}</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Payroll rows={data.reviews} onChanged={load} />

      <div className="chart-grid">
        <Card title="How signed-off rises spread" subtitle={`Each signed-off pay rise${cycle ? " in this cycle" : ""}, by percentage. Policy: ${policy.min_raise}% to ${policy.max_raise}%.`}>
          {summary.distribution.length === 0 ? <EmptyState compact icon={Wallet} title="None signed off yet" text="The spread appears once pay rises are signed off." /> : (
            <BarList label="Signed-off pay rises by percentage" format={(v) => `${v}`} axis={["0", "Most common"]}
              rows={summary.distribution.map((d) => ({ key: d.raise, name: `${d.raise}%${d.within_policy ? "" : " (outside policy)"}`, value: d.count,
                detail: d.count === 1 ? "promotion" : "promotions" }))} />
          )}
        </Card>
        <Card title="Signed off this year, by department">
          {summary.by_department.length === 0 ? <EmptyState compact icon={CheckCircle2} title="None signed off yet this year" text="Each department's promotions and average pay rise appear here once signed off." /> : (
            <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Signed off by department"><table>
              <thead><tr><th>Department</th><th className="num">Promotions</th><th className="num">Average pay rise</th></tr></thead>
              <tbody>{summary.by_department.map((d) => (
                <tr key={d.department}><td>{d.department}</td><td className="num">{d.promotions}</td><td className="num">{d.average_raise}%</td></tr>
              ))}</tbody>
            </table></div>
          )}
        </Card>
      </div>

      <Drawer open={Boolean(opened)} onClose={() => setOpen(null)}
        title={opened ? `Pay rise: ${opened.employee.full_name}` : ""} subtitle={opened ? <PayStatus status={opened.status} /> : null}>
        {opened && <ReviewRow row={opened} policy={policy} onDone={(_, text) => { toast(text); setOpen(null); load(); }} />}
      </Drawer>
    </>
  );
}
