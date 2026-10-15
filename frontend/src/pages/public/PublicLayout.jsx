// The frame around every public page: the menu bar and the footer.
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { ThemeToggle, Wordmark } from "../../components/ui";
import { BRAND, PAGES } from "./parts";
import { PROJECT, TAGLINE } from "../../brand";
import "./public.css";

export default function PublicLayout() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);  // the menu on small screens
  const [scrolled, setScrolled] = useState(false);  // the bar gets a border once the page scrolls

  // A new page starts at the top, with the small-screen menu closed
  useEffect(() => { window.scrollTo(0, 0); setMenuOpen(false); }, [pathname]);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <header className={`landing-header ${scrolled ? "scrolled" : ""}`}>
        <div className="landing-nav">
          <Link to="/" className="brand-inline" aria-label={`${BRAND} home`}><Wordmark small /></Link>
          <nav className="landing-links" aria-label="Pages">
            {PAGES.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
          </nav>
          <div className="landing-actions">
            <ThemeToggle />
            <Link className="btn btn-plain hide-small" to="/login">Sign in</Link>
            <NavLink className="btn btn-primary hide-small" to="/demo">Book a demo</NavLink>
            <button type="button" className="icon-btn menu-toggle" onClick={() => setMenuOpen(!menuOpen)}
              aria-expanded={menuOpen} aria-label={menuOpen ? "Close menu" : "Open menu"}>
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
        {menuOpen && (
          <nav className="landing-dropdown" aria-label="Pages">
            <NavLink to="/" end>Home</NavLink>
            {PAGES.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
            <div className="dropdown-actions">
              <Link className="btn btn-secondary" to="/login">Sign in</Link>
              <Link className="btn btn-primary" to="/demo">Book a demo</Link>
            </div>
          </nav>
        )}
      </header>

      <main className="landing" id="main">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <Wordmark small />
            <p>{TAGLINE}</p>
          </div>
          <nav className="footer-col" aria-label="Product">
            <h2>Product</h2>
            <Link to="/">Overview</Link>
            {PAGES.map(([to, label]) => <Link key={to} to={to}>{label}</Link>)}
          </nav>
          <nav className="footer-col" aria-label="Get started">
            <h2>Get started</h2>
            <Link to="/demo">Book a demo</Link>
            <Link to="/login">Sign in</Link>
          </nav>
        </div>
        <div className="footer-project">
          <p className="footer-title">{PROJECT.title}</p>
          {/* Only the details that have been filled in (brand.js) are shown */}
          <dl className="footer-credits">
            {PROJECT.university && <div><dt>University</dt><dd>{PROJECT.university}</dd></div>}
            {PROJECT.team.length > 0 && <div><dt>Team</dt><dd>{PROJECT.team.join(", ")}</dd></div>}
            {PROJECT.supervisors.length > 0 && <div><dt>Supervised by</dt><dd>{PROJECT.supervisors.join(", ")}</dd></div>}
          </dl>
          <p className="footer-note">A final-year project. Demonstrated on synthetic employee data; screenshots use made-up names.</p>
        </div>
      </footer>
    </>
  );
}
