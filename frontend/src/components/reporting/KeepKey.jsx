// Ways to keep a case ID and key: save on this device, download, copy, or a password manager.
import { useState } from "react";
import { Check, Copy, Download, KeyRound, Smartphone } from "lucide-react";
import { canUsePasswordManager, downloadReceipt, isSaved, saveKey, saveToPasswordManager } from "../../keyStore";

export default function KeepKey({ caseId, secret }) {
  const [onDevice, setOnDevice] = useState(isSaved(caseId));
  const [confirming, setConfirming] = useState(false);
  const [done, setDone] = useState("");

  const flash = (message) => { setDone(message); setTimeout(() => setDone(""), 2500); };

  function save() {
    if (saveKey(caseId, secret)) { setOnDevice(true); setConfirming(false); flash("Saved on this device."); }
    else flash("This browser won't store it (private window?). Use another option.");
  }

  async function passwordManager() {
    try { await saveToPasswordManager(caseId, secret); flash("Sent to your browser's password manager."); }
    catch { flash("Your browser didn't save it. Try downloading instead."); }
  }

  async function copy() {
    try { await navigator.clipboard.writeText(`Case ID: ${caseId}\nKey: ${secret}`); flash("Copied. Paste it somewhere safe."); }
    catch { flash("Couldn't copy. Select the text above instead."); }
  }

  return (
    <div className="keep">
      <div className="keep-options">
        <button type="button" className="keep-option" onClick={() => (onDevice ? null : setConfirming(true))} disabled={onDevice}>
          {onDevice ? <Check size={18} /> : <Smartphone size={18} />}
          <span><strong>{onDevice ? "Saved on this device" : "Save on this device"}</strong><span className="muted small">Find it later under My report keys</span></span>
        </button>
        <button type="button" className="keep-option" onClick={() => downloadReceipt(caseId, secret)}>
          <Download size={18} /><span><strong>Download a receipt</strong><span className="muted small">A small text file</span></span>
        </button>
        {canUsePasswordManager() && (
          <button type="button" className="keep-option" onClick={passwordManager}>
            <KeyRound size={18} /><span><strong>Password manager</strong><span className="muted small">Encrypted, on your devices</span></span>
          </button>
        )}
        <button type="button" className="keep-option" onClick={copy}>
          <Copy size={18} /><span><strong>Copy</strong><span className="muted small">Paste it somewhere safe</span></span>
        </button>
      </div>

      {confirming && (
        <div className="alert alert-warning">
          <strong>Only save it on a device nobody else uses.</strong> Anyone who uses this browser could open
          "My report keys" and read your case. On a shared or work computer, download it or use your own password
          manager instead.
          <div className="row" style={{ marginTop: 10 }}>
            <button type="button" className="btn btn-primary" onClick={save}>It's my own device, save it</button>
            <button type="button" className="btn btn-plain" onClick={() => setConfirming(false)}>Cancel</button>
          </div>
        </div>
      )}
      {done && <p className="small strong" role="status">{done}</p>}
    </div>
  );
}
