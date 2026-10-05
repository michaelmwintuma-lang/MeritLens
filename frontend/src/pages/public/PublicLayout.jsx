// The frame around every public page: the menu bar (each item opens its own page) and the footer.
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { CalendarCheck, Menu, ShieldCheck, X } from "lucide-react";
import { ThemeToggle } from "../../components/ui";
import { CREDITS, PAGES } from "./parts";
import "./public.css";

export default function PublicLayout() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);  // the menu on small screens
  const [scrolled, setScrolled] = useState(false);  // the bar gets a border and shadow once the page scrolls

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
          <Link to="/" className="brand-inline" aria-label="Home">
            <div className="brand-logo brand-logo-teal"><ShieldCheck size={20} aria-hidden="true" /></div>
            <div><div className="brand-name">Promotion &amp; Reporting</div><div className="brand-sub">Staff platform</div></div>
          </Link>
          <nav className="landing-links" aria-label="Pages">
            {PAGES.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
          </nav>
          <div className="landing-actions">
            <ThemeToggle />
            <Link className="btn btn-plain hide-small" to="/login">Sign in</Link>
            <NavLink className="btn btn-accent hide-small" to="/demo"><CalendarCheck size={16} aria-hidden="true" />Book a demo</NavLink>
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
              <Link className="btn btn-plain" to="/login">Sign in</Link>
              <Link className="btn btn-accent" to="/demo"><CalendarCheck size={16} aria-hidden="true" />Book a demo</Link>
            </div>
          </nav>
        )}
      </header>

      <main className="landing">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="footer-grid">
          <div>
            <div className="brand-inline">
              <div className="brand-logo dark"><ShieldCheck size={20} aria-hidden="true" /></div>
              <div><div className="brand-name">Promotion &amp; Reporting</div><div className="brand-sub">Staff platform</div></div>
            </div>
            <p>Fair, explainable promotion decisions and a safe, anonymous way to raise concerns. A final-year project.</p>
          </div>
          <div>
            <h4>Platform</h4>
            <Link to="/approach">Our approach</Link><Link to="/promotion">Promotion readiness</Link>
            <Link to="/reporting">Anonymous reporting</Link><Link to="/privacy">Privacy</Link>
          </div>
          <div>
            <h4>Get started</h4>
            <Link to="/demo">Book a demo</Link><Link to="/login">Sign in</Link><Link to="/approach">Who it's for</Link>
          </div>
          <div>
            <h4>Photos</h4>
            <p className="credits">
              From <a href="https://www.pexels.com" target="_blank" rel="noreferrer">Pexels</a> by{" "}
              {CREDITS.map(([name, url], i) => (
                <span key={name}><a href={url} target="_blank" rel="noreferrer">{name}</a>{i < CREDITS.length - 1 ? ", " : "."}</span>
              ))}
            </p>
          </div>
        </div>
        <div className="footer-bottom">
          <span>Trained and demonstrated on synthetic (made-up) employee data. The people pictured are not users of this system.</span>
          <Link to="/login">Sign in</Link>
        </div>
      </footer>
    </>
  );
}
