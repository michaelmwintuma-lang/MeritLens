// HR: add a new employee, or edit an employee's details (e.g. after a new review). Values are typed the way they
// appear in HR's own records; the server checks them and turns them into the model's inputs.
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Save, UserPlus } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { Button, Card, LoadError, Loading, PageHeader } from "../../components/ui";

const GROUP_NOTES = {
  Performance: "From this year's review and KPI tracking.",
  Development: "Training, certifications and mentoring over the last year.",
  Reliability: "From time and attendance records.",
  Career: "From HR's records. These aren't things the person can change by effort.",
};

export default function EmployeeForm() {
  const { id } = useParams();
  const editing = Boolean(id);
  const navigate = useNavigate();
  const [setup, setSetup] = useState(null);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [problems, setProblems] = useState({});
  const [saving, withSaving] = useAction();

  useEffect(() => {
    Promise.all([api("/promotion/records/fields"), editing ? api(`/promotion/records/${id}`) : null])
      .then(([fields, existing]) => {
        setSetup(fields);
        setForm(existing
          ? { ...existing, manager_user_id: existing.manager_user_id ?? "", values: Object.fromEntries(Object.entries(existing.values).map(([k, v]) => [k, String(v)])) }
          : { full_name: "", department: "", manager_user_id: "", values: {} });
      })
      .catch((err) => setError(err.message));
  }, [id, editing]);

  if (error && !setup) return <><PageHeader icon={UserPlus} title="Employee details" /><LoadError message={error} /></>;
  if (!setup || !form) return <Loading />;

  const setValue = (name) => (e) => setForm({ ...form, values: { ...form.values, [name]: e.target.value } });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function save(e) {
    e.preventDefault();
    setError("");
    setProblems({});
    const body = { ...form, manager_user_id: form.manager_user_id ? Number(form.manager_user_id) : null };
    try {
      const res = await api(editing ? `/promotion/records/${id}` : "/promotion/records", { method: editing ? "PUT" : "POST", body });
      navigate(`/employees/${res.id}`, { state: { saved: editing ? "updated" : "added", warnings: Object.values(res.warnings) } });
    } catch (err) {
      setError(err.message);
      setProblems(err.fields || {});
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  const change = Number(form.values.performance_score) - Number(form.values.performance_last_year);
  const showChange = form.values.performance_score !== undefined && form.values.performance_last_year !== undefined
    && form.values.performance_score !== "" && form.values.performance_last_year !== "" && !Number.isNaN(change);

  return (
    <>
      <Link to={editing ? `/employees/${id}` : "/employees"} className="back"><ArrowLeft size={16} />{editing ? "Back to their readiness" : "Back to all employees"}</Link>
      <PageHeader icon={UserPlus} title={editing ? `Edit ${form.full_name}` : "Add an employee"}
        subtitle={editing ? "Past decisions keep the score they were made with." : undefined} />
      {error && <div className="alert alert-error" role="alert">{error}</div>}

      <form onSubmit={(e) => withSaving(() => save(e))} noValidate>
        <Card title="Who they are" subtitle="Gender, age, education and pay are never asked for: the model doesn't use them.">
          <div className="form-row">
            <Field label="Full name" problem={problems.full_name}>
              <input value={form.full_name} onChange={set("full_name")} required maxLength={120} />
            </Field>
            <Field label="Department" problem={problems.department}>
              <select value={form.department} onChange={set("department")} required>
                <option value="">Choose…</option>
                {setup.departments.map((d) => <option key={d}>{d}</option>)}
              </select>
            </Field>
            <Field label="Manager" hint="Optional. Their manager sees them on My team." problem={problems.manager_user_id}>
              <select value={form.manager_user_id} onChange={set("manager_user_id")}>
                <option value="">No manager yet</option>
                {setup.managers.map((m) => <option key={m.id} value={m.id}>{m.full_name}</option>)}
              </select>
            </Field>
          </div>
        </Card>

        {setup.groups.map((group) => (
          <Card key={group} title={group} subtitle={GROUP_NOTES[group]}>
            <div className="form-row">
              {setup.fields.filter((f) => f.group === group).map((f) => (
                <NumberField key={f.name} field={f} value={form.values[f.name] ?? ""} onChange={setValue(f.name)} problem={problems[f.name]}
                  extra={f.name === "performance_last_year" && showChange
                    ? `Change since last year: ${change >= 0 ? "+" : ""}${change.toFixed(1)} points` : null} />
              ))}
            </div>
          </Card>
        ))}

        {editing && (
          <Card title="Why are you changing this record?" subtitle="Optional. Kept in the record's history, with the readiness score before and after.">
            <label className="field">Reason
              <textarea rows={2} maxLength={1000} value={form.reason || ""} onChange={set("reason")}
                placeholder="e.g. Two projects were missing from this year's review" />
            </label>
          </Card>
        )}

        <div className="row" style={{ gap: 10 }}>
          <Button icon={Save} busy={saving} busyText="Checking and saving…">{editing ? "Save changes" : "Add employee"}</Button>
          <Link to={editing ? `/employees/${id}` : "/employees"} className="btn btn-plain">Cancel</Link>
        </div>
      </form>
    </>
  );
}

function Field({ label, hint, problem, extra, children }) {
  return (
    <label className="field">
      {label}
      {children}
      {problem ? <span className="field-problem" role="alert">{problem}</span> : hint && <span className="field-hint">{hint}</span>}
      {extra && <span className="field-hint">{extra}</span>}
    </label>
  );
}

/** A number box that says what's possible and what's typical, and flags unusual values as they're typed. */
function NumberField({ field, value, onChange, problem, extra }) {
  const unit = field.percent ? "%" : "";
  const number = Number(value);
  const unusual = value !== "" && field.typical && !Number.isNaN(number) && (number < field.typical[0] || number > field.typical[1]);
  const hint = unusual
    ? `Unusual: the model saw ${field.typical[0]}–${field.typical[1]}${unit}, so the score will be less reliable.`
    : `${field.min}–${field.max}${unit}${field.whole ? ", whole number" : ""}${field.typical ? ` · typical ${field.typical[0]}–${field.typical[1]}${unit}` : ""}`;
  return (
    <label className="field">
      {field.label}{unit && ` (${unit})`}
      <input type="number" inputMode="decimal" value={value} onChange={onChange} min={field.min} max={field.max}
        step={field.whole ? 1 : "any"} placeholder={`e.g. ${field.example}`} aria-invalid={Boolean(problem)} />
      {problem ? <span className="field-problem" role="alert">{problem}</span>
        : <span className={unusual ? "field-hint field-unusual" : "field-hint"}>{hint}</span>}
      {extra && <span className="field-hint">{extra}</span>}
    </label>
  );
}
