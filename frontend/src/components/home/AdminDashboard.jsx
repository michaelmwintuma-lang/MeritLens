// The administrator's home: what needs attention, accounts, system health (API, model, release status, fairness at
// training and live, drift, email), recent activity and quick actions. Totals and distributions only, never an
// employee's record.
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, CircleAlert, Info, KeyRound, Mail, ScrollText, ShieldCheck, TriangleAlert, UserPlus } from "lucide-react";
import { ROLE_NAMES } from "../../roles";
import { Card, StatCard } from "../ui";
import Attention, { plural } from "../governance/Attention";
import { STATUS_TAG } from "../../pages/governance/LiveFairness";

const LEVEL_TAG = { stable: "tag tag-yes", "moderate shift": "tag tag-warn", "large shift": "tag tag-off", "too few records": "tag" };

// One row of system health: an icon and a word for its state, what it is, and the detail underneath
const STATES = { ok: [CheckCircle2, "OK"], problem: [CircleAlert, "Problem"], warn: [TriangleAlert, "Check"], info: [Info, "Note"] };
function Health({ state, label, children }) {
  const [Icon, word] = STATES[state];
  return (
    <li>
      <Icon size={18} aria-hidden="true" className={state} />
      <span><strong>{word}:</strong> {label}</span>
      {children && <span className="health-detail">{children}</span>}
    </li>
  );
}
const FAIRNESS_STATE = { passes: "ok", "below four-fifths": "warn", "within chance": "info", "not enough data": "info" };

