// Admin: every account, in two tabs kept apart:
// - Administration: Admin and HR accounts. Not linked to employee records. Admins can be allowed to view employee
//   data (read-only).
// - Employees: Employee and Manager accounts, linked to an employee record; managers get a team.
// In both: create accounts (a welcome email goes out), edit, reset passwords and deactivate.
import { useEffect, useState } from "react";
import { Eye, EyeOff, Mail, Pencil, Trash2, UserCog } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { ROLE_DESCRIPTIONS, ROLE_NAMES } from "../../roles";
import TeamEditor from "../../components/admin/TeamEditor";
import { Button, Card, PageHeader, Segmented } from "../../components/ui";
import { useAction } from "../../useAction";

const TABS = {
  staff: { label: "Administration", roles: ["admin", "hr", "finance"], note: "Admin, HR and Finance accounts. They aren't linked to an employee record." },
  people: { label: "Employees", roles: ["employee", "manager"], note: "Employee and Manager accounts, each linked to their employee record." },
};
const emptyForm = (role) => ({ username: "", full_name: "", email: "", role, job_title: "", employee_id: "" });

/** After creating an account or resetting a password: the details, and what happened to the email. */
function SentDetails({ result, onDone }) {
  return (
    <div className={`alert ${result.email_sent ? "alert-success" : "alert-warning"}`}>
      <strong><Mail size={16} style={{ verticalAlign: "-3px" }} /> {result.email_sent ? "Welcome email sent" : "Email not sent"}</strong>
      <span>{result.email_detail}</span>
      <div className="mono" style={{ margin: "6px 0" }}>Username: {result.user.username}<br />Temporary password: {result.temporary_password}</div>
      <span className="small">
        {result.email_sent ? "You don't need to pass these on yourself. " : "Give these details to the person yourself. "}
        The password is shown only now: it is stored only as a hash. They will choose their own at first sign-in.
      </span>
      <button className="btn btn-plain" onClick={onDone}>Done</button>
    </div>
  );
}

