// Overview: first what needs your attention (each with one link straight to it), then the numbers that matter for
// your role, then the list you work from.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { api, governance } from "../api";
import { useAuth } from "../auth";
import { percent } from "../format";
import { Card, LoadError, PageHeader, PageLoading, StatCard } from "../components/ui";
import ScoreBar, { Verdict } from "../components/promotion/ScoreBar";
import NominationsTable from "../components/promotion/NominationsTable";
import AdminDashboard from "../components/home/AdminDashboard";
import Attention, { plural } from "../components/governance/Attention";
import { StatusTag } from "./governance/LiveFairness";

/** Fetch everything the overview needs for this role. */
async function loadOverview(user) {
  if (user.role === "hr" || user.role === "manager") {
    const hr = user.role === "hr";
    const [people, nominations, decisions, corrections, models] = await Promise.all([
      api("/promotion/employees"), api("/promotion/nominations"),
      hr ? api("/promotion/decisions") : null, hr ? api("/hr/feedback/corrections?status_filter=pending") : null,
      hr ? governance.models() : null,
    ]);
    return { people, nominations, decisions, corrections, models };
  }
  if (user.role === "finance") return { finance: await api("/finance/pay-reviews") };
  if (user.role === "auditor") {
    const [decisions, model, ratings, fairness, models] = await Promise.all([api("/promotion/decisions"),
      api("/public/summary"), api("/feedback/ratings/summary"), governance.fairness(), governance.models()]);
    return { decisions, model, ratings, fairness, models };
  }
  if (user.role === "employee") {
    if (!user.employee_id) return { me: null };
    const [me, requests] = await Promise.all([api(`/promotion/employees/${user.employee_id}`), api("/feedback/corrections/mine")]);
    return { me, requests };
  }
  const [system, employees, fairness, models] = await Promise.all([api("/admin/system"), api("/admin/employees"),
    governance.fairness(), governance.models()]);
  return { system, employees, fairness, models };
}

const waitingModels = (models) => (models || []).filter((m) => m.status === "candidate");

function PromotionOverview({ data, isHr }) {
  const { people, nominations, decisions, corrections, models } = data;
  const recommended = people.employees.filter((e) => e.recommended).length;
  const waiting = nominations.filter((n) => n.status === "pending").length;
  const nominatedIds = new Set(nominations.filter((n) => n.status !== "rejected").map((n) => n.employee.id));
  const notYetNominated = people.employees.filter((e) => e.recommended && !nominatedIds.has(e.id)).length;
  const returned = isHr ? decisions.filter((d) => d.pay_status === "returned").length : 0;
  const candidates = waitingModels(models);
  const attention = isHr ? [
    waiting && { key: "nom", text: `${plural(waiting, "nomination")} to decide`, detail: "Each with the model's view and the manager's reasons.", to: "/nominations", action: "Review" },
    corrections.length && { key: "cor", text: `${plural(corrections.length, "record correction")} to check`, detail: "Employees asked for a value in their record to be corrected.", to: "/corrections", action: "Check" },
    returned && { key: "pay", text: `${plural(returned, "pay rise")} sent back by Finance`, detail: "Revise and resubmit.", to: "/decisions", action: "Open", tone: "warn" },
    candidates.length && { key: "model", text: `A new model version is waiting for release (${candidates[0].version})`, detail: "Read its model card; it goes live only when you release it.", to: "/models", action: "Read the card", tone: "info" },
  ] : [
    notYetNominated && { key: "rec", text: `${plural(notYetNominated, "team member")} the model recommends, not nominated yet`, detail: "The model only advises: you decide whom to recommend.", to: "/team", action: "Open my team", tone: "info" },
    nominations.filter((n) => n.status === "finalising").length && { key: "fin", text: "A promotion you recommended is being finalised", detail: "HR approved it; Finance is signing off the pay rise.", to: "/nominations", action: "Open", tone: "info" },
  ];
  return (
    <>
      <Attention items={attention} />
      <div className="stat-grid">
        <StatCard label={isHr ? "Employees" : "Team members"} value={people.employees.length} note={isHr ? "In the directory" : "People you manage"} />
        <StatCard label="Recommended" value={recommended} note={`Above the ${percent(people.threshold)} threshold`} />
        <StatCard label="Waiting for HR" value={waiting} note={isHr ? "Nominations to review" : "Your nominations"} />
        {isHr
          ? <StatCard label="Decisions" value={decisions.length} note={`${decisions.filter((d) => !d.agrees_with_model).length} differ from the model`} />
          : <StatCard label="Decided" value={nominations.length - waiting} note="Your nominations with a decision" />}
      </div>
      <NominationsTable nominations={nominations} isHr={isHr}
        title={isHr ? "Nominations" : "My nominations"}
        subtitle={isHr ? "Open one to see the model's view and decide." : undefined} />
    </>
  );
}

