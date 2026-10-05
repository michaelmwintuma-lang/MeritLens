// Home: the promise, the tested results, and a way into each part of the platform.
// The numbers come from the last training run (/api/public/summary).
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BadgeCheck, CalendarCheck, Gauge, Megaphone, Quote } from "lucide-react";
import { api } from "../../api";
import { DemoBand, PHOTOS } from "./parts";

const EXPLORE = [
  { to: "/promotion", photo: "growth.webp", alt: "A smiling woman working on her laptop", title: "Promotion readiness",
    text: "Every score comes with its reasons, a second opinion and realistic tips." },
  { to: "/reporting", photo: "speak-up.webp", alt: "A person working calmly at their own desk", title: "Anonymous reporting",
    text: "Raise a concern with names and dates removed, and follow up with a private key." },
  { to: "/privacy", photo: "planning.webp", alt: "A team planning together at a glass wall", title: "Privacy by design",
    text: "Six promises the system keeps because of how it's built, each checked by tests." },
];

export default function Home() {
  const [facts, setFacts] = useState(null);
  useEffect(() => { api("/public/summary").then(setFacts).catch(() => setFacts(null)); }, []);
  const trained = facts?.trained;

  return (
    <>
      <section className="hero">
        <div className="hero-text">
          <span className="pill"><span className="dot" />Fair promotions · Safe reporting</span>
          <h1>Promotions you can explain.<br />Concerns raised <span className="accent">without fear.</span></h1>
          <p className="lead">
            A people-first platform for two things that matter to every employee: a promotion process that shows its
            reasons, and a safe way to report harassment, discrimination or unsafe work without revealing who you are.
          </p>
          <div className="row hero-actions">
            <Link className="btn btn-accent btn-lg" to="/demo"><CalendarCheck size={18} aria-hidden="true" />Book a demo</Link>
            <Link className="btn btn-plain btn-lg" to="/login">Sign in <ArrowRight size={18} aria-hidden="true" /></Link>
          </div>
          <ul className="hero-checks">
            <li><BadgeCheck size={17} aria-hidden="true" />Every score comes with its reasons</li>
            <li><BadgeCheck size={17} aria-hidden="true" />People decide, the model advises</li>
            <li><BadgeCheck size={17} aria-hidden="true" />Reports never linked to accounts</li>
          </ul>
        </div>
        <div className="hero-visual">
          <img className="hero-photo" src={`${PHOTOS}/team-hero.webp`} alt="A diverse team smiling around a table as they work together" />
          <div className="float float-a"><Gauge size={18} /><div><strong>Readiness 82%</strong><span>Recommended · see why</span></div></div>
          <div className="float float-b"><Megaphone size={18} /><div><strong>Report sent anonymously</strong><span>Only you hold the key</span></div></div>
        </div>
      </section>

      <section className="facts" aria-label="Results">
        <div><strong>{trained ? facts.roc_auc.toFixed(2) : "–"}</strong><span>ROC-AUC on {trained ? facts.test_size.toLocaleString() : "unseen"} test employees</span></div>
        <div><strong>{trained ? `${Math.round(facts.lowest_fairness_ratio * 100)}%` : "–"}</strong><span>lowest group ratio in the fairness check (80% needed)</span></div>
        <div><strong>0</strong><span>details about the reporter stored with a report</span></div>
        <div><strong>100%</strong><span>of promotion decisions made by people</span></div>
      </section>

      <section className="section-block">
        <div className="section-intro">
          <div className="eyebrow">Explore</div>
          <h2>One platform, two jobs, done carefully</h2>
        </div>
        <div className="pillars">
          {EXPLORE.map((p) => (
            <Link key={p.to} to={p.to} className="pillar pillar-link">
              <img src={`${PHOTOS}/${p.photo}`} alt={p.alt} loading="lazy" />
              <div className="pillar-body"><h3>{p.title}</h3><p>{p.text}</p><span className="more">Learn more <ArrowRight size={16} aria-hidden="true" /></span></div>
            </Link>
          ))}
        </div>
      </section>

      <section className="principle">
        <Quote size={34} aria-hidden="true" />
        <p className="principle-text">The model advises. People decide.</p>
        <p className="principle-note">
          Our design principle. The model never makes a promotion decision; HR does, and must write down why whenever
          they disagree with it. <Link to="/approach">Read about our approach</Link>.
        </p>
      </section>

      <DemoBand />
    </>
  );
}
