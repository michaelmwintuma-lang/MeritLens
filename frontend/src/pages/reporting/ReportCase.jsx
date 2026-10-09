// HR: one anonymous report. The text with its warning words marked, why it got its priority, the conversation,
// and the priority, status and outcome.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, FileText } from "lucide-react";
import { api } from "../../api";
import { Button, Card, PageHeader } from "../../components/ui";
import Conversation, { CaseStatus, PRIORITY_LABELS, PriorityTag } from "../../components/reporting/Conversation";
import { EvidenceGallery, EvidencePrivacy, loadAsHr } from "../../components/reporting/Evidence";
import { useAction } from "../../useAction";
import Reappraisal from "../../components/feedback/Reappraisal";

/** The report text with the words that triggered its priority marked. */
function MarkedText({ text, triggers }) {
  if (!triggers.length) return <p className="cleaned">{text}</p>;
  const pattern = new RegExp(`\\b(${triggers.map((t) => t.word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`, "gi");
  return (
    <p className="cleaned">
      {text.split(pattern).map((part, i) => {
        const hit = triggers.find((t) => t.word.toLowerCase() === part.toLowerCase());
        return hit ? <mark key={i} className={`trigger ${hit.level}`} title={`Pushed it towards ${PRIORITY_LABELS[hit.level].toLowerCase()} priority`}>{part}</mark> : part;
      })}
    </p>
  );
}

/** What the language model read: its chance for each level, and the words that drove it. */
function ModelReading({ reading }) {
  return (
    <div className="model-reading">
      <ul className="chance-list" aria-label="How likely the model thinks each priority is">
        {["high", "medium", "low"].map((level) => (
          <li key={level} className={reading.priority === level ? "chosen" : ""}>
            <span className="chance-label">{PRIORITY_LABELS[level]}</span>
            <span className="chance-track"><span className={`chance-fill ${level}`} style={{ width: `${Math.round(reading.chances[level] * 100)}%` }} /></span>
            <span className="chance-value">{Math.round(reading.chances[level] * 100)}%</span>
          </li>
        ))}
      </ul>
      {reading.words.length > 0 && (
        <p className="small"><span className="muted">Words that drove it most: </span>
          {reading.words.map((w) => <span key={w.word} className="word-chip">{w.word}</span>)}</p>
      )}
    </div>
  );
}

export default function ReportCase() {
  const { caseId } = useParams();
  const [report, setReport] = useState(null);
  const [form, setForm] = useState({});
  const [reply, setReply] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const show = (r) => { setReport(r); setForm({ priority: r.priority, status: r.status, outcome: r.outcome || "" }); };
  useEffect(() => { api(`/hr/reports/${caseId}`).then(show).catch((err) => setError(err.message)); }, [caseId]);

  const [saving, withSaving] = useAction();
  const [sending, withSending] = useAction();

  async function save(e) {
    e.preventDefault();
    setError(""); setSaved("");
    try {
      show(await api(`/hr/reports/${caseId}`, { method: "PATCH", body: { ...form, outcome: form.outcome || null } }));
      setSaved("Saved.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function send(e) {
    e.preventDefault();
    setError("");
    try {
      await api(`/hr/reports/${caseId}/messages`, { method: "POST", body: { text: reply } });
      setReply("");
      show(await api(`/hr/reports/${caseId}`));
    } catch (err) {
      setError(err.message);
    }
  }

  if (error && !report) return <p className="alert alert-error">{error}</p>;
  if (!report) return <p className="muted">Loading…</p>;
  const closed = report.status === "closed";

  return (
    <>
      <Link to="/reports" className="back"><ArrowLeft size={16} />Back to the inbox</Link>
      <PageHeader icon={FileText} title={`Case ${report.case_id}`} subtitle={`${report.category} · received on ${report.created_on}`}
        actions={<><PriorityTag priority={report.priority} /><CaseStatus status={report.status} /></>} />
      {error && <p className="alert alert-error" role="alert">{error}</p>}

      <Card title="The report" subtitle="As the reporter approved it, after names, contacts and dates were removed.">
        <MarkedText text={report.text} triggers={report.triage.triggers} />
      </Card>

      <Card title="Why this priority"
        subtitle={`Suggested on arrival: ${PRIORITY_LABELS[report.suggested_priority]}. You can change it below.`}>
        <ModelReading reading={report.triage.model} />
        <ul className="links">{report.triage.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
      </Card>

      <Card title="Photos and videos" subtitle={report.evidence.length ? `${report.evidence.length} added by the reporter. Location, device and time were removed before saving.` : undefined}>
        <EvidenceGallery items={report.evidence} load={loadAsHr(report.case_id)} />
        {report.evidence.length > 0 && <details className="details"><summary>What was removed, and what wasn't</summary><EvidencePrivacy /></details>}
      </Card>

      <Card title="Conversation" subtitle="You appear as “Investigator”. Don't sign with your name or ask who they are.">
        <Conversation messages={report.conversation} me="investigator" />
        {!closed && (
          <form onSubmit={(e) => withSending(() => send(e))} style={{ marginTop: 16 }}>
            <label className="field">Reply to the reporter
              <textarea rows={3} value={reply} onChange={(e) => setReply(e.target.value)} maxLength={3000} required minLength={2} />
            </label>
            <Button busy={sending} busyText="Sending…">Send reply</Button>
          </form>
        )}
      </Card>

      <Card title="Manage the case">
        <form onSubmit={(e) => withSaving(() => save(e))}>
          <div className="form-row">
            <label className="field">Priority
              <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {report.options.priorities.map((p) => <option key={p} value={p}>{PRIORITY_LABELS[p]}</option>)}
              </select>
            </label>
            <label className="field">Status
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {report.options.statuses.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
              </select>
            </label>
            <label className="field">Outcome {form.status === "closed" ? "(required to close)" : ""}
              <select value={form.outcome} onChange={(e) => setForm({ ...form, outcome: e.target.value })}>
                <option value="">Not decided yet</option>
                {Object.entries(report.options.outcomes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          </div>
          <div className="row">
            <Button busy={saving} busyText="Saving…" disabled={form.status === "closed" && !form.outcome}>Save changes</Button>
            {saved && <span className="muted">{saved}</span>}
          </div>
        </form>
      </Card>
      {closed && report.outcome === "rating_unfair" && <Reappraisal caseId={report.case_id} />}
    </>
  );
}
