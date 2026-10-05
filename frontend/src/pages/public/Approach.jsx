// Our approach: the three pillars, the design principle, and who the platform is for.
import { Gauge, Quote, ShieldCheck, UserCog, Users } from "lucide-react";
import { Cards, DemoBand, PageIntro, PHOTOS } from "./parts";

const PILLARS = [
  { photo: "together.webp", alt: "Colleagues looking at a laptop together", title: "Explain every score",
    text: "Readiness always comes with its reasons, in plain words, and a second method checks the explanation." },
  { photo: "planning.webp", alt: "A team planning together at a glass wall", title: "Check fairness first",
    text: "Before a model is used, every gender, age group and education level must be recommended at a fair rate." },
  { photo: "progress.webp", alt: "A woman smiling as she works through her tasks", title: "Protect every voice",
    text: "Concerns are raised with names and dates removed, and nobody on either side of the conversation is named." },
];

const ROLES = [
  { icon: Gauge, title: "Employees", text: "See your readiness, what's behind it and how to improve. Raise a concern safely." },
  { icon: Users, title: "Managers", text: "Follow your team's readiness and nominate people, with the reasons in plain words." },
  { icon: ShieldCheck, title: "HR", text: "Decide on promotions with the model's view alongside, and handle reports in one inbox." },
  { icon: UserCog, title: "Administrators", text: "Create accounts for everyone; each person gets a welcome email to sign in." },
];

export default function Approach() {
  return (
    <>
      <PageIntro eyebrow="Our approach" title="Built around people, not just predictions">
        Technology helps, but trust comes from openness, fairness and safety. Every part of the platform is designed
        around those three.
      </PageIntro>

      <section className="section-block">
        <div className="pillars">
          {PILLARS.map((p) => (
            <article key={p.title} className="pillar">
              <img src={`${PHOTOS}/${p.photo}`} alt={p.alt} loading="lazy" />
              <div className="pillar-body"><h3>{p.title}</h3><p>{p.text}</p></div>
            </article>
          ))}
        </div>
      </section>

      <section className="principle">
        <Quote size={34} aria-hidden="true" />
        <p className="principle-text">The model advises. People decide.</p>
        <p className="principle-note">
          The model never makes a promotion decision; HR does, and must write down why whenever they disagree with it.
          Reports are read by people, and only people decide what happens next.
        </p>
      </section>

      <section className="section-block" id="roles">
        <div className="section-intro">
          <div className="eyebrow">Who it's for</div>
          <h2>Each person sees what their role needs</h2>
        </div>
        <Cards items={ROLES} columns={4} />
      </section>

      <DemoBand />
    </>
  );
}
