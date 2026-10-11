// Admin: who did what, and on which day. Only the day is kept, never the time.
import { useEffect, useState } from "react";
import { EyeOff, ScrollText } from "lucide-react";
import { api } from "../../api";
import { Card, EmptyState, LoadError, Loading, PageHeader } from "../../components/ui";

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
        <EyeOff size={16} style={{ verticalAlign: "-3px" }} /> <strong>Only the day is kept, never the time</strong>: an
        audit needs to know what happened and when, not people's working habits.
      </p>
      {error && <LoadError message={error} />}
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
        {!data ? <Loading /> : data.entries.length === 0 ? (
          <EmptyState icon={ScrollText} title="Nothing found" text="Try another action or search." />
        ) : (
          <div className="table-wrap" tabIndex={0}>
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
