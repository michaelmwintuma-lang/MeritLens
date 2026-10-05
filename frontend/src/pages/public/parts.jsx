// Pieces shared by the public pages: photos and their credits, the page intro, feature rows, cards, numbered
// steps and the "Book a demo" band. The people in the photos are from Pexels (free to use under the Pexels
// licence; photographers credited in the footer). The small screenshots are the real app with made-up demo data.
import { Link } from "react-router-dom";
import { ArrowRight, CalendarCheck, CheckCircle2 } from "lucide-react";

export const PHOTOS = "/landing/people";

// The pages in the top menu
export const PAGES = [["/approach", "Approach"], ["/promotion", "Promotion"], ["/reporting", "Reporting"], ["/privacy", "Privacy"]];

// Photo credits (Pexels licence: free to use; credit is a courtesy)
export const CREDITS = [
  ["Antoni Shkraba", "https://www.pexels.com/photo/people-in-the-office-having-a-meeting-7163354/"],
  ["Christina Morillo", "https://www.pexels.com/photo/photography-of-woman-using-laptop-1181742/"],
  ["Mizuno K", "https://www.pexels.com/photo/smiling-woman-sitting-behind-a-desk-and-using-laptop-12912112/"],
  ["Kindel Media", "https://www.pexels.com/photo/people-creative-office-working-6773652/"],
  ["Karola G", "https://www.pexels.com/photo/a-team-at-the-room-looking-at-the-laptop-7876755/"],
  ["Kampus Production", "https://www.pexels.com/photo/a-group-of-business-people-in-a-meeting-8636606/"],
  ["Roman Odintsov", "https://www.pexels.com/photo/smiling-woman-pointing-at-laptop-screen-5912204/"],
];

/** The top of every page except Home: a small label, the title and one paragraph. */
export function PageIntro({ eyebrow, title, children }) {
  return (
    <section className="page-intro">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      <p className="lead">{children}</p>
    </section>
  );
}

/** A real photo with a small screenshot of the app tucked over its corner. */
function PhotoWithScreen({ photo, alt, screen, screenAlt, portrait }) {
  return (
    <div className={`photo-stack ${portrait ? "portrait" : ""}`}>
      <img className="photo" src={`${PHOTOS}/${photo}`} alt={alt} loading="lazy" />
      <figure className="screen-inset">
        <div className="shot-bar" aria-hidden="true"><span /><span /><span /></div>
        <img src={screen} alt={screenAlt} loading="lazy" />
      </figure>
    </div>
  );
}

/** Text with ticked points beside a photo; `flip` puts the photo on the left. */
export function Feature({ eyebrow, title, text, points, flip, ...visual }) {
  return (
    <section className={`feature ${flip ? "flip" : ""}`}>
      <div className="feature-text">
        <div className="eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
        <p className="lead">{text}</p>
        <ul className="checks">{points.map((p) => <li key={p}><CheckCircle2 size={18} aria-hidden="true" />{p}</li>)}</ul>
      </div>
      <PhotoWithScreen {...visual} />
    </section>
  );
}

/** Small cards with an icon, a title and a sentence. */
export function Cards({ items, columns = 3 }) {
  return (
    <div className={`promise-grid cols-${columns}`}>
      {items.map(({ icon: Icon, title, text }) => (
        <div key={title} className="promise"><div className="promise-icon"><Icon size={20} aria-hidden="true" /></div><h3>{title}</h3><p>{text}</p></div>
      ))}
    </div>
  );
}

/** How something works, as numbered steps. */
export function Steps({ title, items }) {
  return (
    <section className="section-block">
      <div className="section-intro"><div className="eyebrow">How it works</div><h2>{title}</h2></div>
      <ol className="steps-grid">
        {items.map(([heading, text], i) => (
          <li key={heading}><span className="step-number" aria-hidden="true">{i + 1}</span><h3>{heading}</h3><p>{text}</p></li>
        ))}
      </ol>
    </section>
  );
}

/** The navy band at the bottom of each page: book a demo, or sign in. */
export function DemoBand() {
  return (
    <section className="cta">
      <div>
        <h2>See it working for your organisation</h2>
        <p>A 30-minute walkthrough of promotion readiness and anonymous reporting, with your questions answered.</p>
      </div>
      <div className="cta-actions">
        <Link className="btn btn-accent btn-lg" to="/demo"><CalendarCheck size={18} aria-hidden="true" />Book a demo</Link>
        <Link className="btn btn-on-dark btn-lg" to="/login">Sign in <ArrowRight size={18} aria-hidden="true" /></Link>
      </div>
    </section>
  );
}
