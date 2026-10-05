// Nominations in one table with a Waiting | Decided | All switch. HR gets a Review button on waiting ones.
import { useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardCheck } from "lucide-react";
import { percent } from "../../format";
import { Card, EmptyState, Segmented } from "../ui";
import { NominationStatus } from "./Status";

const VIEWS = [
  { value: "pending", label: "Waiting" },
  { value: "decided", label: "Decided" },
  { value: "all", label: "All" },
];

export default function NominationsTable({ nominations, isHr, title, subtitle }) {
  const [view, setView] = useState("pending");
  const rows = nominations.filter((n) => view === "all" || (view === "pending") === (n.status === "pending"));

  return (
    <Card flush title={title} subtitle={subtitle} actions={<Segmented label="Show" options={VIEWS} value={view} onChange={setView} />}>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Employee</th><th>Proposed</th><th>Nominated by</th><th>Model's view now</th><th>Status</th><th>Date</th><th style={{ textAlign: "right" }}>Actions</th></tr>
          </thead>
          <tbody>
            {rows.map((n) => (
              <tr key={n.id}>
                <td><span className="strong">{n.employee.full_name}</span><div className="muted small">{n.employee.department}</div></td>
                <td>{n.recommendation?.proposed_title
                  ? <><span className="strong">{n.recommendation.proposed_title}</span><div className="muted small">
                      {n.decision?.approved_raise != null ? `${n.decision.approved_raise}% approved` : `${n.recommendation.proposed_raise}% proposed`}</div></>
                  : <span className="muted">–</span>}</td>
                <td>{n.nominated_by}</td>
                <td>{percent(n.model_now.score)} · {n.model_now.recommended ? "recommends" : "not yet"}</td>
                <td><NominationStatus status={n.status} /></td>
                <td className="nowrap">{(n.decision?.decided_at || n.created_at).slice(0, 10)}</td>
                <td style={{ textAlign: "right" }}>
                  {isHr && n.status === "pending"
                    ? <Link className="btn btn-primary" to={`/nominations/${n.id}`}>Review</Link>
                    : <Link className="btn btn-plain" to={`/employees/${n.employee.id}`}>View</Link>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && (
        <EmptyState icon={ClipboardCheck}
          title={view === "pending" ? "Nothing waiting for a decision" : "No nominations here yet"}
          text={view === "pending" ? "New nominations from managers will appear here." : "Decided nominations will appear here."} />
      )}
    </Card>
  );
}
