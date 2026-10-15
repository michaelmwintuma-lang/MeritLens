// The audit trail: every decision-relevant event, append-only and tamper-evident. Each event is chained to the one
// before it by a hash, so "Check the chain" can prove nothing was changed or deleted since it was written. For the
// compliance auditor and admins, read-only. It never holds anything an employee wrote.
import { useState } from "react";
import { CheckCircle2, Fingerprint, ShieldAlert, ShieldCheck } from "lucide-react";
import { governance } from "../../api";
import { useAction } from "../../useAction";
import { useLoad } from "../../useLoad";
import { Button, Callout, Card, EmptyState, LoadError, PageHeader, PageLoading } from "../../components/ui";

const SUBJECTS = { employee: "Employee", nomination: "Nomination", decision: "Decision", correction: "Correction", model: "Model" };

/** The event's details in plain words: each field on its own line, numbers as they are. */
function Details({ payload }) {
  const entries = Object.entries(payload);
  if (!entries.length) return null;
  return (
    <details className="audit-details">
      <summary>Details</summary>
      <dl>{entries.map(([key, value]) => (
        <div key={key}><dt>{key.replaceAll("_", " ")}</dt>
          <dd className="mono">{typeof value === "object" && value !== null ? JSON.stringify(value) : String(value)}</dd></div>
      ))}</dl>
    </details>
  );
}

function ChainCheck() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [working, withWorking] = useAction();
  async function check() {
    setError("");
    try { setResult(await governance.verify()); } catch (err) { setError(err.message); }
  }
  return (
    <Card title="Is the trail exactly as it was written?"
      subtitle="Recomputes every event's fingerprint (SHA-256) and its link to the event before it."
      actions={<Button look="secondary" icon={Fingerprint} busy={working} busyText="Checking…" onClick={() => withWorking(check)}>Check the chain</Button>}>
      {error && <Callout tone="error">{error}</Callout>}
      {result && (result.intact
        ? <Callout tone="success" icon={ShieldCheck} role="status">Intact: all {result.events} events are exactly as written.</Callout>
        : <Callout tone="error" icon={ShieldAlert}>Broken at event {result.first_broken_id}: it {result.problem}. Everything from there on can't be trusted as written.</Callout>)}
      {!result && !error && <p className="muted">Not checked yet in this visit.</p>}
    </Card>
  );
}

export default function AuditTrail() {
  const [event, setEvent] = useState("");
  const [page, setPage] = useState(1);
  const { data, error, reload } = useLoad(() => governance.audit({ event, page }), [event, page]);

  const header = <PageHeader title="Audit trail"
    subtitle="Every nomination, decision, pay step, record change, correction, hold and model release: append-only, tamper-evident and read-only." />;
  if (error) return <>{header}<LoadError message={error} onRetry={reload} /></>;
  if (!data) return <>{header}<PageLoading /></>;
  return (
    <>
      {header}
      <ChainCheck />
      <Card title="Events" subtitle={`${data.total} in total, newest first.`} flush
        actions={<label className="field filter-field"><span className="visually-hidden">Show</span>
          <select value={event} onChange={(e) => { setEvent(e.target.value); setPage(1); }} aria-label="Show only one kind of event">
            <option value="">Every kind of event</option>
            {Object.entries(data.event_types).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select></label>}>
        {data.events.length === 0 ? <EmptyState icon={CheckCircle2} title="No events yet" text="Events appear here as people nominate, decide and correct records." /> : (
          <div className="table-wrap" tabIndex={0} role="region" aria-label="Audit events"><table>
            <thead><tr><th>When</th><th>What happened</th><th>Who</th><th>About</th><th>Model</th><th>Fingerprint</th></tr></thead>
            <tbody>{data.events.map((e) => (
              <tr key={e.id}>
                <td className="nowrap num">{e.at.replace("T", " ")}</td>
                <td>{e.label}<Details payload={e.payload} /></td>
                <td>{e.actor}</td>
                <td className="nowrap">{SUBJECTS[e.subject_type] || e.subject_type} {e.subject_id}</td>
                <td className="mono">{e.model_version || "–"}</td>
                <td className="mono" title={e.hash}>{e.hash.slice(0, 10)}…</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
        {data.pages > 1 && (
          <nav className="pager" aria-label="Pages of events">
            <button type="button" className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Newer</button>
            <span className="muted" aria-live="polite">Page {data.page} of {data.pages}</span>
            <button type="button" className="btn btn-secondary btn-sm" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Older</button>
          </nav>
        )}
      </Card>
    </>
  );
}
