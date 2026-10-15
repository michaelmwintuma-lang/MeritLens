// The frame around every signed-in page: the menu on the left (grouped per role), a top bar with where you are,
// notifications and your profile, and the page itself. Menu groups open and close when clicked; the group holding
// the current page opens by itself when you go there.
// Widths: from 1024px the full sidebar (which can be collapsed to icons); from 640 to 1023px an icon rail; under
// 640px a drawer, opened from the top bar.
import { Suspense, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ChevronDown, ChevronRight, ChevronsLeft, ChevronsRight, LogOut, Menu, UserRound, X } from "lucide-react";
import { useAuth } from "../auth";
import { ROLE_NAMES, menuFor } from "../roles";
import { BrandMark, PageLoading, ThemeToggle, Wordmark } from "./ui";
import { useFocusTrap } from "./Overlay";
import NotificationBell from "./NotificationBell";
import ErrorBoundary from "./ErrorBoundary";

const RAIL_KEY = "sidebar-narrow";
function readRail() {
  try { return localStorage.getItem(RAIL_KEY) === "1"; } catch { return false; }
}

function useMedia(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [query]);
  return matches;
}

// Pages that aren't in the menu, named for the breadcrumb: [address pattern, name, the menu page above it]
const DETAIL_PAGES = [
  [/^\/employees\/new$/, "Add employee", "/employees"],
  [/^\/employees\/import$/, "Import employees", "/employees"],
  [/^\/employees\/\d+\/edit$/, "Edit details", "/employees"],
  [/^\/employees\/\d+$/, "Employee", "/employees"],
  [/^\/nominations\/\d+$/, "Review", "/nominations"],
  [/^\/account$/, "My profile", null],
];

/** Where the page sits in the menu: [group?, page, detail?], each { label, to? }. */
function breadcrumb(menu, pathname, role) {
  const find = (to) => {
    for (const entry of menu) {
      if (!entry.group && entry.to === to) return [{ label: entry.label, to: entry.to }];
      const item = entry.group && entry.items.find((i) => i.to === to);
      if (item) return [{ label: entry.group }, { label: item.label, to: item.to }];
    }
    return null;
  };
  const direct = find(pathname);
  if (direct) return direct;
  const detail = DETAIL_PAGES.find(([pattern]) => pattern.test(pathname));
  if (!detail) return [{ label: "Overview", to: "/" }];
  const parent = detail[2] === "/employees" && role === "manager" ? "/team" : detail[2];
  return [...(parent ? find(parent) || [] : []), { label: detail[1] }];
}

function NavItem({ to, label, icon: Icon }) {
  return (
    <NavLink to={to} end={to === "/"} className="nav-link" data-tip={label}>
      <Icon size={18} aria-hidden="true" /><span className="nav-label">{label}</span>
    </NavLink>
  );
}

function Group({ group, items }) {
  const { pathname } = useLocation();
  const holdsCurrentPage = items.some((item) => pathname === item.to || pathname.startsWith(`${item.to}/`));
  const [isOpen, setOpen] = useState(true);
  // Going to a page inside this group opens it; clicking the heading always opens or closes it
  useEffect(() => { if (holdsCurrentPage) setOpen(true); }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="nav-group">
      <button type="button" className="nav-link nav-group-head" aria-expanded={isOpen} onClick={() => setOpen(!isOpen)}>
        <span className="nav-label">{group}</span>
        <ChevronDown size={16} className={`chevron ${isOpen ? "open" : ""}`} aria-hidden="true" />
      </button>
      {isOpen && <div className="nav-group-items">{items.map((item) => <NavItem key={item.to} {...item} />)}</div>}
    </div>
  );
}

/** The icon rail shows every page as an icon (no group headings), with its name on hover or focus. */
function RailMenu({ menu }) {
  return menu.map((entry, i) => (entry.group
    ? <div key={entry.group} className="rail-group" role="group" aria-label={entry.group}>
        {i > 0 && <hr className="rail-divider" />}
        {entry.items.map((item) => <NavItem key={item.to} {...item} />)}
      </div>
    : <NavItem key={entry.to} {...entry} />));
}