export default function AdminDashboard({ system, employees, fairness: live, models = [] }) {
  const { accounts, model, fairness, drift, email, backup } = system;
  const backupAge = backup ? (Date.now() - Date.parse(backup.made_at)) / 3_600_000 : null; // hours
  const candidates = models.filter((m) => m.status === "candidate");
  const attention = [
    accounts.locked && { key: "locked", text: `${plural(accounts.locked, "account")} locked after wrong passwords`, detail: "Unlocks after 15 minutes, or reset the password.", to: "/admin/users", action: "Users", tone: "warn" },
    drift && drift.status !== "stable" && drift.status !== "too few records" && { key: "drift", text: `Drift: ${drift.status}`, detail: "Today's employees differ from the ones the model learned from.", to: "/", action: "See below", tone: "warn" },
    live?.overall === "below four-fifths" && { key: "fair", text: "A live fairness check is below four-fifths", to: "/fairness", action: "Open", tone: "warn" },
    candidates.length && { key: "model", text: `A model version is waiting for HR's release (${candidates[0].version})`, detail: "Only HR can release it; you can read its card.", to: "/models", action: "Model registry", tone: "info" },
    !email.configured && { key: "email", text: "Email is saved to the outbox, not sent", detail: "Set up a mail server so people receive their notifications.", to: "/admin/email", action: "Email settings", tone: "info" },
  ];
  return (
    <>
      <Attention items={attention} />
      <div className="stat-grid">
        <StatCard label="Active accounts" value={accounts.active} note={`${accounts.deactivated} deactivated`} />
        <StatCard label="Locked now" value={accounts.locked} note="After 5 wrong passwords; unlocks after 15 minutes or a reset" />
        <StatCard label="Must change password" value={accounts.must_change_password} note="New or reset accounts" />
        <StatCard label="Employees with a login" value={employees.filter((e) => e.login).length} note={`of ${employees.length} in the directory`} />
      </div>

      <Card title="Quick actions">
        <div className="form-actions">
          <Link className="btn btn-primary" to="/admin/users"><UserPlus size={16} aria-hidden="true" />Create a user</Link>
          <Link className="btn btn-secondary" to="/admin/users"><KeyRound size={16} aria-hidden="true" />Reset a password</Link>
          <Link className="btn btn-secondary" to="/admin/activity"><ScrollText size={16} aria-hidden="true" />Activity log</Link>
          <Link className="btn btn-secondary" to="/audit"><ShieldCheck size={16} aria-hidden="true" />Audit trail</Link>
          <Link className="btn btn-secondary" to="/admin/email"><Mail size={16} aria-hidden="true" />Email settings</Link>
        </div>
      </Card>

      <div className="two-cards">
        <Card title="Accounts by role" subtitle="Active accounts only.">
          <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Accounts by role"><table>
            <thead><tr><th>Role</th><th className="num">Active accounts</th></tr></thead>
            <tbody>{Object.entries(accounts.by_role).map(([role, n]) => <tr key={role}><td>{ROLE_NAMES[role]}</td><td className="num strong">{n}</td></tr>)}</tbody>
          </table></div>
        </Card>

        <Card title="System health" subtitle="The model, the fairness gate, releases and email.">
          <ul className="health-list">
            <Health state={system.api === "ok" ? "ok" : "problem"} label="Web API" />
            <Health state={model.loaded ? "ok" : "problem"} label="Promotion model">
              {model.loaded ? `${model.model}, version ${model.version}, trained ${model.trained_at.slice(0, 10)}; test prediction ${model.test_prediction_ms} ms` : model.message}
            </Health>
            {fairness
              ? <Health state={fairness.passes ? "ok" : "problem"} label="Fairness gate at training">
                  Lowest ratios: {Object.entries(fairness.ratios).map(([k, v]) => `${k.replace("_", " ")} ${v.toFixed(2)}`).join(", ")} (needs 0.80)
                </Health>
              : <Health state="info" label="Fairness gate: not run" />}
            {live && <Health state={FAIRNESS_STATE[live.overall] || "info"} label={`Live fairness: ${(STATUS_TAG[live.overall] || [null, live.overall])[1]}`}>
              The model, nominations and approvals. <Link to="/fairness">Details</Link>
            </Health>}
            <Health state={candidates.length ? "info" : "ok"} label={`Model release: ${candidates.length ? `${candidates.length} waiting for HR` : "up to date"}`}>
              <Link to="/models">Model registry</Link>
            </Health>
            <Health state={email.configured ? "ok" : "warn"} label={`Email: ${email.configured ? "sending" : "saved to the outbox, not sent"}`}>
              {email.configured ? `From ${email.sender}` : `${email.outbox_count} saved`}
            </Health>
            <Health state={backup == null ? "warn" : backupAge > 36 ? "warn" : "ok"}
              label={backup ? `Backups: last ${backup.made_at.replace("T", " ").slice(0, 16)} UTC` : "Backups: none yet"}>
              {backup ? `${backup.count} kept in ${backup.folder}; copy them to another disk too.` : "Made every night while the app runs, or by hand (docs/BACKUPS.md)."}
            </Health>
          </ul>
        </Card>
      </div>

      {drift && (
        <Card title="Drift: are today's employees like the ones the model learned from?"
          subtitle={`Population stability index (PSI) of each input, for the ${drift.records} employees in the directory against the training sample.`}
          actions={<span className={LEVEL_TAG[drift.status]}>{drift.status}</span>}>
          {drift.inputs.length > 0 && (
            <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Drift per input"><table>
              <thead><tr><th>Input</th><th className="num">PSI</th><th className="num">PSI from chance alone</th><th>Level</th></tr></thead>
              <tbody>{drift.inputs.slice(0, 6).map((r) => (
                <tr key={r.feature}><td>{r.feature.replaceAll("_", " ")}</td><td className="num strong">{r.psi.toFixed(3)}</td>
                  <td className="num">{r.chance_psi.toFixed(3)}</td><td><span className={LEVEL_TAG[r.level]}>{r.level}</span></td></tr>
              ))}</tbody>
            </table></div>
          )}
          <p className="muted section-gap">{drift.note} Below 0.1 is usually stable; above 0.25 is a large shift. The model is never retrained automatically.</p>
        </Card>
      )}

      <Card title="Recent activity" actions={<Link to="/admin/activity" className="text-link">Full activity log <ArrowRight size={16} aria-hidden="true" /></Link>}>
        {system.recent_activity.length === 0 ? <p className="muted">Nothing yet.</p> : (
          <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Recent activity"><table>
            <thead><tr><th>Day</th><th>Who</th><th>What</th></tr></thead>
            <tbody>{system.recent_activity.map((e, i) => (
              <tr key={i}><td className="nowrap muted">{e.date}</td><td>{e.user}</td><td>{e.action}{e.details && <span className="muted"> · {e.details}</span>}</td></tr>
            ))}</tbody>
          </table></div>
        )}
      </Card>
    </>
  );
}

