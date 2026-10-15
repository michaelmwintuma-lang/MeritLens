// Pieces shared by the public pages. The screenshots are the real app, with made-up demo data.
export { BRAND } from "../../brand";

// The pages in the top menu
export const PAGES = [["/approach", "Who uses it"], ["/promotion", "Promotions"], ["/privacy", "Privacy"]];

/** The top of a page: its title and a short paragraph. */
export function PageIntro({ title, children }) {
  return (
    <section className="page-intro">
      <h1>{title}</h1>
      {children && <p className="lead">{children}</p>}
    </section>
  );
}

/** A screenshot of the app in a window frame, with a caption underneath. `eager` loads it straight away (the hero). */
export function Screenshot({ src, alt, children, eager = false }) {
  return (
    <figure className="screenshot">
      <div className="screenshot-frame"><span aria-hidden="true" /><img src={src} alt={alt} loading={eager ? "eager" : "lazy"} /></div>
      {children && <figcaption>{children}</figcaption>}
    </figure>
  );
}
