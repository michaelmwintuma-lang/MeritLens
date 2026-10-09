// The feedback dashboard (HR and the compliance auditor): how employees respond to their explanations, how record
// corrections are handled, what is reported, and where committees went against the model. Every number comes from
// the server, already filtered and with small groups protected; nothing here is one person's answer.
import { useEffect, useState } from "react";
import { Download, MessageSquareText } from "lucide-react";
import { api, apiBlob } from "../../api";
import { percent } from "../../format";
import { Card, PageHeader, StatCard } from "../../components/ui";
import BarList from "../../components/charts/BarList";

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
      <PageHeader icon={MessageSquareText} title="Feedback dashboard"
        subtitle="How employees respond to their explanations, and how HR and the committee act on it. Totals only: never one person's answer." />

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
          <div className="row">
            <button type="button" className="btn btn-plain" onClick={() => setFilters(NONE)} disabled={filters === NONE}>Clear filters</button>
            <button type="button" className="btn btn-primary" onClick={exportCsv} disabled={!data}><Download size={16} aria-hidden="true" />Export CSV</button>
          </div>
        </div>
        <p className="muted small" style={{ margin: 0 }}>Only departments with at least 5 people can be chosen. Counts of 1 or 2 are shown as “&lt;3”.</p>
      </Card>

      {error && <p className="alert alert-error" role="alert">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}
      {data && (
        <div aria-live="polite">
          <h2 className="section-title">Explanations</h2>
          <div className="stat-grid">
            <StatCard label="Ratings" value={r.count} note="Explanations rated by employees" />
            <StatCard label="Clear" value={shown(r.clarity_rate)} note={r.clarity_rate == null ? WITHHELD : "Rated 4 or 5 for “This explanation was clear”"} />
            <StatCard label="Useful" value={shown(r.usefulness_rate)} note={r.usefulness_rate == null ? WITHHELD : "Rated 4 or 5 for “This explanation was useful”"} />
          </div>
          <Card title="Factors employees contest" subtitle="How often each factor was marked “seems wrong” or “seems unfair”, as a share of ratings. Most contested first.">
            {r.contested.length === 0 ? <p className="muted">No factor has been marked yet.</p> : (
              <BarList label="Contest share per factor" format={(v) => percent(v)}
                rows={r.contested.map((x) => ({ key: x.feature, name: x.label, value: x.share ?? null,
                  detail: `(wrong ${x.wrong}, unfair ${x.unfair})` }))} />
            )}
          </Card>

          <h2 className="section-title">Record corrections</h2>
          <div className="stat-grid">
            <StatCard label="Received" value={c.received} note={`${c.pending} waiting for HR`} />
            <StatCard label="Confirmed" value={c.confirmed} note={`${c.rejected} rejected`} />
            <StatCard label="Confirmation rate" value={shown(c.confirmation_rate)} note="Of decided requests, the share confirmed" />
            <StatCard label="Time to decide" value={hoursText(c.mean_resolution_hours)} note="Average, from request to HR's decision" />
          </div>

          <div className="two-cards">
            <Card title="Anonymous reports by category" subtitle={data.reports.note}>
              <BarList label="Reports by category"
                rows={data.reports.by_category.map((x) => ({ key: x.category, name: x.label, value: x.count }))} />
              {data.reports.earlier_categories !== 0 && <p className="muted small">Reports in earlier categories: {data.reports.earlier_categories}</p>}
            </Card>
            <Card title="Committee decisions" subtitle="Decisions that went against the model, each with its written reason.">
              <div className="stat-grid compact">
                <StatCard label="Decisions" value={m.decisions} />
                <StatCard label="Against the model" value={m.overrides} note={m.override_rate == null ? "No decisions yet" : `${percent(m.override_rate)} of decisions`} />
              </div>
              {m.reasons.length > 0 && (
                <ul className="plain-list reasons">
                  {m.reasons.map((x, i) => (
                    <li key={i}><span className="muted small">{x.decided_on} · {x.decision === "approve" ? "approved" : "rejected"} although the model {x.model_recommended ? "recommended" : "didn't recommend"}</span>
                      <div>{x.reason}</div></li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
          <p className="muted small">Worked out {data.generated_at.slice(0, 16).replace("T", " ")} UTC from the live data.</p>
        </div>
      )}
    </>
  );
}
