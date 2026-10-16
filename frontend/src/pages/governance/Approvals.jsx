// HR: the four-eyes rule (FOUR_EYES=1). A model release, or a record correction that moves someone across the
// threshold, waits here for a second HR person, who approves it (it is carried out then) or declines it with a
// reason. Nobody approves their own request. With the rule off, the page says so and stays empty.
import { useState } from "react";
import { CheckCircle2, Stamp, XCircle } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { useAction } from "../../useAction";
import { useLoad } from "../../useLoad";
import { Badge, Button, Callout, Card, EmptyState, LoadError, PageHeader, PageLoading, Segmented } from "../../components/ui";
import { useToast } from "../../components/Toast";

const STATUS = { pending: ["warning", "Waiting"], approved: ["success", "Approved"], declined: ["neutral", "Declined"] };
const when = (iso) => (iso ? iso.replace("T", " ").slice(0, 16) : "");

function Decide({ item, onDone }) {
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [approving, withApproving] = useAction();
  const [declining, withDeclining] = useAction();
  const toast = useToast();

  const decide = (path, message) => async () => {
    setError("");
    try {
      await api(`/approvals/${item.id}/${path}`, { method: "POST", body: { note: note.trim() || null } });
      toast(message);
      onDone();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="section-gap">
      {error && <Callout tone="error">{error}</Callout>}
      <label className="field">Your note (required to decline; the person who asked receives it)
        <textarea rows={2} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="form-actions">
        <Button icon={CheckCircle2} busy={approving} busyText="Approving…" onClick={() => withApproving(decide("approve", "Approved and carried out."))}>Approve and carry out</Button>
        <Button look="secondary" icon={XCircle} busy={declining} busyText="Declining…" disabled={!note.trim()}
          onClick={() => withDeclining(decide("decline", "Declined. Nothing was changed."))}>Decline</Button>
      </div>
    </div>
  );
}

export default function Approvals() {
  const { user } = useAuth();
  const [show, setShow] = useState("pending");
  const { data, error, reload } = useLoad(() => api(`/approvals?status_filter=${show === "all" ? "" : show}`), [show]);
  const header = <PageHeader title="Approvals" subtitle="Actions that need a second HR person: a model release, and a record correction that moves someone across the threshold." />;
  if (error) return <>{header}<LoadError message={error} onRetry={reload} /></>;
  if (!data) return <>{header}<PageLoading /></>;

  return (
    <>
      {header}
      {!data.four_eyes && (
        <Callout title="The four-eyes rule is off">
          HR's actions happen at once. To make a second HR person approve the riskiest ones, set FOUR_EYES=1 on the
          server; it needs at least two HR accounts.
        </Callout>
      )}
      <Segmented label="Show" value={show} onChange={setShow}
        options={[{ value: "pending", label: "Waiting" }, { value: "all", label: "All" }]} />
      {data.items.length === 0 ? (
        <EmptyState icon={Stamp} title={show === "pending" ? "Nothing waiting" : "No requests yet"}
          text="When an HR person releases a model or confirms a threshold-crossing correction, it waits here." />
      ) : data.items.map((item) => {
        const [tone, text] = STATUS[item.status];
        const mine = item.requested_by_id === user.id;
        return (
          <Card key={item.id} title={item.kind_label} actions={<Badge tone={tone}>{text}</Badge>}
            subtitle={`Asked by ${item.requested_by}, ${when(item.requested_at)}`}>
            <p>{item.summary}</p>
            {item.status !== "pending" && (
              <p className="muted">{text} by {item.decided_by}, {when(item.decided_at)}{item.decision_note ? `: “${item.decision_note}”` : "."}</p>
            )}
            {item.status === "pending" && (mine
              ? <p className="muted">You asked for this, so another HR person must decide.</p>
              : <Decide item={item} onDone={reload} />)}
          </Card>
        );
      })}
    </>
  );
}
