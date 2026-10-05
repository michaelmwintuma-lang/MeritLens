// Small building blocks used by every page, so all pages look the same.
import { Inbox, Loader2, Moon, Sun } from "lucide-react";
import { useTheme } from "../theme";
import NotificationBell from "./NotificationBell";

/** Big page title with an icon, a one-line explanation, and optional buttons on the right. */
export function PageHeader({ icon: Icon, title, subtitle, actions }) {
  return (
    <header className="page-header">
      <div>
        <div className="page-title">{Icon && <span className="page-icon"><Icon size={24} strokeWidth={2} aria-hidden="true" /></span>}<h1>{title}</h1></div>
        {subtitle && <p className="page-sub">{subtitle}</p>}
      </div>
      <div className="page-actions">
        {actions}
        <NotificationBell />
        <ThemeToggle />
      </div>
    </header>
  );
}

/** A number with a small uppercase label, like "PENDING NOMINATIONS 3". */
export function StatCard({ label, value, note }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  );
}

/** A white rounded panel with an optional title, explanation and buttons. `flush` lets a table reach the edges. */
export function Card({ title, subtitle, actions, flush = false, children }) {
  return (
    <section className={`card ${flush ? "flush" : ""}`}>
      {(title || actions) && (
        <div className="card-head">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

/** A row of buttons where exactly one is chosen (Pending | Decided | All). */
export function Segmented({ options, value, onChange, label }) {
  return (
    <div className="segmented" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" role="tab" aria-selected={value === o.value}
          className={value === o.value ? "on" : ""} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Friendly message when a list is empty. */
export function EmptyState({ icon: Icon = Inbox, title, text }) {
  return (
    <div className="empty">
      <div className="empty-icon"><Icon size={20} aria-hidden="true" /></div>
      <div className="empty-title">{title}</div>
      {text && <p>{text}</p>}
    </div>
  );
}

/** Switch between light and dark. */
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button type="button" className="icon-btn" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} title="Light / dark">
      {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  );
}

/**
 * A button that shows when the system is working: while `busy`, it spins an icon, shows `busyText` and can't be
 * clicked again. `look` is "primary" (dark) or "plain".
 */
export function Button({ busy = false, busyText, icon: Icon, look = "primary", children, disabled, className = "", ...rest }) {
  return (
    <button {...rest} className={`btn btn-${look} ${busy ? "is-busy" : ""} ${className}`} disabled={busy || disabled} aria-busy={busy}>
      {busy ? <Loader2 size={16} className="spin" aria-hidden="true" /> : Icon && <Icon size={16} aria-hidden="true" />}
      {busy && busyText ? busyText : children}
    </button>
  );
}
