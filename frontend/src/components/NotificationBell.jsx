// The bell at the top right. HR is told about new reports and replies, record corrections waiting, and pay rises
// Finance sent back; Finance about pay rises waiting for sign-off; employees about HR's decisions on their record.
//
// Reporters get no notifications: that would need the website to know which cases are theirs. They open a case
// with its ID and key when they want to check it.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";

const CHECK_EVERY_MS = 60_000;

async function hrItems() {
  const [items, decisions, waiting] = await Promise.all([api("/hr/reports/notifications"),
    api("/promotion/decisions?pay_status=returned"), // only those Finance sent back, not the whole log
    api("/hr/feedback/corrections?status_filter=pending")]);
  const corrections = waiting.length ? [{ id: "corrections", text: `${waiting.length} record correction${waiting.length === 1 ? "" : "s"} waiting`,
    detail: "Check the evidence and decide", to: "/corrections" }] : [];
  const sentBack = decisions.map((d) => ({
    id: `pay-${d.id}`, text: "Finance sent a pay rise back", detail: d.employee.full_name, to: `/nominations/${d.nomination_id}` }));
  return [...corrections, ...sentBack, ...items.map((i) => ({ id: `${i.case_id}-${i.kind}`, text: i.text, detail: `Case ${i.case_id}`, to: `/reports/${i.case_id}` }))];
}

async function employeeItems() {
  const decided = await api("/feedback/notifications");
  return decided.map((d) => ({ id: `correction-${d.id}`, to: "/my-readiness",
    text: d.status === "confirmed" ? "HR corrected your record" : "HR decided on your correction request",
    detail: d.label }));
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
  const role = ["hr", "finance", "employee"].includes(user.role) ? user.role : null;

  useEffect(() => {
    if (!role) return undefined;
    const load = () => ({ hr: hrItems, finance: financeItems, employee: employeeItems }[role])().then(setItems).catch(() => {});
    load();
    const timer = setInterval(load, CHECK_EVERY_MS);
    return () => clearInterval(timer);
  }, [role]);

  // Close the list when clicking anywhere else
  useEffect(() => {
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
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
        <Bell size={17} />
        {items.length > 0 && <span className="bell-count">{items.length}</span>}
      </button>
      {open && (
        <div className="bell-panel" role="menu">
          <div className="bell-head">Notifications</div>
          {items.length === 0 ? (
            <p className="muted small bell-empty">You're all caught up.</p>
          ) : items.map((item) => (
            <button key={item.id} type="button" role="menuitem" className="bell-item" onClick={() => go(item)}>
              <strong>{item.text}</strong><span className="muted small">{item.detail}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
