// Overview: the numbers that matter for your role, then the list that needs attention.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, LayoutGrid } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { percent } from "../format";
import { Card, LoadError, Loading, PageHeader, StatCard } from "../components/ui";
import ScoreBar, { Verdict } from "../components/promotion/ScoreBar";
import NominationsTable from "../components/promotion/NominationsTable";
import AdminDashboard from "../components/home/AdminDashboard";

/** Fetch everything the overview needs for this role. */
async function loadOverview(user) {
  if (user.role === "hr" || user.role === "manager") {
    const hr = user.role === "hr";
    const [people, nominations, decisions, corrections] = await Promise.all([
      api("/promotion/employees"), api("/promotion/nominations"),
      hr ? api("/promotion/decisions") : null, hr ? api("/hr/feedback/corrections?status_filter=pending") : null,
    ]);
    return { people, nominations, decisions, corrections };
  }
  if (user.role === "finance") return { finance: await api("/finance/pay-reviews") };
  if (user.role === "auditor") {
    const [decisions, model, ratings] = await Promise.all([api("/promotion/decisions"), api("/public/summary"),
      api("/feedback/ratings/summary")]);
    return { decisions, model, ratings };
  }
  if (user.role === "employee") {
    if (!user.employee_id) return { me: null };
    const [me, requests] = await Promise.all([api(`/promotion/employees/${user.employee_id}`), api("/feedback/corrections/mine")]);
    return { me, requests };
  }
  const [system, employees] = await Promise.all([api("/admin/system"), api("/admin/employees")]);
  return { system, employees };
}

function PromotionOverview({ data, isHr }) {
  const { people, nominations, decisions, corrections } = data;
  const recommended = people.employees.filter((e) => e.recommended).length;
  const waiting = nominations.filter((n) => n.status === "pending").length;
  return (
    <>
      <div className="stat-grid">
        <StatCard label={isHr ? "Employees" : "Team members"} value={people.employees.length} note={isHr ? "In the directory" : "People you manage"} />
        <StatCard label="Recommended" value={recommended} note={`Above the ${percent(people.threshold)} threshold`} />
        <StatCard label="Waiting for HR" value={waiting} note={isHr ? "Nominations to review" : "Your nominations"} />
        {isHr
          ? <StatCard label="Decisions" value={decisions.length} note={`${decisions.filter((d) => !d.agrees_with_model).length} differ from the model`} />
          : <StatCard label="Decided" value={nominations.length - waiting} note="Your nominations with a decision" />}
        {isHr && <StatCard label="Corrections waiting" value={corrections.length} note="Employees' record corrections to check" />}
      </div>
      {isHr && (
        <Card title="Employee feedback" subtitle="Record corrections wait for you; the dashboard shows how employees rate their explanations.">
          <div className="row">
            <Link className="btn btn-primary" to="/corrections">{corrections.length ? `Check ${corrections.length} correction${corrections.length === 1 ? "" : "s"}` : "Record corrections"} <ArrowRight size={16} /></Link>
            <Link className="btn btn-plain" to="/feedback">Feedback dashboard</Link>
          </div>
        </Card>
      )}
      <NominationsTable nominations={nominations} isHr={isHr}
        title={isHr ? "Nominations" : "My nominations"}
        subtitle={isHr ? "Open one to see the model's view and decide." : undefined} />
    </>
  );
}

function EmployeeOverview({ me, requests = [] }) {
  const waiting = requests.filter((r) => r.status === "pending").length;
  if (!me) return <Card title="Your account isn't linked yet"><p className="muted">Ask an administrator to link your login to your employee record.</p></Card>;
  return (
    <>
      <div className="stat-grid">
        <StatCard label="My readiness" value={percent(me.score)} note={me.recommended ? "Above the threshold" : "Below the threshold"} />
        <StatCard label="Threshold" value={percent(me.threshold)} note="Where the model recommends promotion" />
        <StatCard label="Average employee" value={percent(me.average_employee_score)} note="For comparison" />
      </div>
      <Card title="Where you stand" actions={<Verdict recommended={me.recommended} />}>
        <ScoreBar score={me.score} threshold={me.threshold} />
        <p className="summary">{me.summary}</p>
        <Link className="btn btn-primary" to="/my-readiness">See why, try changes and get tips <ArrowRight size={16} /></Link>
      </Card>
      <Card title="Respond to your explanation"
        subtitle="Rate whether it was clear and useful, ask HR to correct a value in your record, or report an unfair assessment anonymously. None of this changes your score.">
        <p className="muted small">{requests.length
          ? `Your correction requests: ${requests.length}, of which ${waiting} waiting for HR.`
          : "You haven't asked for a correction."}</p>
        <Link className="btn btn-plain" to="/my-readiness">Open My growth to respond</Link>
      </Card>
    </>
  );
}

