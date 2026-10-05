// HR: every anonymous report, urgent and open ones first.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Inbox } from "lucide-react";
import { api } from "../../api";
import { Card, EmptyState, PageHeader, Segmented, StatCard } from "../../components/ui";
import { CaseStatus, PriorityTag } from "../../components/reporting/Conversation";

const VIEWS = [
  { value: "open", label: "Open" },
  { value: "investigating", label: "Investigating" },
  { value: "closed", label: "Closed" },
  { value: "all", label: "All" },
];

export default function ReportInbox() {
  const [reports, setReports] = useState(null);
  const [view, setView] = useState("open");
  const [error, setError] = useState("");
  useEffect(() => { api("/hr/reports").then(setReports).catch((err) => setError(err.message)); }, []);

  if (error) return <p className="alert alert-error">{error}</p>;
  if (!reports) return <p className="muted">Loading…</p>;
  const notClosed = reports.filter((r) => r.status !== "closed");
  const rows = reports.filter((r) => view === "all" || r.status === view);

  return (
    <>
      <PageHeader icon={Inbox} title="Report inbox" subtitle="Anonymous reports from members of the organisation. Nothing here identifies who sent them." />
      <div className="stat-grid">
        <StatCard label="Open cases" value={notClosed.length} note="Open or being investigated" />
        <StatCard label="High priority" value={notClosed.filter((r) => r.priority === "high").length} note="Open cases marked high" />
        <StatCard label="Awaiting your reply" value={notClosed.filter((r) => r.reporter_wrote_last).length} note="The reporter wrote last" />
        <StatCard label="Closed" value={reports.length - notClosed.length} note="With an outcome recorded" />
      </div>
      <Card flush title="Reports" subtitle="High priority first, then newest." actions={<Segmented label="Show" options={VIEWS} value={view} onChange={setView} />}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Case</th><th>Category</th><th>Priority</th><th>Status</th><th>Received</th><th>Conversation</th><th style={{ textAlign: "right" }}>Actions</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.case_id}>
                  <td className="mono strong">{r.case_id}</td>
                  <td>{r.category}</td>
                  <td><PriorityTag priority={r.priority} /></td>
                  <td><CaseStatus status={r.status} /></td>
                  <td className="nowrap">{r.created_on}</td>
                  <td>{r.messages ? `${r.messages} message${r.messages > 1 ? "s" : ""}` : <span className="muted">None yet</span>}
                    {r.reporter_wrote_last && <div className="small strong">Reporter is waiting for a reply</div>}</td>
                  <td style={{ textAlign: "right" }}><Link className="btn btn-primary" to={`/reports/${r.case_id}`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 && <EmptyState icon={Inbox} title={view === "all" ? "No reports yet" : `No ${view} reports`} text="New anonymous reports will appear here." />}
      </Card>
    </>
  );
}
