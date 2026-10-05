// Admin: is email set up, send a test email, and read the emails saved in the outbox (when no server is set up).
import { useEffect, useState } from "react";
import { CheckCircle2, Inbox, Mail, Send, TriangleAlert } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { Button, Card, EmptyState, PageHeader } from "../../components/ui";

const EMAILS_SENT = [
  ["Welcome", "A new account's sign-in details", "the new person"],
  ["Password reset", "A new temporary password", "the person"],
  ["Security alert", "Their password or username changed", "the person"],
  ["Nomination received", "A manager nominated someone", "every HR account"],
  ["Decision", "HR approved or rejected a nomination", "the manager (and the employee, if approved)"],
  ["New report alert", "Only the case ID, category and priority, never the text or anything about the reporter", "every HR account"],
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
      <PageHeader icon={Mail} title="Email" subtitle="Welcome emails, security alerts and notifications: check they're being delivered." />
      {error && <p className="alert alert-error" role="alert">{error}</p>}

      {status && (status.configured ? (
        <p className="alert alert-success"><span><CheckCircle2 size={16} style={{ verticalAlign: "-3px" }} /> <strong>Email is set up.</strong> Sending through {status.host}:{status.port} as <span className="mono">{status.sender}</span>.</span></p>
      ) : (
        <div className="alert alert-warning">
          <strong><TriangleAlert size={16} style={{ verticalAlign: "-3px" }} /> Email isn't set up yet, so emails are saved in the outbox instead of sent.</strong>
          <span>To send with Gmail:</span>
          <ol className="steps-list">
            <li>Switch on 2-Step Verification for the Google account that will send the emails.</li>
            <li>Create an <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">app password</a> (name it "Promotion platform").</li>
            <li>Copy <span className="mono">backend/.env.example</span> to <span className="mono">backend/.env</span> and fill in your Gmail address and the 16-letter app password.</li>
            <li>Restart the app (<span className="mono">python run.py</span>), then send a test email below.</li>
          </ol>
        </div>
      ))}

      <div className="two-columns">
        <Card title="Send a test email" subtitle="Checks that emails really arrive. Use your own address.">
          <form onSubmit={(e) => withSending(() => sendTest(e))}>
            <label className="field">Send to<input type="email" value={to} onChange={(e) => setTo(e.target.value)} required placeholder="you@example.com" /></label>
            <Button icon={Send} busy={sending} busyText="Sending…">Send test email</Button>
          </form>
          {result && <p className={`alert ${result.sent ? "alert-success" : "alert-warning"}`} style={{ marginTop: 14 }}>{result.detail}</p>}
        </Card>
        <Card title="What the platform emails" subtitle="Reporters are never emailed about their reports: that would link them to it.">
          <ul className="email-kinds">
            {EMAILS_SENT.map(([name, what, who]) => <li key={name}><strong>{name}</strong><span className="muted small">{what} · to {who}</span></li>)}
          </ul>
        </Card>
      </div>

      <Card flush title={`Outbox (${status?.outbox_count ?? 0})`} subtitle="Emails saved instead of sent, newest first. Once email is set up, new emails are sent instead.">
        {outbox.length === 0 ? <EmptyState icon={Inbox} title="The outbox is empty" text="Saved emails appear here when no mail server is set up." /> : (
          <ul className="outbox">
            {outbox.map((m) => (
              <li key={m.file}>
                <details>
                  <summary><span className="strong">{m.subject}</span><span className="muted small">to {m.to}</span></summary>
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
