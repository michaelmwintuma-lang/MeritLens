// HR's review of a nomination: a note when a record correction is pending for the nominee (the score may change),
// with the option to hold the decision until it is resolved. A hold is not a decision: it is never counted as
// agreeing or disagreeing with the model, and it lifts by itself once the correction is decided. While it holds,
// the server refuses a decision, so a held nomination can't be decided by accident from anywhere.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PauseCircle } from "lucide-react";
import { api } from "../../api";
import { Button, Callout, Card } from "../ui";
import { useAction } from "../../useAction";

export default function CommitteeNote({ nominationId, pending, onChange }) {
  const [note, setNote] = useState(null);
  const [error, setError] = useState("");
  const [working, withWorking] = useAction();

  const show = (n) => { setNote(n); onChange?.(n); };
  useEffect(() => {
    api(`/hr/feedback/nominations/${nominationId}/note`).then(show).catch((err) => setError(err.message));
  }, [nominationId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function act(path) {
    setError("");
    try { show(await api(`/hr/feedback/nominations/${nominationId}/${path}`, { method: "POST" })); }
    catch (err) { setError(err.message); }
  }

  if (error) return <Callout tone="error">{error}</Callout>;
  if (!note || (!note.pending_corrections.length && !note.deferred)) return null;
  return (
    <Card id="committee-note" tone="warn" icon={PauseCircle} title="Committee note: a record correction is pending">
      <p>The nominee has asked HR to correct their record. If it's confirmed, their score may change.</p>
      <ul className="plain-list">
        {note.pending_corrections.map((r) => (
          <li key={r.id}><strong>{r.label}</strong>: {r.current_display} in the record, {r.requested_display} asked for
            <span className="muted"> (since {r.created_at.slice(0, 10)})</span></li>
        ))}
      </ul>
      {note.deferred ? (
        <>
          <p>
            <strong>The decision is on hold</strong> until the correction is resolved (held by {note.deferred_by} on {note.deferred_at.slice(0, 10)}).
            It isn't a decision and isn't counted as an override; no decision can be recorded until the hold lifts.
          </p>
          <div className="form-actions">
            <Link className="btn btn-primary" to="/corrections">Open the correction queue</Link>
            <Button look="secondary" busy={working} busyText="Resuming…" onClick={() => withWorking(() => act("resume"))}>Decide now anyway</Button>
          </div>
        </>
      ) : pending && (
        <div className="form-actions">
          <Button busy={working} busyText="Putting on hold…" onClick={() => withWorking(() => act("defer"))}>Hold the decision until it's resolved</Button>
          <Link className="btn btn-secondary" to="/corrections">Open the correction queue</Link>
        </div>
      )}
    </Card>
  );
}
