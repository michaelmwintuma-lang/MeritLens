// Nomination status and decision, always in words. A rejection is a decision about a person, not a system error, so
// it is shown neutrally rather than in red.

export function NominationStatus({ status }) {
  if (status === "approved") return <span className="tag tag-yes">Approved</span>;
  if (status === "rejected") return <span className="tag">Not approved</span>;
  if (status === "finalising") return <span className="tag tag-info">Being finalised</span>;  // a manager's view, until Finance signs off
  return <span className="tag">Waiting for HR</span>;
}

export function AgreesWithModel({ agrees }) {
  return agrees
    ? <span className="small">Same as the model</span>
    : <span className="small strong">Differs from the model</span>;
}
