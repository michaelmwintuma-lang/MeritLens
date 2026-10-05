// A case's conversation. People appear only as "Reporter" and "Investigator", never by name.
import { MessageSquare } from "lucide-react";
import { EmptyState } from "../ui";

export default function Conversation({ messages, me }) {
  if (!messages.length) {
    return <EmptyState icon={MessageSquare} title="No messages yet" text="Messages between the reporter and the investigator appear here." />;
  }
  return (
    <ol className="thread">
      {messages.map((m) => (
        <li key={m.number} className={`bubble ${m.sender === me ? "mine" : ""}`}>
          <div className="bubble-meta">
            <strong>{m.sender === "investigator" ? "Investigator" : "Reporter"}{m.sender === me ? " (you)" : ""}</strong>
            <span className="muted">{m.sent_on}</span>
          </div>
          <div className="bubble-text">{m.text}</div>
        </li>
      ))}
    </ol>
  );
}

/** Priority as a word with an icon, never colour alone. */
export function PriorityTag({ priority }) {
  const label = { high: "High", medium: "Medium", low: "Low" }[priority] || priority;
  const cls = { high: "tag-off", medium: "tag-warn", low: "" }[priority] || "";
  return <span className={`tag ${cls}`}>{priority === "high" ? "▲▲" : priority === "medium" ? "▲" : "–"} {label}</span>;
}

export function CaseStatus({ status }) {
  const label = { open: "Open", investigating: "Investigating", closed: "Closed" }[status] || status;
  const cls = { open: "tag-info", investigating: "tag-warn", closed: "tag-yes" }[status] || "";
  return <span className={`tag ${cls}`}>{label}</span>;
}
