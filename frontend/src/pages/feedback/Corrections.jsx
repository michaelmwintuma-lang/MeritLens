// HR: the record-correction queue. Each request shows the value, what the employee asked for and their evidence.
// HR confirms the value they verified (the record is corrected, the employee re-scored and the change logged) or
// rejects it with a reason the employee receives.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, ClipboardPen, FileText, XCircle } from "lucide-react";
import { api, apiBlob } from "../../api";
import { percent } from "../../format";
import { Button, Callout, Card, EmptyState, LoadError, PageLoading, PageHeader, Segmented } from "../../components/ui";
import CorrectionStatus from "../../components/feedback/CorrectionStatus";
import { useAction } from "../../useAction";
import { useToast } from "../../components/Toast";

const MIN_REASON = 20;

async function openEvidence(id) {
  const url = URL.createObjectURL(await apiBlob(`/hr/feedback/corrections/${id}/evidence`));
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** One waiting request, with the two decisions. */
function Decide({ request, onDone }) {
  const [verified, setVerified] = useState(String(request.requested_value));
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [confirming, withConfirming] = useAction();
  const [rejecting, withRejecting] = useAction();
  const toast = useToast();

  const act = (path, body) => async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api(`/hr/feedback/corrections/${request.id}/${path}`, { method: "POST", body });
      if (res.approval) toast("This moves them across the threshold, so a second HR person must approve it (see Approvals).");
      onDone(res);
    } catch (err) {
      setError(err.message);
    }
  };
  const unit = request.current_display.endsWith("%") ? " (%)" : "";

  return (
    <>
      {error && <Callout tone="error">{error}</Callout>}
      <div className="queue-actions">
        <form className="pay-box confirm" onSubmit={(e) => withConfirming(() => act("confirm", { verified_value: Number(verified), note: note.trim() || null })(e))}>
          <h3><CheckCircle2 size={18} aria-hidden="true" />Confirm</h3>
          <p className="muted">The record is corrected, the employee re-scored, and the change logged with both scores.</p>
          <label className="field">Verified value{unit}
            <input type="number" step="any" value={verified} onChange={(e) => setVerified(e.target.value)} required />
          </label>
          <label className="field">How you checked it (optional, kept in the record's history)
            <textarea rows={2} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
          <Button busy={confirming} busyText="Correcting…" disabled={verified === ""}>Confirm and correct</Button>
        </form>
        <form className="pay-box reject" onSubmit={(e) => withRejecting(() => act("reject", { reason: reason.trim() })(e))}>
          <h3><XCircle size={18} aria-hidden="true" />Reject</h3>
          <p className="muted">The record stays as it is. The employee receives your reason.</p>
          <label className="field"><span>Reason <span className="muted">(required, {reason.trim().length}/{MIN_REASON} characters)</span></span>
            <textarea rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <Button look="secondary" busy={rejecting} busyText="Rejecting…" disabled={reason.trim().length < MIN_REASON}>Reject the request</Button>
        </form>
      </div>
    </>
  );
}

function RequestCard({ request, onDone }) {
  const [error, setError] = useState("");
  return (
    <Card title={`${request.employee_name}: ${request.label}`}
      subtitle={`Asked by the employee on ${request.created_at.slice(0, 10)}`}
      actions={<CorrectionStatus request={request} />}>
      <div className="change" role="group" aria-label="The change asked for">
        <div className="change-value"><span className="label muted">In the record</span><strong>{request.current_display}</strong></div>
        <ArrowRight size={20} aria-hidden="true" />
        <div className="change-value asked"><span className="label muted">Asked for</span><strong>{request.requested_display}</strong></div>
        {request.status === "confirmed" && <>
          <ArrowRight size={20} aria-hidden="true" />
          <div className="change-value"><span className="label muted">Corrected to</span><strong>{request.verified_display}</strong></div>
        </>}
      </div>
      {(request.score_before != null || request.decided_by) && (
        <dl className="details-list">
          {request.score_before != null && <div><dt>Readiness</dt><dd>{percent(request.score_before)} → {percent(request.score_after)}</dd></div>}
          {request.decided_by && <div><dt>Decided</dt><dd>{request.decided_by}, {request.decided_at.slice(0, 10)}</dd></div>}
        </dl>
      )}
      <h3 className="form-subhead">The employee's evidence</h3>
      <p className="quote">{request.note}</p>
      {request.has_evidence && (
        <button type="button" className="btn btn-secondary" onClick={() => openEvidence(request.id).catch((err) => setError(err.message))}>
          <FileText size={16} aria-hidden="true" />Open the attached document
        </button>
      )}
      {error && <Callout tone="error" className="section-gap">{error}</Callout>}
      {request.decision_reason && <p className="section-gap"><span className="muted">{request.status === "rejected" ? "Reason given:" : "HR's note:"}</span> {request.decision_reason}</p>}
      {request.status === "pending" && <Decide request={request} onDone={onDone} />}
      <p className="section-gap"><Link className="text-link" to={`/employees/${request.employee_id}`}>{request.employee_name}'s explanation and record history <ArrowRight size={16} aria-hidden="true" /></Link></p>
    </Card>
  );
}

export default function Corrections() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [view, setView] = useState("pending");
  const load = () => { setError(""); return api("/hr/feedback/corrections").then(setRows).catch((err) => setError(err.message)); };
  useEffect(() => { load(); }, []);

  const shown = rows?.filter((r) => (view === "pending" ? r.status === "pending" : r.status !== "pending")) || [];
  const waiting = rows?.filter((r) => r.status === "pending").length ?? 0;

  return (
    <>
      <PageHeader title="Record corrections"
        subtitle="Employees' requests to correct a value in their work record. Nothing changes until you confirm it." />
      {error && <LoadError message={error} onRetry={load} />}
      {!rows && !error && <PageLoading />}
      {rows && (
        <>
          <div className="tabs-bar">
            <Segmented label="Which requests" value={view} onChange={setView}
              options={[{ value: "pending", label: `Waiting (${waiting})` }, { value: "decided", label: `Decided (${rows.length - waiting})` }]} />
          </div>
          {shown.length === 0 && (
            <div className="card">
              <EmptyState icon={ClipboardPen} title={view === "pending" ? "Nothing waiting" : "No decisions yet"}
                text={view === "pending" ? "When an employee asks for a value in their record to be corrected, it appears here, oldest first." : "Requests you confirm or reject are kept here."} />
            </div>
          )}
          {shown.map((r) => <RequestCard key={r.id} request={r} onDone={load} />)}
        </>
      )}
    </>
  );
}
