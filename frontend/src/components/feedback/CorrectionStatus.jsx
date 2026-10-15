// A correction request's status as a labelled tag: the word is always shown, colour only supports it.
import { CheckCircle2, Clock, XCircle } from "lucide-react";

import { Badge } from "../ui";

const LOOKS = {
  pending: { label: "Waiting for HR", icon: Clock, tone: "warning" },
  confirmed: { label: "Corrected", icon: CheckCircle2, tone: "success" },
  rejected: { label: "Not changed", icon: XCircle, tone: "neutral" },
};

export default function CorrectionStatus({ request }) {
  const look = LOOKS[request.status];
  return <Badge tone={look.tone} icon={look.icon}>{look.label}</Badge>;
}
