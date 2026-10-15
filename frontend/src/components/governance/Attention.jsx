// "Needs your attention": the first thing on each role's overview. Each row is one thing waiting for this person,
// in words, with one link that goes straight to it. When nothing is waiting, it says so, so the page never looks
// broken or empty.
import { Link } from "react-router-dom";
import { ArrowRight, BellRing, CheckCircle2 } from "lucide-react";

/** items: [{ key, text, detail?, to, action, tone? ("warn" | "info") }]; empty rows are left out. */
export default function Attention({ items }) {
  const rows = items.filter(Boolean);
  return (
    <section className="card attention" aria-labelledby="attention-title">
      <div className="card-head">
        <div className="row">
          <span className={`attention-icon ${rows.length ? "" : "clear"}`}>
            {rows.length ? <BellRing size={18} aria-hidden="true" /> : <CheckCircle2 size={18} aria-hidden="true" />}
          </span>
          <h2 id="attention-title">{rows.length ? "Needs your attention" : "Nothing needs your attention right now"}</h2>
        </div>
      </div>
      {rows.length > 0 && (
        <ul className="attention-list">
          {rows.map((r) => (
            <li key={r.key} className={r.tone ? `tone-${r.tone}` : ""}>
              <div>
                <div className="strong">{r.text}</div>
                {r.detail && <div className="muted small">{r.detail}</div>}
              </div>
              <Link className="btn btn-plain" to={r.to}>{r.action} <ArrowRight size={16} aria-hidden="true" /></Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export const plural = (n, word, many = `${word}s`) => `${n} ${n === 1 ? word : many}`;
