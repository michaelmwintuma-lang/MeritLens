// A promotion pay rise's sign-off by Finance: its status in words, and every step so far (for HR and Finance).
import { CheckCircle2, CornerUpLeft, Send, RefreshCw } from "lucide-react";

const STATUS = {
  awaiting_finance: ["tag-info", "With Finance"],
  returned: ["tag-warn", "Sent back by Finance"],
  signed_off: ["tag-yes", "Pay signed off"],
};

/** "With Finance", "Sent back by Finance" or "Pay signed off". Nothing for rejections or older approvals. */
export function PayStatus({ status }) {
  if (!STATUS[status]) return null;
  const [cls, label] = STATUS[status];
  return <span className={`tag ${cls}`}>{label}</span>;
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
                <span className="muted small"> · {step.at.slice(0, 10)}{step.raise != null ? ` · ${step.raise}%` : ""}</span></div>
              {step.note && <p className="pay-step-note">{step.note}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
