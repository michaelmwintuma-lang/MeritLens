// Admin: is email set up, every email's delivery (with retries and resending), reminders, a test email, and the
// emails saved in the outbox (when no server is set up).
import { useEffect, useState } from "react";
import { CheckCircle2, Inbox, Send, TriangleAlert } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { Button, Callout, Card, EmptyState, PageHeader } from "../../components/ui";
import DeliveryLog from "../../components/admin/DeliveryLog";

const EMAILS_SENT = [
  ["Welcome", "A new account's sign-in details", "the new person"],
  ["Password reset", "A new temporary password", "the person"],
  ["Security alert", "Their password or username changed", "the person"],
  ["Nomination received", "A manager nominated someone", "every HR account"],
  ["Decision", "HR approved or rejected a nomination", "the manager (and the employee, if approved)"],
  ["Correction waiting", "An employee asked for a record correction", "every HR account"],
  ["Correction decided", "HR confirmed or rejected a record correction, with the reason", "the employee"],
  ["Pay rise to sign off", "HR approved a promotion (or revised a pay rise)", "every Finance account"],
  ["Review cycle open", "HR opened a review cycle", "every manager with a team"],
  ["Reminders", "Nominations closing soon; pay rises waiting; a cycle ready to close; corrections waiting", "the person who needs to act, once each"],
  ["Daily digest", "The day's routine emails in one, for people who chose that on My profile", "those people"],
];

export default function Email() {
  const [status, setStatus] = useState(null);
  const [outbox, setOutbox] = useState([]);
  const [to, setTo] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [sending, withSending] = useAction();

  const load = () => Promise.all([api("/admin/email"), api("/admin/email/outbox")])
    .then(([s, o]) => { setStatus(s); setOutbox(o); })
    .catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);

  async function sendTest(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    try {
      setResult(await api("/admin/email/test", { method: "POST", body: { to } }));
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <PageHeader title="Email" subtitle="Delivery settings, every email's delivery, reminders, a test email and the outbox." />
      {error && <Callout tone="error">{error}</Callout>}

      {status && (status.configured ? (
        <Callout tone="success" icon={CheckCircle2} title="Email is set up.">Sending through {status.host}:{status.port} as <span className="mono">{status.sender}</span>.</Callout>
      ) : (
        <Callout tone="warning" icon={TriangleAlert} title="Email isn't set up yet, so emails are saved in the outbox instead of sent.">
          <span>To send with Gmail:</span>
          <ol className="steps-list">
            <li>Switch on 2-Step Verification for the Google account that will send the emails.</li>
            <li>Create an <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">app password</a> (name it "Promotion platform").</li>
            <li>Copy <span className="mono">backend/.env.example</span> to <span className="mono">backend/.env</span> and fill in your Gmail address and the 16-letter app password.</li>
            <li>Restart the app (<span className="mono">python run.py</span>), then send a test email below.</li>
          </ol>
        </Callout>
      ))}

      <DeliveryLog />

      <div className="two-columns">
        <Card title="Send a test email">
          <form onSubmit={(e) => withSending(() => sendTest(e))}>
            <label className="field">Send to<input type="email" value={to} onChange={(e) => setTo(e.target.value)} required placeholder="you@example.com" /></label>
            <Button icon={Send} busy={sending} busyText="Sending…">Send test email</Button>
          </form>
          {result && <Callout tone={result.sent ? "success" : "warning"} className="section-gap" role="status">{result.detail}</Callout>}
        </Card>
        <Card title="What the platform emails" subtitle="Emails say what happened and link to the page; scores and records stay in the app.">
          <ul className="email-kinds">
            {EMAILS_SENT.map(([name, what, who]) => <li key={name}><strong>{name}</strong><span className="muted">{what} · to {who}</span></li>)}
          </ul>
        </Card>
      </div>

      <Card flush title={`Outbox (${status?.outbox_count ?? 0})`} subtitle="Saved here while no mail server is set up.">
        {outbox.length === 0 ? <EmptyState icon={Inbox} title="The outbox is empty" text="Saved emails appear here when no mail server is set up." /> : (
          <ul className="outbox">
            {outbox.map((m) => (
              <li key={m.file}>
                <details>
                  <summary><span className="strong">{m.subject}</span><span className="muted">to {m.to}</span></summary>
                  <pre className="email-body">{m.body}</pre>
                </details>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
