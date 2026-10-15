// HR: add many employees at once from a CSV file (what HR systems and Excel can export).
// 1. download the template, 2. choose the filled-in file: every row is checked, 3. import, only if all rows are fine.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Download, TriangleAlert, Upload, XCircle } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { Button, Callout, Card, PageHeader } from "../../components/ui";

export default function ImportEmployees() {
  const [setup, setSetup] = useState(null);
  const [file, setFile] = useState(null); // { name, text }
  const [check, setCheck] = useState(null);
  const [saved, setSaved] = useState(null);
  const [error, setError] = useState("");
  const [checking, withChecking] = useAction();
  const [importing, withImporting] = useAction();

  useEffect(() => { api("/promotion/records/fields").then(setSetup).catch((err) => setError(err.message)); }, []);

  function downloadTemplate() {
    // Two example rows, so the expected format is obvious. Rates are percentages, e.g. 93 for 93%.
    const example = (name, department) => setup.csv_columns.map((c) =>
      c === "full_name" ? name : c === "department" ? department : c === "manager_username" ? "" : setup.fields.find((f) => f.name === c).example);
    const lines = [setup.csv_columns, example("Example Person", setup.departments[0]), example("Another Example", setup.departments[1])];
    const blob = new Blob([lines.map((l) => l.join(",")).join("\r\n")], { type: "text/csv" });
    const link = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "employees-template.csv" });
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function chooseFile(e) {
    const chosen = e.target.files[0];
    e.target.value = ""; // so choosing the same file again (after fixing it) checks it again
    if (!chosen) return;
    setError(""); setCheck(null); setSaved(null);
    const text = await chosen.text();
    setFile({ name: chosen.name, text });
    try {
      setCheck(await api("/promotion/records/import", { method: "POST", body: { csv: text } }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function importAll() {
    setError("");
    try {
      const res = await api("/promotion/records/import", { method: "POST", body: { csv: file.text, save: true } });
      if (res.saved) { setSaved(res.saved); setCheck(null); setFile(null); } else setCheck(res);
    } catch (err) {
      setError(err.message);
    }
  }

  const ready = check ? check.total - check.failed : 0;
  const withWarnings = check ? check.rows.filter((r) => !r.errors.length && r.warnings.length).length : 0;

  return (
    <>
      <PageHeader title="Import employees" subtitle="From a CSV file, such as an export from your HR system." />
      {error && <Callout tone="error">{error}</Callout>}
      {saved && (
        <Callout tone="success" title={`${saved} employee${saved === 1 ? "" : "s"} added.`}>
          They can be scored now, and the admin can link each one to a login on the Users page. <Link to="/employees">Go to all employees</Link>
        </Callout>
      )}

      <div className="two-columns">
        <Card title="1. Get the template" subtitle="One row per employee, with the columns the system expects.">
          <ul className="steps-list">
            <li>Rates (attendance, deadlines met) are percentages: type <span className="mono">93</span> for 93%.</li>
            <li>Give both this year's and last year's performance score; the system works out the change.</li>
            <li><span className="mono">manager_username</span> is optional; it puts the person on that manager's team.</li>
            <li>Departments: {setup ? setup.departments.join(", ") : "…"}.</li>
          </ul>
          <Button look="secondary" icon={Download} className="section-gap" onClick={downloadTemplate} disabled={!setup} type="button">Download template</Button>
        </Card>
        <Card title="2. Choose your file" subtitle="Every row is checked first. Nothing is saved until you import.">
          <label className={`btn btn-primary file-button ${checking ? "is-busy" : ""}`}>
            <Upload size={16} aria-hidden="true" /> {checking ? "Checking…" : "Choose CSV file"}
            <input type="file" accept=".csv,text/csv" onChange={(e) => withChecking(() => chooseFile(e))} disabled={!setup || checking} />
          </label>
          {file && <p className="muted section-gap">Checked: <span className="mono">{file.name}</span></p>}
        </Card>
      </div>

      {check && (
        <Card flush title="3. Check and import"
          subtitle={`${check.total} rows · ${ready} ready${withWarnings ? ` (${withWarnings} with a warning)` : ""} · ${check.failed} with problems`}
          actions={check.failed === 0
            ? <Button icon={CheckCircle2} busy={importing} busyText="Importing…" onClick={() => withImporting(importAll)}>Import {ready} employee{ready === 1 ? "" : "s"}</Button>
            : null}>
          {check.failed > 0 && (
            <div className="card-inset"><Callout tone="warning">Fix the rows with problems in your file, then choose it again. Nobody is imported until every row is fine, so the file is never half-imported.</Callout></div>
          )}
          <div className="table-wrap" tabIndex={0} role="region" aria-label="Rows in the file"><table>
            <thead><tr><th className="num">Line</th><th>Name</th><th>Department</th><th>Result</th></tr></thead>
            <tbody>
              {check.rows.map((r) => (
                <tr key={r.line}>
                  <td className="num">{r.line}</td>
                  <td>{r.full_name || <span className="muted">(no name)</span>}</td>
                  <td>{r.department}</td>
                  <td>
                    {r.errors.length ? <span className="tag tag-off"><XCircle size={14} aria-hidden="true" /> {r.errors.length} problem{r.errors.length === 1 ? "" : "s"}</span>
                      : r.warnings.length ? <span className="tag tag-warn"><TriangleAlert size={14} aria-hidden="true" /> Ready, with a warning</span>
                        : <span className="tag tag-yes"><CheckCircle2 size={14} aria-hidden="true" /> Ready</span>}
                    {[...r.errors, ...r.warnings].length > 0 && (
                      <ul className="row-problems">{[...r.errors, ...r.warnings].map((p) => <li key={p}>{p}</li>)}</ul>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Card>
      )}
    </>
  );
}
