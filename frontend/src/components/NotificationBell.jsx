// The bell in the top bar, for everyone. Two parts:
// - "Waiting for you": what needs doing right now, worked out live. HR: record corrections waiting and pay rises
//   Finance sent back; Finance: pay rises to sign off; managers, during a review cycle: team members the model
//   recommends who aren't nominated yet.
// - "Recent": the notification centre's history (things that happened, the same events as the emails), read or
//   unread. Opening one marks it read; "Mark all read" clears the rest.
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

async function managerItems() {
  // During a review cycle, before its deadline: team members the model recommends who aren't nominated yet
  const [team, nominations] = await Promise.all([api("/promotion/employees"), api("/promotion/nominations")]);
  const { cycle } = team;
  if (!cycle?.nominations_open) return [];
  const nominated = new Set(nominations.filter((n) => n.cycle_id === cycle.id).map((n) => n.employee.id));
  const open = team.employees.filter((e) => e.recommended && e.relation !== "branch" && !nominated.has(e.id)).length;
  return open ? [{ id: `cycle-${cycle.id}`, to: "/team",
    text: `${open} team member${open === 1 ? "" : "s"} the model recommends, not nominated yet`,
    detail: `${cycle.name}${cycle.nominations_close ? `: nominations close on ${cycle.nominations_close}` : ""}` }] : [];
}

async function financeItems() {
  const { reviews } = await api("/finance/pay-reviews");
  return reviews.filter((r) => r.status === "awaiting_finance").map((r) => ({
    id: `pay-${r.id}`, text: `Pay rise to sign off: ${r.raise}%`, detail: `${r.employee.full_name} · ${r.new_title || "promotion"}`, to: "/finance" }));
}

const WAITING = { hr: hrItems, finance: financeItems, manager: managerItems };
const when = (iso) => new Date(`${iso}Z`).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default function NotificationBell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [waiting, setWaiting] = useState([]);
  const [recent, setRecent] = useState({ unread: 0, items: [] });
  const [open, setOpen] = useState(false);
  const box = useRef(null);

  useEffect(() => {
    const load = () => {
      WAITING[user.role]?.().then(setWaiting).catch(() => {});
      api("/notifications").then(setRecent).catch(() => {});
    };
    load();
    const timer = setInterval(load, CHECK_EVERY_MS);
    return () => clearInterval(timer);
  }, [user.role]);

  // Close the list when clicking anywhere else, or with Escape
  useEffect(() => {
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    const escape = (e) => { if (e.key === "Escape" && box.current?.contains(document.activeElement)) { setOpen(false); box.current.querySelector("button").focus(); } };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", escape); };
  }, []);

  async function markRead(ids) {
    await api("/notifications/read", { method: "POST", body: { ids } }).catch(() => {});
    setRecent((r) => ({ unread: ids ? Math.max(0, r.unread - ids.length) : 0,
      items: r.items.map((n) => (!ids || ids.includes(n.id) ? { ...n, read: true } : n)) }));
  }

  function go(to, notification) {
    setOpen(false);
    if (notification && !notification.read) markRead([notification.id]);
    if (to) navigate(to);
  }

  const count = waiting.length + recent.unread;
  return (
    <div className="bell" ref={box}>
      <button type="button" className="icon-btn" onClick={() => setOpen(!open)} aria-expanded={open}
        aria-label={`Notifications: ${count} new`} title="Notifications">
        <Bell size={18} aria-hidden="true" />
        {count > 0 && <span className="bell-count" aria-hidden="true">{count > 99 ? "99+" : count}</span>}
      </button>
      {open && (
        <div className="bell-panel" role="menu">
          <div className="bell-head row spread">
            <span>Notifications</span>
            {recent.unread > 0 && <button type="button" className="btn btn-ghost btn-sm" onClick={() => markRead(null)}>Mark all read</button>}
          </div>
          {waiting.length === 0 && recent.items.length === 0 && <p className="muted bell-empty">You're all caught up.</p>}
          {waiting.length > 0 && <div className="bell-section label">Waiting for you</div>}
          {waiting.map((item) => (
            <button key={item.id} type="button" role="menuitem" className="bell-item" onClick={() => go(item.to)}>
              <strong>{item.text}</strong><span className="muted">{item.detail}</span>
            </button>
          ))}
          {recent.items.length > 0 && <div className="bell-section label">Recent</div>}
          <div className="bell-recent">
            {recent.items.map((n) => (
              <button key={n.id} type="button" role="menuitem" className={`bell-item ${n.read ? "" : "unread"}`} onClick={() => go(n.link, n)}>
                <span className={n.read ? "" : "strong"}>{!n.read && <span className="unread-dot" aria-hidden="true" />}{n.text}
                  {!n.read && <span className="visually-hidden"> (unread)</span>}</span>
                <span className="muted">{when(n.at)}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
