// Ways to keep a case ID and key: download, copy, or a password manager. The website itself never keeps it.
import { useState } from "react";
import { Copy, Download, KeyRound } from "lucide-react";
import { canUsePasswordManager, downloadReceipt, saveToPasswordManager } from "../../keyStore";

export default function KeepKey({ caseId, secret }) {
  const [done, setDone] = useState("");

  const flash = (message) => { setDone(message); setTimeout(() => setDone(""), 2500); };

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

      {done && <p className="small strong" role="status">{done}</p>}
    </div>
  );
}
