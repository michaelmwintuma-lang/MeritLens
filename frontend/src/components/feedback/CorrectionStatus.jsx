// A correction request's status as a labelled tag: the word is always shown, colour only supports it.
import { CheckCircle2, Clock, XCircle } from "lucide-react";

const LOOKS = {
  pending: { label: "Waiting for HR", icon: Clock, className: "tag tag-warn" },
  confirmed: { label: "Corrected", icon: CheckCircle2, className: "tag tag-yes" },
  rejected: { label: "Not changed", icon: XCircle, className: "tag" },
};

export default function CorrectionStatus({ request }) {
  const look = LOOKS[request.status];
  const Icon = look.icon;
  return <span className={look.className}><Icon size={13} aria-hidden="true" style={{ verticalAlign: "-2px" }} /> {look.label}</span>;
}
