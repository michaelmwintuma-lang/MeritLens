// The administrator's home: what needs attention, accounts, system health (API, model, release status, fairness at
// training and live, drift, email), recent activity and quick actions. Totals and distributions only, never an
// employee's record.
import { Link } from "react-router-dom";
import { Activity, ArrowRight, KeyRound, Mail, ScrollText, ShieldCheck, UserPlus } from "lucide-react";
import { ROLE_NAMES } from "../../roles";
import { Card, StatCard } from "../ui";
import Attention, { plural } from "../governance/Attention";
import { StatusTag } from "../../pages/governance/LiveFairness";

const LEVEL_TAG = { stable: "tag tag-yes", "moderate shift": "tag tag-warn", "large shift": "tag tag-off", "too few records": "tag" };

function Health({ ok, children }) {
  return <span className={ok ? "tag tag-yes" : "tag tag-off"}>{ok ? "OK" : "Problem"}: {children}</span>;
}

export default function AdminDashboard({ system, employees, fairness: live, models = [] }) {
  const { accounts, model, fairness, drift, email } = system;
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
        <div className="row">
          <Link className="btn btn-primary" to="/admin/users"><UserPlus size={16} aria-hidden="true" />Create a user</Link>
          <Link className="btn btn-plain" to="/admin/users"><KeyRound size={16} aria-hidden="true" />Reset a password</Link>
          <Link className="btn btn-plain" to="/admin/activity"><ScrollText size={16} aria-hidden="true" />Activity log</Link>
          <Link className="btn btn-plain" to="/audit"><ShieldCheck size={16} aria-hidden="true" />Audit trail</Link>
          <Link className="btn btn-plain" to="/admin/email"><Mail size={16} aria-hidden="true" />Email settings</Link>
        </div>
      </Card>

      <div className="two-cards">
        <Card title="Accounts by role" subtitle="Active accounts only.">
          <div className="table-wrap" tabIndex={0}><table>
            <tbody>{Object.entries(accounts.by_role).map(([role, n]) => <tr key={role}><td>{ROLE_NAMES[role]}</td><td className="strong">{n}</td></tr>)}</tbody>
          </table></div>
        </Card>

        <Card title="System health" actions={<Activity size={20} aria-hidden="true" className="feedback-icon" />}>
          <ul className="plain-list">
            <li><Health ok={system.api === "ok"}>web API</Health></li>
            <li><Health ok={model.loaded}>promotion model</Health>{" "}
              {model.loaded
                ? <span className="small">{model.model}, version {model.version}, trained {model.trained_at.slice(0, 10)}; test prediction {model.test_prediction_ms} ms</span>
                : <span className="small">{model.message}</span>}</li>
            <li>{fairness ? <Health ok={fairness.passes}>fairness at training</Health> : <span className="tag">Fairness gate: not run</span>}{" "}
              {fairness && <span className="small">lowest ratios: {Object.entries(fairness.ratios).map(([k, v]) => `${k.replace("_", " ")} ${v.toFixed(2)}`).join(", ")} (needs 0.80)</span>}</li>
            {live && <li><StatusTag status={live.overall} /> <span className="small">live fairness (model, nominations, approvals) · <Link to="/fairness">details</Link></span></li>}
            <li><span className={candidates.length ? "tag tag-info" : "tag tag-yes"}>Model release: {candidates.length ? `${candidates.length} waiting for HR` : "up to date"}</span>{" "}
              <span className="small"><Link to="/models">model registry</Link></span></li>
            <li><span className={email.configured ? "tag tag-yes" : "tag tag-warn"}>Email: {email.configured ? "sending" : "saved to the outbox, not sent"}</span>{" "}
              <span className="small">{email.configured ? `from ${email.sender}` : `${email.outbox_count} saved`}</span></li>
          </ul>
        </Card>
      </div>

      {drift && (
        <Card title="Drift: are today's employees like the ones the model learned from?"
          subtitle={`Population stability index (PSI) of each input, for the ${drift.records} employees in the directory against the training sample.`}
          actions={<span className={LEVEL_TAG[drift.status]}>{drift.status}</span>}>
          {drift.inputs.length > 0 && (
            <div className="table-wrap" tabIndex={0}><table>
              <thead><tr><th>Input</th><th>PSI</th><th>Chance alone reaches</th><th>Level</th></tr></thead>
              <tbody>{drift.inputs.slice(0, 6).map((r) => (
                <tr key={r.feature}><td>{r.feature.replaceAll("_", " ")}</td><td className="strong">{r.psi.toFixed(3)}</td>
                  <td>{r.chance_psi.toFixed(3)}</td><td><span className={LEVEL_TAG[r.level]}>{r.level}</span></td></tr>
              ))}</tbody>
            </table></div>
          )}
          <p className="muted small">{drift.note} Below 0.1 is usually stable; above 0.25 is a large shift. The model is never retrained automatically.</p>
        </Card>
      )}

      <Card title="Recent activity" actions={<Link to="/admin/activity" className="text-link">Full audit trail <ArrowRight size={16} aria-hidden="true" /></Link>}>
        {system.recent_activity.length === 0 ? <p className="muted">Nothing yet.</p> : (
          <div className="table-wrap" tabIndex={0}><table>
            <tbody>{system.recent_activity.map((e, i) => (
              <tr key={i}><td className="nowrap muted">{e.date}</td><td>{e.user}</td><td>{e.action}{e.details && <span className="muted small"> · {e.details}</span>}</td></tr>
            ))}</tbody>
          </table></div>
        )}
      </Card>
    </>
  );
}

