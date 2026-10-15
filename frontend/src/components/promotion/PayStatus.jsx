// A promotion pay rise's sign-off by Finance: its status in words, and every step so far (for HR and Finance).
import { CheckCircle2, CornerUpLeft, Hourglass, Send, RefreshCw } from "lucide-react";
import { Badge } from "../ui";

const STATUS = {
  awaiting_finance: ["info", Hourglass, "With Finance"],
  returned: ["warning", CornerUpLeft, "Sent back by Finance"],
  signed_off: ["success", CheckCircle2, "Pay signed off"],
};

/** "With Finance", "Sent back by Finance" or "Pay signed off", with an icon. Nothing for rejections or older approvals. */
export function PayStatus({ status }) {
  if (!STATUS[status]) return null;
  const [tone, icon, label] = STATUS[status];
  return <Badge tone={tone} icon={icon}>{label}</Badge>;
}

const STEPS = {
  submitted: [Send, "Sent to Finance by"],
  returned: [CornerUpLeft, "Sent back to HR by"],
  resubmitted: [RefreshCw, "Revised and resubmitted by"],
  signed_off: [CheckCircle2, "Signed off by"],
};

/** Every step of the sign-off, oldest first, with the pay rise at that step and any note. */
export function PayTimeline({ history }) {
  if (!history?.length) return null;
  return (
    <ol className="pay-timeline">
      {history.map((step, i) => {
        const [Icon, words] = STEPS[step.action] || [Send, step.action];
        return (
          <li key={i} className={`pay-step ${step.action}`}>
            <span className="pay-step-icon"><Icon size={15} aria-hidden="true" /></span>
            <div>
              <div><span className="strong">{words} {step.by}</span>
                <span className="muted"> · {step.at.slice(0, 10)}{step.raise != null ? ` · ${step.raise}%` : ""}</span></div>
              {step.note && <p className="pay-step-note">{step.note}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
