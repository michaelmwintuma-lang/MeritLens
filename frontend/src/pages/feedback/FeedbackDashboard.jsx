// The feedback dashboard (HR and the compliance auditor): how employees respond to their explanations, how record
// corrections are handled, and where committees went against the model. Every number comes from
// the server, already filtered and with small groups protected; nothing here is one person's answer.
import { useEffect, useState } from "react";
import { Download, Flag } from "lucide-react";
import { api, apiBlob } from "../../api";
import { percent } from "../../format";
import { Button, Card, EmptyState, LoadError, PageHeader, PageLoading, StatCard } from "../../components/ui";
import BarList, { Meter, StackedBar } from "../../components/charts/BarList";

const NONE = { start: "", end: "", department: "", model_version: "" };
const WITHHELD = "Fewer than 5 ratings: withheld so no one's answer can be read off";

function query(filters) {
  const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
  return params.toString() ? `?${params}` : "";
}

const shown = (value, format = percent) => (value == null ? "–" : format(value));

function hoursText(hours) {
  if (hours == null) return "–";
  return hours < 48 ? `${hours} h` : `${(hours / 24).toFixed(1)} days`;
}

export default function FeedbackDashboard() {
  const [filters, setFilters] = useState(NONE);
  const [data, setData] = useState(null);
  const [options, setOptions] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    api(`/feedback/dashboard${query(filters)}`)
      .then((d) => { setData(d); setOptions((o) => o || d.options); })
      .catch((err) => setError(err.message));
  }, [filters]);

  async function exportCsv() {
    try {
      const url = URL.createObjectURL(await apiBlob(`/feedback/dashboard/export.csv${query(filters)}`));
      Object.assign(document.createElement("a"), { href: url, download: "feedback-dashboard.csv" }).click();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (err) {
      setError(err.message);
    }
  }

  const set = (key) => (e) => setFilters({ ...filters, [key]: e.target.value });
  const r = data?.ratings, c = data?.corrections, m = data?.committee;

  return (
    <>
      <PageHeader title="Feedback dashboard"
        subtitle="How employees respond to their explanations, and how HR and the committee act on it. Totals only: never one person's answer."
        actions={<Button icon={Download} onClick={exportCsv} disabled={!data}>Export CSV</Button>} />

      <Card>
        <div className="filters dashboard-filters">
          <label className="field">From<input type="date" value={filters.start} onChange={set("start")} /></label>
          <label className="field">To<input type="date" value={filters.end} onChange={set("end")} /></label>
          <label className="field">Department
            <select value={filters.department} onChange={set("department")}>
              <option value="">All departments</option>
              {options?.departments.map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>
          <label className="field">Model version
            <select value={filters.model_version} onChange={set("model_version")}>
              <option value="">All versions</option>
              {options?.model_versions.map((v) => <option key={v} value={v}>{v}{v === options.current_model_version ? " (live)" : ""}</option>)}
            </select>
          </label>
          <Button look="ghost" onClick={() => setFilters(NONE)} disabled={filters === NONE}>Clear filters</Button>
        </div>
        <p className="muted section-gap">Only departments with at least 5 people can be chosen. Counts of 1 or 2 are shown as “&lt;3”.</p>
      </Card>

      {error && <LoadError message={error} onRetry={() => setFilters({ ...filters })} />}
      {!data && !error && <PageLoading />}
      {data && (
        <div aria-live="polite">
          <div className="stat-grid">
            <StatCard label="Ratings" value={r.count} note="Explanations rated by employees" />
            <StatCard label="Received" value={c.received} note={`${c.pending} waiting for HR`} />
            <StatCard label="Confirmation rate" value={shown(c.confirmation_rate)} note="Of decided correction requests" />
            <StatCard label="Time to decide" value={hoursText(c.mean_resolution_hours)} note="Average, from request to HR's decision" />
          </div>

          <div className="chart-grid">
            <Card title="Explanations" subtitle="Share of ratings that answered 4 or 5 out of 5.">
              <Meter label="Clear" value={r.clarity_rate} format={percent} note="“This explanation was clear”" withheld={WITHHELD} />
              <Meter label="Useful" value={r.usefulness_rate} format={percent} note="“This explanation was useful”" withheld={WITHHELD} />
            </Card>
            <Card title="Record corrections" subtitle={`${c.received} received. Nothing in a record changes until HR confirms it.`}>
              <StackedBar label="Record corrections by outcome" parts={[
                { key: "confirmed", label: "Confirmed", value: c.confirmed, slot: 1 },
                { key: "rejected", label: "Rejected", value: c.rejected, slot: 2 },
                { key: "pending", label: "Waiting for HR", value: c.pending, slot: 4 },
              ]} />
            </Card>
          </div>

          <Card title="Factors employees contest" subtitle="How often each factor was marked “seems wrong” or “seems unfair”, as a share of ratings. Most contested first.">
            {r.contested.length === 0 ? <EmptyState compact icon={Flag} title="No factor has been marked yet" text="When employees flag a factor as wrong or unfair, it is counted here." /> : (
              <BarList label="Contest share per factor" format={(v) => percent(v)} axis={["0%", "Most contested"]}
                rows={r.contested.map((x) => ({ key: x.feature, name: x.label, value: x.share ?? null,
                  detail: `(wrong ${x.wrong}, unfair ${x.unfair})` }))} />
            )}
          </Card>

          <Card title="Committee decisions" subtitle="Decisions that went against the model, each with its written reason.">
            <StackedBar label="Decisions compared with the model" parts={[
              { key: "same", label: "Same as the model", value: typeof m.decisions === "number" && typeof m.overrides === "number" ? m.decisions - m.overrides : "–", slot: 1 },
              { key: "against", label: "Against the model", value: m.overrides, slot: 2 },
            ]} />
            <p className="muted">{m.override_rate == null ? "No decisions yet." : `${percent(m.override_rate)} of ${m.decisions} decisions went against the model.`}</p>
            {m.reasons.length > 0 && (
              <ul className="plain-list reasons">
                {m.reasons.map((x, i) => (
                  <li key={i}><span className="muted">{x.decided_on} · {x.decision === "approve" ? "approved" : "rejected"} although the model {x.model_recommended ? "recommended" : "didn't recommend"}</span>
                    <div>{x.reason}</div></li>
                ))}
              </ul>
            )}
          </Card>
          <p className="muted">Worked out {data.generated_at.slice(0, 16).replace("T", " ")} UTC from the live data.</p>
        </div>
      )}
    </>
  );
}
