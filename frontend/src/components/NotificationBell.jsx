// The bell at the top right. HR is told about new reports and replies; reporters about replies on their cases.
//
// Reporters' notifications are worked out in their own browser: it checks only the cases saved on this device
// (My report keys) and compares them with what the reporter has already seen. The server never stores which
// account follows which case, so these notifications can't link a report to anyone.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { savedKeys, seenCases } from "../keyStore";
import { REPORTER_ROLES } from "../roles";

const CHECK_EVERY_MS = 60_000;

async function hrItems() {
  const items = await api("/hr/reports/notifications");
  return items.map((i) => ({ id: `${i.case_id}-${i.kind}`, text: i.text, detail: `Case ${i.case_id}`, to: `/reports/${i.case_id}` }));
}

async function reporterItems() {
  const keys = savedKeys();
  if (!keys.length) return [];
  const updates = await api("/reports/updates", { method: "POST", body: { cases: keys.map(({ case_id, key }) => ({ case_id, key })) } });
  const seen = seenCases();
  const items = [];
  for (const u of updates) {
    const before = seen[u.case_id] || { messages: 0, status: "open" };
    const key = keys.find((k) => k.case_id === u.case_id).key;
    if (u.investigator_wrote_last && u.messages > before.messages) {
      items.push({ id: `${u.case_id}-reply`, text: "The investigator replied", detail: `Case ${u.case_id}`, open: { case_id: u.case_id, key } });
    } else if (u.status !== before.status && u.status === "closed") {
      items.push({ id: `${u.case_id}-closed`, text: "Your case was closed, with an outcome", detail: `Case ${u.case_id}`, open: { case_id: u.case_id, key } });
    }
  }
  return items;
}

export default function NotificationBell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const role = user.role === "hr" ? "hr" : REPORTER_ROLES.includes(user.role) ? "reporter" : null;

  useEffect(() => {
    if (!role) return undefined;
    const load = () => (role === "hr" ? hrItems() : reporterItems()).then(setItems).catch(() => {});
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
    if (item.to) navigate(item.to);
    else navigate("/my-report", { state: item.open }); // the key travels inside the app, never in the address
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
          {role === "reporter" && <p className="muted small bell-foot">Only cases saved under My report keys on this device are checked.</p>}
        </div>
      )}
    </div>
  );
}
