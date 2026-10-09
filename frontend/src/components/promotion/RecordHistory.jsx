// Every change to an employee's work record: who changed what, why, and the readiness before and after.
// Shown to HR on the readiness page. The history is kept for audit and can't be edited or deleted.
import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { api } from "../../api";
import { percent } from "../../format";
import { Card, EmptyState } from "../ui";

const SOURCES = { hr_edit: "HR edited the record", correction: "Correction confirmed by HR" };

export default function RecordHistory({ employeeId }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api(`/promotion/records/${employeeId}/history`).then(setRows).catch((err) => setError(err.message));
  }, [employeeId]);

  return (
    <Card title="Record history" subtitle="Changes to the work record the model uses, with the readiness before and after. Kept for audit; nobody can edit it.">
      {error && <p className="alert alert-error">{error}</p>}
      {!rows && !error && <p className="muted">Loading…</p>}
      {rows?.length === 0 && <EmptyState icon={History} title="No changes yet" text="The record is as it was first entered." />}
      {rows?.length > 0 && (
        <div className="table-wrap"><table>
          <thead><tr><th>When</th><th>What changed</th><th>Readiness</th><th>By</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="nowrap">{r.changed_at.slice(0, 10)}</td>
                <td>
                  {r.changes.map((c) => <div key={c.field}>{c.label}: {c.old_display} → <strong>{c.new_display}</strong></div>)}
                  {r.reason && <div className="muted small">Reason: {r.reason}</div>}
                </td>
                <td className="nowrap">{percent(r.score_before)} → <strong>{percent(r.score_after)}</strong>
                  <div className="muted small">model {r.model_version}</div></td>
                <td>{r.changed_by}<div className="muted small">{SOURCES[r.source] || r.source}</div></td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </Card>
  );
}
