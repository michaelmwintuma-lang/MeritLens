// Nominations. Managers see the ones they made; HR sees all of them and opens a waiting one to decide.
import { useEffect, useState } from "react";
import { ClipboardCheck } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Button, Card, PageHeader } from "../../components/ui";
import { useAction } from "../../useAction";
import NominationsTable from "../../components/promotion/NominationsTable";

/** HR: the range promotion pay rises should fall in. Managers propose within it; HR can go outside with a reason. */
function PayPolicy() {
  const [policy, setPolicy] = useState(null);
  const [form, setForm] = useState({ min_raise: "", max_raise: "" });
  const [message, setMessage] = useState({ text: "", ok: true });
  const [saving, withSaving] = useAction();
  useEffect(() => {
    api("/promotion/pay-policy").then((p) => { setPolicy(p); setForm({ min_raise: String(p.min_raise), max_raise: String(p.max_raise) }); })
      .catch((err) => setMessage({ text: err.message, ok: false }));
  }, []);
  if (!policy) return null;

  async function save(e) {
    e.preventDefault();
    try {
      const saved = await api("/promotion/pay-policy", { method: "PUT", body: { min_raise: Number(form.min_raise), max_raise: Number(form.max_raise) } });
      setPolicy(saved);
      setMessage({ text: "Saved. New recommendations must fall in this range.", ok: true });
    } catch (err) {
      setMessage({ text: err.message, ok: false });
    }
  }

  return (
    <Card title="Promotion pay policy" subtitle="Managers propose within this range. Going outside it needs a written reason.">
      <form onSubmit={(e) => withSaving(() => save(e))} className="row" style={{ alignItems: "flex-end", gap: 14 }}>
        <label className="field" style={{ marginBottom: 0 }}>Lowest rise (%)<input type="number" min={0} max={100} step="0.5" value={form.min_raise} onChange={(e) => setForm({ ...form, min_raise: e.target.value })} required /></label>
        <label className="field" style={{ marginBottom: 0 }}>Highest rise (%)<input type="number" min={0} max={100} step="0.5" value={form.max_raise} onChange={(e) => setForm({ ...form, max_raise: e.target.value })} required /></label>
        <Button look="plain" busy={saving} busyText="Saving…">Save range</Button>
      </form>
      {message.text && <p className={`alert ${message.ok ? "alert-success" : "alert-error"}`} role="status" style={{ marginTop: 14 }}>{message.text}</p>}
    </Card>
  );
}

export default function Nominations() {
  const { user } = useAuth();
  const isHr = user.role === "hr";
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/promotion/nominations").then(setList).catch((err) => setError(err.message)); }, []);

  return (
    <>
      <PageHeader icon={ClipboardCheck} title={isHr ? "Nominations" : "My nominations"}
        subtitle={isHr ? undefined : "To recommend someone, open them from My team."} />
      {error && <p className="alert alert-error">{error}</p>}
      {!list && !error && <p className="muted">Loading…</p>}
      {list && <NominationsTable nominations={list} isHr={isHr} title="Recommendations" />}
      {isHr && <PayPolicy />}
    </>
  );
}
