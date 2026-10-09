// A manager's team, or every employee for HR, with their readiness. Click a name to see why.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { percent } from "../../format";
import ScoreBar, { Verdict } from "../../components/promotion/ScoreBar";
import { FileUp, UserPlus, Users } from "lucide-react";
import { EmptyState, LoadError, Loading, PageHeader } from "../../components/ui";

export default function EmployeeList() {
  const { user } = useAuth();
  const isManager = user.role === "manager";
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [onlyRecommended, setOnlyRecommended] = useState(false);
  const [sortBy, setSortBy] = useState("score");

  const load = () => { setError(""); return api("/promotion/employees").then(setData).catch((err) => setError(err.message)); };
  useEffect(() => { load(); }, []);

  if (error) return <LoadError message={error} onRetry={load} />;
  if (!data) return <Loading />;

  const departments = [...new Set(data.employees.map((e) => e.department))].sort();
  const rows = data.employees
    .filter((e) => e.full_name.toLowerCase().includes(search.toLowerCase()))
    .filter((e) => !department || e.department === department)
    .filter((e) => !onlyRecommended || e.recommended)
    .sort((a, b) => (sortBy === "score" ? b.score - a.score : a.full_name.localeCompare(b.full_name)));
  const recommendedCount = data.employees.filter((e) => e.recommended).length;

  return (
    <>
      <PageHeader icon={Users} title={isManager ? "My team" : "All employees"}
        subtitle={`${data.employees.length} employees, ${recommendedCount} above the ${percent(data.threshold)} threshold`}
        actions={user.role === "hr" && (
          <>
            <Link to="/employees/import" className="btn btn-plain"><FileUp size={16} aria-hidden="true" />Import</Link>
            <Link to="/employees/new" className="btn btn-primary"><UserPlus size={16} aria-hidden="true" />Add employee</Link>
          </>
        )} />

      {user.role === "admin" && <p className="alert alert-info">You're viewing employee data as an administrator: read-only. Nominations, decisions and reports stay with managers and HR.</p>}
      <div className="card flush">
        <div className="card-head filters">
          <input placeholder="Search by name" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search by name" />
          {!isManager && (
            <select value={department} onChange={(e) => setDepartment(e.target.value)} aria-label="Department">
              <option value="">All departments</option>
              {departments.map((d) => <option key={d}>{d}</option>)}
            </select>
          )}
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label="Sort">
            <option value="score">Highest readiness first</option>
            <option value="name">By name</option>
          </select>
          <label className="check"><input type="checkbox" checked={onlyRecommended} onChange={(e) => setOnlyRecommended(e.target.checked)} /> Recommended only</label>
        </div>
        <div className="table-wrap"><table>
          <thead><tr><th>Name</th><th>Department</th><th>Readiness</th><th style={{ width: "30%" }} /><th>Model's view</th></tr></thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.id}>
                <td><Link to={`/employees/${e.id}`}>{e.full_name}</Link></td>
                <td>{e.department}</td>
                <td className="strong">{percent(e.score)}</td>
                <td><ScoreBar score={e.score} threshold={data.threshold} compact /></td>
                <td><Verdict recommended={e.recommended} /></td>
              </tr>
            ))}
          </tbody>
        </table></div>
        {rows.length === 0 && <EmptyState icon={Users} title="No one matches" text="Try a different name or filter." />}
      </div>
    </>
  );
}
