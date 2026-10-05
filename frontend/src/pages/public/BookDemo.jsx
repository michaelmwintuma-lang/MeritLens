// Book a demo: a short form. The request is emailed to the team and listed for the admin.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarCheck, CheckCircle2, Clock, MessagesSquare, MonitorPlay } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { Button } from "../../components/ui";
import { PHOTOS } from "./parts";

const EMPTY = { name: "", email: "", organisation: "", job_title: "", size: "", interest: "", message: "", website: "" };

export default function BookDemo() {
  const [options, setOptions] = useState({ sizes: [], interests: [] });
  const [form, setForm] = useState(EMPTY);
  const [done, setDone] = useState("");
  const [error, setError] = useState("");
  const [sending, withSending] = useAction();
  useEffect(() => { api("/public/demo-requests/options").then(setOptions).catch(() => {}); }, []);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function send(e) {
    e.preventDefault();
    setError("");
    try {
      setDone((await api("/public/demo-requests", { method: "POST", body: form })).message);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="demo-page">
      <div className="demo-info">
        <div className="eyebrow">Book a demo</div>
        <h1>See the platform in action</h1>
        <p className="lead">Tell us a little about your organisation and we'll arrange a time that suits you.</p>
        <ul className="demo-points">
          <li><Clock size={20} aria-hidden="true" /><div><strong>30 minutes, online</strong><span>At a time that suits you.</span></div></li>
          <li><MonitorPlay size={20} aria-hidden="true" /><div><strong>A live walkthrough</strong><span>Promotion readiness and anonymous reporting, as each role sees them.</span></div></li>
          <li><MessagesSquare size={20} aria-hidden="true" /><div><strong>Your questions answered</strong><span>Fairness, privacy and how your own data would be used.</span></div></li>
        </ul>
        <img className="demo-photo" src={`${PHOTOS}/together.webp`} alt="Colleagues looking at a laptop together" loading="lazy" />
      </div>

      <div className="demo-card">
        {done ? (
          <div className="demo-done" role="status">
            <CheckCircle2 size={40} aria-hidden="true" />
            <h2>Request received</h2>
            <p>{done}</p>
            <Link className="btn btn-plain" to="/">Back to the home page</Link>
          </div>
        ) : (
          <form onSubmit={(e) => withSending(() => send(e))}>
            <h2>Your details</h2>
            <p className="muted small" style={{ marginTop: 0 }}>We only use these to contact you about the demo.</p>
            {error && <p className="alert alert-error" role="alert">{error}</p>}
            <div className="form-row">
              <label className="field">Full name<input value={form.name} onChange={set("name")} required minLength={2} maxLength={120} autoComplete="name" /></label>
              <label className="field">Work email<input type="email" value={form.email} onChange={set("email")} required autoComplete="email" /></label>
            </div>
            <div className="form-row">
              <label className="field">Organisation<input value={form.organisation} onChange={set("organisation")} required minLength={2} maxLength={160} autoComplete="organization" /></label>
              <label className="field"><span>Job title <span className="muted small">(optional)</span></span><input value={form.job_title} onChange={set("job_title")} maxLength={120} autoComplete="organization-title" /></label>
            </div>
            <div className="form-row">
              <label className="field">Number of employees
                <select value={form.size} onChange={set("size")} required>
                  <option value="">Choose…</option>
                  {options.sizes.map((s) => <option key={s}>{s}</option>)}
                </select>
              </label>
              <label className="field">Interested in
                <select value={form.interest} onChange={set("interest")} required>
                  <option value="">Choose…</option>
                  {options.interests.map((s) => <option key={s}>{s}</option>)}
                </select>
              </label>
            </div>
            <label className="field"><span>Anything you'd like us to cover? <span className="muted small">(optional)</span></span>
              <textarea rows={4} value={form.message} onChange={set("message")} maxLength={1000} />
            </label>
            {/* Hidden from people; form-filling robots fill it in, and their requests are dropped */}
            <label className="hp" aria-hidden="true">Website<input tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} /></label>
            <Button icon={CalendarCheck} look="accent" busy={sending} busyText="Sending…" className="btn-lg demo-submit">Request a demo</Button>
          </form>
        )}
      </div>
    </section>
  );
}
