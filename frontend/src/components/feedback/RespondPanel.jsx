// "Respond to this explanation": the employee's three ways to answer back, on their own explanation page.
// 1. Rate it (clear? useful?) and mark factors that seem wrong or unfair.
// 2. Ask HR to correct a value in their record, with evidence.
// 3. Report an unfair assessment anonymously (the reporting pages; never linked to the account).
// None of these changes the score. Only HR confirming a correction changes the record, and that is logged.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquareText } from "lucide-react";
import { api, uploadFile } from "../../api";
import { Button, Card, LoadError, Loading, Segmented } from "../ui";
import { useAction } from "../../useAction";
import CorrectionStatus from "./CorrectionStatus";

const SCALE = [1, 2, 3, 4, 5];

/** A 1-5 answer to one statement, as a group of radio buttons. */
function Agree({ name, statement, value, onChange }) {
  return (
    <fieldset className="agree">
      <legend>{statement}</legend>
      <div className="agree-options">
        <span className="muted small" aria-hidden="true">Disagree</span>
        {SCALE.map((n) => (
          <label key={n} className="agree-option">
            <input type="radio" name={name} value={n} checked={value === n} onChange={() => onChange(n)} />
            <span>{n}</span>
          </label>
        ))}
        <span className="muted small" aria-hidden="true">Agree</span>
      </div>
    </fieldset>
  );
}

