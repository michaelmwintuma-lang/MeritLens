// One employee's readiness, in plain words first: the score as a gauge beside a plain-language summary, what raised
// and lowered it, the path to promotion and a what-if, then (for the employee) the respond panel. The exact numbers,
// the second opinion (LIME) and the model's details sit under "Show technical details". Employees see their own
// (worked out as the page opens); HR and managers open it from a list and click "Run prediction".
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ChevronRight, MessageSquareQuote, PartyPopper, Pencil } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { percent } from "../../format";
import { Callout, Card, LoadError, Loading, PageHeader, PageLoading } from "../../components/ui";
import { Gauge, Verdict } from "../../components/promotion/ScoreBar";
import Contributions, { ExactNumbers } from "../../components/promotion/Contributions";
import Lime from "../../components/promotion/Lime";
import WhatIf from "../../components/promotion/WhatIf";
import Tips from "../../components/promotion/Tips";
import NominateBox from "../../components/promotion/NominateBox";
import RunPrediction from "../../components/promotion/RunPrediction";
import RecordHistory from "../../components/promotion/RecordHistory";
import RespondPanel from "../../components/feedback/RespondPanel";
import TrendChart from "../../components/charts/TrendChart";

export default function Readiness() {
  const { user } = useAuth();
  const params = useParams();
  const saved = useLocation().state; // { saved: "added" | "updated", warnings } after the employee form
  const own = !params.id; // "My growth" for an employee
  const employeeId = own ? user.employee_id : Number(params.id);
  const [promotions, setPromotions] = useState([]); // an employee's approved promotions (their own page only)
  useEffect(() => { if (own) api("/promotion/my-promotions").then(setPromotions).catch(() => {}); }, [own]);
  const [trend, setTrend] = useState([]); // saved scores in each review cycle, oldest first
  const [profile, setProfile] = useState(null);
  const [result, setResult] = useState(null); // { prediction, lime, tips }, filled in step by step
  const [error, setError] = useState("");

  const loadProfile = () => {
    setError("");
    return api(`/promotion/employees/${employeeId}/profile`).then(setProfile).catch((err) => setError(err.message));
  };
  useEffect(() => {
    if (!employeeId) return;
    setProfile(null);
    setResult(null);
    loadProfile();
    api(`/promotion/employees/${employeeId}/trend`).then(setTrend).catch(() => setTrend([]));
  }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!employeeId) {
    return (
      <>
        <PageHeader title="My growth" />
        <Callout title="Your account isn't linked to an employee record yet">Ask an administrator to link it.</Callout>
      </>
    );
  }
  if (error) return <><PageHeader title={own ? "My growth" : "Readiness"} /><LoadError message={error} onRetry={loadProfile} /></>;
  if (!profile) return <PageLoading />;

  const data = result?.prediction;
  return (
    <>
      <PageHeader title={own ? "My growth" : profile.full_name}
        subtitle={own
          ? `Your readiness for promotion, why, and the smallest steps that would raise it.${profile.manager ? ` Your manager, ${profile.manager}, can recommend you.` : ""}`
          : `${profile.department} · employee ${profile.id} · ${profile.manager ? `managed by ${profile.manager}` : "no manager yet"}`}
        actions={user.role === "hr" && <Link to={`/employees/${profile.id}/edit`} className="btn btn-secondary"><Pencil size={16} aria-hidden="true" />Edit details</Link>} />
      {saved?.saved && (
        <Callout tone="success" title={`Details ${saved.saved}. Click Run prediction to score them${saved.saved === "added" ? "; the admin can now link them to a login" : ""}.`}>
          {saved.warnings?.length > 0 && <ul>{saved.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
        </Callout>
      )}

      {profile.cover && <Callout>{profile.cover.name} is covering for {own ? "your manager" : profile.manager} until {profile.cover.until}.</Callout>}
      {user.role === "manager" && profile.relation === "branch" && (
        <Callout title="Read-only for you">{profile.manager} manages {profile.full_name} and is the one who can recommend them.</Callout>
      )}
      {user.role === "admin" && <Callout>Read-only view for administrators: you can run the prediction, but not nominate, decide or edit.</Callout>}
      {promotions.map((p) => (
        <Callout key={p.approved_on + p.title} tone="success" icon={PartyPopper} title={`Promotion approved${p.title ? `: ${p.title}` : ""}`}>
          {p.start && `Starting ${p.start}. `}{p.raise != null && `Pay rise: ${p.raise}%. `}Approved on {p.approved_on}.
        </Callout>
      ))}
      <RunPrediction key={profile.id} profile={profile} onResult={setResult} autoRun={own} compact={own} />

      {data && (
        <div className="appear">
          <div className="score-layout">
            <section className="card gauge-card" aria-labelledby="score-title">
              <h2 id="score-title">{own ? "Your readiness" : "Readiness"}</h2>
              <Gauge score={data.score} threshold={data.threshold} recommended={data.recommended} />
              <Verdict recommended={data.recommended} large />
              <p className="muted">Threshold {percent(data.threshold)}: the model recommends promotion at or above it.</p>
            </section>
            <section className="card highlight plain-summary" aria-labelledby="summary-title">
              <h2 id="summary-title" className="label"><MessageSquareQuote size={16} aria-hidden="true" />In plain words</h2>
              <p className="summary">{data.summary}</p>
              <p className="helper">
                {own ? "Your readiness is compared with an average employee. " : "Readiness is compared with an average employee. "}
                Scores match past promotions closely: of employees scoring around {percent(data.threshold)}, about{" "}
                {Math.round(data.threshold * 100)} in 100 were promoted. It describes past decisions, so it isn't a promise:
                the model only advises, and people make the decision.
              </p>
            </section>
          </div>

          <Card id="factors" title={own ? "What raised and lowered your score" : "Why: what raised and lowered the score"}
            subtitle="Compared with an average employee. The longer the bar, the bigger the effect.">
            <Contributions contributions={data.contributions} numbers={!own} />
          </Card>

          <Card id="tips" title={own ? "Your path to promotion" : "Tips to improve"}>
            {result.tips ? <Tips data={result.tips} threshold={data.threshold} /> : <Loading label="Finding realistic steps…" />}
          </Card>

          {trend.length > 0 && (
            <Card id="trend" title={own ? "Your readiness over time" : "Readiness over time"}
              subtitle="The score saved in each review cycle. During an open cycle it changes only when the record changes.">
              <TrendChart points={trend} />
            </Card>
          )}

          <Card id="what-if" title="What if?">
            <WhatIf key={data.id} employeeId={data.id} options={data.improvable} score={data.score} />
          </Card>

          {own && user.role === "employee" && <RespondPanel contributions={data.contributions} />}

          <details className="card technical-details" id="technical-details">
            <summary><ChevronRight size={18} aria-hidden="true" />Show technical details</summary>
            <p>
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

      {user.role === "manager" && profile.may_nominate && (
        <Card id="recommend" title="Recommend for promotion">
          <NominateBox employeeId={profile.id} name={profile.full_name} />
        </Card>
      )}
    </>
  );
}
