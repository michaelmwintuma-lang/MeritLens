// Home page. The first two results come from the last training run (/api/public/summary); the reporting results
// are from results/reporting_evaluation.md.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { api } from "../../api";
import { BRAND, Screenshot } from "./parts";

export default function Home() {
  const [facts, setFacts] = useState(null);
  useEffect(() => { api("/public/summary").then(setFacts).catch(() => setFacts(null)); }, []);
  const trained = facts?.trained;

  return (
    <>
      <section className="home-intro">
        <h1>Promotion decisions you can check, and a safe way to report misconduct.</h1>
        <p className="lead">
          {BRAND} scores how ready each employee is for promotion and shows what moved the score. A manager
          recommends, HR decides and Finance confirms the pay rise. The same system lets staff report harassment,
          fraud or unsafe work without their name attached.
        </p>
        <div className="row intro-actions">
          <Link className="btn btn-accent btn-lg" to="/demo">Book a demo</Link>
          <Link className="btn btn-plain btn-lg" to="/login">Sign in</Link>
        </div>
      </section>

      <Screenshot wide src="/landing/readiness.webp" alt="An employee's readiness page, listing the factors that raised and lowered the score">
        An employee's readiness page. Each factor shows its real value and how far it moved the score.
      </Screenshot>

      <section className="two-col">
        <article>
          <h2>Promotion readiness</h2>
          <p>
            The model looks at 21 performance and development measures. It never sees gender, age, education or pay.
            Anyone looking at a score can open it and see the factors behind it, plus a few realistic things the person
            could work on.
          </p>
          <Link className="text-link" to="/promotion">How a decision is made <ArrowRight size={16} aria-hidden="true" /></Link>
        </article>
        <article>
          <h2>Anonymous reporting</h2>
          <p>
            Names, phone numbers and dates are taken out of a report before it is sent, and the reporter checks what's
            left. They follow up with a case ID and a key. HR never finds out who they are.
          </p>
          <Link className="text-link" to="/reporting">How reporting works <ArrowRight size={16} aria-hidden="true" /></Link>
        </article>
      </section>

      <section className="results-section">
        <h2>How it did in testing</h2>
        <p className="muted">Measured on synthetic (made-up) employee data and 50 hand-labelled test reports.</p>
        <dl className="results">
          <div><dt>{trained ? facts.roc_auc.toFixed(2) : "0.93"}</dt>
            <dd>ROC-AUC for the promotion model on {trained ? facts.test_size.toLocaleString() : "20,000"} employees it hadn't seen during training.</dd></div>
          <div><dt>{trained ? `${Math.round(facts.lowest_fairness_ratio * 100)}%` : "93%"}</dt>
            <dd>Lowest selection ratio between groups (gender, age, education). The four-fifths rule asks for at least 80%.</dd></div>
          <div><dt>87%</dt><dd>Of names, emails, phone numbers and dates removed automatically. The reporter reviews the rest before sending.</dd></div>
          <div><dt>14 of 14</dt><dd>Urgent test reports given high priority. The trade-off: some less urgent ones were rated too high.</dd></div>
        </dl>
      </section>

      <p className="closing">
        Want to see it with your own questions? <Link to="/demo">Book a demo</Link>, or <Link to="/login">sign in</Link> if you have an account.
      </p>
    </>
  );
}
