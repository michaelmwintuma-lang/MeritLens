// Overview: the numbers that matter for your role, then the list that needs attention.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, LayoutGrid } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { percent } from "../format";
import { ROLE_DESCRIPTIONS } from "../roles";
import { Card, PageHeader, StatCard } from "../components/ui";
import ScoreBar, { Verdict } from "../components/promotion/ScoreBar";
import NominationsTable from "../components/promotion/NominationsTable";

/** Fetch everything the overview needs for this role. */
async function loadOverview(user) {
  if (user.role === "hr" || user.role === "manager") {
    const [people, nominations, decisions] = await Promise.all([
      api("/promotion/employees"), api("/promotion/nominations"),
      user.role === "hr" ? api("/promotion/decisions") : Promise.resolve(null),
    ]);
    return { people, nominations, decisions };
  }
  if (user.role === "employee") {
    return { me: user.employee_id ? await api(`/promotion/employees/${user.employee_id}`) : null };
  }
  const [users, employees] = await Promise.all([api("/admin/users"), api("/admin/employees")]);
  return { users, employees };
}

function PromotionOverview({ data, isHr }) {
  const { people, nominations, decisions } = data;
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
      </div>
      <NominationsTable nominations={nominations} isHr={isHr}
        title={isHr ? "Nominations" : "My nominations"}
        subtitle={isHr ? "Review managers' nominations alongside the model's view." : "People you nominated and HR's decisions."} />
    </>
  );
}

function EmployeeOverview({ me }) {
  if (!me) return <Card title="Your account isn't linked yet"><p className="muted">Ask an administrator to link your login to your employee record.</p></Card>;
  return (
    <>
      <div className="stat-grid">
        <StatCard label="My readiness" value={percent(me.score)} note={me.recommended ? "Above the threshold" : "Below the threshold"} />
        <StatCard label="Threshold" value={percent(me.threshold)} note="Where the model recommends promotion" />
        <StatCard label="Average employee" value={percent(me.average_employee_score)} note="For comparison" />
      </div>
      <Card title="Where you stand" subtitle="The model only advises: HR makes promotion decisions." actions={<Verdict recommended={me.recommended} />}>
        <ScoreBar score={me.score} threshold={me.threshold} />
        <p className="summary">{me.summary}</p>
        <Link className="btn btn-primary" to="/my-readiness">See why, try changes and get tips <ArrowRight size={16} /></Link>
      </Card>
    </>
  );
}

function AdminOverview({ data }) {
  const { users, employees } = data;
  return (
    <>
      <div className="stat-grid">
        <StatCard label="Accounts" value={users.length} note={`${users.filter((u) => !u.is_active).length} deactivated`} />
        <StatCard label="Managers" value={users.filter((u) => u.role === "manager").length} note="Each with a team you set" />
        <StatCard label="Employees with a login" value={employees.filter((e) => e.login).length} note={`of ${employees.length} in the directory`} />
        <StatCard label="Must change password" value={users.filter((u) => u.must_change_password).length} note="New or reset accounts" />
      </div>
      <Card title="Accounts" subtitle="Create accounts for every role, link employees to their records, and set managers' teams.">
        <Link className="btn btn-primary" to="/admin/users">Manage users <ArrowRight size={16} /></Link>
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
      <PageHeader icon={LayoutGrid} title="Overview" subtitle={`Welcome, ${user.full_name.split(" ")[0]}. ${ROLE_DESCRIPTIONS[user.role]}`} />
      {error && <p className="alert alert-error">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}
      {data && (user.role === "hr" || user.role === "manager") && <PromotionOverview data={data} isHr={user.role === "hr"} />}
      {data && user.role === "employee" && <EmployeeOverview me={data.me} />}
      {data && user.role === "admin" && <AdminOverview data={data} />}
    </>
  );
}
