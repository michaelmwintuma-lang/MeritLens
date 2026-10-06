// The frame around every public page: the menu bar and the footer.
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { BrandMark, ThemeToggle } from "../../components/ui";
import { BRAND, PAGES } from "./parts";
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
          <Link to="/" className="brand-inline" aria-label="Home"><BrandMark small /><span className="brand-name">{BRAND}</span></Link>
          <nav className="landing-links" aria-label="Pages">
            {PAGES.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
          </nav>
          <div className="landing-actions">
            <ThemeToggle />
            <Link className="btn btn-plain hide-small" to="/login">Sign in</Link>
            <NavLink className="btn btn-accent hide-small" to="/demo">Book a demo</NavLink>
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
              <Link className="btn btn-accent" to="/demo">Book a demo</Link>
            </div>
          </nav>
        )}
      </header>

      <main className="landing">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="brand-inline"><BrandMark small /><span className="brand-name">{BRAND}</span></div>
          <nav className="footer-links" aria-label="Footer">
            {PAGES.map(([to, label]) => <Link key={to} to={to}>{label}</Link>)}
            <Link to="/demo">Book a demo</Link>
            <Link to="/login">Sign in</Link>
          </nav>
        </div>
        <p className="footer-note">A final-year project. Demonstrated on synthetic employee data; screenshots use made-up names.</p>
      </footer>
    </>
  );
}
