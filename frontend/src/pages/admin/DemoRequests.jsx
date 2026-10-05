// Admin: the "Book a demo" requests from the public website. Each was also emailed to the demo inbox; replying
// to that email answers the person directly. Tick a request once it's been answered.
import { useEffect, useState } from "react";
import { CalendarCheck, CheckCircle2, Circle, Mail } from "lucide-react";
import { api } from "../../api";
import { Card, EmptyState, PageHeader, Segmented } from "../../components/ui";

export default function DemoRequests() {
  const [requests, setRequests] = useState(null);
  const [show, setShow] = useState("open");
  const [error, setError] = useState("");

  const load = () => api("/admin/demo-requests").then(setRequests).catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);

  async function toggle(request) {
    try {
      await api(`/admin/demo-requests/${request.id}`, { method: "PATCH", body: { handled: !request.handled } });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!requests) return error ? <p className="alert alert-error">{error}</p> : <p className="muted">Loading…</p>;
  const open = requests.filter((r) => !r.handled).length;
  const rows = requests.filter((r) => show === "all" || !r.handled);

  return (
    <>
      <PageHeader icon={CalendarCheck} title="Demo requests"
        subtitle={`${open} waiting for a reply. Each request was also emailed to the demo inbox: reply to that email to answer the person.`} />
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      <Card flush actions={<Segmented label="Show" value={show} onChange={setShow}
        options={[{ value: "open", label: `Waiting (${open})` }, { value: "all", label: `All (${requests.length})` }]} />}>
        {rows.length === 0 ? <EmptyState icon={CalendarCheck} title={show === "open" ? "Nothing waiting" : "No requests yet"}
          text="Requests from the website's Book a demo page appear here." /> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Received</th><th>Who</th><th>Organisation</th><th>Interested in</th><th>Message</th><th /></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="nowrap">{r.created_on}</td>
                  <td><div className="strong">{r.name}</div><a href={`mailto:${r.email}`} className="small"><Mail size={13} style={{ verticalAlign: "-2px" }} /> {r.email}</a>{r.job_title && <div className="muted small">{r.job_title}</div>}</td>
                  <td>{r.organisation}<div className="muted small">{r.size} employees</div></td>
                  <td>{r.interest}</td>
                  <td className="small" style={{ maxWidth: 280 }}>{r.message || <span className="muted">–</span>}</td>
                  <td>
                    <button type="button" className={`btn btn-plain nowrap ${r.handled ? "" : ""}`} onClick={() => toggle(r)}>
                      {r.handled ? <><CheckCircle2 size={16} aria-hidden="true" />Answered</> : <><Circle size={16} aria-hidden="true" />Mark answered</>}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>
    </>
  );
}
