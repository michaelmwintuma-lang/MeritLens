// The frame around every signed-in page: brand and menu on the left, the user at the bottom.
// Menu groups open and close when clicked; the group holding the current page opens by itself when you go there.
// On a computer the sidebar can shrink to a narrow strip of icons. On a phone it becomes a tab bar at the bottom,
// and "Menu" slides the full menu in from the side.
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { ChevronDown, ChevronsLeft, ChevronsRight, LogOut, Menu, X } from "lucide-react";
import { useAuth } from "../auth";
import { ACCOUNT, PHONE_TABS, ROLE_NAMES, SHORT_LABELS, menuFor } from "../roles";
import { BRAND } from "../brand";
import { BrandMark } from "./ui";

const NARROW_KEY = "sidebar-narrow";
function readNarrow() {
  try { return localStorage.getItem(NARROW_KEY) === "1"; } catch { return false; }
}

function Link({ to, label, icon: Icon, nested }) {
  return (
    <NavLink to={to} end={to === "/"} className={`nav-link ${nested ? "nested" : ""}`} data-tip={label}>
      <Icon size={nested ? 17 : 19} aria-hidden="true" /><span className="nav-label">{label}</span>
    </NavLink>
  );
}

function Group({ group, icon: Icon, items }) {
  const { pathname } = useLocation();
  const holdsCurrentPage = items.some((item) => pathname === item.to || pathname.startsWith(`${item.to}/`));
  const [isOpen, setOpen] = useState(holdsCurrentPage);
  // Going to a page inside this group opens it; clicking the heading always opens or closes it
  useEffect(() => { if (holdsCurrentPage) setOpen(true); }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="nav-group">
      <button type="button" className={`nav-link nav-group-head ${holdsCurrentPage ? "holds" : ""}`} aria-expanded={isOpen}
        onClick={() => setOpen(!isOpen)}>
        <Icon size={19} aria-hidden="true" /><span className="nav-label">{group}</span>
        <ChevronDown size={16} className={`chevron ${isOpen ? "open" : ""}`} aria-hidden="true" />
      </button>
      {isOpen && <div className="nav-group-items">{items.map((item) => <Link key={item.to} {...item} nested />)}</div>}
    </div>
  );
}

/** The narrow sidebar shows every page as an icon (no groups), with its name on hover. */
function IconMenu({ menu }) {
  return menu.map((entry, i) => (entry.group
    ? <div key={entry.group} className="rail-group" role="group" aria-label={entry.group}>
        {i > 0 && <hr className="rail-divider" />}
        {entry.items.map((item) => <Link key={item.to} {...item} />)}
      </div>
    : <Link key={entry.to} {...entry} />));
}

export default function Layout() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const [narrow, setNarrow] = useState(readNarrow);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const menu = [...menuFor(user), ACCOUNT];
  const pages = menu.flatMap((entry) => (entry.group ? entry.items : [entry]));
  const tabs = (PHONE_TABS[user.role] || []).map((to) => pages.find((page) => page.to === to)).filter(Boolean);

  useEffect(() => { setDrawerOpen(false); }, [pathname]);
  useEffect(() => {
    if (!drawerOpen) return undefined;
    const close = (e) => { if (e.key === "Escape") setDrawerOpen(false); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [drawerOpen]);

  function toggleNarrow() {
    setNarrow(!narrow);
    try { localStorage.setItem(NARROW_KEY, narrow ? "0" : "1"); } catch { /* remembered for this visit only */ }
  }

  return (
    <div className={`layout ${narrow ? "is-narrow" : ""}`}>
      <header className="phone-bar">
        <BrandMark small />
        <span className="brand-name">{BRAND}</span>
        <button type="button" className="icon-btn" onClick={() => setDrawerOpen(true)} aria-label="Open the menu"><Menu size={18} /></button>
      </header>

      {drawerOpen && <div className="scrim" onClick={() => setDrawerOpen(false)} aria-hidden="true" />}
      <aside className={`sidebar ${drawerOpen ? "open" : ""}`}>
        <div className="brand">
          <BrandMark />
          <div className="brand-text"><div className="brand-name">{BRAND}</div></div>
          <button type="button" className="icon-btn drawer-close" onClick={() => setDrawerOpen(false)} aria-label="Close the menu"><X size={18} /></button>
        </div>
        <button type="button" className="narrow-toggle" onClick={toggleNarrow}
          aria-label={narrow ? "Widen the menu" : "Narrow the menu"} title={narrow ? "Widen the menu" : "Narrow the menu"}>
          {narrow ? <ChevronsRight size={15} /> : <ChevronsLeft size={15} />}
        </button>
        <nav aria-label="Main menu">
          {narrow
            ? <IconMenu menu={menu} />
            : menu.map((entry) => (entry.group ? <Group key={entry.group} {...entry} /> : <Link key={entry.to} {...entry} />))}
        </nav>
        <div className="sidebar-user">
          {user.photo ? <img className="avatar" src={user.photo} alt="" /> : <div className="avatar" aria-hidden="true">{user.full_name.charAt(0)}</div>}
          <div className="user-text">
            <div className="user-name">{user.full_name}</div>
            <span className="role-badge">{ROLE_NAMES[user.role]}</span>
          </div>
          <button type="button" className="icon-btn" onClick={logout} aria-label="Sign out" title="Sign out"><LogOut size={17} /></button>
        </div>
      </aside>

      <main className="main"><div className="main-inner"><Outlet /></div></main>

      <nav className="tab-bar" aria-label="Quick menu">
        {tabs.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === "/"} className="tab" aria-label={label}>
            <span className="tab-pill"><Icon size={20} aria-hidden="true" /></span>
            <span className="tab-label">{SHORT_LABELS[to] || label}</span>
          </NavLink>
        ))}
        <button type="button" className="tab" onClick={() => setDrawerOpen(true)}>
          <span className="tab-pill"><Menu size={20} aria-hidden="true" /></span>
          <span className="tab-label">Menu</span>
        </button>
      </nav>
    </div>
  );
}
