// A manager's team, or every employee for HR, with their readiness. Click a name to see why.
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { useLoad } from "../../useLoad";
import { useAuth } from "../../auth";
import { percent } from "../../format";
import ScoreBar, { Verdict } from "../../components/promotion/ScoreBar";
import { FileUp, UserPlus, Users } from "lucide-react";
import { EmptyState, LoadError, Loading, PageHeader } from "../../components/ui";

// Long lists are shown a page at a time: drawing thousands of rows at once makes the page slow to use
const PAGE_SIZE = 50;

export default function EmployeeList() {
  const { user } = useAuth();
  const isManager = user.role === "manager";
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [onlyRecommended, setOnlyRecommended] = useState(false);
  const [sortBy, setSortBy] = useState("score");
  const [page, setPage] = useState(0);
  // Any new search or filter starts again at the first page
  const filter = (setter) => (e) => { setter(e.target.type === "checkbox" ? e.target.checked : e.target.value); setPage(0); };

  const { data: data, error, reload: load } = useLoad(() => api("/promotion/employees"), []);

  if (error) return <LoadError message={error} onRetry={load} />;
  if (!data) return <Loading />;

  const departments = [...new Set(data.employees.map((e) => e.department))].sort();
  const rows = data.employees
    .filter((e) => e.full_name.toLowerCase().includes(search.toLowerCase()))
    .filter((e) => !department || e.department === department)
    .filter((e) => !onlyRecommended || e.recommended)
    .sort((a, b) => (sortBy === "score" ? b.score - a.score : a.full_name.localeCompare(b.full_name)));
  const recommendedCount = data.employees.filter((e) => e.recommended).length;
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const shown = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

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

      {user.role === "admin" && <p className="alert alert-info">You're viewing employee data as an administrator: read-only. Nominations, decisions and feedback stay with managers and HR.</p>}
      <div className="card flush">
        <div className="card-head filters">
          <input placeholder="Search by name" value={search} onChange={filter(setSearch)} aria-label="Search by name" />
          {!isManager && (
            <select value={department} onChange={filter(setDepartment)} aria-label="Department">
              <option value="">All departments</option>
              {departments.map((d) => <option key={d}>{d}</option>)}
            </select>
          )}
          <select value={sortBy} onChange={filter(setSortBy)} aria-label="Sort">
            <option value="score">Highest readiness first</option>
            <option value="name">By name</option>
          </select>
          <label className="check"><input type="checkbox" checked={onlyRecommended} onChange={filter(setOnlyRecommended)} /> Recommended only</label>
        </div>
        <div className="table-wrap" tabIndex={0}><table>
          <thead><tr><th>Name</th><th>Department</th><th>Readiness</th><th style={{ width: "30%" }} /><th>Model's view</th></tr></thead>
          <tbody>
            {shown.map((e) => (
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
        {rows.length > PAGE_SIZE && (
          <nav className="pager" aria-label="Pages of employees">
            <button type="button" className="btn btn-plain" onClick={() => setPage(page - 1)} disabled={page === 0}>Previous</button>
            <span className="muted small" aria-live="polite">
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, rows.length)} of {rows.length}
            </span>
            <button type="button" className="btn btn-plain" onClick={() => setPage(page + 1)} disabled={page >= pages - 1}>Next</button>
          </nav>
        )}
      </div>
    </>
  );
}
