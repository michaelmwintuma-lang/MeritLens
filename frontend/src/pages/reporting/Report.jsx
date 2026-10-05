// Report anonymously, in three steps: write it, check what will be sent, save your case ID and key.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { Megaphone } from "lucide-react";
import { Button, PageHeader } from "../../components/ui";
import KeepKey from "../../components/reporting/KeepKey";
import { EvidencePicker, EvidenceUploader } from "../../components/reporting/Evidence";
import { useAction } from "../../useAction";

/** Shows the cleaned text with the replacement tags highlighted. */
function Highlighted({ text }) {
  return <p className="cleaned">{text.split(/(\[(?:PERSON|EMAIL|PHONE|DATE) \d+\])/).map((part, i) =>
    /^\[(PERSON|EMAIL|PHONE|DATE) \d+\]$/.test(part) ? <mark key={i}>{part}</mark> : part)}</p>;
}

export default function Report() {
  const [categories, setCategories] = useState([]); // [{ group, items: [{ value, label }] }]
  const [step, setStep] = useState(1);
  const [category, setCategory] = useState("");
  const [draft, setDraft] = useState("");
  const [check, setCheck] = useState(null);      // the anonymiser's answer for the current text
  const [edited, setEdited] = useState("");       // the cleaned text, which the reporter may edit
  const [confirmed, setConfirmed] = useState(false);
  const [receipt, setReceipt] = useState(null);   // case ID and key, shown once
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [files, setFiles] = useState([]);         // photos and videos chosen, uploaded after the report is sent
  const [uploading, setUploading] = useState(false);

  useEffect(() => { api("/reports/categories").then(setCategories).catch((err) => setError(err.message)); }, []);

  const [checking, withChecking] = useAction();
  const [sending, withSending] = useAction();

  async function runCheck(text) {
    setError("");
    try {
      const result = await api("/reports/preview", { method: "POST", body: { text } });
      setCheck({ ...result, checkedText: result.text });
      setEdited(result.text);
      setConfirmed(false);
      setStep(2);
    } catch (err) {
      setError(err.message);
    }
  }

  async function send() {
    setError("");
    try {
      setReceipt(await api("/reports", { method: "POST", body: { category, text: edited } }));
      setDraft("");
      setEdited("");
      setUploading(files.length > 0);
      setStep(3);
    } catch (err) {
      setError(err.message);
    }
  }

  const editedSinceCheck = check && edited !== check.checkedText;

  return (
    <>
      <PageHeader icon={Megaphone} title="Report anonymously"
        subtitle="Raise any workplace concern: how people are treated, safety and wellbeing, or honesty and the law. Your report is never linked to your account." />
      <ol className="steps" aria-label="Steps">
        <li className={step === 1 ? "current" : ""}>1. Write</li>
        <li className={step === 2 ? "current" : ""}>2. Check what will be sent</li>
        <li className={step === 3 ? "current" : ""}>3. Save your key</li>
      </ol>
      {error && <p className="alert alert-error" role="alert">{error}</p>}

      {step === 1 && (
        <div className="card">
          <p className="alert alert-info">
            Your report is <strong>not linked to your account</strong>. You need to be signed in so only members of the
            organisation can report, but your name, account and the time are never saved with it. Only the day is.
          </p>
          <label className="field"><span>What is it about? <span className="muted small">(if it fits more than one, choose the most serious)</span></span>
            <select value={category} onChange={(e) => setCategory(e.target.value)} required>
              <option value="">Choose a category</option>
              {categories.map(({ group, items }) => (
                <optgroup key={group} label={group}>
                  {items.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
                </optgroup>
              ))}
            </select>
          </label>
          <label className="field">What happened? <span className="muted small">(at least 20 characters)</span>
            <textarea rows={8} value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={5000}
              placeholder="Describe what happened, how often, and how it affected you or others." />
          </label>
          <p className="muted small">Names, emails, phone numbers and dates are removed automatically in the next step, before anything is sent.</p>
          <h3 className="form-subhead">Evidence</h3>
          <EvidencePicker files={files} setFiles={setFiles} />
          <Button busy={checking} busyText="Removing names and details…" disabled={!category || draft.trim().length < 20} onClick={() => withChecking(() => runCheck(draft))}>Check what will be sent</Button>
        </div>
      )}

      {step === 2 && check && (
        <div className="card">
          <h2>This is what HR will see</h2>
          <Highlighted text={check.text} />
          {check.replaced.length > 0 && (
            <>
              <h3>Removed</h3>
              <ul className="small">{check.replaced.map((r, i) => <li key={i}>"{r.original}" → {r.tag}</li>)}</ul>
              <p className="muted small">This list is only shown to you. It isn't sent or saved.</p>
            </>
          )}
          {check.warnings.length > 0 && (
            <div className="alert alert-warning">
              <strong>These phrases could identify you.</strong> Consider rewording them:
              <ul>{check.warnings.map((w, i) => <li key={i}>"{w.phrase}" · {w.reason}</li>)}</ul>
            </div>
          )}
          <label className="field">You can edit the text before sending
            <textarea rows={8} value={edited} onChange={(e) => setEdited(e.target.value)} maxLength={5000} />
          </label>
          {editedSinceCheck && <p className="alert alert-info">You changed the text. Check it again before sending.</p>}
          {files.length > 0 && (
            <p className="alert alert-info">
              {files.length} {files.length === 1 ? "file" : "files"} will be added after the report is sent, with their hidden
              details removed. Go <button type="button" className="link-btn" onClick={() => setStep(1)}>back</button> to look at them again.
            </p>
          )}
          <label className="check"><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
            I've read this{files.length > 0 ? " and checked my photos and videos," : ""} and it doesn't contain anything that identifies me.</label>
          <div className="row">
            <button className="btn btn-plain" onClick={() => setStep(1)}>Back</button>
            {editedSinceCheck
              ? <Button busy={checking} busyText="Checking…" onClick={() => withChecking(() => runCheck(edited))}>Check again</Button>
              : <Button busy={sending} busyText="Sending securely…" disabled={!confirmed} onClick={() => withSending(send)}>Send report</Button>}
          </div>
        </div>
      )}

      {step === 3 && receipt && (
        <div className="card">
          <h2>Your report has been sent</h2>
          <p>To follow up or read HR's replies, you'll need both of these:</p>
          <div className="receipt">
            <div><span className="muted small">Case ID</span><div className="mono big">{receipt.case_id}</div></div>
            <div><span className="muted small">Secret key</span><div className="mono big">{receipt.key}</div></div>
          </div>
          <p className="alert alert-warning">
            <strong>Keep these somewhere safe now.</strong> The key is shown only once. It isn't linked to your account,
            so if you lose it, nobody (not even an administrator) can recover it.
          </p>
          {files.length > 0 && (
            <>
              <h3>Adding your evidence</h3>
              {uploading && <p className="muted small">Please keep this page open until every file is added.</p>}
              <EvidenceUploader caseId={receipt.case_id} secret={receipt.key} files={files} onFinished={() => setUploading(false)} />
              <p className="muted small">If a file wasn't added, you can add it later from <strong>Check my report</strong>.</p>
            </>
          )}
          <h3>Choose how to keep it</h3>
          <KeepKey caseId={receipt.case_id} secret={receipt.key} />
          <label className="check" style={{ marginTop: 16 }}><input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} /> I've kept my case ID and key.</label>
          {saved && <p className="row"><Link to="/my-report">Check my report</Link> · <Link to="/report-keys">My report keys</Link> · <button className="btn btn-plain" onClick={() => { setReceipt(null); setSaved(false); setCategory(""); setFiles([]); setStep(1); }}>Make another report</button></p>}
        </div>
      )}
    </>
  );
}
