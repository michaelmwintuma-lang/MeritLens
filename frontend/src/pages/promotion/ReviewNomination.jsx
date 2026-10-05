// HR reviews one nomination: the manager's reason, the model's score and explanation, then decides.
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api";
import { percent } from "../../format";
import ScoreBar, { Verdict } from "../../components/promotion/ScoreBar";
import Contributions from "../../components/promotion/Contributions";
import { NominationStatus } from "../../components/promotion/Status";
import { ArrowLeft, ClipboardCheck } from "lucide-react";
import { Button, PageHeader } from "../../components/ui";
import { useAction } from "../../useAction";

const MIN_REASON = 20;

export default function ReviewNomination() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [nomination, setNomination] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [decision, setDecision] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/promotion/nominations/${id}`)
      .then((n) => {
        setNomination(n);
        return api(`/promotion/employees/${n.employee.id}`).then(setExplanation);
      })
      .catch((err) => setError(err.message));
  }, [id]);

  if (error && !nomination) return <p className="alert alert-error">{error}</p>;
  if (!nomination || !explanation) return <p className="muted">Loading…</p>;

  // Disagreeing = approving someone the model doesn't recommend, or rejecting someone it does
  const disagrees = decision && (decision === "approve") !== explanation.recommended;
  const reasonTooShort = disagrees && reason.trim().length < MIN_REASON;

  const [working, withWorking] = useAction();

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api(`/promotion/nominations/${id}/decision`, { method: "POST", body: { decision, reason: reason.trim() || null } });
      navigate("/decisions");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <Link to="/nominations" className="back"><ArrowLeft size={16} />Back to nominations</Link>
      <PageHeader icon={ClipboardCheck} title={`Review: ${nomination.employee.full_name}`}
        subtitle={`${nomination.employee.department} · nominated by ${nomination.nominated_by} on ${nomination.created_at.slice(0, 10)}`}
        actions={<NominationStatus status={nomination.status} />} />

      <section className="card">
        <h2>The manager's reason</h2>
        <blockquote className="quote">{nomination.reason}</blockquote>
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

      {nomination.status === "pending" ? (
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
          <label className="field">Reason {disagrees ? <span className="small">(required, {reason.trim().length}/{MIN_REASON} characters)</span> : <span className="muted small">(optional)</span>}
            <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={2000} />
          </label>
          <Button busy={working} busyText="Saving decision…" disabled={!decision || reasonTooShort}>Save decision</Button>
        </form>
      ) : (
        <p className="alert alert-info">This nomination has already been decided. See the decision log.</p>
      )}
    </>
  );
}
