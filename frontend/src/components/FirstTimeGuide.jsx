// The first time someone signs in: what their role can do here, in a few steps, each with a link straight to it.
// Closing it is remembered on their account (every device); My profile can show it again.
import { Link } from "react-router-dom";
import { Compass, X } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";

const STEPS = {
  employee: [
    ["/my-readiness", "See your readiness score", "and the measures that raise or lower it, in plain words."],
    ["/my-readiness", "Try the tips", "to see which changes would move your score most."],
    ["/my-readiness", "Something wrong in your record?", "Ask HR to correct it, with evidence. Nothing changes until HR checks."],
    ["/model", "How the model works", "what it looks at, what it never looks at, and its limits."],
  ],
  manager: [
    ["/team", "Open My team", "to see each person's readiness score and why."],
    ["/team", "Recommend someone", "for promotion: the model only advises, you decide whom to nominate."],
    ["/nominations", "Follow your nominations", "until HR decides."],
    ["/team", "Away soon?", "Arrange cover on My team, so your team isn't left waiting."],
  ],
  hr: [
    ["/cycles", "Open a review cycle", "so everyone is scored once, by the same model, and saved."],
    ["/nominations", "Decide on nominations", "with the model's reasons and the manager's case side by side."],
    ["/corrections", "Check record corrections", "employees asked for, with their evidence."],
    ["/models", "Release new model versions", "after reading their model card and what would change."],
  ],
  admin: [
    ["/admin/users", "Create the real accounts", "each person gets a temporary password by email."],
    ["/admin/email", "Set up email", "and send a test, so people get their notifications."],
    ["/", "Watch system health", "here: the model, fairness, backups and errors."],
    ["/audit", "Check the audit trail", "is intact, now and then."],
  ],
  finance: [
    ["/finance", "Sign off pay rises", "of approved promotions, or send one back to HR with a reason."],
    ["/finance", "Send signed-off rises to payroll", "as a file, so each is applied once."],
  ],
  auditor: [
    ["/decisions", "Read the decision log", "every decision with the model's advice and HR's reason."],
    ["/audit", "Check the audit trail", "a tamper-evident record of every change."],
    ["/fairness", "Watch live fairness", "for the model, managers and HR."],
    ["/models", "Read the model cards", "test results, fairness and limitations of each version."],
  ],
};

export default function FirstTimeGuide() {
  const { user, setUser } = useAuth();
  const steps = STEPS[user.role];
  if (user.guide_done || !steps) return null;

  async function close() {
    try { setUser(await api("/auth/guide", { method: "PUT", body: { done: true } })); }
    catch { setUser({ ...user, guide_done: true }); } // hidden for now; it shows again next time
  }

  return (
    <section className="card highlight guide" aria-labelledby="guide-title">
      <div className="card-head">
        <div>
          <h2 id="guide-title"><Compass size={20} aria-hidden="true" />Getting started</h2>
          <p className="card-sub">What you can do here, in {steps.length} steps. You can bring this back from My profile.</p>
        </div>
        <button type="button" className="btn btn-ghost" onClick={close} aria-label="Close the getting-started guide"><X size={18} aria-hidden="true" /></button>
      </div>
      <ol className="guide-steps">
        {steps.map(([to, title, text]) => (
          <li key={title}><Link to={to} className="strong">{title}</Link> <span className="muted">{text}</span></li>
        ))}
      </ol>
    </section>
  );
}
