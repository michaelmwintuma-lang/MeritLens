// "Run prediction": runs the machine learning model for one employee, in three real steps, showing each one as
// it happens. Each step is its own request to the server, so the progress on screen is the progress of the work.
import { useEffect, useState } from "react";
import { Brain, CheckCircle2, Circle, Loader2, Play, RotateCcw, XCircle } from "lucide-react";
import { api, apiWhenReady } from "../../api";
import { Button, Callout } from "../ui";

const STEPS = [
  { key: "predict", label: "Scoring the record with the model", detail: "and working out each factor's exact contribution" },
  { key: "lime", label: "Checking with a second method", detail: "LIME builds a simple model around this one person (in the background)" },
  { key: "tips", label: "Finding realistic tips", detail: "the smallest improvements that would reach the threshold" },
];

function StepIcon({ status }) {
  if (status === "running") return <Loader2 size={18} className="spin step-running" aria-hidden="true" />;
  if (status === "done") return <CheckCircle2 size={18} className="step-done" aria-hidden="true" />;
  if (status === "error") return <XCircle size={18} className="step-error" aria-hidden="true" />;
  return <Circle size={18} className="step-waiting" aria-hidden="true" />;
}

/**
 * `autoRun`: start as soon as the page opens (the employee's own page). `compact`: a short line instead of the
 * step-by-step card, with the steps and their timings folded away (they are technical detail).
 */
export default function RunPrediction({ profile, onResult, autoRun = false, compact = false }) {
  const [steps, setSteps] = useState(null); // { key: { status, ms } }
  const [error, setError] = useState("");
  const running = steps && Object.values(steps).some((s) => s.status === "running");
  const finished = steps && Object.values(steps).every((s) => s.status === "done");

  async function step(key, request) {
    setSteps((s) => ({ ...s, [key]: { status: "running" } }));
    const started = performance.now();
    try {
      const result = await request();
      setSteps((s) => ({ ...s, [key]: { status: "done", ms: Math.round(performance.now() - started) } }));
      return result;
    } catch (err) {
      setSteps((s) => ({ ...s, [key]: { status: "error" } }));
      throw err;
    }
  }

  async function run() {
    setError("");
    onResult(null);
    setSteps(Object.fromEntries(STEPS.map((s) => [s.key, { status: "waiting" }])));
    try {
      const base = `/promotion/employees/${profile.id}`;
      const prediction = await step("predict", () => api(`${base}/predict`, { method: "POST" }));
      let shown = { prediction };
      onResult(shown);                                            // show the score as soon as it's ready
      // The second opinion and the tips don't depend on each other, so they run at the same time
      await Promise.all([
        // LIME runs as a background job on the server: start it, then ask until it's ready (kept once worked out)
        step("lime", () => apiWhenReady(`${base}/lime`)).then((lime) => onResult(shown = { ...shown, lime })),
        step("tips", () => api(`${base}/tips`)).then((tips) => onResult(shown = { ...shown, tips })),
      ]);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { if (autoRun) run(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const stepList = steps && (
    <ol className="run-steps">
      {STEPS.map((s) => {
        const state = steps[s.key];
        return (
          <li key={s.key} className={`run-step ${state.status}`}>
            <StepIcon status={state.status} />
            <span><strong>{s.label}</strong> <span className="muted">{s.detail}</span></span>
            <span className="muted small nowrap">{state.status === "done" ? `${state.ms} ms` : state.status === "running" ? "working…" : ""}</span>
          </li>
        );
      })}
    </ol>
  );

  if (compact) {
    const working = running || (!steps && autoRun);
    return (
      <section className="run-compact" aria-busy={working} aria-label="How this was worked out">
        <span>
          {working ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <CheckCircle2 size={16} aria-hidden="true" className="step-done" />}
          {working ? "Working out your readiness from your current work record…"
            : "Worked out just now from your current work record. The model only advises."}
        </span>
        <Button look="ghost" onClick={run} busy={running} busyText="Working…" icon={RotateCcw}>Work it out again</Button>
        {error && <Callout tone="error">{error}</Callout>}
        {steps && finished && <details className="details run-details"><summary>How it was worked out</summary>{stepList}</details>}
      </section>
    );
  }

  return (
    <section className="card run-card">
      <div className="run-head">
        <div className="run-icon"><Brain size={20} aria-hidden="true" /></div>
        <div>
          <h2>{finished ? "Prediction complete" : "Predict and explain"}</h2>
          <p className="card-sub">
            The {profile.model} model (trained on {profile.trained_at.slice(0, 10)}) scores {profile.full_name}'s current
            work record and explains the result. This run saves nothing, and the model only advises.
          </p>
        </div>
        <Button onClick={run} busy={running} busyText="Running…" icon={finished ? RotateCcw : Play} look={finished ? "secondary" : "primary"}>
          {finished ? "Run again" : "Run prediction"}
        </Button>
      </div>
      {stepList}
      {error && <Callout tone="error" className="section-gap">{error}</Callout>}
    </section>
  );
}
