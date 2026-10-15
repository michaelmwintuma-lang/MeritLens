// Cover while a manager is away: another manager sees and may recommend their team, for the dates given. HR arranges
// it for anyone; a manager arranges it for their own team (on My team). It ends by itself after the last day.
import { useEffect, useState } from "react";
import { CalendarClock, UserCheck } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { useAction } from "../../useAction";
import { Badge, Button, Callout, Card, EmptyState } from "../ui";
import { useToast } from "../Toast";

const inDays = (days) => new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);
const STATUS = { active: ["success", "Covering now"], upcoming: ["info", "Coming up"], ended: ["neutral", "Ended"] };

export default function Cover({ onChanged }) {
  const { user } = useAuth();
  const isHr = user.role === "hr";
  const [covers, setCovers] = useState(null);
  const [managers, setManagers] = useState([]);
  const [form, setForm] = useState({ manager_user_id: "", cover_user_id: "", starts: inDays(0), ends: inDays(7), note: "" });
  const [error, setError] = useState("");
  const [saving, withSaving] = useAction();
  const toast = useToast();
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const load = () => Promise.all([api("/promotion/teams/covers"), api("/promotion/teams/managers")])
    .then(([c, m]) => { setCovers(c); setManagers(m); })
    .catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);

  async function arrange(e) {
    e.preventDefault();
    setError("");
    try {
      const made = await api("/promotion/teams/covers", { method: "POST", body: {
        manager_user_id: isHr ? Number(form.manager_user_id) : null, cover_user_id: Number(form.cover_user_id),
        starts: form.starts, ends: form.ends, note: form.note.trim() || null } });
      toast(`${made.cover} covers ${made.manager}'s team from ${made.starts} to ${made.ends}.`);
      setForm({ ...form, cover_user_id: "", note: "" });
      load();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  async function end(cover) {
    setError("");
    try {
      await api(`/promotion/teams/covers/${cover.id}/end`, { method: "POST" });
      toast("Cover ended.");
      load();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  const others = managers.filter((m) => m.user_id !== (isHr ? Number(form.manager_user_id) : user.id));
  return (
    <Card id="cover" icon={CalendarClock} title={isHr ? "Cover while a manager is away" : "Cover while you're away"}
      subtitle={isHr ? "Another manager sees and may recommend the team, for those dates only. It ends by itself."
        : "Hand your team to another manager while you're away: they see and may recommend your team, for those dates only."}>
      {error && <Callout tone="error">{error}</Callout>}
      {covers?.length > 0 ? (
        <ul className="plain-list">
          {covers.map((c) => {
            const [tone, label] = STATUS[c.status];
            return (
              <li key={c.id} className="row spread cover-row">
                <span><UserCheck size={16} aria-hidden="true" className="icon-inline" /> <strong>{c.cover}</strong> covers <strong>{c.manager}</strong>
                  <span className="muted"> · {c.starts} to {c.ends}{c.note ? ` · ${c.note}` : ""}</span></span>
                <span className="row"><Badge tone={tone}>{label}</Badge>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => end(c)}>{c.status === "upcoming" ? "Cancel" : "End now"}</button></span>
              </li>
            );
          })}
        </ul>
      ) : covers && <EmptyState compact icon={CalendarClock} title="No cover arranged" text="Covers now and coming up appear here." />}
      <form className="section-gap" onSubmit={(e) => withSaving(() => arrange(e))}>
        <div className="form-row">
          {isHr && (
            <label className="field">Manager who is away
              <select value={form.manager_user_id} onChange={set("manager_user_id")} required>
                <option value="">Choose a manager</option>
                {managers.map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name}</option>)}
              </select>
            </label>
          )}
          <label className="field">Covered by
            <select value={form.cover_user_id} onChange={set("cover_user_id")} required>
              <option value="">Choose a manager</option>
              {others.map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name}</option>)}
            </select>
          </label>
          <label className="field">From<input type="date" value={form.starts} onChange={set("starts")} min={inDays(0)} required /></label>
          <label className="field">To (inclusive)<input type="date" value={form.ends} onChange={set("ends")} min={form.starts} required /></label>
        </div>
        <label className="field"><span>Note <span className="muted">(optional)</span></span>
          <input value={form.note} onChange={set("note")} maxLength={500} placeholder="e.g. Annual leave" />
        </label>
        <Button busy={saving} busyText="Arranging…" disabled={!form.cover_user_id || (isHr && !form.manager_user_id) || others.length === 0}>Arrange cover</Button>
        {others.length === 0 && <p className="field-hint section-gap">There is no other manager to cover yet.</p>}
      </form>
    </Card>
  );
}
