// Admin: choose which employees a manager manages. A manager sees and can nominate only these people.
import { useState } from "react";
import { api } from "../../api";
import { Button } from "../ui";
import { useAction } from "../../useAction";

export default function TeamEditor({ manager, employees, managers, onSaved, onClose }) {
  const [chosen, setChosen] = useState(() => new Set(employees.filter((e) => e.manager_user_id === manager.id).map((e) => e.id)));
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const managerName = Object.fromEntries(managers.map((m) => [m.id, m.full_name]));

  const toggle = (id) => {
    const next = new Set(chosen);
    if (next.has(id)) next.delete(id); else next.add(id);
    setChosen(next);
  };
  const shown = employees
    .filter((e) => `${e.full_name} ${e.department} ${e.id}`.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => Number(chosen.has(b.id)) - Number(chosen.has(a.id)) || a.full_name.localeCompare(b.full_name));

  const [working, withWorking] = useAction();

  async function save() {
    setError("");
    try {
      await api(`/admin/users/${manager.id}/team`, { method: "PUT", body: { employee_ids: [...chosen] } });
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="card">
      <h2>Team for {manager.full_name}</h2>
      <p className="muted">Tick the people this manager manages. They will see these people's readiness and can nominate them. Unticking someone leaves them without a manager.</p>
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      <div className="row spread">
        <input placeholder="Search name, department or number" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search employees" />
        <span className="muted">{chosen.size} selected</span>
      </div>
      <div className="picklist">
        {shown.map((e) => (
          <label key={e.id} className="check">
            <input type="checkbox" checked={chosen.has(e.id)} onChange={() => toggle(e.id)} />
            <span>{e.full_name} <span className="muted small">· {e.department} · no. {e.id}
              {e.manager_user_id && e.manager_user_id !== manager.id && ` · now managed by ${managerName[e.manager_user_id] || "another manager"}`}</span></span>
          </label>
        ))}
      </div>
      <div className="row">
        <Button busy={working} busyText="Saving team…" onClick={() => withWorking(save)}>Save team ({chosen.size})</Button>
        <button className="btn btn-plain" onClick={onClose}>Cancel</button>
      </div>
    </div>
  );
}
