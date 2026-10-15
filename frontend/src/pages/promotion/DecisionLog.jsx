// HR and the auditor: every promotion decision, with what the model said at the time and the reason.
import { useState } from "react";
import { api } from "../../api";
import { useLoad } from "../../useLoad";
import { percent } from "../../format";
import { AgreesWithModel } from "../../components/promotion/Status";
import { PayStatus } from "../../components/promotion/PayStatus";
import { BookCheck } from "lucide-react";
import { EmptyState, LoadError, PageHeader, PageLoading, Pager, StatCard } from "../../components/ui";

const PAGE_SIZE = 25;

export default function DecisionLog() {
  const { data: log, error, reload: load } = useLoad(() => api("/promotion/decisions"), []);
  const [page, setPage] = useState(0);
  const header = <PageHeader title="Decision log" subtitle="Every promotion decision, with the model's score at the time and the reason given." />;

  if (error) return <>{header}<LoadError message={error} onRetry={load} /></>;
  if (!log) return <>{header}<PageLoading /></>;
  const differs = log.filter((d) => !d.agrees_with_model).length;

  return (
    <>
      {header}
      <div className="stat-grid">
        <StatCard label="Decisions" value={log.length} note="Approved or rejected" />
        <StatCard label="Approved" value={log.filter((d) => d.decision === "approve").length} note="Promotions granted" />
        <StatCard label="Differ from the model" value={differs} note="Each with a written reason" />
      </div>
      <div className="card flush">
        <div className="card-head"><div><h2>All decisions</h2><p className="card-sub">Newest first.</p></div></div>
        {log.length === 0 ? <EmptyState icon={BookCheck} title="No decisions yet" text="Decisions on nominations will be recorded here." /> : (
          <div className="table-wrap" tabIndex={0} role="region" aria-label="All decisions"><table>
            <thead><tr><th>When</th><th>Employee</th><th>Decision</th><th>Role and pay rise</th><th>Decided by</th><th className="num">Model at the time</th><th>Compared with the model</th><th>Reason</th></tr></thead>
            <tbody>
              {log.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).map((d) => (
                <tr key={d.id}>
                  <td className="nowrap">{d.decided_at.replace("T", " ").slice(0, 16)}</td>
                  <td>{d.employee.full_name}<div className="cell-sub">{d.employee.department}</div></td>
                  <td className="strong">{d.decision === "approve" ? "Approved" : "Rejected"}</td>
                  <td>{d.proposed_title || <span className="muted">–</span>}
                    {d.approved_raise != null && <div><span className="strong">{d.approved_raise}%</span>
                      {d.proposed_raise != null && d.proposed_raise !== d.approved_raise && <span className="muted"> (proposed {d.proposed_raise}%)</span>}</div>}
                    {d.raise_reason && <div className="cell-sub">Outside policy: {d.raise_reason}</div>}
                    {d.pay_status && <div className="tag-stack"><PayStatus status={d.pay_status} /></div>}</td>
                  <td>{d.decided_by}</td>
                  <td className="num"><span className="strong">{percent(d.model_score)}</span><div className="cell-sub">{d.model_recommended ? "Recommended" : "Not recommended"}</div></td>
                  <td><AgreesWithModel agrees={d.agrees_with_model} /></td>
                  <td>{d.reason || <span className="muted">None given</span>}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
        <Pager page={page} size={PAGE_SIZE} total={log.length} onPage={setPage} label="Pages of decisions" />
      </div>
    </>
  );
}
