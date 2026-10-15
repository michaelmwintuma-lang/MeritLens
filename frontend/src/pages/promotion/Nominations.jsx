// Nominations. Managers see the ones they made; HR sees all of them and opens a waiting one to decide.
import { useEffect, useState } from "react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Button, Callout, Card, LoadError, PageHeader, PageLoading } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { useAction } from "../../useAction";
import NominationsTable from "../../components/promotion/NominationsTable";

/** HR: the range promotion pay rises should fall in. Managers propose within it; HR can go outside with a reason. */
function PayPolicy() {
  const [policy, setPolicy] = useState(null);
  const [form, setForm] = useState({ min_raise: "", max_raise: "" });
  const [error, setError] = useState("");
  const toast = useToast();
  const [saving, withSaving] = useAction();
  useEffect(() => {
    api("/promotion/pay-policy").then((p) => { setPolicy(p); setForm({ min_raise: String(p.min_raise), max_raise: String(p.max_raise) }); })
      .catch((err) => setError(err.message));
  }, []);
  if (!policy) return error ? <Callout tone="error">{error}</Callout> : null;

  async function save(e) {
    e.preventDefault();
    setError("");
    try {
      const saved = await api("/promotion/pay-policy", { method: "PUT", body: { min_raise: Number(form.min_raise), max_raise: Number(form.max_raise) } });
      setPolicy(saved);
      toast("Pay policy saved. New recommendations must fall in this range.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card id="pay-policy" title="Promotion pay policy" subtitle="The range promotion pay rises should fall in. Managers propose within it; going outside it needs a written reason.">
      {error && <Callout tone="error">{error}</Callout>}
      <form onSubmit={(e) => withSaving(() => save(e))} className="inline-form">
        <label className="field">Lowest rise (%)<input type="number" min={0} max={100} step="0.5" value={form.min_raise} onChange={(e) => setForm({ ...form, min_raise: e.target.value })} required /></label>
        <label className="field">Highest rise (%)<input type="number" min={0} max={100} step="0.5" value={form.max_raise} onChange={(e) => setForm({ ...form, max_raise: e.target.value })} required /></label>
        <Button look="secondary" busy={saving} busyText="Saving…">Save range</Button>
      </form>
    </Card>
  );
}

export default function Nominations() {
  const { user } = useAuth();
  const isHr = user.role === "hr";
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const load = () => { setError(""); return api("/promotion/nominations").then(setList).catch((err) => setError(err.message)); };
  useEffect(() => { load(); }, []);

  return (
    <>
      <PageHeader title={isHr ? "Nominations" : "My nominations"}
        subtitle={isHr ? "Managers' recommendations, each with the model's view. Open a waiting one to decide." : "Your recommendations and where they stand. To recommend someone, open them from My team."} />
      {error && <LoadError message={error} onRetry={load} />}
      {!list && !error && <PageLoading />}
      {list && <NominationsTable nominations={list} isHr={isHr} title="Recommendations" />}
      {isHr && <PayPolicy />}
    </>
  );
}