/** Your name and role in the top bar; opens a menu with your profile and signing out. */
function ProfileMenu({ user, logout }) {
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const outside = (e) => { if (!box.current?.contains(e.target)) setOpen(false); };
    const escape = (e) => { if (e.key === "Escape") { setOpen(false); box.current?.querySelector("button")?.focus(); } };
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", outside); document.removeEventListener("keydown", escape); };
  }, [open]);

  return (
    <div className="profile" ref={box}>
      <button type="button" className="profile-button" aria-expanded={open} aria-haspopup="menu"
        aria-label={`Account: ${user.full_name}, ${ROLE_NAMES[user.role]}`} onClick={() => setOpen(!open)}>
        {user.photo ? <img className="avatar" src={user.photo} alt="" /> : <span className="avatar" aria-hidden="true">{user.full_name.charAt(0)}</span>}
        <span className="profile-text" aria-hidden="true"><span className="user-name">{user.full_name}</span><span className="role-badge">{ROLE_NAMES[user.role]}</span></span>
        <ChevronDown size={16} aria-hidden="true" className="muted" />
      </button>
      {open && (
        <div className="menu-panel" role="menu">
          <div className="menu-head"><span className="user-name">{user.full_name}</span><span className="role-badge">{ROLE_NAMES[user.role]}</span></div>
          <Link className="menu-item" role="menuitem" to="/account"><UserRound size={16} aria-hidden="true" />My profile</Link>
          <button type="button" className="menu-item" role="menuitem" onClick={logout}><LogOut size={16} aria-hidden="true" />Sign out</button>
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const phone = useMedia("(max-width: 639px)");
  const tablet = useMedia("(min-width: 640px) and (max-width: 1023px)");
  const [railChosen, setRailChosen] = useState(readRail);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const sidebar = useRef(null);
  const menu = menuFor(user);
  const rail = !phone && (tablet || railChosen);
  const crumbs = breadcrumb(menu, pathname, user.role);

  useEffect(() => { setDrawerOpen(false); }, [pathname]);
  useFocusTrap(sidebar, phone && drawerOpen, () => setDrawerOpen(false));

  function toggleRail() {
    setRailChosen(!railChosen);
    try { localStorage.setItem(RAIL_KEY, railChosen ? "0" : "1"); } catch { /* remembered for this visit only */ }
  }

  return (
    <div className={`app-shell ${rail ? "is-rail" : ""}`}>
      <a className="skip-link" href="#main">Skip to the page</a>
      {phone && drawerOpen && <div className="scrim" onClick={() => setDrawerOpen(false)} aria-hidden="true" />}
      <aside ref={sidebar} className={`sidebar ${drawerOpen ? "open" : ""}`} aria-label="Menu">
        <div className="sidebar-inner">
          <div className="brand">
            {rail ? <BrandMark /> : <Wordmark />}
            <button type="button" className="icon-btn drawer-close" onClick={() => setDrawerOpen(false)} aria-label="Close the menu"><X size={18} aria-hidden="true" /></button>
          </div>
          <nav aria-label="Main menu">
            {rail ? <RailMenu menu={menu} /> : menu.map((entry) => (entry.group ? <Group key={entry.group} {...entry} /> : <NavItem key={entry.to} {...entry} />))}
          </nav>
          {!phone && !tablet && (
            <div className="sidebar-foot">
              <button type="button" className="nav-link" onClick={toggleRail} aria-label={rail ? "Expand the menu" : "Collapse the menu"} data-tip="Expand the menu">
                {rail ? <ChevronsRight size={18} aria-hidden="true" /> : <ChevronsLeft size={18} aria-hidden="true" />}
                <span className="nav-label">Collapse the menu</span>
              </button>
            </div>
          )}
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <button type="button" className="icon-btn menu-button" onClick={() => setDrawerOpen(true)} aria-label="Open the menu" aria-expanded={drawerOpen}>
            <Menu size={20} aria-hidden="true" />
          </button>
          <nav className="crumbs" aria-label="Breadcrumb">
            <ol>
              {crumbs.map((c, i) => (
                <li key={`${c.label}-${i}`} aria-current={i === crumbs.length - 1 ? "page" : undefined}>
                  {i > 0 && <ChevronRight size={14} aria-hidden="true" />}
                  {c.to && i < crumbs.length - 1 ? <Link to={c.to}>{c.label}</Link> : <span>{c.label}</span>}
                </li>
              ))}
            </ol>
          </nav>
          <div className="topbar-actions">
            <ThemeToggle />
            <NotificationBell />
            <ProfileMenu user={user} logout={logout} />
          </div>
        </header>
        <main id="main" className="content" tabIndex={-1}>
          <div className="content-inner"><ErrorBoundary resetKey={pathname}>
            {/* A page opened for the first time loads its code here, inside the frame, with a placeholder */}
            <Suspense fallback={<PageLoading />}><Outlet /></Suspense>
          </ErrorBoundary></div>
        </main>
      </div>
    </div>
  );
}
