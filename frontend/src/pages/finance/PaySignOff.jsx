// Finance: sign off the pay rise that comes with each approved promotion, or send it back to HR with a reason.
// Finance sees only what a pay decision needs: not the model's score, nor the reasons for the promotion.
import { Fragment, useEffect, useState } from "react";
import { Banknote, CheckCircle2, CornerUpLeft, Wallet } from "lucide-react";
import { api } from "../../api";
import { Button, Card, EmptyState, PageHeader, Segmented, StatCard } from "../../components/ui";
import { PayStatus, PayTimeline } from "../../components/promotion/PayStatus";
import { useAction } from "../../useAction";

const MIN_NOTE = 20;
const VIEWS = [
  { value: "awaiting_finance", label: "Waiting" },
  { value: "returned", label: "Sent back" },
  { value: "signed_off", label: "Signed off" },
  { value: "all", label: "All" },
];

/** The open review of one pay rise: its history, and sign off or send back. */
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
    <div className="review-panel appear">
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
            <p className="alert alert-warning" style={{ marginTop: 12 }}>
              <strong>Outside the pay policy.</strong> HR's reason: {row.raise_reason}
            </p>
          )}
        </div>
        <div>
          <h3>History</h3>
          <PayTimeline history={row.history} />
        </div>
      </div>
      {waiting && (
        <div className="review-actions">
          {error && <p className="alert alert-error" role="alert">{error}</p>}
          <label className="field"><span>Note <span className="muted small">(optional to sign off; at least {MIN_NOTE} characters to send back, {note.trim().length} so far)</span></span>
            <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000}
              placeholder="e.g. Within this quarter's budget, or why HR should look at it again" />
          </label>
          <div className="row">
            <Button icon={CheckCircle2} busy={signing} busyText="Signing off…" disabled={returning} onClick={() => withSigning(() => act("sign-off"))}>
              Sign off {row.raise}%
            </Button>
            <Button look="plain" icon={CornerUpLeft} busy={returning} busyText="Sending back…" disabled={signing || note.trim().length < MIN_NOTE}
              onClick={() => withReturning(() => act("return"))}>Send back to HR</Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PaySignOff() {
  const [data, setData] = useState(null);
  const [view, setView] = useState("awaiting_finance");
  const [open, setOpen] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = () => api("/finance/pay-reviews").then(setData).catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);

  if (error && !data) return <p className="alert alert-error">{error}</p>;
  if (!data) return <p className="muted">Loading…</p>;
  const { summary, policy } = data;
  const rows = data.reviews.filter((r) => view === "all" || r.status === view);

  return (
    <>
      <PageHeader icon={Banknote} title="Pay sign-off"
        subtitle="Approved promotions whose pay rise needs confirming." />
      {message && <p className="alert alert-success" role="status">{message}</p>}

      <div className="stat-grid">
        <StatCard label="Waiting for you" value={summary.awaiting} note="Pay rises to sign off" />
        <StatCard label="Sent back to HR" value={summary.returned} note="Waiting for HR to revise" />
        <StatCard label="Signed off this year" value={summary.signed_off_this_year}
          note={summary.outside_policy_this_year ? `${summary.outside_policy_this_year} outside the policy` : "All within the policy"} />
        <StatCard label="Average rise this year" value={summary.average_raise_this_year != null ? `${summary.average_raise_this_year}%` : "–"}
          note={`Policy: ${policy.min_raise}% to ${policy.max_raise}%`} />
      </div>

      <Card flush title="Promotion pay rises" subtitle="Only percentages are used here, never salaries."
        actions={<Segmented label="Show" options={VIEWS} value={view} onChange={(v) => { setView(v); setOpen(null); }} />}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Employee</th><th>New role</th><th>Pay rise</th><th>Approved by HR</th><th>Status</th><th style={{ textAlign: "right" }}>Actions</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <Fragment key={r.id}>
                  <tr>
                    <td><span className="strong">{r.employee.full_name}</span><div className="muted small">{r.employee.department}</div></td>
                    <td>{r.new_title || "–"}{r.start && <div className="muted small">from {r.start}</div>}</td>
                    <td><span className="strong">{r.raise}%</span>
                      <div className="small">{r.within_policy ? <span className="muted">Within policy</span> : <span className="field-unusual strong">Outside policy</span>}</div></td>
                    <td>{r.approved_by}<div className="muted small">{r.approved_on}</div></td>
                    <td><PayStatus status={r.status} /></td>
                    <td style={{ textAlign: "right" }}>
                      <button type="button" className={`btn ${r.status === "awaiting_finance" ? "btn-primary" : "btn-plain"}`} aria-expanded={open === r.id}
                        onClick={() => setOpen(open === r.id ? null : r.id)}>
                        {open === r.id ? "Close" : r.status === "awaiting_finance" ? "Review" : "Details"}
                      </button>
                    </td>
                  </tr>
                  {open === r.id && (
                    <tr className="review-row"><td colSpan={6}>
                      <ReviewRow row={r} policy={policy} onDone={(_, text) => { setMessage(text); setOpen(null); load(); }} />
                    </td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 && (
          <EmptyState icon={Wallet} title={view === "awaiting_finance" ? "Nothing waiting for sign-off" : "Nothing here yet"}
            text={view === "awaiting_finance" ? "When HR approves a promotion, its pay rise appears here." : "Pay rises will appear here as they move through sign-off."} />
        )}
      </Card>

      <Card title="Signed off this year, by department">
        {summary.by_department.length === 0 ? <p className="muted">None signed off yet this year.</p> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Department</th><th>Promotions</th><th>Average pay rise</th></tr></thead>
            <tbody>{summary.by_department.map((d) => (
              <tr key={d.department}><td>{d.department}</td><td>{d.promotions}</td><td>{d.average_raise}%</td></tr>
            ))}</tbody>
          </table></div>
        )}
      </Card>
    </>
  );
}
