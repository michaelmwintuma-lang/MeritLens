// One employee's readiness. The page shows who it is; the model runs when someone clicks "Run prediction", and the
// results (score, why, second opinion, what-if, tips) appear as each step finishes.
// Employees see their own; HR and managers open it from a list.
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Gauge, PartyPopper, Pencil } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { percent } from "../../format";
import { PageHeader } from "../../components/ui";
import ScoreBar, { Verdict } from "../../components/promotion/ScoreBar";
import Contributions from "../../components/promotion/Contributions";
import Lime from "../../components/promotion/Lime";
import WhatIf from "../../components/promotion/WhatIf";
import Tips from "../../components/promotion/Tips";
import NominateBox from "../../components/promotion/NominateBox";
import RunPrediction from "../../components/promotion/RunPrediction";

export default function Readiness() {
  const { user } = useAuth();
  const params = useParams();
  const saved = useLocation().state; // { saved: "added" | "updated", warnings } after the employee form
  const own = !params.id; // "My readiness" for an employee
  const employeeId = own ? user.employee_id : Number(params.id);
  const [promotions, setPromotions] = useState([]); // an employee's approved promotions (their own page only)
  useEffect(() => { if (own) api("/promotion/my-promotions").then(setPromotions).catch(() => {}); }, [own]);
  const [profile, setProfile] = useState(null);
  const [result, setResult] = useState(null); // { prediction, lime, tips }, filled in step by step
  const [error, setError] = useState("");

  useEffect(() => {
    if (!employeeId) return;
    setProfile(null);
    setResult(null);
    api(`/promotion/employees/${employeeId}/profile`).then(setProfile).catch((err) => setError(err.message));
  }, [employeeId]);

  if (!employeeId) return <><PageHeader icon={Gauge} title="My readiness" /><p className="alert alert-info">Your account isn't linked to an employee record yet. Ask an administrator to link it.</p></>;
  if (error) return <><PageHeader icon={Gauge} title="Readiness" /><p className="alert alert-error">{error}</p></>;
  if (!profile) return <p className="muted">Loading…</p>;

  const data = result?.prediction;
  return (
    <>
      {!own && <Link to={user.role === "manager" ? "/team" : "/employees"} className="back"><ArrowLeft size={16} />Back to the list</Link>}
      <PageHeader icon={Gauge} title={own ? "My readiness" : profile.full_name} subtitle={`${profile.department} · employee ${profile.id}`}
        actions={user.role === "hr" && <Link to={`/employees/${profile.id}/edit`} className="btn btn-plain"><Pencil size={16} aria-hidden="true" />Edit details</Link>} />
      {saved?.saved && (
        <div className="alert alert-success">
          <strong><CheckCircle2 size={16} style={{ verticalAlign: "-3px" }} /> Details {saved.saved}. Click Run prediction to score them{saved.saved === "added" ? "; the admin can now link them to a login" : ""}.</strong>
          {saved.warnings?.length > 0 && <ul>{saved.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
        </div>
      )}

      {user.role === "admin" && <p className="alert alert-info">Read-only view for administrators: you can run the prediction, but not nominate, decide or edit.</p>}
      {promotions.map((p) => (
        <div key={p.approved_on + p.title} className="alert alert-success">
          <strong><PartyPopper size={16} style={{ verticalAlign: "-3px" }} /> Promotion approved{p.title ? `: ${p.title}` : ""}</strong>
          <span>{p.start && `Starting ${p.start}. `}{p.raise != null && `Pay rise: ${p.raise}%. `}Approved on {p.approved_on}.</span>
        </div>
      ))}
      <RunPrediction key={profile.id} profile={profile} onResult={setResult} />

      {data && (
        <div className="appear">
          <section className="card">
            <div className="row spread">
              <h2>Readiness: {percent(data.score)}</h2>
              <Verdict recommended={data.recommended} />
            </div>
            <ScoreBar score={data.score} threshold={data.threshold} />
            <p className="summary">{data.summary}</p>
            <p className="muted small">
              The score ranks readiness against the {percent(data.threshold)} threshold; it isn't a probability. An employee with
              average values on everything would score {percent(data.average_employee_score)}. The model ({data.model}) only
              advises: HR makes the decision.
            </p>
          </section>

          <section className="card">
            <h2>Why: what raised and lowered the score</h2>
            <p className="muted">Compared with an average employee. These are exact: added together they give the score.</p>
            <Contributions contributions={data.contributions} />
          </section>

          <section className="card">
            <h2>Second opinion (LIME)</h2>
            {result.lime ? <Lime lime={result.lime} contributions={data.contributions} /> : <p className="muted">Running…</p>}
          </section>

          <section className="card">
            <h2>What if?</h2>
            <WhatIf key={data.id} employeeId={data.id} options={data.improvable} score={data.score} />
          </section>

          <section className="card">
            <h2>Tips to improve</h2>
            {result.tips ? <Tips data={result.tips} threshold={data.threshold} /> : <p className="muted">Waiting for the previous step…</p>}
          </section>
        </div>
      )}

      {user.role === "manager" && (
        <section className="card">
          <h2>Recommend for promotion</h2>
          <NominateBox employeeId={profile.id} name={profile.full_name} />
        </section>
      )}
    </>
  );
}
