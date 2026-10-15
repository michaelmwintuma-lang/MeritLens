// A manager's recommendation as HR (and the manager) see it: new role, start date, pay rise, the four ratings with
// examples, and the reasons. Older nominations made before the structured form show only their reason.
const RATING_WORDS = ["", "Below expectations", "Partly meets", "Meets", "Exceeds", "Outstanding"];

/** Five dots plus the rating in words, so it never depends on colour alone. */
function Rating({ value }) {
  return (
    <span className="rating" role="img" aria-label={`${value} out of 5: ${RATING_WORDS[value]}`}>
      <span className="rating-dots" aria-hidden="true">{[1, 2, 3, 4, 5].map((i) => <span key={i} className={i <= value ? "on" : ""} />)}</span>
      <span className="strong num" aria-hidden="true">{value}/5 · {RATING_WORDS[value]}</span>
    </span>
  );
}

export default function Recommendation({ nomination }) {
  const rec = nomination.recommendation || {};
  if (!rec.proposed_title) return <blockquote className="quote">{nomination.reason}</blockquote>;
  return (
    <>
      <dl className="rec-facts">
        <div><dt>Proposed role</dt><dd>{rec.proposed_title}</dd></div>
        <div><dt>Start date</dt><dd>{rec.proposed_start}</dd></div>
        <div><dt>Proposed pay rise</dt><dd>{rec.proposed_raise}%</dd></div>
      </dl>
      <h3 className="form-subhead">Ratings, with an example for each</h3>
      <ul className="criteria-list">
        {rec.criteria.map((c) => (
          <li key={c.key}>
            <span className="strong">{c.label}</span>
            <Rating value={c.rating} />
            <span className="example">{c.example}</span>
          </li>
        ))}
      </ul>
      <h3 className="form-subhead">Overall</h3>
      <blockquote className="quote">{rec.reason}</blockquote>
      {rec.model_disagreement && (
        <>
          <h3 className="form-subhead">Why the manager disagrees with the model</h3>
          <blockquote className="quote">{rec.model_disagreement}</blockquote>
        </>
      )}
    </>
  );
}
