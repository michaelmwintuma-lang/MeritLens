// On a case HR closed as "Rating found unfair": open a re-appraisal of the affected value. It becomes a normal
// record correction in the queue. The case ID is checked but never stored with it, so they can't be linked, and
// the report itself never reaches the model.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { Button, Card } from "../ui";
import { useAction } from "../../useAction";

export default function Reappraisal({ caseId }) {
  const [people, setPeople] = useState(null);
  const [fields, setFields] = useState([]);
  const [form, setForm] = useState({ employee_id: "", field: "", requested_value: "", note: "" });
  const [done, setDone] = useState(null);
  const [error, setError] = useState("");
  const [sending, withSending] = useAction();

  useEffect(() => {
    Promise.all([api("/promotion/employees"), api("/promotion/records/fields")])
      .then(([p, f]) => { setPeople(p.employees); setFields(f.fields); })
      .catch((err) => setError(err.message));
  }, []);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const chosen = fields.find((f) => f.name === form.field);

  async function send(e) {
    e.preventDefault();
    setError("");
    try {
      setDone(await api("/hr/feedback/reappraisals", { method: "POST", body: {
        case_id: caseId, employee_id: Number(form.employee_id), field: form.field,
        requested_value: Number(form.requested_value), note: form.note.trim() } }));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card title="Re-appraisal" subtitle="This case was closed as “Rating found unfair”. Open a correction of the affected value; it goes to the correction queue like any other. It is not linked to this case, and the report never reaches the model.">
      {done ? (
        <p className="alert alert-success" role="status">
          A correction of {done.employee_name}'s {done.label.toLowerCase()} is waiting in the <Link to="/corrections">correction queue</Link>.
        </p>
      ) : !people ? (error ? <p className="alert alert-error">{error}</p> : <p className="muted">Loading…</p>) : (
        <form onSubmit={(e) => withSending(() => send(e))}>
          {error && <p className="alert alert-error" role="alert">{error}</p>}
          <div className="form-row">
            <label className="field">Employee
              <select value={form.employee_id} onChange={set("employee_id")} required>
                <option value="">Choose who was assessed</option>
                {people.map((p) => <option key={p.id} value={p.id}>{p.full_name} ({p.department})</option>)}
              </select>
            </label>
            <label className="field">Value to re-appraise
              <select value={form.field} onChange={set("field")} required>
                <option value="">Choose a value</option>
                {fields.map((f) => <option key={f.name} value={f.name}>{f.label}</option>)}
              </select>
            </label>
            <label className="field">Proposed value{chosen?.percent ? " (%)" : ""}
              <input type="number" step={chosen?.whole ? 1 : "any"} min={chosen?.min} max={chosen?.max}
                value={form.requested_value} onChange={set("requested_value")} required />
            </label>
          </div>
          <label className="field"><span>Why <span className="small">(at least 10 characters; don't quote the report)</span></span>
            <textarea rows={2} maxLength={2000} value={form.note} onChange={set("note")} required minLength={10} />
          </label>
          <Button busy={sending} busyText="Opening…" disabled={!form.employee_id || !form.field || form.requested_value === "" || form.note.trim().length < 10}>
            Open the re-appraisal
          </Button>
        </form>
      )}
    </Card>
  );
}
