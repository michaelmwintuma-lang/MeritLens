// HR reviews one nomination: the manager's recommendation, the model's score and explanation, then decides,
// setting the final pay rise for an approval.
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, Banknote } from "lucide-react";
import { api } from "../../api";
import { percent } from "../../format";
import ScoreBar, { Verdict } from "../../components/promotion/ScoreBar";
import Contributions from "../../components/promotion/Contributions";
import Recommendation from "../../components/promotion/Recommendation";
import { NominationStatus } from "../../components/promotion/Status";
import { PayStatus, PayTimeline } from "../../components/promotion/PayStatus";
import { Button, Callout, Card, LoadError, PageHeader, PageLoading } from "../../components/ui";
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
    <Card id="pay" icon={Banknote} title={`Pay rise: ${decision.approved_raise}%`} actions={<PayStatus status={decision.pay_status} />}>
      <p className="muted">
        {decision.pay_status === "awaiting_finance" && "Waiting for Finance to sign it off. The manager and employee are told only after that."}
        {decision.pay_status === "returned" && "Finance sent this back. Revise the pay rise (or keep it) and answer their note."}
        {decision.pay_status === "signed_off" && "Finance has signed it off, and the manager and employee have been told."}
        {!decision.pay_status && "Approved before Finance sign-off was introduced."}
      </p>
      <PayTimeline history={decision.pay_history} />
      {decision.pay_status === "returned" && (
        <form onSubmit={(e) => withWorking(() => resubmit(e))} className="section-gap">
          {error && <Callout tone="error">{error}</Callout>}
          <div className="form-row">
            <label className="field">Revised pay rise (%)
              <input type="number" value={raise} onChange={(e) => setRaise(e.target.value)} min={0} max={100} step="0.5" required />
              <span className={outside ? "field-problem" : "field-hint"}>Policy: {policy.min_raise}% to {policy.max_raise}%.</span>
            </label>
          </div>
          {outside && (
            <label className="field"><span>Why go outside the policy? <span className="muted">(required, {raiseReason.trim().length}/{MIN_REASON} characters)</span></span>
              <textarea rows={2} value={raiseReason} onChange={(e) => setRaiseReason(e.target.value)} maxLength={2000} />
            </label>
          )}
          <label className="field"><span>Your answer to Finance <span className="muted">(at least 10 characters)</span></span>
            <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} />
          </label>
          <Button busy={working} busyText="Sending to Finance…" disabled={blocked}>Send to Finance again</Button>
        </form>
      )}
    </Card>
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

  // Any of the three missing with an error: show the error (not an endless spinner)
  if (error && (!nomination || !explanation || !policy)) return <LoadError message={error} />;
  if (!nomination || !explanation || !policy) return <PageLoading />;

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

  const pending = nomination.status === "pending";
  return (
    <>
      <PageHeader title={`Review: ${nomination.employee.full_name}`}
        subtitle={`${nomination.employee.department} · recommended by ${nomination.nominated_by} on ${nomination.created_at.slice(0, 10)}`}
        status={<NominationStatus status={nomination.status} />} />

      <CommitteeNote nominationId={nomination.id} pending={pending} onChange={(note) => setOnHold(note.deferred)} />

      <div className="review-columns">
        <Card id="manager" title="The manager's recommendation">
          <Recommendation nomination={nomination} />
        </Card>

        <Card id="model" title="The model's view" actions={<Verdict recommended={explanation.recommended} />}>
          <div className="score-big">{percent(explanation.score)}</div>
          <ScoreBar score={explanation.score} threshold={explanation.threshold} />
          <p className="summary section-gap">{explanation.summary}</p>
          <Contributions contributions={explanation.contributions} limit={3} />
          <p className="section-gap"><Link className="text-link" to={`/employees/${nomination.employee.id}`}>Full explanation, what-if and tips <ArrowRight size={16} aria-hidden="true" /></Link></p>
        </Card>
      </div>

      {pending && onHold ? null : pending ? (
        <form className="card" onSubmit={(e) => withWorking(() => submit(e))} aria-labelledby="decision-title">
          <h2 id="decision-title">Your decision</h2>
          <p className="muted">The model only advises. Your decision is final and is recorded in the decision log with the model's score.</p>
          {error && <Callout tone="error">{error}</Callout>}
          <div className="choices" role="radiogroup" aria-label="Decision">
            <label className="check"><input type="radio" name="decision" value="approve" checked={decision === "approve"} onChange={() => setDecision("approve")} /> Approve the promotion</label>
            <label className="check"><input type="radio" name="decision" value="reject" checked={decision === "reject"} onChange={() => setDecision("reject")} /> Reject the promotion</label>
          </div>
          {disagrees && (
            <Callout>
              This differs from the model, which {explanation.recommended ? "recommends" : "doesn't recommend"} promotion.
              That's allowed, but please explain why, in at least {MIN_REASON} characters.
            </Callout>
          )}
          <label className="field"><span>Reason {disagrees ? <span className="muted">(required, {reason.trim().length}/{MIN_REASON} characters)</span> : <span className="muted">(optional)</span>}</span>
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
                <label className="field"><span>Why go outside the policy? <span className="muted">(required, {raiseReason.trim().length}/{MIN_REASON} characters)</span></span>
                  <textarea rows={2} value={raiseReason} onChange={(e) => setRaiseReason(e.target.value)} maxLength={2000} />
                </label>
              )}
              <p className="muted">Only the percentage is recorded, never a salary. It's never used by the model.</p>
            </div>
          )}
          <Button busy={working} busyText="Saving decision…" disabled={!decision || reasonTooShort || raiseMissing || raiseReasonTooShort}>Save decision</Button>
        </form>
      ) : nomination.decision?.decision === "approve" ? (
        <PaySignOff decision={nomination.decision} policy={policy}
          onChange={(decision) => setNomination({ ...nomination, decision })} />
      ) : (
        <Callout>This nomination has already been decided. See the <Link to="/decisions">decision log</Link>.</Callout>
      )}
    </>
  );
}
