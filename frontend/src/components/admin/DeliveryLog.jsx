// Admin: every email the platform sent (or tried to), newest first: whether it was delivered, how many attempts,
// and any error. A failed email is tried again automatically; after the last attempt, or when it was only saved to
// the outbox, the admin can resend it. Also: run the reminders that are due now (the timer does this every hour).
import { useState } from "react";
import { AlarmClock, CheckCircle2, CircleAlert, Clock, Inbox, MailCheck, RotateCcw, TriangleAlert } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { useLoad } from "../../useLoad";
import { Badge, Button, Callout, Card, EmptyState, LoadError, Loading, Segmented } from "../ui";
import { useToast } from "../Toast";

const STATUS = {
  sent: ["success", CheckCircle2, "Sent"],
  saved: ["neutral", Inbox, "Saved to outbox"],
  failed: ["warning", Clock, "Will retry"],
  gave_up: ["danger", CircleAlert, "Not delivered"],
  held: ["info", Clock, "For daily digest"],
  in_digest: ["success", MailCheck, "Sent in digest"],
  queued: ["neutral", Clock, "Queued"],
};
const VIEWS = [
  { value: "", label: "All" },
  { value: "failed", label: "Retrying" },
  { value: "gave_up", label: "Not delivered" },
  { value: "held", label: "In digests" },
];
const when = (iso) => (iso ? iso.replace("T", " ").slice(0, 16) : "–");

export default function DeliveryLog() {
  const [view, setView] = useState("");
  const { data, error, reload } = useLoad(() => api(`/admin/email/log${view ? `?status_filter=${view}` : ""}`), [view]);
  const [busy, setBusy] = useState(null);
  const [running, withRunning] = useAction();
  const [problem, setProblem] = useState("");
  const toast = useToast();

  async function resend(entry) {
    setProblem("");
    setBusy(entry.id);
    try {
      const res = await api(`/admin/email/log/${entry.id}/resend`, { method: "POST" });
      toast(res.detail, res.sent ? "success" : "error");
      reload();
    } catch (err) {
      setProblem(err.message);
    } finally {
      setBusy(null);
    }
  }

  async function runReminders() {
    setProblem("");
    try {
      const { sent } = await api("/admin/email/reminders/run", { method: "POST" });
      toast(sent.length ? `Reminders sent: ${sent.join("; ")}.` : "No reminders are due right now.");
      reload();
    } catch (err) {
      setProblem(err.message);
    }
  }

  const counts = data?.counts || {};
  return (
    <Card flush id="delivery" title="Delivery log"
      subtitle="Every email, newest first. One the mail server didn't accept is tried again automatically (after 1, 5, 15, 60 and 240 minutes). Once delivered, only who, what and when are kept."
      actions={<Button look="secondary" icon={AlarmClock} busy={running} busyText="Checking…" onClick={() => withRunning(runReminders)}>Run reminders now</Button>}>
      <div className="card-inset">
        {(counts.failed || counts.gave_up) ? (
          <Callout tone={counts.gave_up ? "warning" : "info"} icon={TriangleAlert}>
            {counts.failed ? `${counts.failed} email${counts.failed === 1 ? " is" : "s are"} waiting to be tried again. ` : ""}
            {counts.gave_up ? `${counts.gave_up} couldn't be delivered: check the mail settings, then resend.` : ""}
          </Callout>
        ) : null}
        {problem && <Callout tone="error">{problem}</Callout>}
        <Segmented label="Show" options={VIEWS} value={view} onChange={setView} />
      </div>
      {error ? <div className="card-inset"><LoadError message={error} onRetry={reload} /></div> : !data ? <div className="card-inset"><Loading /></div>
        : data.items.length === 0 ? <EmptyState compact icon={MailCheck} title="Nothing here" text="Emails appear here as the platform sends them." /> : (
          <div className="table-wrap" tabIndex={0} role="region" aria-label="Delivery log"><table>
            <thead><tr><th>When</th><th>To</th><th>Subject</th><th>Status</th><th className="num">Attempts</th><th><span className="visually-hidden">Resend</span></th></tr></thead>
            <tbody>{data.items.map((e) => {
              const [tone, icon, label] = STATUS[e.status] || ["neutral", Clock, e.status];
              return (
                <tr key={e.id}>
                  <td className="nowrap num">{when(e.created_at)}</td>
                  <td>{e.to}</td>
                  <td>{e.subject}{e.kind === "security" && <div className="cell-sub">Account email: always sent at once</div>}
                    {e.last_error && e.status !== "sent" && <div className="cell-sub">{e.last_error}{e.next_attempt_at ? `; next try ${when(e.next_attempt_at)}` : ""}</div>}</td>
                  <td><Badge tone={tone} icon={icon}>{label}</Badge></td>
                  <td className="num">{e.attempts}</td>
                  <td><div className="actions">{e.can_resend && (
                    <Button look="secondary" size="sm" icon={RotateCcw} busy={busy === e.id} busyText="Sending…" onClick={() => resend(e)}>
                      Resend<span className="visually-hidden"> to {e.to}</span></Button>)}</div></td>
                </tr>
              );
            })}</tbody>
          </table></div>
        )}
    </Card>
  );
}
