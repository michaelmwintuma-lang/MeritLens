// HR reviews one nomination: the manager's recommendation, the model's score and explanation, then decides,
// setting the final pay rise for an approval.
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ClipboardCheck } from "lucide-react";
import { api } from "../../api";
import { percent } from "../../format";
import ScoreBar, { Verdict } from "../../components/promotion/ScoreBar";
import Contributions from "../../components/promotion/Contributions";
import Recommendation from "../../components/promotion/Recommendation";
import { NominationStatus } from "../../components/promotion/Status";
import { PayStatus, PayTimeline } from "../../components/promotion/PayStatus";
import { Button, PageHeader } from "../../components/ui";
import CommitteeNote from "../../components/feedback/CommitteeNote";
import { useAction } from "../../useAction";

const MIN_REASON = 20;

/** After approval: where the pay rise is with Finance, and (if Finance sent it back) HR's revision. */
function PaySignOff({ decision, policy, onChange }) {
  const [raise, setRaise] = useState(String(decision.approved_raise));
  const [raiseReason, setRaiseReason] = useState(decision.raise_reason || "");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [working, withWorking] = useAction();
  const value = Number(raise);
  const outside = raise !== "" && (value < policy.min_raise || value > policy.max_raise);
  const blocked = raise === "" || note.trim().length < 10 || (outside && raiseReason.trim().length < MIN_REASON);

  async function resubmit(e) {
    e.preventDefault();
    setError("");
    try {
      onChange(await api(`/promotion/decisions/${decision.id}/resubmit`, { method: "POST",
        body: { approved_raise: value, raise_reason: raiseReason.trim() || null, note: note.trim() } }));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="card">
      <div className="row spread"><h2>Pay rise: {decision.approved_raise}%</h2><PayStatus status={decision.pay_status} /></div>
      <p className="muted">
        {decision.pay_status === "awaiting_finance" && "Waiting for Finance to sign it off. The manager and employee are told only after that."}
        {decision.pay_status === "returned" && "Finance sent this back. Revise the pay rise (or keep it) and answer their note."}
        {decision.pay_status === "signed_off" && "Finance has signed it off, and the manager and employee have been told."}
        {!decision.pay_status && "Approved before Finance sign-off was introduced."}
      </p>
      <PayTimeline history={decision.pay_history} />
      {decision.pay_status === "returned" && (
        <form onSubmit={(e) => withWorking(() => resubmit(e))} style={{ marginTop: 16 }}>
          {error && <p className="alert alert-error" role="alert">{error}</p>}
          <div className="form-row">
            <label className="field">Revised pay rise (%)
              <input type="number" value={raise} onChange={(e) => setRaise(e.target.value)} min={0} max={100} step="0.5" required />
              <span className={outside ? "field-problem" : "field-hint"}>Policy: {policy.min_raise}% to {policy.max_raise}%.</span>
            </label>
          </div>
          {outside && (
            <label className="field"><span>Why go outside the policy? <span className="small">(required, {raiseReason.trim().length}/{MIN_REASON} characters)</span></span>
              <textarea rows={2} value={raiseReason} onChange={(e) => setRaiseReason(e.target.value)} maxLength={2000} />
            </label>
          )}
          <label className="field"><span>Your answer to Finance <span className="small">(at least 10 characters)</span></span>
            <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} />
          </label>
          <Button busy={working} busyText="Sending to Finance…" disabled={blocked}>Send to Finance again</Button>
        </form>
      )}
    </section>
  );
}

