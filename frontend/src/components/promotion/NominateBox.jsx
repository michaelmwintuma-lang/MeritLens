// For managers, on a team member's readiness page: nominate them, or see that a nomination is waiting.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { Button } from "../ui";
import { useAction } from "../../useAction";

export default function NominateBox({ employeeId, name }) {
  const [pending, setPending] = useState(null); // an existing pending nomination, if any
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    api("/promotion/nominations")
      .then((list) => setPending(list.find((n) => n.employee.id === employeeId && n.status === "pending") || false))
      .catch((err) => setError(err.message));
  }, [employeeId, done]);

  const [working, withWorking] = useAction();

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/promotion/nominations", { method: "POST", body: { employee_id: employeeId, reason } });
      setDone(true);
    } catch (err) {
      setError(err.message);
    }
  }

  if (pending === null) return null;
  if (pending) {
    return (
      <p className="alert alert-info">
        You nominated {name} on {pending.created_at.slice(0, 10)}. HR hasn't decided yet. <Link to="/nominations">See your nominations</Link>
      </p>
    );
  }
  return (
    <form onSubmit={(e) => withWorking(() => submit(e))}>
      <p className="muted">HR will see your reason next to the model's score and explanation, and makes the final decision.</p>
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      <label className="field">Why should {name} be promoted? <span className="muted small">(at least 10 characters)</span>
        <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} minLength={10} maxLength={2000} required />
      </label>
      <Button busy={working} busyText="Sending to HR…">Nominate for promotion</Button>
    </form>
  );
}
