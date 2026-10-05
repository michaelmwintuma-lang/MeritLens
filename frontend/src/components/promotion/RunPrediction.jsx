// "Run prediction": runs the machine learning model for one employee, in three real steps, showing each one as
// it happens. Each step is its own request to the server, so the progress on screen is the progress of the work.
import { useState } from "react";
import { Brain, CheckCircle2, Circle, Loader2, Play, RotateCcw, XCircle } from "lucide-react";
import { api } from "../../api";
import { Button } from "../ui";

const STEPS = [
  { key: "predict", label: "Scoring the record with the model", detail: "and working out each factor's exact contribution" },
  { key: "lime", label: "Checking with a second method", detail: "LIME builds a simple model around this one person" },
  { key: "tips", label: "Finding realistic tips", detail: "the smallest improvements that would reach the threshold" },
];

function StepIcon({ status }) {
  if (status === "running") return <Loader2 size={18} className="spin step-running" aria-hidden="true" />;
  if (status === "done") return <CheckCircle2 size={18} className="step-done" aria-hidden="true" />;
  if (status === "error") return <XCircle size={18} className="step-error" aria-hidden="true" />;
  return <Circle size={18} className="step-waiting" aria-hidden="true" />;
}

export default function RunPrediction({ profile, onResult }) {
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
      onResult({ prediction });                                   // show the score as soon as it's ready
      const lime = await step("lime", () => api(`${base}/lime`, { method: "POST" }));
      onResult({ prediction, lime });
      const tips = await step("tips", () => api(`${base}/tips`));
      onResult({ prediction, lime, tips });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="card run-card">
      <div className="run-head">
        <div className="run-icon"><Brain size={22} aria-hidden="true" /></div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h2>{finished ? "Prediction complete" : "Run the readiness prediction"}</h2>
          <p className="card-sub">
            The {profile.model} model (trained on {profile.trained_at.slice(0, 10)}) scores {profile.full_name}'s current
            work record and explains the result. Nothing is saved, and the model only advises.
          </p>
        </div>
        <Button onClick={run} busy={running} busyText="Running…" icon={finished ? RotateCcw : Play}>
          {finished ? "Run again" : "Run prediction"}
        </Button>
      </div>
      {steps && (
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
      )}
      {error && <p className="alert alert-error" role="alert" style={{ marginTop: 14 }}>{error}</p>}
    </section>
  );
}