export default function ReviewNomination() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [nomination, setNomination] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [policy, setPolicy] = useState(null);
  const [decision, setDecision] = useState("");
  const [reason, setReason] = useState("");
  const [raise, setRaise] = useState("");
  const [raiseReason, setRaiseReason] = useState("");
  const [error, setError] = useState("");
  const [onHold, setOnHold] = useState(false); // held until a pending record correction is resolved
  const [working, withWorking] = useAction(); // hooks before any early return, so their order never changes

  useEffect(() => {
    Promise.all([api(`/promotion/nominations/${id}`), api("/promotion/pay-policy")])
      .then(([n, pay]) => {
        setNomination(n);
        setPolicy(pay);
        setRaise(n.recommendation?.proposed_raise != null ? String(n.recommendation.proposed_raise) : String(pay.min_raise));
        return api(`/promotion/employees/${n.employee.id}`).then(setExplanation);
      })
      .catch((err) => setError(err.message));
  }, [id]);

  if (error && !nomination) return <p className="alert alert-error">{error}</p>;
  if (!nomination || !explanation || !policy) return <p className="muted">Loading…</p>;

  // Disagreeing = approving someone the model doesn't recommend, or rejecting someone it does
  const disagrees = decision && (decision === "approve") !== explanation.recommended;
  const reasonTooShort = disagrees && reason.trim().length < MIN_REASON;
  const raiseNumber = Number(raise);
  const raiseOutside = decision === "approve" && raise !== "" && (raiseNumber < policy.min_raise || raiseNumber > policy.max_raise);
  const raiseMissing = decision === "approve" && raise === "";
  const raiseReasonTooShort = raiseOutside && raiseReason.trim().length < MIN_REASON;

  async function submit(e) {
    e.preventDefault();
    setError("");
    const body = { decision, reason: reason.trim() || null };
    if (decision === "approve") Object.assign(body, { approved_raise: raiseNumber, raise_reason: raiseReason.trim() || null });
    try {
      await api(`/promotion/nominations/${id}/decision`, { method: "POST", body });
      navigate("/decisions");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <Link to="/nominations" className="back"><ArrowLeft size={16} />Back to nominations</Link>
      <PageHeader icon={ClipboardCheck} title={`Review: ${nomination.employee.full_name}`}
        subtitle={`${nomination.employee.department} · recommended by ${nomination.nominated_by} on ${nomination.created_at.slice(0, 10)}`}
        actions={<NominationStatus status={nomination.status} />} />

      <section className="card">
        <h2>The manager's recommendation</h2>
        <Recommendation nomination={nomination} />
      </section>

      <section className="card">
        <div className="row spread">
          <h2>The model's view: {percent(explanation.score)}</h2>
          <Verdict recommended={explanation.recommended} />
        </div>
        <ScoreBar score={explanation.score} threshold={explanation.threshold} />
        <p className="summary">{explanation.summary}</p>
        <Contributions contributions={explanation.contributions} limit={4} />
        <p className="small"><Link to={`/employees/${nomination.employee.id}`}>Full explanation, what-if and tips</Link></p>
      </section>

      <CommitteeNote nominationId={nomination.id} pending={nomination.status === "pending"}
        onChange={(note) => setOnHold(note.deferred)} />

      {nomination.status === "pending" && onHold ? (
        <p className="alert alert-info">Your decision is on hold until the record correction above is resolved.</p>
      ) : nomination.status === "pending" ? (
        <form className="card" onSubmit={(e) => withWorking(() => submit(e))}>
          <h2>Your decision</h2>
          <p className="muted">The model only advises. Your decision is final and is recorded in the decision log with the model's score.</p>
          {error && <p className="alert alert-error" role="alert">{error}</p>}
          <div className="choices" role="radiogroup" aria-label="Decision">
            <label className="check"><input type="radio" name="decision" value="approve" checked={decision === "approve"} onChange={() => setDecision("approve")} /> Approve the promotion</label>
            <label className="check"><input type="radio" name="decision" value="reject" checked={decision === "reject"} onChange={() => setDecision("reject")} /> Reject the promotion</label>
          </div>
          {disagrees && (
            <p className="alert alert-info">
              This differs from the model, which {explanation.recommended ? "recommends" : "doesn't recommend"} promotion.
              That's allowed, but please explain why, in at least {MIN_REASON} characters.
            </p>
          )}
          <label className="field"><span>Reason {disagrees ? <span className="small">(required, {reason.trim().length}/{MIN_REASON} characters)</span> : <span className="muted small">(optional)</span>}</span>
            <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={2000} />
          </label>

          {decision === "approve" && (
            <div className="pay-box">
              <h3>Pay rise</h3>
              <div className="form-row">
                <label className="field">Approved pay rise (%)
                  <input type="number" value={raise} onChange={(e) => setRaise(e.target.value)} min={0} max={100} step="0.5" required />
                  <span className={raiseOutside ? "field-problem" : "field-hint"}>
                    The manager proposed {nomination.recommendation?.proposed_raise ?? "–"}%. Policy: {policy.min_raise}% to {policy.max_raise}%.
                  </span>
                </label>
              </div>
              {raiseOutside && (
                <label className="field"><span>Why go outside the policy? <span className="small">(required, {raiseReason.trim().length}/{MIN_REASON} characters)</span></span>
                  <textarea rows={2} value={raiseReason} onChange={(e) => setRaiseReason(e.target.value)} maxLength={2000} />
                </label>
              )}
              <p className="muted small" style={{ margin: 0 }}>Only the percentage is recorded, never a salary. It's never used by the model.</p>
            </div>
          )}
          <Button busy={working} busyText="Saving decision…" disabled={!decision || reasonTooShort || raiseMissing || raiseReasonTooShort}>Save decision</Button>
        </form>
      ) : nomination.decision?.decision === "approve" ? (
        <PaySignOff decision={nomination.decision} policy={policy}
          onChange={(decision) => setNomination({ ...nomination, decision })} />
      ) : (
        <p className="alert alert-info">This nomination has already been decided. See the decision log.</p>
      )}
    </>
  );
}
