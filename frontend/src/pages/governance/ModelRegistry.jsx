// The model registry: every trained model version with its model card. Training never changes the live model by
// itself: a version goes live only when an HR person has read its card and releases it with a written note. A
// version that failed the fairness check can never be released. Releasing an older version is how a release is
// rolled back. Admins and the auditor can read everything here; only HR releases.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Rocket, RotateCcw, ShieldAlert } from "lucide-react";
import { governance } from "../../api";
import { useAuth } from "../../auth";
import { useAction } from "../../useAction";
import { useLoad } from "../../useLoad";
import { percent } from "../../format";
import { Button, Callout, Card, LoadError, Loading, PageHeader, PageLoading } from "../../components/ui";
import CalibrationChart, { CalibrationSummary } from "../../components/governance/CalibrationChart";

const STATUS = {
  live: ["tag tag-yes", "Live"],
  candidate: ["tag tag-info", "Waiting for release"],
  retired: ["tag", "Previously live"],
  blocked: ["tag tag-warn", "Blocked: failed fairness"],
};
const MIN_NOTE = 20;

export function ModelStatus({ status }) {
  const [className, text] = STATUS[status] || ["tag", status];
  return <span className={className}>{text}</span>;
}

const date = (iso) => (iso ? iso.slice(0, 10) : "–");
const num = (v, digits = 3) => (v == null ? "–" : Number(v).toFixed(digits));

function Delta({ value, live }) {
  if (value == null || live == null || value === live) return null;
  const d = value - live;
  return <span className="muted"> ({d > 0 ? "+" : "−"}{Math.abs(d).toFixed(3)} vs live)</span>;
}

function ReleaseBox({ row, onReleased }) {
  const [note, setNote] = useState("");
  const [read, setRead] = useState(false);
  const [error, setError] = useState("");
  const [waiting, setWaiting] = useState(false); // four-eyes rule: a second HR person must approve
  const [working, withWorking] = useAction();
  const rollback = row.status === "retired";

  async function release(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await governance.release(row.version, { note });
      if ("approval" in res) setWaiting(true);
      else onReleased(res);
      setNote(""); setRead(false);
    } catch (err) { setError(err.message); }
  }

  if (waiting) return (
    <Callout tone="success" title="Waiting for a second HR person" className="section-gap">
      A second HR person must approve this release before it goes live. They have been told; it is listed under <Link to="/approvals">Approvals</Link>.
    </Callout>
  );

  return (
    <form className="release-box" onSubmit={(e) => withWorking(() => release(e))}>
      <h3>{rollback ? "Restore this version (roll back)" : "Release this version"}</h3>
      <p className="muted">
        It becomes the live model at once, for every score and explanation. The release is recorded with your name,
        your note and the version it replaces, in the tamper-evident audit trail.
      </p>
      <label className="field">Why are you releasing it?
        <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000}
          placeholder="e.g. Retrained on the 2026 review cycle; test results and fairness checked against the live model." />
        <span className="field-hint">{note.trim().length < MIN_NOTE ? `At least ${MIN_NOTE} characters (${note.trim().length} so far).` : "Thank you."}</span>
      </label>
      <label className="check"><input type="checkbox" checked={read} onChange={(e) => setRead(e.target.checked)} />
        I have read this model card, including its fairness results and limitations.</label>
      {error && <Callout tone="error" className="section-gap">{error}</Callout>}
      <div className="form-actions section-gap">
        <Button type="submit" busy={working} busyText="Releasing…" icon={rollback ? RotateCcw : Rocket}
          disabled={!read || note.trim().length < MIN_NOTE}>{rollback ? "Restore as the live model" : "Release as the live model"}</Button>
      </div>
    </form>
  );
}

