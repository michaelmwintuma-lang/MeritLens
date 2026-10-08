// Open your report with its case ID and secret key, read the investigator's replies, and reply.
import { useState } from "react";
import { Download, FileSearch } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Button, Card, PageHeader } from "../../components/ui";
import { downloadReceipt, legacyKeys, removeLegacyKeys } from "../../keyStore";
import Conversation, { CaseStatus } from "../../components/reporting/Conversation";
import { EvidenceGallery, EvidencePicker, EvidenceUploader, MAX_FILES, loadAsReporter } from "../../components/reporting/Evidence";
import { useAction } from "../../useAction";

/** The reporter's reply box. Like the report, a reply is anonymised and checked before it is sent. */
function Reply({ caseId, secret, onSent }) {
  const [draft, setDraft] = useState("");
  const [check, setCheck] = useState(null);
  const [error, setError] = useState("");

  const [checking, withChecking] = useAction();
  const [sending, withSending] = useAction();

  async function runCheck(e) {
    e.preventDefault();
    setError("");
    try {
      // The preview needs at least 20 characters; short replies are checked when sent instead
      setCheck(draft.trim().length >= 20 ? await api("/reports/preview", { method: "POST", body: { text: draft } }) : { text: draft, replaced: [], warnings: [] });
    } catch (err) {
      setError(err.message);
    }
  }

  async function send() {
    setError("");
    try {
      const res = await api("/reports/messages", { method: "POST", body: { case_id: caseId, key: secret, text: check.text } });
      setDraft(""); setCheck(null);
      onSent(res.messages);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div style={{ marginTop: 16 }}>
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      {!check ? (
        <form onSubmit={(e) => withChecking(() => runCheck(e))}>
          <label className="field">Reply to the investigator
            <textarea rows={3} value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={3000} required minLength={2} />
          </label>
          <Button busy={checking} busyText="Checking…">Check my reply</Button>
        </form>
      ) : (
        <>
          <p className="small strong">This is what the investigator will see:</p>
          <p className="cleaned">{check.text}</p>
          {check.warnings.length > 0 && (
            <div className="alert alert-warning"><strong>These phrases could identify you:</strong>
              <ul>{check.warnings.map((w, i) => <li key={i}>"{w.phrase}" · {w.reason}</li>)}</ul></div>
          )}
          <div className="row">
            <button className="btn btn-plain" onClick={() => setCheck(null)}>Edit</button>
            <Button busy={sending} busyText="Sending…" onClick={() => withSending(send)}>Send reply</Button>
          </div>
        </>
      )}
    </div>
  );
}

/** The reporter's photos and videos: see them, add more, or remove one (e.g. if it could identify them). */
function ReporterEvidence({ report, secret, onChange }) {
  const [chosen, setChosen] = useState([]);
  const [sending, setSending] = useState(null);   // the files being uploaded now
  const [removing, setRemoving] = useState(null);
  const [error, setError] = useState("");
  const open = report.status !== "closed";

  async function remove(item) {
    if (!window.confirm(`Remove ${item.kind} ${item.number}? HR will no longer be able to see it.`)) return;
    setError(""); setRemoving(item.id);
    try {
      const res = await api(`/reports/evidence/${item.id}/remove`, { method: "POST", body: { case_id: report.case_id, key: secret } });
      onChange(res.evidence);
    } catch (err) {
      setError(err.message);
    } finally {
      setRemoving(null);
    }
  }

  return (
    <Card title="Photos and videos" subtitle="Exactly what HR sees: the hidden details were removed when each file was added.">
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      <EvidenceGallery items={report.evidence} load={loadAsReporter(report.case_id, secret)} onRemove={open ? remove : null} removing={removing} />
      {open && !sending && report.evidence.length < MAX_FILES && (
        <div style={{ marginTop: 18 }}>
          <EvidencePicker files={chosen} setFiles={setChosen} already={report.evidence.length} />
          {chosen.length > 0 && <Button onClick={() => { setSending(chosen); setChosen([]); }}>Add {chosen.length} {chosen.length === 1 ? "file" : "files"}</Button>}
        </div>
      )}
      {sending && (
        <div style={{ marginTop: 18 }}>
          <EvidenceUploader caseId={report.case_id} secret={secret} files={sending} onDone={onChange} />
          <button type="button" className="btn btn-plain" onClick={() => setSending(null)}>Done</button>
        </div>
      )}
    </Card>
  );
}

// What's been typed or pasted so far, kept in memory while moving between pages (e.g. to fetch the key from a
// password manager after pasting the case ID). Never written to storage; gone when the tab closes, and never shown to
// another account signing in on the same tab.
const draft = { owner: null, caseId: "", key: "" };
const CASE_IN_TEXT = /R-[A-Z2-9]{4}-[A-Z2-9]{4}/i;
const KEY_IN_TEXT = /\b(?:[A-Z2-9]{4}-){3}[A-Z2-9]{4}\b/i;

/**
 * Keys an earlier version of the website saved in this browser. They are shown so the reporter can keep them
 * somewhere safe, and removed from the browser when the reporter says so (never silently: a lost key can't be
 * recovered, so deleting it unseen could lock someone out of their case for good).
 */
function OldSavedKeys({ onOpen }) {
  const [keys, setKeys] = useState(legacyKeys);
  if (!keys.length) return null;
  return (
    <Card title="Keys saved in this browser by an earlier version"
      subtitle="The website no longer keeps report keys. Download each one, or put it in your password manager, then remove them from this browser.">
      <ul className="plain-list">
        {keys.map((k) => (
          <li key={k.case_id} className="row spread">
            <span className="mono">{k.case_id}{k.note ? <span className="muted small"> · {k.note}</span> : null}</span>
            <span className="row">
              <button type="button" className="btn btn-plain" onClick={() => downloadReceipt(k.case_id, k.key)}><Download size={16} aria-hidden="true" />Download</button>
              <button type="button" className="btn btn-plain" onClick={() => onOpen(k.case_id, k.key)}>Open</button>
            </span>
          </li>
        ))}
      </ul>
      <button type="button" className="btn btn-primary" onClick={() => { removeLegacyKeys(); setKeys([]); }}>
        I've kept them: remove them from this browser
      </button>
    </Card>
  );
}

export default function CheckReport() {
  const { user } = useAuth();
  if (draft.owner !== user.id) Object.assign(draft, { owner: user.id, caseId: "", key: "" });
  const [caseId, setCaseIdState] = useState(draft.caseId);
  const [key, setKeyState] = useState(draft.key);
  const setCaseId = (value) => { draft.caseId = value; setCaseIdState(value); };
  const setKey = (value) => { draft.key = value; setKeyState(value); };

  /** Pasting text that holds both (e.g. from "Copy both" or the receipt) fills both boxes at once. */
  function smartPaste(e) {
    const text = e.clipboardData.getData("text");
    const foundCase = text.match(CASE_IN_TEXT)?.[0];
    const foundKey = text.replace(CASE_IN_TEXT, "").match(KEY_IN_TEXT)?.[0];
    if (!foundCase && !foundKey) return; // ordinary paste
    e.preventDefault();
    if (foundCase) setCaseId(foundCase.toUpperCase());
    if (foundKey) setKey(foundKey.toUpperCase());
  }
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  const [working, withWorking] = useAction();

  async function openCase(id, secret) {
    setError("");
    try {
      const opened = await api("/reports/access", { method: "POST", body: { case_id: id, key: secret } });
      draft.caseId = ""; draft.key = ""; // opened: nothing left to remember
      setReport(opened);
    } catch (err) {
      setError(err.message);
    }
  }

  if (report) {
    return (
      <>
        <PageHeader icon={FileSearch} title={`Report ${report.case_id}`} subtitle={`${report.category} · sent on ${report.created_on}`}
          actions={<CaseStatus status={report.status} />} />
        {report.outcome && <p className="alert alert-success">This case is closed. Outcome: <strong>{report.outcome}</strong></p>}
        <Card title="Your report"><p className="cleaned">{report.text}</p></Card>
        <ReporterEvidence report={report} secret={key} onChange={(evidence) => setReport((r) => ({ ...r, evidence }))} />
        <Card title="Conversation" subtitle="You appear as “Reporter” and HR as “Investigator”.">
          <Conversation messages={report.messages} me="reporter" />
          {report.status !== "closed" && <Reply caseId={report.case_id} secret={key} onSent={(messages) => setReport({ ...report, messages })} />}
        </Card>
        <button className="btn btn-plain" onClick={() => { setReport(null); setKey(""); }}>Close this case</button>
      </>
    );
  }

  return (
    <>
      <PageHeader icon={FileSearch} title="Check my report" />
      <OldSavedKeys onOpen={(id, secret) => { setCaseId(id); setKey(secret); withWorking(() => openCase(id, secret)); }} />
      <form className="card narrow" onSubmit={(e) => { e.preventDefault(); withWorking(() => openCase(caseId, key)); }}>
        <p className="muted">Enter the case ID and secret key you kept when you sent the report (from the receipt or your password manager). After five wrong keys, a case is locked for 15 minutes.</p>
        <p className="muted small">Tip: paste a copied “Case ID … Key …” into either box and both are filled in.</p>
        {error && <p className="alert alert-error" role="alert">{error}</p>}
        <label className="field">Case ID<input className="mono" value={caseId} onChange={(e) => setCaseId(e.target.value)} onPaste={smartPaste} placeholder="R-XXXX-XXXX" required autoComplete="username" /></label>
        <label className="field">Secret key<input className="mono" type="password" value={key} onChange={(e) => setKey(e.target.value)} onPaste={smartPaste} placeholder="XXXX-XXXX-XXXX-XXXX" required autoComplete="current-password" /></label>
        <Button busy={working} busyText="Opening…">Open my report</Button>
      </form>
    </>
  );
}
