// HR: every promotion decision, with what the model said at the time and the reason.
import { useEffect, useState } from "react";
import { api } from "../../api";
import { percent } from "../../format";
import { AgreesWithModel } from "../../components/promotion/Status";
import { PayStatus } from "../../components/promotion/PayStatus";
import { BookCheck } from "lucide-react";
import { EmptyState, PageHeader, StatCard } from "../../components/ui";

export default function DecisionLog() {
  const [log, setLog] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/promotion/decisions").then(setLog).catch((err) => setError(err.message)); }, []);

  if (error) return <p className="alert alert-error">{error}</p>;
  if (!log) return <p className="muted">Loading…</p>;
  const differs = log.filter((d) => !d.agrees_with_model).length;

  return (
    <>
      <PageHeader icon={BookCheck} title="Decision log"
        subtitle="Every promotion decision, with the model's score and recommendation at the moment it was made." />
      <div className="stat-grid">
        <StatCard label="Decisions" value={log.length} note="Approved or rejected" />
        <StatCard label="Approved" value={log.filter((d) => d.decision === "approve").length} note="Promotions granted" />
        <StatCard label="Differ from the model" value={differs} note="Each with a written reason" />
      </div>
      <div className="card flush">
        <div className="card-head"><div><h2>All decisions</h2><p className="card-sub">Newest first.</p></div></div>
        {log.length === 0 ? <EmptyState icon={BookCheck} title="No decisions yet" text="Decisions on nominations will be recorded here." /> : (
          <div className="table-wrap"><table>
            <thead><tr><th>When</th><th>Employee</th><th>Decision</th><th>Role and pay rise</th><th>Decided by</th><th>Model at the time</th><th>Compared with the model</th><th>Reason</th></tr></thead>
            <tbody>
              {log.map((d) => (
                <tr key={d.id}>
                  <td className="nowrap">{d.decided_at.replace("T", " ").slice(0, 16)}</td>
                  <td>{d.employee.full_name}<div className="muted small">{d.employee.department}</div></td>
                  <td className="strong">{d.decision === "approve" ? "Approved" : "Rejected"}</td>
                  <td>{d.proposed_title || <span className="muted">–</span>}
                    {d.approved_raise != null && <div className="small"><span className="strong">{d.approved_raise}%</span>
                      {d.proposed_raise != null && d.proposed_raise !== d.approved_raise && <span className="muted"> (proposed {d.proposed_raise}%)</span>}</div>}
                    {d.raise_reason && <div className="muted small">Outside policy: {d.raise_reason}</div>}
                    {d.pay_status && <div style={{ marginTop: 4 }}><PayStatus status={d.pay_status} /></div>}</td>
                  <td>{d.decided_by}</td>
                  <td>{percent(d.model_score)} · {d.model_recommended ? "recommended" : "not recommended"}</td>
                  <td><AgreesWithModel agrees={d.agrees_with_model} /></td>
                  <td>{d.reason || <span className="muted">None given</span>}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  );
}