function ModelCard({ version, rows, onChanged }) {
  const { user } = useAuth();
  const { data, error, reload, setData } = useLoad(() => governance.model(version), [version]);
  if (error) return <LoadError message={error} onRetry={reload} />;
  if (!data) return <Loading label="Opening the model card…" />;
  const card = data.card;
  const metrics = card.test_results || {};
  const live = rows.find((r) => r.status === "live");
  const row = rows.find((r) => r.version === version);
  const checks = Object.entries(card.fairness?.checks || {});
  const comparison = Object.entries(card.model_comparison?.validation || {});

  return (
    <Card title={`Model card: ${version}`} subtitle={`${card.model}, trained ${date(card.trained_at)}`}
      actions={<ModelStatus status={data.status} />}>
      <dl className="rec-facts">
        <div><dt>Decision threshold</dt><dd>{percent(card.threshold)} <span className="muted">({card.threshold_rule})</span></dd></div>
        <div><dt>Inputs</dt><dd>{card.inputs.length} performance and development measures</dd></div>
        <div><dt>Data</dt><dd>{card.mapping?.name || card.data?.note || "–"}{card.data?.rows && <span className="muted"> · {card.data.rows.toLocaleString()} rows</span>}</dd></div>
      </dl>

      <div className="two-columns">
        <div>
          <h3>Tested once, on {metrics.test_size?.toLocaleString() ?? "–"} unseen records</h3>
          <table className="compact-table"><tbody>
            <tr><td>ROC-AUC</td><td className="strong">{num(metrics.roc_auc)}<Delta value={metrics.roc_auc} live={live && version !== live.version ? live.roc_auc : null} /></td></tr>
            <tr><td>PR-AUC</td><td className="strong">{num(metrics.pr_auc)} <span className="muted">(random guessing {num(metrics.pr_auc_baseline, 2)})</span><Delta value={metrics.pr_auc} live={live && version !== live.version ? live.pr_auc : null} /></td></tr>
            <tr><td>Precision · recall</td><td>{percent(metrics.precision ?? 0)} · {percent(metrics.recall ?? 0)}</td></tr>
            <tr><td>Share recommended</td><td>{percent(metrics.share_recommended ?? 0)}</td></tr>
          </tbody></table>
        </div>
        <div>
          <h3>Fairness at training (four-fifths rule)</h3>
          <table className="compact-table"><tbody>
            {checks.map(([name, check]) => (
              <tr key={name}><td>{name.replace("_", " ")}</td><td className="strong">{num(check.ratio, 2)}</td>
                <td>{check.passes ? <span className="tag tag-yes">Passes</span> : <span className="tag tag-warn">Fails</span>}</td></tr>
            ))}
          </tbody></table>
        </div>
      </div>

      <h3 className="section-gap">Calibration: does a score of 30% mean about 30%?</h3>
      {card.calibration ? (
        <>
          <CalibrationSummary calibration={card.calibration} />
          <p className="muted measure">
            Employees are put in ten equal groups by score. If each point sits on the dashed line (perfect calibration), a score can be read
            as the share of similar employees promoted in the past data. It describes past decisions, not a promise.
          </p>
          <CalibrationChart calibration={card.calibration} />
        </>
      ) : <p className="muted">Not measured for this version yet (python -m evaluation.calibration {version}).</p>}

      {card.why_this_model && (
        <details className="details">
          <summary>Why this model, and the models it was compared with</summary>
          <p>{card.why_this_model}</p>
          {comparison.length > 0 && (
            <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Models compared"><table>
              <thead><tr><th>Model</th><th>Validation PR-AUC</th><th>ROC-AUC</th><th>Scores that dropped when an input improved</th></tr></thead>
              <tbody>{comparison.map(([name, m]) => (
                <tr key={name}><td className={name === card.model ? "strong" : ""}>{name}</td><td>{num(m.val_pr_auc, 4)}</td>
                  <td>{num(m.val_roc_auc, 4)}</td><td>{percent(m.common_sense_violations)}</td></tr>
              ))}</tbody>
            </table></div>
          )}
        </details>
      )}

      <div className="two-columns section-gap">
        <div><h3>Intended use</h3><p>{card.intended_use}</p></div>
        <div><h3>Limitations</h3><ul className="small tips">{card.limitations.map((l) => <li key={l}>{l}</li>)}</ul></div>
      </div>
      {card.registered_note && <p className="muted">{card.registered_note}</p>}

      <h3 className="section-gap">Release history</h3>
      {data.releases.length === 0 ? <p className="muted">Never released{data.status === "live" ? " through the registry (it was live before the registry existed)" : ""}.</p> : (
        <ul className="plain-list">{data.releases.map((r) => (
          <li key={r.released_at}><strong>{r.released_by}</strong> released it on {date(r.released_at)}
            {r.previous_version && <> (replacing {r.previous_version})</>}: <span className="muted">"{r.note}"</span></li>
        ))}</ul>
      )}

      {data.status === "blocked" && (
        <Callout tone="warning" icon={ShieldAlert}>This version failed the four-fifths fairness check, so it can never be released.</Callout>
      )}
      {user.role === "hr" && (data.status === "candidate" || data.status === "retired") && (
        <ReleaseBox row={row} onReleased={(result) => { setData(result); onChanged(); }} />
      )}
      {user.role !== "hr" && data.status === "candidate" && (
        <Callout>Waiting for an HR person to read this card and release it. Read-only for your role.</Callout>
      )}
    </Card>
  );
}

export default function ModelRegistry() {
  const { data: rows, error, reload } = useLoad(() => governance.models(), []);
  const [open, setOpen] = useState(null);
  useEffect(() => {  // open the version waiting for release first, otherwise the live one
    if (rows && !open) setOpen((rows.find((r) => r.status === "candidate") || rows.find((r) => r.status === "live") || rows[0])?.version);
  }, [rows, open]);

  const header = <PageHeader title="Model registry"
    subtitle="Every trained model version and its model card. Training never changes the live model: a person releases it." />;
  if (error) return <>{header}<LoadError message={error} onRetry={reload} /></>;
  if (!rows) return <>{header}<PageLoading /></>;
  return (
    <>
      {header}
      <Card title="Versions" subtitle="Newest first. Open one to read its card." flush>
        <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Model versions"><table>
          <thead><tr><th>Version</th><th>Trained</th><th className="num">Test ROC-AUC</th><th className="num">Lowest fairness ratio</th><th>Status</th><th><span className="visually-hidden">Open</span></th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.version} className={r.version === open ? "row-open" : ""}>
              <td><span className="strong mono">{r.version}</span><div className="cell-sub">{r.model}</div></td>
              <td className="num">{date(r.trained_at)}</td>
              <td className="num">{num(r.roc_auc)}</td>
              <td className="num">{num(r.lowest_fairness_ratio, 2)}</td>
              <td><ModelStatus status={r.status} />{r.released_by && <div className="muted">by {r.released_by}, {date(r.released_at)}</div>}</td>
              <td><div className="actions"><button type="button" className="btn btn-secondary btn-sm" aria-pressed={r.version === open}
                onClick={() => setOpen(r.version)}>{r.version === open ? "Open" : "Open card"}</button></div></td>
            </tr>
          ))}</tbody>
        </table></div>
      </Card>
      {open && <ModelCard key={open} version={open} rows={rows} onChanged={reload} />}
    </>
  );
}
