// Open your report with its case ID and secret key, read the investigator's replies, and reply.
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { FileSearch } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Button, Card, PageHeader } from "../../components/ui";
import { markSeen } from "../../keyStore";
import Conversation, { CaseStatus } from "../../components/reporting/Conversation";
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

// What's been typed or pasted so far, kept in memory while moving between pages (e.g. to "My report keys" to copy
// the key after pasting the case ID). Never written to storage; gone when the tab closes, and never shown to
// another account signing in on the same tab.
const draft = { owner: null, caseId: "", key: "" };
const CASE_IN_TEXT = /R-[A-Z2-9]{4}-[A-Z2-9]{4}/i;
const KEY_IN_TEXT = /\b(?:[A-Z2-9]{4}-){3}[A-Z2-9]{4}\b/i;

export default function CheckReport() {
  const { state } = useLocation(); // set when opened from "My report keys"; never put in the address bar
  const { user } = useAuth();
  if (draft.owner !== user.id) Object.assign(draft, { owner: user.id, caseId: "", key: "" });
  const [caseId, setCaseIdState] = useState(state?.case_id || draft.caseId);
  const [key, setKeyState] = useState(state?.key || draft.key);
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
      markSeen(opened.case_id, opened.messages.length, opened.status);
      draft.caseId = ""; draft.key = ""; // opened: nothing left to remember
      setReport(opened);
    } catch (err) {
      setError(err.message);
    }
  }

  // Opened from a saved key: go straight to the case
  useEffect(() => { if (state?.case_id && state?.key) openCase(state.case_id, state.key); }, [state]);

  if (report) {
    return (
      <>
        <PageHeader icon={FileSearch} title={`Report ${report.case_id}`} subtitle={`${report.category} · sent on ${report.created_on}`}
          actions={<CaseStatus status={report.status} />} />
        {report.outcome && <p className="alert alert-success">This case is closed. Outcome: <strong>{report.outcome}</strong></p>}
        <Card title="Your report"><p className="cleaned">{report.text}</p></Card>
        <Card title="Conversation" subtitle="You appear as “Reporter”. HR never learns who you are, and you see them only as “Investigator”.">
          <Conversation messages={report.messages} me="reporter" />
          {report.status !== "closed" && <Reply caseId={report.case_id} secret={key} onSent={(messages) => { markSeen(report.case_id, messages.length, report.status); setReport({ ...report, messages }); }} />}
        </Card>
        <button className="btn btn-plain" onClick={() => { setReport(null); setKey(""); }}>Close this case</button>
      </>
    );
  }

  return (
    <>
      <PageHeader icon={FileSearch} title="Check my report" subtitle="Open your report with the case ID and secret key you saved." />
      <form className="card narrow" onSubmit={(e) => { e.preventDefault(); withWorking(() => openCase(caseId, key)); }}>
        <p className="muted">Enter the case ID and secret key you saved when you sent the report, or open it from <Link to="/report-keys">My report keys</Link>. After five wrong keys, a case is locked for 15 minutes.</p>
        <p className="muted small">Tip: paste a copied “Case ID … Key …” into either box and both are filled in.</p>
        {error && <p className="alert alert-error" role="alert">{error}</p>}
        <label className="field">Case ID<input className="mono" value={caseId} onChange={(e) => setCaseId(e.target.value)} onPaste={smartPaste} placeholder="R-XXXX-XXXX" required autoComplete="username" /></label>
        <label className="field">Secret key<input className="mono" type="password" value={key} onChange={(e) => setKey(e.target.value)} onPaste={smartPaste} placeholder="XXXX-XXXX-XXXX-XXXX" required autoComplete="current-password" /></label>
        <Button busy={working} busyText="Opening…">Open my report</Button>
      </form>
    </>
  );
}