/** Edit an account's username, name and email, in place. */
function EditRow({ account, onSaved, onCancel }) {
  const [form, setForm] = useState({ username: account.username, full_name: account.full_name, email: account.email || "", job_title: account.job_title || "" });
  const [error, setError] = useState("");
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const [working, withWorking] = useAction();

  async function save(e) {
    e.preventDefault();
    setError("");
    try {
      await api(`/admin/users/${account.id}`, { method: "PATCH", body: { ...form, email: form.email || null } });
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <tr>
      <td colSpan={5}>
        <form onSubmit={(e) => withWorking(() => save(e))} className="edit-row">
          <label className="field">Full name<input value={form.full_name} onChange={set("full_name")} required minLength={2} /></label>
          <label className="field">Username<input value={form.username} onChange={set("username")} required minLength={2} pattern="[a-zA-Z0-9._\-]+" /></label>
          <label className="field">Email<input type="email" value={form.email} onChange={set("email")} /></label>
          <label className="field">Job title<input value={form.job_title} onChange={set("job_title")} maxLength={120} /></label>
          <div className="row">
            <Button busy={working} busyText="Saving…">Save</Button>
            <button type="button" className="btn btn-plain" onClick={onCancel}>Cancel</button>
          </div>
          {error && <p className="alert alert-error" role="alert" style={{ gridColumn: "1 / -1" }}>{error}</p>}
        </form>
      </td>
    </tr>
  );
}

export default function Users() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [tab, setTab] = useState("people");
  const [form, setForm] = useState(emptyForm("employee"));
  const [error, setError] = useState("");
  const [sent, setSent] = useState(null);       // details of the account just created or reset, shown once
  const [employees, setEmployees] = useState([]);
  const [teamFor, setTeamFor] = useState(null); // the manager whose team is being edited
  const [editing, setEditing] = useState(null); // the account being edited

  const load = () => Promise.all([api("/admin/users"), api("/admin/employees")])
    .then(([u, e]) => { setUsers(u); setEmployees(e); })
    .catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const [busyKey, setBusyKey] = useState(null); // which button's action is running

  async function act(request, key) {
    setError("");
    setBusyKey(key);
    try {
      return await request();
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusyKey(null);
    }
  }

  async function create(e) {
    e.preventDefault();
    const body = { ...form, employee_id: tab === "people" && form.employee_id ? Number(form.employee_id) : null };
    const result = await act(() => api("/admin/users", { method: "POST", body }), "create");
    if (result) { setSent(result); setForm(emptyForm(form.role)); load(); }
  }

  async function resetPassword(u) {
    if (!window.confirm(`Give ${u.full_name} a new temporary password? Their current password stops working.`)) return;
    const result = await act(() => api(`/admin/users/${u.id}/reset-password`, { method: "POST" }), `reset-${u.id}`);
    if (result) { setSent(result); load(); }
  }

  function switchTab(next) {
    setTab(next);
    setForm(emptyForm(TABS[next].roles[0]));
    setEditing(null);
  }

  async function togglePermission(u) {
    const giving = !u.can_view_employees;
    if (giving && !window.confirm(`Let ${u.full_name} view every employee's record and readiness score (read-only)? They still can't see reports, nominate or decide. This is recorded in the activity log.`)) return;
    if (await act(() => api(`/admin/users/${u.id}/permissions`, { method: "PATCH", body: { can_view_employees: giving } }), `perm-${u.id}`)) load();
  }

  async function remove(u) {
    if (!window.confirm(`Delete ${u.full_name}'s account (${u.username}) for good? This can't be undone. `
      + "If you only want to stop them signing in, choose Deactivate instead.")) return;
    if (await act(() => api(`/admin/users/${u.id}`, { method: "DELETE" }), `delete-${u.id}`)) load();
  }

  async function toggleActive(u) {
    if (await act(() => api(`/admin/users/${u.id}/active`, { method: "PATCH", body: { is_active: !u.is_active } }), `active-${u.id}`)) load();
  }

  return (
    <>
      <PageHeader icon={UserCog} title="Users"
        subtitle="New users get a temporary password by email."
        actions={<Segmented label="Account type" value={tab} onChange={switchTab} options={Object.entries(TABS).map(([value, t]) => (
          { value, label: `${t.label} (${users.filter((u) => t.roles.includes(u.role)).length})` }))} />} />
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      {sent && <SentDetails result={sent} onDone={() => setSent(null)} />}

      <Card title={`Create ${tab === "staff" ? "an administration" : "an employee"} account`} subtitle={`${TABS[tab].note} The welcome email goes to the address you enter, with the username and a temporary password.`}>
        <form onSubmit={create}>
          <div className="form-row">
            <label className="field">Full name<input value={form.full_name} onChange={set("full_name")} required minLength={2} /></label>
            <label className="field">Email<input type="email" value={form.email} onChange={set("email")} required /></label>
            <label className="field">Username<input value={form.username} onChange={set("username")} required minLength={2} pattern="[a-zA-Z0-9._\-]+" title="Letters, numbers, dots, dashes and underscores" /></label>
            <label className="field">Job title<input value={form.job_title} onChange={set("job_title")} maxLength={120} placeholder={tab === "staff" ? "e.g. HR Business Partner" : "e.g. Operations Analyst"} /></label>
            <label className="field">Role
              <select value={form.role} onChange={set("role")}>
                {TABS[tab].roles.map((value) => <option key={value} value={value}>{ROLE_NAMES[value]}</option>)}
              </select>
            </label>
            {tab === "people" && <label className="field">Employee record
              <select value={form.employee_id} onChange={set("employee_id")}>
                <option value="">Not linked</option>
                {employees.filter((e) => !e.login).map((e) => <option key={e.id} value={e.id}>{e.full_name} · {e.department} · no. {e.id}</option>)}
              </select>
              <span className="muted small" style={{ fontWeight: 400 }}>{form.role === "employee" ? "Needed, so they see their own readiness" : "Optional"}</span>
            </label>}
          </div>
          <p className="muted small">{ROLE_NAMES[form.role]}: {ROLE_DESCRIPTIONS[form.role]}</p>
          <Button icon={Mail} busy={busyKey === "create"} busyText="Creating account and sending email…">Create account and send welcome email</Button>
        </form>
      </Card>

      {teamFor && (
        <TeamEditor manager={teamFor} employees={employees} managers={users.filter((u) => u.role === "manager")}
          onSaved={() => { setTeamFor(null); load(); }} onClose={() => setTeamFor(null)} />
      )}

      <Card flush title={`${TABS[tab].label} accounts`} subtitle={tab === "staff"
        ? undefined
        : "Managers are emailed when people join their team."}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Status</th><th style={{ textAlign: "right" }}>Actions</th></tr></thead>
            <tbody>
              {users.filter((u) => TABS[tab].roles.includes(u.role)).map((u) => editing === u.id ? (
                <EditRow key={u.id} account={u} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />
              ) : (
                <tr key={u.id}>
                  <td><span className="strong">{u.full_name}</span>{u.id === me.id && <span className="muted"> (you)</span>}<div className="muted small">{u.job_title ? `${u.job_title} · ` : ""}{u.email || "no email"}</div></td>
                  <td className="mono">{u.username}</td>
                  <td><span className="tag">{ROLE_NAMES[u.role]}</span>
                    {u.role === "admin" && u.can_view_employees && <div className="muted small"><Eye size={12} style={{ verticalAlign: "-1px" }} /> may view employee data</div>}
                    {u.employee_id && <div className="muted small">employee no. {u.employee_id}</div>}</td>
                  <td>{u.is_active ? "Active" : <span className="tag tag-off">Deactivated</span>}{u.must_change_password && <div className="muted small">must choose a password</div>}</td>
                  <td><div className="actions">
                    <button className="btn btn-plain" onClick={() => setEditing(u.id)}><Pencil size={14} />Edit</button>
                    {u.role === "manager" && (
                      <button className="btn btn-plain" onClick={() => setTeamFor(u)}>Team ({employees.filter((e) => e.manager_user_id === u.id).length})</button>
                    )}
                    {u.role === "admin" && (
                      <Button look="plain" icon={u.can_view_employees ? EyeOff : Eye} busy={busyKey === `perm-${u.id}`} busyText="Saving…" onClick={() => togglePermission(u)}>
                        {u.can_view_employees ? "Remove employee data" : "Allow employee data"}
                      </Button>
                    )}
                    <Button look="plain" busy={busyKey === `reset-${u.id}`} busyText="Resetting…" onClick={() => resetPassword(u)}>Reset password</Button>
                    {u.id !== me.id && <Button look="plain" busy={busyKey === `active-${u.id}`} busyText="Saving…" onClick={() => toggleActive(u)}>{u.is_active ? "Deactivate" : "Reactivate"}</Button>}
                    {u.id !== me.id && <Button look="plain" className="btn-danger" icon={Trash2} busy={busyKey === `delete-${u.id}`} busyText="Deleting…" onClick={() => remove(u)}>Delete</Button>}
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
