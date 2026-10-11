// The public landing page: what the platform is (predict → explain → respond), what it offers, the promises it
// keeps, and its measured results. Every result comes from the last training and evaluation runs
// (/api/public/summary); a result that hasn't been measured yet shows as "–", never as an example number.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ClipboardPen, FileCheck2, Gauge, ListChecks, MessageSquareText, Route, Scale, ScanSearch, ShieldCheck, UserCheck, Users } from "lucide-react";
import { api } from "../../api";
import { BRAND, TAGLINE } from "../../brand";
import { Screenshot } from "./parts";

const STEPS = [
  { icon: Gauge, title: "Predict", text: "A fairness-checked model estimates how ready each person is for promotion, from their performance and development record only." },
  { icon: ScanSearch, title: "Explain", text: "Every score comes with the reasons in plain words, and the smallest realistic steps that would reach the threshold." },
  { icon: MessageSquareText, title: "Respond", text: "Employees rate the explanation, and ask HR to correct a wrong record, with evidence." },
];

const FEATURES = [
  { icon: ScanSearch, title: "Explainable predictions", text: "Each score splits exactly into what raised it and what lowered it (equal to its SHAP values), with LIME as an independent second opinion." },
  { icon: Route, title: "Path to promotion", text: "The smallest realistic improvements that would reach the threshold, plus a what-if tool for trying changes. Nothing is saved." },
  { icon: Scale, title: "Fairness audit", text: "Before a model goes live it must pass the four-fifths rule for gender, age and education. A model that fails is never used." },
  { icon: MessageSquareText, title: "Employee feedback channel", text: "Rate the explanation, flag factors that seem wrong or unfair, and ask HR to correct your record with evidence." },
  { icon: FileCheck2, title: "Accountable records", text: "Every change to a record is kept: who made it, the old and new value, why, and the score before and after." },
  { icon: UserCheck, title: "People decide", text: "Managers recommend and HR decides; going against the model needs a written reason, and every decision is logged." },
];

const PROMISES = [
  { icon: ShieldCheck, title: "A complaint never changes a score", text: "Ratings never reach the model. Only a record correction that HR confirms against evidence can, and it is logged. An automated test checks this." },
  { icon: ClipboardPen, title: "A wrong record can be put right", text: "If a value in your record is wrong, ask HR to correct it with evidence. HR checks it and tells you the outcome, with a reason." },
  { icon: Users, title: "People make every decision", text: "The model only advises. Every decision records who made it, what the model said and, if they differed, why." },
];

export default function Home() {
  const [facts, setFacts] = useState(null);
  useEffect(() => { api("/public/summary").then(setFacts).catch(() => setFacts(null)); }, []);
  const trained = facts?.trained;

  return (
    <>
      <section className="home-intro">
        <p className="eyebrow">{BRAND}</p>
        <h1>{TAGLINE}</h1>
        <p className="lead">
          {BRAND} helps an organisation decide promotions it can explain. It predicts how ready each employee is, shows
          why in plain words, and gives every employee a way to respond.
        </p>
        <div className="row intro-actions">
          <Link className="btn btn-primary btn-lg" to="/login">Sign in</Link>
          <a className="btn btn-accent btn-lg" href="#how-it-works">How it works</a>
        </div>
      </section>

      <section aria-labelledby="how-it-works" className="home-section">
        <h2 id="how-it-works">How it works</h2>
        <ol className="how-steps">
          {STEPS.map(({ icon: Icon, title, text }, i) => (
            <li key={title}>
              <span className="how-icon"><Icon size={22} aria-hidden="true" /></span>
              <h3><span className="how-number">{i + 1}.</span> {title}</h3>
              <p>{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <Screenshot wide src="/landing/growth.webp" alt="An employee's My growth page: the readiness score, the factors that raised and lowered it, and the panel to respond">
        An employee's own page: the score, and exactly what raised and lowered it compared with an average employee.
      </Screenshot>

      <section aria-labelledby="features" className="home-section">
        <h2 id="features">What it does</h2>
        <ul className="feature-grid">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <li key={title}>
              <Icon size={20} aria-hidden="true" className="feature-icon" />
              <h3>{title}</h3>
              <p>{text}</p>
            </li>
          ))}
        </ul>
      </section>

      <Screenshot src="/landing/respond.webp" alt="The Respond to this explanation panel, with tabs to rate the explanation or correct the record, and two 1 to 5 scales">
        Further down: the smallest realistic steps to the threshold, then the panel to respond: rate the explanation, or ask HR to correct a value.
      </Screenshot>

      <section aria-labelledby="promises" className="home-section trust">
        <h2 id="promises">What we promise</h2>
        <ul className="promise-grid">
          {PROMISES.map(({ icon: Icon, title, text }) => (
            <li key={title}>
              <Icon size={22} aria-hidden="true" className="feature-icon" />
              <h3>{title}</h3>
              <p>{text}</p>
            </li>
          ))}
        </ul>
        <p className="small"><Link className="text-link" to="/privacy">What we store, and what we don't <ArrowRight size={16} aria-hidden="true" /></Link></p>
      </section>

      <section className="results-section">
        <h2>How it did in testing</h2>
        <p className="muted">Measured on synthetic (made-up) employee data, on employees the model never saw in training.</p>
        <dl className="results">
          <div><dt>{trained ? facts.roc_auc.toFixed(2) : "–"}</dt>
            <dd>ROC-AUC for the promotion model on {trained ? `${facts.test_size.toLocaleString()} employees` : "employees"} it hadn't seen during training, using {trained ? `${facts.inputs} ` : ""}performance and development measures only.</dd></div>
          <div><dt>{trained ? `${Math.round(facts.lowest_fairness_ratio * 100)}%` : "–"}</dt>
            <dd>Lowest selection ratio between groups (gender, age, education). The four-fifths rule asks for at least 80%.</dd></div>
          <div><dt>{trained ? facts.pr_auc.toFixed(2) : "–"}</dt>
            <dd>PR-AUC, the measure that suits a rare outcome: about 1 in 10 employees were promoted, so guessing scores {trained ? facts.pr_auc_baseline.toFixed(2) : "–"}.</dd></div>
          <div><dt>{trained ? facts.inputs : "–"}</dt>
            <dd>Inputs, all about performance and development: never gender, age, education, department or pay.</dd></div>
        </dl>
        <p className="muted small"><ListChecks size={14} aria-hidden="true" style={{ verticalAlign: "-2px" }} /> The model never sees gender, age, education, department or pay.</p>
      </section>

      <p className="closing">
        Want to see it with your own questions? <Link to="/demo">Book a demo</Link>, or <Link to="/login">sign in</Link> if you have an account.
      </p>
    </>
  );
}
