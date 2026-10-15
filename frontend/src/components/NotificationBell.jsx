// The bell in the top bar. HR is told about record corrections waiting and pay rises Finance sent back; Finance
// about pay rises waiting for sign-off; employees about HR's decisions on their record; managers, during a review
// cycle, about team members the model recommends who aren't nominated yet.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";

const CHECK_EVERY_MS = 60_000;

async function hrItems() {
  const [decisions, waiting] = await Promise.all([
    api("/promotion/decisions?pay_status=returned"), // only those Finance sent back, not the whole log
    api("/hr/feedback/corrections?status_filter=pending")]);
  const corrections = waiting.length ? [{ id: "corrections", text: `${waiting.length} record correction${waiting.length === 1 ? "" : "s"} waiting`,
    detail: "Check the evidence and decide", to: "/corrections" }] : [];
  const sentBack = decisions.map((d) => ({
    id: `pay-${d.id}`, text: "Finance sent a pay rise back", detail: d.employee.full_name, to: `/nominations/${d.nomination_id}` }));
  return [...corrections, ...sentBack];
}

async function employeeItems() {
  const decided = await api("/feedback/notifications");
  return decided.map((d) => ({ id: `correction-${d.id}`, to: "/my-readiness",
    text: d.status === "confirmed" ? "HR corrected your record" : "HR decided on your correction request",
    detail: d.label }));
}

async function managerItems() {
  // During a review cycle, before its deadline: team members the model recommends who aren't nominated yet
  const [team, nominations] = await Promise.all([api("/promotion/employees"), api("/promotion/nominations")]);
  const { cycle } = team;
  if (!cycle?.nominations_open) return [];
  const nominated = new Set(nominations.filter((n) => n.cycle_id === cycle.id).map((n) => n.employee.id));
  const open = team.employees.filter((e) => e.recommended && !nominated.has(e.id)).length;
  return open ? [{ id: `cycle-${cycle.id}`, to: "/team",
    text: `${open} team member${open === 1 ? "" : "s"} the model recommends, not nominated yet`,
    detail: `${cycle.name}${cycle.nominations_close ? `: nominations close on ${cycle.nominations_close}` : ""}` }] : [];
}

async function financeItems() {
  const { reviews } = await api("/finance/pay-reviews");
  return reviews.filter((r) => r.status === "awaiting_finance").map((r) => ({
    id: `pay-${r.id}`, text: `Pay rise to sign off: ${r.raise}%`, detail: `${r.employee.full_name} · ${r.new_title || "promotion"}`, to: "/finance" }));
}

export default function NotificationBell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const role = ["hr", "finance", "employee", "manager"].includes(user.role) ? user.role : null;

  useEffect(() => {
    if (!role) return undefined;
    const load = () => ({ hr: hrItems, finance: financeItems, employee: employeeItems, manager: managerItems }[role])().then(setItems).catch(() => {});
    load();
    const timer = setInterval(load, CHECK_EVERY_MS);
    return () => clearInterval(timer);
  }, [role]);

  // Close the list when clicking anywhere else, or with Escape
  useEffect(() => {
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    const escape = (e) => { if (e.key === "Escape" && box.current?.contains(document.activeElement)) { setOpen(false); box.current.querySelector("button").focus(); } };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", escape); };
  }, []);

  if (!role) return null;

  function go(item) {
    setOpen(false);
    navigate(item.to);
  }

  return (
    <div className="bell" ref={box}>
      <button type="button" className="icon-btn" onClick={() => setOpen(!open)} aria-expanded={open}
        aria-label={`Notifications: ${items.length} new`} title="Notifications">
        <Bell size={18} aria-hidden="true" />
        {items.length > 0 && <span className="bell-count" aria-hidden="true">{items.length}</span>}
      </button>
      {open && (
        <div className="bell-panel" role="menu">
          <div className="bell-head">Notifications</div>
          {items.length === 0 ? (
            <p className="muted small bell-empty">You're all caught up.</p>
          ) : items.map((item) => (
            <button key={item.id} type="button" role="menuitem" className="bell-item" onClick={() => go(item)}>
              <strong>{item.text}</strong><span className="muted">{item.detail}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
