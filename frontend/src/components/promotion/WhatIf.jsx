// What-if: move sliders for things a person can work on and see the new score. Nothing is saved.
import { useState } from "react";
import { api } from "../../api";
import { formatValue, percent, stepFor } from "../../format";
import { Button } from "../ui";
import { useAction } from "../../useAction";

export default function WhatIf({ employeeId, options, score }) {
  const start = Object.fromEntries(options.map((o) => [o.feature, o.value]));
  const [values, setValues] = useState(start);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const changes = Object.fromEntries(options.filter((o) => values[o.feature] !== o.value).map((o) => [o.feature, Number(values[o.feature])]));
  const changedCount = Object.keys(changes).length;

  const [working, withWorking] = useAction();

  async function run() {
    setError("");
    try {
      setResult(await api(`/promotion/employees/${employeeId}/what-if`, { method: "POST", body: { changes } }));
    } catch (err) {
      setError(err.message);
    }
  }

  function reset() {
    setValues(start);
    setResult(null);
  }

  return (
    <>
      <p className="muted">Only things a person can work on are listed. Department, time in role and personal characteristics can't be changed. Nothing is saved.</p>
      <div className="sliders">
        {options.map((o) => (
          <label key={o.feature} className="slider">
            <span className="slider-head">
              <span className="strong">{o.label}</span>
              <span className={values[o.feature] !== o.value ? "changed" : "muted"}>{formatValue(o.unit, values[o.feature])}</span>
            </span>
            <input type="range" min={o.min} max={o.max} step={stepFor(o.unit, o.whole)} value={values[o.feature]}
              onChange={(e) => { setValues({ ...values, [o.feature]: Number(e.target.value) }); setResult(null); }} />
            <span className="muted small">Now: {formatValue(o.unit, o.value)}</span>
          </label>
        ))}
      </div>
      <div className="row">
        <Button busy={working} busyText="Running the model…" onClick={() => withWorking(run)} disabled={!changedCount}>See the new score</Button>
        <button className="btn btn-plain" onClick={reset} disabled={!changedCount && !result}>Reset</button>
        <span className="muted small">{changedCount ? `${changedCount} changed` : "Move a slider to try a change."}</span>
      </div>
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      {result && (
        <div className="alert alert-info">
          <strong>Readiness would be {percent(result.score)}</strong> instead of {percent(score)}
          {" "}({result.score >= score ? "+" : ""}{Math.round((result.score - score) * 100)} points), {result.recommended ? "above" : "still below"} the {percent(result.threshold)} threshold.
          <div className="small" style={{ marginTop: 6 }}>{result.summary}</div>
        </div>
      )}
    </>
  );
}