function EmployeeOverview({ me, requests = [] }) {
  const waiting = requests.filter((r) => r.status === "pending").length;
  if (!me) return <Card title="Your account isn't linked yet"><p className="muted">Ask an administrator to link your login to your employee record.</p></Card>;
  const attention = [
    !me.recommended && { key: "path", text: "See the smallest realistic steps that would reach the threshold", detail: "Your path to promotion, worked out from your own record.", to: "/my-readiness", action: "My growth", tone: "info" },
    waiting && { key: "req", text: `${plural(waiting, "correction request")} waiting for HR`, detail: "You'll get an email when HR decides.", to: "/my-readiness", action: "Open", tone: "info" },
  ];
  return (
    <>
      <Attention items={attention} />
      <Card title="Where you stand" actions={<Verdict recommended={me.recommended} />}>
        <div className="score-big">{percent(me.score)}</div>
        <ScoreBar score={me.score} threshold={me.threshold} />
        <p className="summary section-gap">{me.summary}</p>
        <p className="muted">An average employee scores {percent(me.average_employee_score)}. The model only advises: people make every decision.</p>
        <Link className="btn btn-primary" to="/my-readiness">See why, try changes and get tips <ArrowRight size={16} aria-hidden="true" /></Link>
      </Card>
      <Card title="Respond to your explanation"
        subtitle="Rate whether it was clear and useful, or ask HR to correct a value in your record. Neither changes your score.">
        <p className="muted">{requests.length
          ? `Your correction requests: ${requests.length}, of which ${waiting} waiting for HR.`
          : "You haven't asked for a correction."}</p>
        <Link className="btn btn-secondary" to="/my-readiness">Open My growth to respond</Link>
      </Card>
    </>
  );
}

function FinanceOverview({ finance }) {
  const { summary, policy } = finance;
  const attention = [summary.awaiting && { key: "pay", text: `${plural(summary.awaiting, "pay rise")} to sign off`, detail: "Nobody is told about a promotion until you confirm its pay rise.", to: "/finance", action: "Review" }];
  return (
    <>
      <Attention items={attention} />
      <div className="stat-grid">
        <StatCard label="Waiting for you" value={summary.awaiting} note="Pay rises to sign off" />
        <StatCard label="Sent back to HR" value={summary.returned} note="Waiting for HR to revise" />
        <StatCard label="Signed off this year" value={summary.signed_off_this_year} note="Promotion pay rises confirmed" />
        <StatCard label="Average rise this year" value={summary.average_raise_this_year != null ? `${summary.average_raise_this_year}%` : "–"}
          note={`Policy: ${policy.min_raise}% to ${policy.max_raise}%`} />
      </div>
    </>
  );
}

function AuditorOverview({ data }) {
  const { decisions, model, ratings, fairness, models } = data;
  const differ = decisions.filter((d) => !d.agrees_with_model).length;
  const candidates = waitingModels(models);
  const attention = [
    fairness.overall === "below four-fifths" && { key: "fair", text: "A live fairness check is below four-fifths", detail: "See which stage: the model, managers' nominations or HR's approvals.", to: "/fairness", action: "Open", tone: "warn" },
    candidates.length && { key: "model", text: `A model version is waiting for HR's release (${candidates[0].version})`, detail: "Its model card is open to you, read-only.", to: "/models", action: "Read the card", tone: "info" },
  ];
  return (
    <>
      <Attention items={attention} />
      <div className="stat-grid">
        <StatCard label="Decisions" value={decisions.length} note="Promotion decisions in the log" />
        <StatCard label="Differ from the model" value={differ}
          note={decisions.length ? `${percent(differ / decisions.length)} of decisions, each with a written reason` : "No decisions yet"} />
        <StatCard label="Fairness at training" value={model.trained ? (model.fairness_passes ? "Passed" : "Failed") : "–"}
          note={model.trained ? `Lowest group ratio ${percent(model.lowest_fairness_ratio)} (needs 80%)` : "No model trained yet"} />
        <StatCard label="Explanations rated clear" value={ratings.clarity_rate == null ? "–" : percent(ratings.clarity_rate)}
          note={ratings.clarity_rate == null ? `${ratings.ratings} rating${ratings.ratings === 1 ? "" : "s"} so far: shown from 5` : `Of ${ratings.ratings} ratings, 4 or 5 out of 5`} />
      </div>
      <Card title="Live fairness" subtitle="The four-fifths rule on today's directory and decisions." actions={<StatusTag status={fairness.overall} />}>
        <p className="muted">Everything here is read-only for your role.</p>
        <div className="form-actions">
          <Link className="btn btn-primary" to="/audit">Open the audit trail <ArrowRight size={16} aria-hidden="true" /></Link>
          <Link className="btn btn-secondary" to="/fairness">Live fairness</Link>
          <Link className="btn btn-secondary" to="/decisions">Decision log</Link>
        </div>
      </Card>
    </>
  );
}

// One line under the greeting: what this overview is for
const INTROS = {
  employee: "Where you stand, and what you can do next.",
  manager: "Your team's readiness and your recommendations.",
  hr: "What's waiting for you, and how promotions are going.",
  admin: "Accounts, system health and recent activity.",
  finance: "Promotion pay rises waiting for your sign-off.",
  auditor: "Decisions, fairness and the model, read-only.",
};

export default function Home() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = () => { setError(""); return loadOverview(user).then(setData).catch((err) => setError(err.message)); };
  useEffect(() => { load(); }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <PageHeader title={`Hello, ${user.full_name.split(" ")[0]}`} subtitle={INTROS[user.role]} />
      {error && <LoadError message={error} onRetry={load} />}
      {!data && !error && <PageLoading />}
      {data && (user.role === "hr" || user.role === "manager") && <PromotionOverview data={data} isHr={user.role === "hr"} />}
      {data && user.role === "employee" && <EmployeeOverview me={data.me} requests={data.requests} />}
      {data && user.role === "admin" && <AdminDashboard system={data.system} employees={data.employees} fairness={data.fairness} models={data.models} />}
      {data && user.role === "finance" && <FinanceOverview finance={data.finance} />}
      {data && user.role === "auditor" && <AuditorOverview data={data} />}
    </>
  );
}
