// Nomination status and decision, always in words.

export function NominationStatus({ status }) {
  if (status === "approved") return <span className="tag tag-yes">Approved</span>;
  if (status === "rejected") return <span className="tag tag-off">Rejected</span>;
  return <span className="tag">Waiting for HR</span>;
}

export function AgreesWithModel({ agrees }) {
  return agrees
    ? <span className="small">Same as the model</span>
    : <span className="small strong">Differs from the model</span>;
}
