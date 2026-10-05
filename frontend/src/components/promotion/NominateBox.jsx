// For managers, on a team member's readiness page: recommend them for promotion with stated reasons, or see that a
// recommendation is already waiting for HR.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Send } from "lucide-react";
import { api } from "../../api";
import { percent } from "../../format";
import { Button } from "../ui";
import { useAction } from "../../useAction";

const CRITERIA = [
  ["performance", "Performance", "Results and quality of work"],
  ["leadership", "Leadership", "Guiding, supporting and developing others"],
  ["skills", "Skills and knowledge", "Expertise the new role needs"],
  ["impact", "Impact", "Difference made to the team and organisation"],
];
const RATINGS = ["1 · Below expectations", "2 · Partly meets", "3 · Meets", "4 · Exceeds", "5 · Outstanding"];
const MIN_DISAGREEMENT = 20;

const inDays = (days) => new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);

export default function NominateBox({ employeeId, name }) {
  const [pending, setPending] = useState(null); // an existing pending nomination, if any
  const [modelView, setModelView] = useState(null);
  const [policy, setPolicy] = useState(null);
  const [form, setForm] = useState({
    proposed_title: "", proposed_start: inDays(30), reason: "", model_disagreement: "", proposed_raise: "",
    criteria: Object.fromEntries(CRITERIA.map(([key]) => [key, { rating: "", example: "" }])),
  });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [working, withWorking] = useAction();

  useEffect(() => {
    Promise.all([api("/promotion/nominations"), api("/promotion/employees"), api("/promotion/pay-policy")])
      .then(([list, team, pay]) => {
        setPending(list.find((n) => n.employee.id === employeeId && n.status === "pending") || false);
        const me = team.employees.find((e) => e.id === employeeId);
        setModelView(me ? { score: me.score, recommended: me.recommended, threshold: team.threshold } : null);
        setPolicy(pay);
        setForm((f) => (f.proposed_raise === "" ? { ...f, proposed_raise: String(pay.min_raise) } : f));
      })
      .catch((err) => setError(err.message));
  }, [employeeId, done]);

  if (pending === null || !policy) return error ? <p className="alert alert-error">{error}</p> : null;
  if (pending) {
    return (
      <p className="alert alert-info">
        You recommended {name} {pending.recommendation?.proposed_title ? `as ${pending.recommendation.proposed_title} ` : ""}
        on {pending.created_at.slice(0, 10)}. HR hasn't decided yet. <Link to="/nominations">See your nominations</Link>
      </p>
    );
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const setCriterion = (key, field) => (e) =>
    setForm({ ...form, criteria: { ...form.criteria, [key]: { ...form.criteria[key], [field]: e.target.value } } });
  const disagrees = modelView && !modelView.recommended;
  const raise = Number(form.proposed_raise);
  const raiseOutside = form.proposed_raise !== "" && (raise < policy.min_raise || raise > policy.max_raise);

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/promotion/nominations", { method: "POST", body: {
        employee_id: employeeId,
        proposed_title: form.proposed_title,
        proposed_start: form.proposed_start,
        criteria: Object.fromEntries(Object.entries(form.criteria).map(([k, c]) => [k, { rating: Number(c.rating), example: c.example }])),
        reason: form.reason,
        model_disagreement: disagrees ? form.model_disagreement : null,
        proposed_raise: raise,
      } });
      setDone(true);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={(e) => withWorking(() => submit(e))} className="recommend-form">
      <p className="muted">HR sees your recommendation next to the model's score and explanation, and makes the final decision.</p>
      {error && <p className="alert alert-error" role="alert">{error}</p>}

      <div className="form-row">
        <label className="field">Proposed new role<input value={form.proposed_title} onChange={set("proposed_title")} required minLength={2} maxLength={120} placeholder="e.g. Senior Analyst" /></label>
        <label className="field">Proposed start date<input type="date" value={form.proposed_start} onChange={set("proposed_start")} min={inDays(0)} max={inDays(365)} required /></label>
        <label className="field">Proposed pay rise (%)
          <input type="number" value={form.proposed_raise} onChange={set("proposed_raise")} min={policy.min_raise} max={policy.max_raise} step="0.5" required aria-invalid={raiseOutside} />
          <span className={raiseOutside ? "field-problem" : "field-hint"}>HR's policy: {policy.min_raise}% to {policy.max_raise}%. HR sets the final figure.</span>
        </label>
      </div>

      <h3 className="form-subhead">Why? Rate each area and give a real example</h3>
      <div className="criteria-grid">
        {CRITERIA.map(([key, label, help]) => (
          <fieldset key={key} className="criterion">
            <legend>{label} <span className="muted small">· {help}</span></legend>
            <select value={form.criteria[key].rating} onChange={setCriterion(key, "rating")} required aria-label={`${label} rating`}>
              <option value="">Rate…</option>
              {RATINGS.map((r, i) => <option key={r} value={i + 1}>{r}</option>)}
            </select>
            <textarea rows={2} value={form.criteria[key].example} onChange={setCriterion(key, "example")} required minLength={10} maxLength={500}
              placeholder="A specific example from this year" aria-label={`${label} example`} />
          </fieldset>
        ))}
      </div>

      {modelView && (
        <div className={`alert ${disagrees ? "alert-warning" : "alert-info"}`}>
          <span>The model gives {name} <strong>{percent(modelView.score)}</strong>, {disagrees
            ? `below the ${percent(modelView.threshold)} threshold, so it doesn't recommend promotion yet. You can still recommend them: say why you see it differently.`
            : "above the threshold, so it also recommends promotion."}</span>
        </div>
      )}
      {disagrees && (
        <label className="field"><span>Why you disagree with the model <span className="small">(required, {form.model_disagreement.trim().length}/{MIN_DISAGREEMENT} characters)</span></span>
          <textarea rows={2} value={form.model_disagreement} onChange={set("model_disagreement")} required minLength={MIN_DISAGREEMENT} maxLength={2000}
            placeholder="What do you know that the data doesn't show?" />
        </label>
      )}
      <label className="field"><span>Overall recommendation <span className="muted small">(at least 10 characters)</span></span>
        <textarea rows={3} value={form.reason} onChange={set("reason")} required minLength={10} maxLength={2000} placeholder={`Why ${name} is ready for this role`} />
      </label>
      <Button icon={Send} busy={working} busyText="Sending to HR…" disabled={raiseOutside}>Send recommendation to HR</Button>
    </form>
  );
}