function FinanceOverview({ finance }) {
  const { summary, policy } = finance;
  return (
    <>
      <div className="stat-grid">
        <StatCard label="Waiting for you" value={summary.awaiting} note="Pay rises to sign off" />
        <StatCard label="Sent back to HR" value={summary.returned} note="Waiting for HR to revise" />
        <StatCard label="Signed off this year" value={summary.signed_off_this_year} note="Promotion pay rises confirmed" />
        <StatCard label="Average rise this year" value={summary.average_raise_this_year != null ? `${summary.average_raise_this_year}%` : "–"}
          note={`Policy: ${policy.min_raise}% to ${policy.max_raise}%`} />
      </div>
      <Card title="Pay sign-off" subtitle="Nobody is told about a promotion until you confirm its pay rise.">
        <Link className="btn btn-primary" to="/finance">{summary.awaiting ? `Review ${summary.awaiting} waiting` : "Open pay sign-off"} <ArrowRight size={16} /></Link>
      </Card>
    </>
  );
}

function AuditorOverview({ data }) {
  const { decisions, model, ratings } = data;
  const differ = decisions.filter((d) => !d.agrees_with_model).length;
  return (
    <>
      <div className="stat-grid">
        <StatCard label="Decisions" value={decisions.length} note="Promotion decisions in the log" />
        <StatCard label="Differ from the model" value={differ}
          note={decisions.length ? `${percent(differ / decisions.length)} of decisions, each with a written reason` : "No decisions yet"} />
        <StatCard label="Fairness check" value={model.trained ? (model.fairness_passes ? "Passed" : "Failed") : "–"}
          note={model.trained ? `Lowest group ratio ${percent(model.lowest_fairness_ratio)} (needs 80%)` : "No model trained yet"} />
        <StatCard label="Explanations rated clear" value={ratings.clarity_rate == null ? "–" : percent(ratings.clarity_rate)}
          note={ratings.clarity_rate == null ? `${ratings.ratings} rating${ratings.ratings === 1 ? "" : "s"} so far: shown from 5` : `Of ${ratings.ratings} ratings, 4 or 5 out of 5`} />
        <StatCard label="Model" value={model.trained ? `ROC-AUC ${model.roc_auc.toFixed(2)}` : "–"}
          note={model.trained ? `${model.model}, tested on ${model.test_size.toLocaleString()} unseen records` : "No model trained yet"} />
      </div>
      <Card title="Oversight" subtitle="Read-only. You see decisions and the model, never anonymous reports.">
        <div className="row">
          <Link className="btn btn-primary" to="/decisions">Open the decision log <ArrowRight size={16} /></Link>
          <Link className="btn btn-plain" to="/feedback">Feedback dashboard</Link>
          <Link className="btn btn-plain" to="/model">How the model works</Link>
        </div>
      </Card>
    </>
  );
}

export default function Home() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { loadOverview(user).then(setData).catch((err) => setError(err.message)); }, [user]);

  return (
    <>
      <PageHeader icon={LayoutGrid} title={`Hello, ${user.full_name.split(" ")[0]}`} />
      {error && <LoadError message={error} />}
      {!data && !error && <Loading />}
      {data && (user.role === "hr" || user.role === "manager") && <PromotionOverview data={data} isHr={user.role === "hr"} />}
      {data && user.role === "employee" && <EmployeeOverview me={data.me} requests={data.requests} />}
      {data && user.role === "admin" && <AdminDashboard system={data.system} employees={data.employees} />}
      {data && user.role === "finance" && <FinanceOverview finance={data.finance} />}
      {data && user.role === "auditor" && <AuditorOverview data={data} />}
    </>
  );
}
