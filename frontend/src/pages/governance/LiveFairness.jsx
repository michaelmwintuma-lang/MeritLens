// Live fairness: the four-fifths rule on what is happening now. For each characteristic, three stages side by
// side (the model, managers' nominations, HR's approvals), so a gap can be traced to where it appears. Totals per
// group only; a group under 5 people is never shown.
import { Scale } from "lucide-react";
import { governance } from "../../api";
import { useLoad } from "../../useLoad";
import { percent } from "../../format";
import { Card, LoadError, Loading, PageHeader } from "../../components/ui";

export const STATUS_TAG = {
  passes: ["tag tag-yes", "Passes"],
  "below four-fifths": ["tag tag-warn", "Below four-fifths: look into it"],
  "within chance": ["tag tag-info", "Below 0.8, within chance at this size"],
  "not enough data": ["tag", "Not enough data yet"],
};

export function StatusTag({ status }) {
  const [className, text] = STATUS_TAG[status] || ["tag", status];
  return <span className={className}>{text}</span>;
}

function Stage({ stage }) {
  const shown = stage.groups.filter((g) => g.shown);
  const top = Math.max(...shown.map((g) => g.rate ?? 0), 0);
  return (
    <div className="fair-stage">
      <div className="row spread">
        <h3>{stage.stage}</h3>
        <StatusTag status={stage.status} />
      </div>
      <ul className="bar-list" aria-label={`${stage.stage}: rate per group`}>
        {stage.groups.map((g) => (
          <li key={g.group}>
            <span className="bar-name">{g.group}</span>
            <span className="bar-track" aria-hidden="true">
              {g.rate != null && top > 0 && <span className="bar-fill" style={{ width: `${Math.max((g.rate / top) * 100, g.rate ? 2 : 0)}%` }} />}
            </span>
            <span className="bar-value">{g.shown ? (g.rate != null ? percent(g.rate) : "–") : "fewer than 5"}
              {g.count != null && <span className="muted small"> of {g.count}</span>}</span>
          </li>
        ))}
      </ul>
      <p className="muted small">
        {stage.ratio != null ? `Lowest ÷ highest: ${stage.ratio.toFixed(2)} (needs 0.80).` : "Needs at least two groups of 5 or more, and at least 5 people selected."}
        {stage.p_value != null && ` A gap this size would happen by chance ${percent(stage.p_value)} of the time${stage.p_value < 0.05 ? ", so it is unlikely to be chance." : ", so it may well be chance; keep watching."}`}
      </p>
    </div>
  );
}

export default function LiveFairness() {
  const { data, error, reload } = useLoad(() => governance.fairness(), []);
  const header = <PageHeader icon={Scale} title="Live fairness"
    subtitle="The four-fifths rule on today's directory and decisions, not only on the test set at training time." />;
  if (error) return <>{header}<LoadError message={error} onRetry={reload} /></>;
  if (!data) return <>{header}<Loading /></>;
  return (
    <>
      {header}
      <Card title="How to read this" actions={<StatusTag status={data.overall} />}>
        <p className="muted" style={{ margin: 0 }}>
          For each characteristic, every group's rate should be at least 80% of the highest group's. Three stages are
          checked: what the model recommends ({data.model_version}), whom managers nominate, and whom HR approves.
          Comparing them shows where a gap appears. In a small directory a few people more or less move a ratio a lot,
          so a ratio under 0.8 is flagged only when it is unlikely to be chance. Characteristics are kept apart from the employee directory, used
          only here, and never by the model. Groups under {data.min_group} are not shown.
          {" "}{data.with_monitoring_data} of {data.employees} employees have equality-monitoring data.
        </p>
      </Card>
      {data.checks.map((c) => (
        <Card key={c.characteristic} title={c.label}>
          <div className="fair-stages">{c.stages.map((s) => <Stage key={s.stage} stage={s} />)}</div>
        </Card>
      ))}
    </>
  );
}
