// Small building blocks used by every page, so all pages look and behave the same. Styles: styles.css.
import { ArrowDown, ArrowUp, ArrowUpDown, CheckCircle2, CircleAlert, Inbox, Info, Loader2, Moon, RotateCcw, Sun, TriangleAlert } from "lucide-react";
import { useTheme } from "../theme";
import { BRAND, MONOGRAM } from "../brand";

/** The product's small square mark. */
export function BrandMark({ small = false }) {
  return <span className={`brand-logo ${small ? "small" : ""}`} aria-hidden="true">{MONOGRAM}</span>;
}

/** The mark and the name together. */
export function Wordmark({ small = false }) {
  return <span className="wordmark"><BrandMark small={small} /><span className="brand-name">{BRAND}</span></span>;
}

/** Page title, a one-line description, and the page's main action on the right. `status` sits beside the title. */
export function PageHeader({ title, subtitle, actions, status }) {
  return (
    <header className="page-header">
      <div>
        <div className="page-title"><h1>{title}</h1>{status}</div>
        {subtitle && <p className="page-sub">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

/** A number with a small uppercase label and a note, like "WAITING FOR YOU 3 / Pay rises to sign off". */
export function StatCard({ label, value, note }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  );
}

/**
 * A white panel with an optional title, explanation and buttons. `flush` lets a table reach the edges; `tone`
 * "highlight" or "warn" makes it stand out (the plain-language summary, the committee note).
 */
export function Card({ title, subtitle, actions, flush = false, tone, icon: Icon, className = "", id, children }) {
  const titleId = title && id ? `${id}-title` : undefined;
  return (
    <section id={id} aria-labelledby={titleId}
      className={`card ${flush ? "flush" : ""} ${tone ? "highlight" : ""} ${tone === "warn" ? "warn" : ""} ${className}`}>
      {(title || actions) && (
        <div className="card-head">
          <div>
            {title && <h2 id={titleId}>{Icon && <Icon size={20} aria-hidden="true" />}{title}</h2>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

/**
 * Tabs: a row of buttons where exactly one is chosen (Waiting | Decided | All). Toggle buttons (aria-pressed) rather
 * than ARIA tabs: tabs promise arrow-key movement, and these are moved through with Tab like any button.
 */
export function Segmented({ options, value, onChange, label }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value}
          className={value === o.value ? "on" : ""} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** A helpful message when a list is empty: what will appear here, and optionally what to do. */
export function EmptyState({ icon: Icon = Inbox, title, text, action, compact = false }) {
  return (
    <div className={`empty ${compact ? "compact" : ""}`}>
      <div className="empty-icon"><Icon size={22} aria-hidden="true" /></div>
      <div className="empty-title">{title}</div>
      {text && <p>{text}</p>}
      {action}
    </div>
  );
}

/** Switch between light and dark. */
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const label = `Switch to ${theme === "dark" ? "light" : "dark"} mode`;
  return (
    <button type="button" className="icon-btn" onClick={toggle} aria-label={label} title={label}>
      {theme === "dark" ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
    </button>
  );
}

/**
 * A button that shows when the system is working: while `busy`, it spins, shows `busyText` and can't be clicked
 * again. `look`: "primary" (the one main action), "secondary", "ghost" or "danger".
 */
export function Button({ busy = false, busyText, icon: Icon, look = "primary", size, children, disabled, className = "", ...rest }) {
  const variant = look === "plain" ? "secondary" : look;
  return (
    <button {...rest} className={`btn btn-${variant} ${size ? `btn-${size}` : ""} ${busy ? "is-busy" : ""} ${className}`}
      disabled={busy || disabled} aria-busy={busy}>
      {busy ? <Loader2 size={16} className="spin" aria-hidden="true" /> : Icon && <Icon size={16} aria-hidden="true" />}
      {busy && busyText ? busyText : children}
    </button>
  );
}

/** Status in words, as a small pill. tone: neutral, success, warning, danger, info, up (the model's view). */
const BADGE_TONES = { success: "tag-yes", warning: "tag-warn", danger: "tag-off", info: "tag-info", up: "tag-up", neutral: "" };
export function Badge({ tone = "neutral", icon: Icon, className = "", children }) {
  return <span className={`tag ${BADGE_TONES[tone]} ${className}`}>{Icon && <Icon size={14} aria-hidden="true" />}{children}</span>;
}

/** A message in the page: info, success, warning or error, always with an icon and words. */
const CALLOUT_ICONS = { info: Info, success: CheckCircle2, warning: TriangleAlert, error: CircleAlert };
export function Callout({ tone = "info", icon, title, children, role, className = "" }) {
  const Icon = icon || CALLOUT_ICONS[tone];
  return (
    <div className={`alert alert-${tone} ${className}`} role={role || (tone === "error" ? "alert" : undefined)}>
      <Icon size={18} aria-hidden="true" />
      <div className="alert-body">
        {title && <strong>{title}</strong>}
        {children && <div>{children}</div>}
      </div>
    </div>
  );
}

/** Placeholder lines while part of a page loads. Screen readers hear the label once, politely. */
export function Loading({ label = "Loading…", lines = 3 }) {
  return (
    <div className="skeleton" role="status" aria-live="polite" aria-busy="true">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: lines }, (_, i) => <span key={i} className="skeleton-line" aria-hidden="true" />)}
    </div>
  );
}

/** A whole page loading: a title, a row of tiles and a panel. */
export function PageLoading({ label = "Loading…" }) {
  return (
    <div className="skeleton-page" role="status" aria-live="polite" aria-busy="true">
      <span className="visually-hidden">{label}</span>
      <span className="skeleton-line title" aria-hidden="true" />
      <div className="skeleton-tiles" aria-hidden="true">{[0, 1, 2].map((i) => <span key={i} className="skeleton-tile" />)}</div>
      <div className="card" aria-hidden="true"><div className="skeleton">{[0, 1, 2, 3].map((i) => <span key={i} className="skeleton-line" />)}</div></div>
    </div>
  );
}

/** Something couldn't be loaded: what went wrong in plain words, and a button to try again (else reload the page). */
export function LoadError({ message, onRetry }) {
  return (
    <div className="alert alert-error load-error" role="alert">
      <CircleAlert size={18} aria-hidden="true" />
      <div className="alert-body">
        <strong>This couldn't be loaded.</strong>
        <span>{message}</span>
      </div>
      <button type="button" className="btn btn-secondary" onClick={onRetry || (() => window.location.reload())}>
        <RotateCcw size={16} aria-hidden="true" />Try again
      </button>
    </div>
  );
}

/** A table heading that sorts by its column. sort: { by, dir: "asc" | "desc" }. Numbers sort biggest first. */
export function SortHeader({ label, by, sort, onSort, numeric = false }) {
  const active = sort.by === by;
  const Icon = !active ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;
  const first = numeric ? "desc" : "asc";
  const next = active && sort.dir === first ? (first === "asc" ? "desc" : "asc") : first;
  return (
    <th className={numeric ? "num" : ""} aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className="sort" onClick={() => onSort({ by, dir: next })}>
        {label}<Icon size={14} aria-hidden="true" />
      </button>
    </th>
  );
}

/** Sort rows by sort.by: numbers as numbers, everything else alphabetically. Rows without a value go last. */
export function sortRows(rows, sort, value = (row, by) => row[by]) {
  const factor = sort.dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const [x, y] = [value(a, sort.by), value(b, sort.by)];
    if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1;
    return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * factor;
  });
}

/** "Previous · 1–50 of 120 · Next" under a long list. Nothing when everything fits on one page. */
export function Pager({ page, size, total, onPage, label, previous = "Previous", next = "Next" }) {
  if (total <= size) return null;
  const pages = Math.ceil(total / size);
  return (
    <nav className="pager" aria-label={label}>
      <button type="button" className="btn btn-secondary btn-sm" onClick={() => onPage(page - 1)} disabled={page === 0}>{previous}</button>
      <span className="muted" aria-live="polite">{page * size + 1}–{Math.min((page + 1) * size, total)} of {total}</span>
      <button type="button" className="btn btn-secondary btn-sm" onClick={() => onPage(page + 1)} disabled={page >= pages - 1}>{next}</button>
    </nav>
  );
}
