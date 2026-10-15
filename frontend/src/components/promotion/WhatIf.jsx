// What-if: move sliders for things a person can work on and see the new score. Nothing is saved.
import { useState } from "react";
import { RotateCcw } from "lucide-react";
import { api } from "../../api";
import { formatValue, percent, stepFor } from "../../format";
import { Button, Callout } from "../ui";
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
        {options.map((o) => {
          const changed = values[o.feature] !== o.value;
          return (
            <label key={o.feature} className={`slider ${changed ? "is-changed" : ""}`}>
              <span className="slider-head">
                <span>{o.label}</span>
                <span className={`slider-value ${changed ? "changed" : "muted"}`}>{formatValue(o.unit, values[o.feature])}</span>
              </span>
              <input type="range" min={o.min} max={o.max} step={stepFor(o.unit, o.whole)} value={values[o.feature]}
                onChange={(e) => { setValues({ ...values, [o.feature]: Number(e.target.value) }); setResult(null); }} />
              {changed && <span className="muted">Now {formatValue(o.unit, o.value)}</span>}
            </label>
          );
        })}
      </div>
      <div className="form-actions">
        <Button busy={working} busyText="Running the model…" onClick={() => withWorking(run)} disabled={!changedCount}>See the new score</Button>
        <Button look="ghost" icon={RotateCcw} onClick={reset} disabled={!changedCount && !result}>Reset</Button>
        <span className="muted" aria-live="polite">{changedCount ? `${changedCount} changed` : "Move a slider to try a change."}</span>
      </div>
      {error && <Callout tone="error">{error}</Callout>}
      {result && (
        <Callout tone="info" title={`Readiness would be ${percent(result.score)} instead of ${percent(score)}`} className="section-gap" role="status">
          {result.score >= score ? "+" : ""}{Math.round((result.score - score) * 100)} points, {result.recommended ? "above" : "still below"} the {percent(result.threshold)} threshold. {result.summary}
        </Callout>
      )}
    </>
  );
}
