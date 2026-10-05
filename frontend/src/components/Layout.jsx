// The frame around every signed-in page: brand and menu on the left, the user at the bottom.
// Menu groups open and close when clicked; the group holding the current page opens by itself when you go there.
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { ChevronDown, LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth";
import { ACCOUNT, ROLE_NAMES, menuFor } from "../roles";
import { ThemeToggle } from "./ui";

function Link({ to, label, icon: Icon, nested }) {
  return (
    <NavLink to={to} end={to === "/"} className={`nav-link ${nested ? "nested" : ""}`}>
      <Icon size={nested ? 17 : 19} aria-hidden="true" />{label}
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
        <Icon size={19} aria-hidden="true" />{group}
        <ChevronDown size={16} className={`chevron ${isOpen ? "open" : ""}`} aria-hidden="true" />
      </button>
      {isOpen && <div className="nav-group-items">{items.map((item) => <Link key={item.to} {...item} nested />)}</div>}
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo"><ShieldCheck size={20} aria-hidden="true" /></div>
          <div>
            <div className="brand-name">Promotion &amp; Reporting</div>
            <div className="brand-sub">Staff platform</div>
          </div>
        </div>
        <nav aria-label="Main menu">
          {[...menuFor(user), ACCOUNT].map((entry) =>
            entry.group ? <Group key={entry.group} {...entry} /> : <Link key={entry.to} {...entry} />)}
        </nav>
        <div className="sidebar-user">
          {user.photo ? <img className="avatar" src={user.photo} alt="" /> : <div className="avatar" aria-hidden="true">{user.full_name.charAt(0)}</div>}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="user-name">{user.full_name}</div>
            <span className="role-badge">{ROLE_NAMES[user.role]}</span>
          </div>
          <ThemeToggle />
          <button type="button" className="icon-btn" onClick={logout} aria-label="Sign out" title="Sign out"><LogOut size={17} /></button>
        </div>
      </aside>
      <main className="main"><div className="main-inner"><Outlet /></div></main>
    </div>
  );
}