function RateExplanation({ contributions }) {
  const [clarity, setClarity] = useState(null);
  const [usefulness, setUsefulness] = useState(null);
  const [marks, setMarks] = useState({}); // feature -> "wrong" | "unfair"
  const [comment, setComment] = useState("");
  const [done, setDone] = useState("");
  const [error, setError] = useState("");
  const [saving, withSaving] = useAction();

  // An earlier rating of this model's explanation is shown, so it can be changed
  useEffect(() => {
    api("/feedback/ratings/mine").then(({ rating }) => {
      if (!rating) return;
      setClarity(rating.clarity);
      setUsefulness(rating.usefulness);
      setMarks(Object.fromEntries(rating.flagged.map((f) => [f.feature, f.kind])));
      setComment(rating.comment || "");
      setDone(`You rated this explanation on ${rating.created_at.slice(0, 10)}. You can change your answers.`);
    }).catch(() => {});
  }, []);

  async function save(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/feedback/ratings", { method: "POST", body: {
        clarity, usefulness, comment: comment.trim() || null,
        flagged: Object.entries(marks).filter(([, kind]) => kind).map(([feature, kind]) => ({ feature, kind })) } });
      setDone("Thank you. Your rating is saved. It doesn't change your score; HR sees ratings only added together, never yours alone, and your manager never sees them.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={(e) => withSaving(() => save(e))}>
      {done && <p className="alert alert-success" role="status">{done}</p>}
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      <Agree name="clarity" statement="This explanation was clear" value={clarity} onChange={setClarity} />
      <Agree name="usefulness" statement="This explanation was useful" value={usefulness} onChange={setUsefulness} />
      <details className="details">
        <summary>Does any factor seem wrong or unfair? (optional)</summary>
        <div className="table-wrap"><table>
          <thead><tr><th>Factor</th><th>Your value</th><th>Your view</th></tr></thead>
          <tbody>
            {contributions.map((c) => (
              <tr key={c.feature}>
                <td>{c.label}</td>
                <td>{c.value_display}</td>
                <td>
                  <select aria-label={`Your view of ${c.label}`} value={marks[c.feature] || ""}
                    onChange={(e) => setMarks({ ...marks, [c.feature]: e.target.value })}>
                    <option value="">Seems fine</option>
                    <option value="wrong">Seems wrong</option>
                    <option value="unfair">Seems unfair</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
        <p className="muted small">If a value in your record is wrong, you can also ask HR to correct it (the next tab).</p>
      </details>
      <label className="field">Anything else? (optional)
        <textarea rows={2} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
      </label>
      <Button busy={saving} busyText="Saving…" disabled={!clarity || !usefulness}>Save my rating</Button>
    </form>
  );
}

function RequestCorrection() {
  const [fields, setFields] = useState(null);
  const [requests, setRequests] = useState([]);
  const [field, setField] = useState("");
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");
  const [file, setFile] = useState(null);
  const [done, setDone] = useState("");
  const [error, setError] = useState("");
  const [sending, withSending] = useAction();

  const load = () => Promise.all([api("/feedback/fields"), api("/feedback/corrections/mine")])
    .then(([f, r]) => { setFields(f); setRequests(r); })
    .catch((err) => setError(err.message));
  useEffect(() => {
    load();
    api("/feedback/notifications/seen", { method: "POST" }).catch(() => {}); // the outcomes are shown below
  }, []);

  const chosen = fields?.find((f) => f.name === field);

  async function send(e) {
    e.preventDefault();
    setError("");
    try {
      const request = await api("/feedback/corrections", { method: "POST", body: { field, requested_value: Number(value), note: note.trim() } });
      if (file) await uploadFile(`/feedback/corrections/${request.id}/evidence`, {}, file);
      setDone(`Sent. HR will check your evidence; nothing changes in your record until they confirm it. You'll get an email and a notification with the outcome.`);
      setField(""); setValue(""); setNote(""); setFile(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!fields) return error ? <LoadError message={error} onRetry={load} /> : <Loading />;
  return (
    <>
      <form onSubmit={(e) => withSending(() => send(e))}>
        {done && <p className="alert alert-success" role="status">{done}</p>}
        {error && <p className="alert alert-error" role="alert">{error}</p>}
        <p className="muted">Pick a value from your work record that you believe is wrong. Only values from your record can be corrected.</p>
        <div className="form-row">
          <label className="field">Value to correct
            <select value={field} onChange={(e) => { setField(e.target.value); setValue(""); }} required>
              <option value="">Choose a value</option>
              {fields.map((f) => (
                <option key={f.name} value={f.name} disabled={f.pending}>
                  {f.label}: {f.current}{f.percent ? "%" : ""}{f.pending ? " (already waiting for HR)" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="field">The correct value{chosen?.percent ? " (%)" : ""}
            <input type="number" value={value} onChange={(e) => setValue(e.target.value)} required disabled={!chosen}
              min={chosen?.min} max={chosen?.max} step={chosen?.whole ? 1 : "any"} inputMode="decimal" />
            {chosen && <span className="field-hint">Your record says {chosen.current}{chosen.percent ? "%" : ""}.</span>}
          </label>
        </div>
        <label className="field"><span>Your evidence, in words <span className="small">(at least 10 characters)</span></span>
          <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} minLength={10} maxLength={2000} required
            placeholder="e.g. My signed review form from March lists 9 completed projects." />
        </label>
        <label className="field">A document (optional: PDF, JPEG or PNG, up to 10 MB)
          <input type="file" accept="application/pdf,image/jpeg,image/png" onChange={(e) => setFile(e.target.files[0] || null)} />
        </label>
        <Button busy={sending} busyText="Sending to HR…" disabled={!field || value === "" || note.trim().length < 10}>Send to HR</Button>
      </form>

      {requests.length > 0 && (
        <>
          <h3 style={{ marginTop: 24 }}>Your requests</h3>
          <div className="table-wrap"><table>
            <thead><tr><th>Sent</th><th>Value</th><th>Asked for</th><th>Outcome</th></tr></thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td className="nowrap">{r.created_at.slice(0, 10)}</td>
                  <td>{r.label}<div className="muted small">was {r.current_display}</div></td>
                  <td>{r.source === "reappraisal" ? <span className="muted">HR re-appraisal</span> : r.requested_display}</td>
                  <td><CorrectionStatus request={r} />
                    {r.status === "confirmed" && <div className="small">Corrected to <strong>{r.verified_display}</strong></div>}
                    {r.status === "rejected" && <div className="small">HR's reason: {r.decision_reason}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </>
      )}
    </>
  );
}

function ReportUnfair() {
  return (
    <>
      <p>
        If you believe your assessment was unfair (a biased rating, favouritism, discrimination, or a record that's
        wrong or missing), you can report it <strong>anonymously</strong>. Names and details are removed before
        anything is sent, and the report is never linked to your account or to this page.
      </p>
      <p className="muted small">HR may open a re-appraisal if they find a rating was unfair. Your report itself never reaches the model.</p>
      <div className="row">
        <Link className="btn btn-accent" to="/report" state={{ category: "biased_rating" }}>Report an unfair assessment</Link>
        <Link className="btn btn-plain" to="/my-report">Follow up a report</Link>
      </div>
    </>
  );
}

const TABS = [
  { value: "rate", label: "Rate this explanation" },
  { value: "correct", label: "Correct my record" },
  { value: "report", label: "Report anonymously" },
];

export default function RespondPanel({ contributions }) {
  const [tab, setTab] = useState("rate");
  return (
    <Card title="Respond to this explanation" actions={<MessageSquareText size={20} className="feedback-icon" aria-hidden="true" />}
      subtitle="Tell us whether it helped, ask HR to fix a wrong value, or raise a concern anonymously. None of this changes your score.">
      <Segmented label="How to respond" options={TABS} value={tab} onChange={setTab} />
      <div className="respond-body">
        {tab === "rate" && <RateExplanation contributions={contributions} />}
        {tab === "correct" && <RequestCorrection />}
        {tab === "report" && <ReportUnfair />}
      </div>
    </Card>
  );
}
