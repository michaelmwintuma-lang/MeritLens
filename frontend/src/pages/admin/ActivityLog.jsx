// Admin: who did what, and on which day. Nothing a reporter does is recorded, and only the day is kept.
import { useEffect, useState } from "react";
import { EyeOff, ScrollText } from "lucide-react";
import { api } from "../../api";
import { Card, EmptyState, PageHeader } from "../../components/ui";

export default function ActivityLog() {
  const [data, setData] = useState(null);
  const [action, setAction] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ ...(action && { action }), ...(search.trim() && { search: search.trim() }) });
    const timer = setTimeout(() => {
      api(`/admin/activity?${params}`).then(setData).catch((err) => setError(err.message));
    }, 250); // wait until the admin stops typing
    return () => clearTimeout(timer);
  }, [action, search]);

  return (
    <>
      <PageHeader icon={ScrollText} title="Activity log" subtitle="Recorded by day, not time." />
      <p className="alert alert-info">
        <EyeOff size={16} style={{ verticalAlign: "-3px" }} /> <strong>Nothing a reporter does is recorded</strong>, and
        only the day is kept, never the time, so this log can't be used to work out who sent a report.
      </p>
      {error && <p className="alert alert-error">{error}</p>}
      <Card flush title="Entries" subtitle="Newest first (the latest 500)."
        actions={
          <div className="filters">
            <input placeholder="Search names or details" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
            <select value={action} onChange={(e) => setAction(e.target.value)} aria-label="Action">
              <option value="">All actions</option>
              {data && Object.entries(data.actions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </div>
        }>
        {!data ? <p className="muted" style={{ padding: "0 24px 24px" }}>Loading…</p> : data.entries.length === 0 ? (
          <EmptyState icon={ScrollText} title="Nothing found" text="Try another action or search." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Who</th><th>What</th><th>Details</th></tr></thead>
              <tbody>
                {data.entries.map((e) => (
                  <tr key={e.id}>
                    <td className="nowrap">{e.date}</td>
                    <td className="strong">{e.user}</td>
                    <td><span className={`tag ${e.action === "sign_in_failed" ? "tag-warn" : ""}`}>{e.action_label}</span></td>
                    <td className="muted">{e.details || "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
