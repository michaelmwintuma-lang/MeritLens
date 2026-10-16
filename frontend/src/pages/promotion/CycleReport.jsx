// A review cycle's report, laid out for printing or saving as a PDF (the browser's Print → Save as PDF): the
// cycle, its totals, each department, the movement since the previous cycle, and fairness at every stage, with pay.
// HR's copy names the people the model recommended but nobody nominated; the auditor's has totals only.
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Printer } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { useLoad } from "../../useLoad";
import { percent } from "../../format";
import { Button, LoadError, PageLoading } from "../../components/ui";
import { STATUS_TAG } from "../governance/LiveFairness";

const day = (iso) => (iso ? iso.slice(0, 10) : "–");
const signed = (v) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v * 100).toFixed(1)} points`;
const statusText = (s) => (STATUS_TAG[s] || [null, s])[1];

export default function CycleReport() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data, error, reload } = useLoad(async () => {
    const [progress, fairness] = await Promise.all([api(`/promotion/cycles/${id}`), api(`/governance/fairness?cycle_id=${id}`)]);
    return { progress, fairness };
  }, [id]);
  if (error) return <LoadError message={error} onRetry={reload} />;
  if (!data) return <PageLoading />;
  const { cycle, totals, by_department: departments, movement, not_nominated: notNominated } = data.progress;
  const fairness = data.fairness;

  return (
    <article className="print-report">
      <div className="form-actions no-print">
        <Link className="btn btn-secondary" to="/cycles"><ArrowLeft size={16} aria-hidden="true" />Back to review cycles</Link>
        <Button icon={Printer} onClick={() => window.print()}>Print or save as PDF</Button>
      </div>

      <header className="report-head">
        <p className="report-kicker">MeritLens · review cycle report</p>
        <h1>{cycle.name}</h1>
        <p>
          {cycle.status === "open" ? "Open" : "Closed"} · opened {day(cycle.opened_at)} by {cycle.opened_by}
          {cycle.closed_at && <> · closed {day(cycle.closed_at)} by {cycle.closed_by}</>}
          {" "}· model {cycle.model_version}, threshold {percent(cycle.threshold)}
        </p>
        {cycle.note && <p className="quote">{cycle.note}</p>}
      </header>

      <section>
        <h2>In numbers</h2>
        <div className="report-scroll" tabIndex={0} role="region" aria-label="In numbers"><table className="report-table"><tbody>
          <tr><th scope="row">People scored</th><td className="num">{totals.people}</td></tr>
          <tr><th scope="row">Recommended by the model</th><td className="num">{totals.recommended}</td></tr>
          <tr><th scope="row">Nominated by managers</th><td className="num">{totals.nominated}</td></tr>
          <tr><th scope="row">Approved · rejected</th><td className="num">{totals.approved} · {totals.rejected}</td></tr>
          <tr><th scope="row">Still waiting · on hold</th><td className="num">{totals.waiting} · {totals.on_hold}</td></tr>
          <tr><th scope="row">HR decisions against the model's advice</th><td className="num">{totals.against_model}</td></tr>
          <tr><th scope="row">Recommended, not nominated</th><td className="num">{totals.recommended_not_nominated}</td></tr>
          <tr><th scope="row">Scores updated after a record change</th><td className="num">{totals.rescored}</td></tr>
        </tbody></table></div>
      </section>

      <section>
        <h2>By department</h2>
        <div className="report-scroll" tabIndex={0} role="region" aria-label="By department"><table className="report-table">
          <thead><tr><th>Department</th><th className="num">People</th><th className="num">Recommended</th><th className="num">Nominated</th><th className="num">Approved</th></tr></thead>
          <tbody>{departments.map((d) => (
            <tr key={d.department}><td>{d.department}</td><td className="num">{d.people}</td><td className="num">{d.recommended || 0}</td>
              <td className="num">{d.nominated || 0}</td><td className="num">{d.approved || 0}</td></tr>
          ))}</tbody>
        </table></div>
      </section>

      <section>
        <h2>Since the previous cycle</h2>
        {movement.previous ? (
          <p>Compared with “{movement.previous.name}”, for the {movement.compared} people in both: {movement.crossed_up} now
            recommended, {movement.crossed_down} no longer recommended
            {movement.average_change != null && <>, average change {signed(movement.average_change)}</>}.</p>
        ) : <p>This is the first cycle, so there is nothing to compare with.</p>}
      </section>

      <section>
        <h2>Fairness (four-fifths rule)</h2>
        <p className="muted">Each group's rate should be at least 80% of the highest group's. Groups under {fairness.min_group} are not shown.</p>
        <div className="report-scroll" tabIndex={0} role="region" aria-label="Fairness"><table className="report-table">
          <thead><tr><th>Characteristic</th><th>Stage</th><th className="num">Lowest ÷ highest</th><th>Result</th></tr></thead>
          <tbody>
            {fairness.checks.flatMap((c) => c.stages.map((s, i) => (
              <tr key={`${c.characteristic}-${s.stage}`}><td>{i === 0 ? c.label : ""}</td><td>{s.stage}</td>
                <td className="num">{s.ratio == null ? "–" : s.ratio.toFixed(2)}</td><td>{statusText(s.status)}</td></tr>
            )))}
            {fairness.pay.map((p, i) => (
              <tr key={`pay-${p.characteristic}`}><td>{i === 0 ? "Pay rises" : ""}</td><td>{p.label}</td>
                <td className="num">{p.ratio == null ? "–" : p.ratio.toFixed(2)}</td><td>{statusText(p.status)}</td></tr>
            ))}
          </tbody>
        </table></div>
      </section>

      {notNominated?.length > 0 && (
        <section>
          <h2>Recommended by the model, not nominated</h2>
          <div className="report-scroll" tabIndex={0} role="region" aria-label="Recommended, not nominated"><table className="report-table">
            <thead><tr><th>Name</th><th>Department</th><th>Manager</th><th className="num">Score</th></tr></thead>
            <tbody>{notNominated.map((p) => (
              <tr key={p.employee_id}><td>{p.full_name}</td><td>{p.department}</td><td>{p.manager || "No manager"}</td><td className="num">{percent(p.score)}</td></tr>
            ))}</tbody>
          </table></div>
        </section>
      )}

      <footer className="report-foot">
        Made {new Date().toISOString().slice(0, 16).replace("T", " ")} UTC by {user.full_name}.
        {user.role === "hr" ? " Contains names: keep it within HR." : " Totals only."} The model advises; people decide.
      </footer>
    </article>
  );
}
