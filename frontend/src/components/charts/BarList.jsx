// The charts used across the app, in one style: thin rounded bars on a light track, every value written out beside
// its mark (so nothing depends on colour, hovering or seeing the bar), a legend for anything with two or more parts,
// and the palette from tokens.css. Values the server withholds (e.g. "<3") show as text with no bar.

/** A sorted list of horizontal bars: one row per item with its name, a bar and its value. `axis` labels the scale. */
export default function BarList({ rows, max, format = (v) => v, label, axis }) {
  const top = max ?? Math.max(...rows.map((r) => (typeof r.value === "number" ? r.value : 0)), 0);
  return (
    <>
      <ul className="bar-list" aria-label={label}>
        {rows.map((r) => {
          const numeric = typeof r.value === "number";
          return (
            <li key={r.key}>
              <span className="bar-name">{r.name}</span>
              <span className="bar-track" aria-hidden="true" title={`${r.name}: ${numeric ? format(r.value) : r.value ?? "–"}${r.detail ? ` ${r.detail}` : ""}`}>
                {numeric && top > 0 && <span className="bar-fill" style={{ width: `${Math.max((r.value / top) * 100, r.value ? 2 : 0)}%` }} />}
              </span>
              <span className="bar-value">{numeric ? format(r.value) : r.value ?? "–"}{r.detail && <span className="muted"> {r.detail}</span>}</span>
            </li>
          );
        })}
      </ul>
      {axis && <p className="bar-axis" aria-hidden="true"><span>{axis[0]}</span><span>{axis[1]}</span></p>}
    </>
  );
}

/** One share from 0 to 100%, with its label and value written out. A withheld value (null) shows `withheld`. */
export function Meter({ label, value, format, note, withheld }) {
  return (
    <div className="meter">
      <div className="meter-head"><span className="strong">{label}</span><span className="bar-value">{value == null ? "–" : format(value)}</span></div>
      <div className="bar-track" aria-hidden="true">{value != null && <span className="bar-fill" style={{ width: `${Math.max(value * 100, 1)}%` }} />}</div>
      <p className="chart-note">{value == null ? withheld : note}</p>
    </div>
  );
}

/**
 * One bar split into parts (e.g. confirmed, rejected, waiting), each in a fixed chart colour, with a legend that
 * names every part and gives its number. If any part is withheld ("<3"), only the legend is shown: a bar can't be
 * drawn to scale without the number.
 */
export function StackedBar({ parts, label }) {
  const numeric = parts.every((p) => typeof p.value === "number");
  const total = numeric ? parts.reduce((sum, p) => sum + p.value, 0) : 0;
  return (
    <figure className="stacked-chart" aria-label={label}>
      {numeric && total > 0 && (
        <div className="stacked" aria-hidden="true">
          {parts.filter((p) => p.value > 0).map((p) => (
            <span key={p.key} className={`chart-${p.slot}`} style={{ flexGrow: p.value }} title={`${p.label}: ${p.value}`} />
          ))}
        </div>
      )}
      <ul className="legend">
        {parts.map((p) => (
          <li key={p.key}><span className={`swatch chart-${p.slot}`} aria-hidden="true" />{p.label} <strong className="num">{p.value}</strong></li>
        ))}
      </ul>
    </figure>
  );
}
