// My report keys: the case IDs and keys saved on this device, kept only in this browser.
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Copy, Download, KeyRound, ShieldCheck, Trash2 } from "lucide-react";
import { Card, EmptyState, PageHeader } from "../../components/ui";
import { downloadReceipt, forgetKey, saveKey, savedKeys } from "../../keyStore";

const CASE = /^R-[A-Z2-9]{4}-[A-Z2-9]{4}$/;
const KEY = /^([A-Z2-9]{4}-){3}[A-Z2-9]{4}$/;

/** A small copy button that says "Copied" for a moment, so it's clear the copy worked. */
function CopyButton({ label, done, onClick }) {
  return (
    <button type="button" className={`btn btn-plain copy-btn ${done ? "copied" : ""}`} onClick={onClick} aria-live="polite">
      {done ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}{done ? "Copied" : label}
    </button>
  );
}

export default function ReportKeys() {
  const navigate = useNavigate();
  const [keys, setKeys] = useState(savedKeys);
  const [shown, setShown] = useState(null);      // the case whose key is revealed
  const [form, setForm] = useState({ case_id: "", key: "", note: "" });
  const [message, setMessage] = useState("");
  const [copied, setCopied] = useState(""); // which value was just copied, e.g. "R-AB12-CD34:key"

  async function copy(text, what) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(what);
      setTimeout(() => setCopied((current) => (current === what ? "" : current)), 2000);
    } catch {
      setMessage("Your browser didn't allow copying. Use Show key and copy it by hand.");
    }
  }

  const refresh = () => setKeys(savedKeys());

  function add(e) {
    e.preventDefault();
    const caseId = form.case_id.trim().toUpperCase();
    const key = form.key.trim().toUpperCase();
    if (!CASE.test(caseId) || !KEY.test(key)) return setMessage("That doesn't look like a case ID (R-XXXX-XXXX) and key (XXXX-XXXX-XXXX-XXXX).");
    setMessage(saveKey(caseId, key, form.note) ? "Saved." : "This browser won't store it (private window?).");
    setForm({ case_id: "", key: "", note: "" });
    refresh();
  }

  function forget(caseId) {
    if (!window.confirm(`Remove ${caseId} from this device? Make sure you've kept the key somewhere else.`)) return;
    forgetKey(caseId);
    refresh();
  }

  return (
    <>
      <PageHeader icon={KeyRound} title="My report keys"  />

      <Card flush title={`Saved on this device (${keys.length})`} subtitle="Kept in this browser only, never sent to the server.">
        {keys.length === 0 ? (
          <EmptyState icon={KeyRound} title="No keys saved here" text="When you send a report, choose “Save on this device”, or add a key you wrote down below." />
        ) : (
          <ul className="key-list">
            {keys.map((k) => (
              <li key={k.case_id}>
                <div>
                  <div className="mono strong">{k.case_id}</div>
                  <div className="muted small">{k.note ? `${k.note} · ` : ""}saved {k.saved_on}</div>
                  <button type="button" className="link-btn mono small" onClick={() => setShown(shown === k.case_id ? null : k.case_id)}>
                    {shown === k.case_id ? k.key : "Show key"}
                  </button>
                </div>
                <div className="actions">
                  <button className="btn btn-primary" onClick={() => navigate("/my-report", { state: { case_id: k.case_id, key: k.key } })}>Open</button>
                  <CopyButton label="Copy case ID" done={copied === `${k.case_id}:id`} onClick={() => copy(k.case_id, `${k.case_id}:id`)} />
                  <CopyButton label="Copy key" done={copied === `${k.case_id}:key`} onClick={() => copy(k.key, `${k.case_id}:key`)} />
                  <CopyButton label="Copy both" done={copied === `${k.case_id}:both`} onClick={() => copy(`Case ID: ${k.case_id}\nKey: ${k.key}`, `${k.case_id}:both`)} />
                  <button className="icon-btn" title="Download" aria-label={`Download ${k.case_id}`} onClick={() => downloadReceipt(k.case_id, k.key)}><Download size={16} /></button>
                  <button className="icon-btn" title="Forget on this device" aria-label={`Forget ${k.case_id}`} onClick={() => forget(k.case_id)}><Trash2 size={16} /></button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="two-columns">
        <Card title="Add a key you wrote down">
          <form onSubmit={add}>
            <label className="field">Case ID<input className="mono" value={form.case_id} onChange={(e) => setForm({ ...form, case_id: e.target.value })} placeholder="R-XXXX-XXXX" required autoComplete="off" /></label>
            <label className="field">Secret key<input className="mono" value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} placeholder="XXXX-XXXX-XXXX-XXXX" required autoComplete="off" /></label>
            <label className="field">Note for yourself <span className="muted small">(optional, avoid details)</span><input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} maxLength={40} /></label>
            {message && <p className="small strong" role="status">{message}</p>}
            <button className="btn btn-primary">Save on this device</button>
          </form>
        </Card>
        <Card title="Opening a case">
          <ul className="tips-list">
            <li><ShieldCheck size={16} /><span><strong>Open</strong> fills everything in for you.</span></li>
            <li><ShieldCheck size={16} /><span><strong>Copy both</strong>, then paste once into either box on Check my report: both boxes are filled.</span></li>
            <li><ShieldCheck size={16} /><span>Copying one at a time? What you've already pasted stays there while you come back here for the other.</span></li>
          </ul>
        </Card>
        <Card title="Keeping keys safe">
          <ul className="tips-list">
            <li><ShieldCheck size={16} /><span><strong>Own device only.</strong> Anyone using this browser can open this page.</span></li>
            <li><ShieldCheck size={16} /><span><strong>A password manager is best:</strong> encrypted and on your own devices.</span></li>
            <li><ShieldCheck size={16} /><span><strong>On paper?</strong> Keep it somewhere private, not on your desk.</span></li>
            <li><ShieldCheck size={16} /><span><strong>Lost it?</strong> It can't be recovered, but you can always make a new report.</span></li>
          </ul>
        </Card>
      </div>
    </>
  );
}
