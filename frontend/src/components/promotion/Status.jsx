// Nomination status and decision, always in words with an icon. A rejection is a decision about a person, not a
// system error, so it is shown neutrally rather than in red.
import { CheckCircle2, CircleDashed, Clock, GitCompareArrows, Hourglass, MinusCircle } from "lucide-react";
import { Badge } from "../ui";

export function NominationStatus({ status }) {
  if (status === "approved") return <Badge tone="success" icon={CheckCircle2}>Approved</Badge>;
  if (status === "rejected") return <Badge icon={MinusCircle}>Not approved</Badge>;
  if (status === "finalising") return <Badge tone="info" icon={Hourglass}>Being finalised</Badge>;  // a manager's view, until Finance signs off
  return <Badge icon={Clock}>Waiting for HR</Badge>;
}

export function AgreesWithModel({ agrees }) {
  return agrees
    ? <span className="row"><CircleDashed size={16} aria-hidden="true" className="muted" />Same as the model</span>
    : <span className="row strong"><GitCompareArrows size={16} aria-hidden="true" />Differs from the model</span>;
}
