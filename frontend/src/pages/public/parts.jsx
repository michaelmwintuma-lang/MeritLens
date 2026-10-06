// Pieces shared by the public pages. The screenshots are the real app, with made-up demo data.
export { BRAND } from "../../brand";

// The pages in the top menu
export const PAGES = [["/approach", "Who uses it"], ["/promotion", "Promotions"], ["/reporting", "Reporting"], ["/privacy", "Privacy"]];

/** The top of a page: its title and a short paragraph. */
export function PageIntro({ title, children }) {
  return (
    <section className="page-intro">
      <h1>{title}</h1>
      {children && <p className="lead">{children}</p>}
    </section>
  );
}

/** A screenshot of the app with a caption underneath. */
export function Screenshot({ src, alt, children, wide = false }) {
  return (
    <figure className={`screenshot ${wide ? "wide" : ""}`}>
      <img src={src} alt={alt} loading="lazy" />
      {children && <figcaption>{children}</figcaption>}
    </figure>
  );
}
