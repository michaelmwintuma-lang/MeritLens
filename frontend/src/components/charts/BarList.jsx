// A sorted list of horizontal bars: one row per item with its name, a thin bar and its value written out, so the
// chart never relies on colour or hovering. Values that are withheld (e.g. "<3") show as text with no bar.
export default function BarList({ rows, max, format = (v) => v, label }) {
  const top = max ?? Math.max(...rows.map((r) => (typeof r.value === "number" ? r.value : 0)), 0);
  return (
    <ul className="bar-list" aria-label={label}>
      {rows.map((r) => {
        const numeric = typeof r.value === "number";
        return (
          <li key={r.key} title={r.title}>
            <span className="bar-name">{r.name}</span>
            <span className="bar-track" aria-hidden="true">
              {numeric && top > 0 && <span className="bar-fill" style={{ width: `${Math.max((r.value / top) * 100, r.value ? 2 : 0)}%` }} />}
            </span>
            <span className="bar-value">{numeric ? format(r.value) : r.value ?? "–"}{r.detail && <span className="muted small"> {r.detail}</span>}</span>
          </li>
        );
      })}
    </ul>
  );
}
