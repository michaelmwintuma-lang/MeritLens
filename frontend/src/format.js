// Showing numbers the way people expect them. Mirrors backend/app/promotion/labels.py.

export const percent = (score) => `${Math.round(score * 100)}%`;

/** A value in its everyday unit, for the what-if sliders. */
export function formatValue(unit, value) {
  switch (unit) {
    case "rate": return `${(value * 100).toFixed(1)}%`;
    case "percent": return `${value.toFixed(1)}%`;
    case "of5": return `${value.toFixed(1)} / 5`;
    case "hours": return `${Math.round(value)} hours`;
    case "count": return `${Math.round(value)}`;
    default: return value.toFixed(1);
  }
}

/** Slider step size for each kind of input. */
export function stepFor(unit, whole) {
  if (whole) return 1;
  if (unit === "rate") return 0.005;
  if (unit === "of5") return 0.1;
  return 0.5;
}

/** "Leadership score" -> "leadership score" mid-sentence, but "KPI achievement" keeps its capitals. */
export const midSentence = (text) => (/^[A-Z]{2}/.test(text) ? text : text.charAt(0).toLowerCase() + text.slice(1));
