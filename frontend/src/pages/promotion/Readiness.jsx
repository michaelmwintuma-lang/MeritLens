// One employee's readiness, in plain words first: the score, what raised and lowered it, the path to promotion and a
// what-if, then (for the employee) the respond panel. The exact numbers, the second opinion (LIME) and the model's
// details sit under "Show technical details". Employees see their own (worked out as the page opens); HR and
// managers open it from a list and click "Run prediction".
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Gauge, PartyPopper, Pencil } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { percent } from "../../format";
import { LoadError, Loading, PageHeader } from "../../components/ui";
import ScoreBar, { Verdict } from "../../components/promotion/ScoreBar";
import Contributions, { ExactNumbers } from "../../components/promotion/Contributions";
import Lime from "../../components/promotion/Lime";
import WhatIf from "../../components/promotion/WhatIf";
import Tips from "../../components/promotion/Tips";
import NominateBox from "../../components/promotion/NominateBox";
import RunPrediction from "../../components/promotion/RunPrediction";
import RecordHistory from "../../components/promotion/RecordHistory";
import RespondPanel from "../../components/feedback/RespondPanel";

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

  if (!employeeId) return <><PageHeader icon={Gauge} title="My growth" /><p className="alert alert-info">Your account isn't linked to an employee record yet. Ask an administrator to link it.</p></>;
  if (error) return <><PageHeader icon={Gauge} title="Readiness" /><LoadError message={error} /></>;
  if (!profile) return <Loading />;

  const data = result?.prediction;
  return (
    <>
      {!own && <Link to={user.role === "manager" ? "/team" : "/employees"} className="back"><ArrowLeft size={16} />Back to the list</Link>}
      <PageHeader icon={Gauge} title={own ? "My growth" : profile.full_name} subtitle={`${profile.department} · employee ${profile.id}`}
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
      <RunPrediction key={profile.id} profile={profile} onResult={setResult} autoRun={own} compact={own} />

      {data && (
        <div className="appear">
          <section className="card">
            <div className="row spread">
              <h2>{own ? "Your readiness" : "Readiness"}: {percent(data.score)}</h2>
              <Verdict recommended={data.recommended} />
            </div>
            <ScoreBar score={data.score} threshold={data.threshold} />
            <p className="summary">{data.summary}</p>
            <p className="muted small helper">
              {own ? "Your readiness is compared with an average employee. " : "Readiness is compared with an average employee. "}
              It ranks readiness against the {percent(data.threshold)} threshold; it isn't a chance of promotion. The model
              only advises: people make the decision.
            </p>
          </section>

          <section className="card">
            <h2>{own ? "What raised and lowered your score" : "Why: what raised and lowered the score"}</h2>
            <p className="muted">Compared with an average employee. The longer the bar, the bigger the effect.</p>
            <Contributions contributions={data.contributions} numbers={!own} />
          </section>

          <section className="card">
            <h2>{own ? "Your path to promotion" : "Tips to improve"}</h2>
            {result.tips ? <Tips data={result.tips} threshold={data.threshold} /> : <Loading label="Finding realistic steps…" />}
          </section>

          <section className="card">
            <h2>What if?</h2>
            <WhatIf key={data.id} employeeId={data.id} options={data.improvable} score={data.score} />
          </section>

          {own && user.role === "employee" && <RespondPanel contributions={data.contributions} />}

          <details className="card technical-details" id="technical-details">
            <summary>Show technical details</summary>
            <p className="small">
              Model: {data.model}, version {data.model_version}, trained {profile.trained_at.slice(0, 10)}. Threshold
              {" "}{data.threshold} (best F1 on validation data). An employee with average values on everything would
              score {percent(data.average_employee_score)}.
            </p>
            <ExactNumbers contributions={data.contributions} />
            <h3>Second opinion (LIME)</h3>
            {result.lime ? <Lime lime={result.lime} contributions={data.contributions} /> : <Loading label="Running LIME…" />}
          </details>
        </div>
      )}

      {user.role === "hr" && <RecordHistory employeeId={profile.id} />}

      {user.role === "manager" && (
        <section className="card">
          <h2>Recommend for promotion</h2>
          <NominateBox employeeId={profile.id} name={profile.full_name} />
        </section>
      )}
    </>
  );
}
