// HR, on an employee's page: erase the personal data of someone who has left. Their name, record, ratings, correction
// requests and equality-monitoring answers are removed; past decisions stay in the log under a pseudonym. It can't
// be undone, so it asks for a reason and a typed confirmation.
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserX } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { Button, Callout, Card } from "../ui";
import { Modal } from "../Overlay";
import { useToast } from "../Toast";

export default function EraseEmployee({ employee }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [typed, setTyped] = useState("");
  const [error, setError] = useState("");
  const [working, withWorking] = useAction();
  const navigate = useNavigate();
  const toast = useToast();

  async function erase(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await api(`/privacy/employees/${employee.id}/erase`, { method: "POST", body: { reason: reason.trim() } });
      toast(`Erased. Past decisions stay in the log as “${res.pseudonym}”.`);
      navigate("/employees");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card id="erase" icon={UserX} title="Someone who has left"
      subtitle="When this person leaves, erase their personal data. Decisions about them stay in the log under a pseudonym.">
      <Button look="secondary" className="danger-text" icon={UserX} onClick={() => setOpen(true)}>Erase {employee.full_name}'s personal data…</Button>
      <Modal open={open} onClose={() => setOpen(false)} title={`Erase ${employee.full_name}'s personal data?`}>
        <form onSubmit={(e) => withWorking(() => erase(e))}>
          <p>Their name, work record, ratings, correction requests (with evidence) and equality-monitoring answers are removed,
            and they leave every list and check. This can't be undone.</p>
          {error && <Callout tone="error">{error}</Callout>}
          <label className="field">Why <span className="muted">(kept in the audit trail)</span>
            <input value={reason} onChange={(e) => setReason(e.target.value)} minLength={10} maxLength={500} required placeholder="e.g. Left the organisation on 30 June 2026" />
          </label>
          <label className="field">Type their name to confirm
            <input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
          </label>
          <div className="form-actions">
            <Button look="danger" busy={working} busyText="Erasing…" disabled={typed.trim() !== employee.full_name || reason.trim().length < 10}>Erase</Button>
            <button type="button" className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      </Modal>
    </Card>
  );
}
