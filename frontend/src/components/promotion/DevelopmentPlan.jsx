// A development plan: goals the employee works on with their manager, often taken straight from the tips. The
// employee, their manager and HR add goals and tick them off; the other side is told on their bell. Goals are never
// an input to the model: ticking one off changes no score (only the work record does).
import { useState } from "react";
import { ListChecks, Plus, Trash2 } from "lucide-react";
import { api } from "../../api";
import { useLoad } from "../../useLoad";
import { useAction } from "../../useAction";
import { midSentence } from "../../format";
import { Button, Callout, Card, EmptyState, LoadError, Loading } from "../ui";

/** A tip as a goal: "Increase training hours from 20 to 35". */
function fromTip(t) {
  return { title: `${t.to > t.from ? "Increase" : "Reduce"} ${midSentence(t.label)} to ${t.to_display}`, feature: t.feature, target: t.to };
}

export default function DevelopmentPlan({ employeeId, own, tips }) {
  const { data, error, reload, setData } = useLoad(() => api(`/development/${employeeId}`), [employeeId]);
  const [title, setTitle] = useState("");
  const [due, setDue] = useState("");
  const [problem, setProblem] = useState("");
  const [adding, withAdding] = useAction();

  if (error) return <Card id="plan" title="Development plan"><LoadError message={error} onRetry={reload} /></Card>;
  if (!data) return <Card id="plan" title="Development plan"><Loading /></Card>;

  async function add(goal) {
    setProblem("");
    try {
      await api(`/development/${employeeId}/goals`, { method: "POST", body: goal });
      setTitle(""); setDue("");
      reload();
    } catch (err) {
      setProblem(err.message);
    }
  }

  async function tick(goal) {
    try {
      const updated = await api(`/development/goals/${goal.id}`, { method: "PATCH", body: { done: !goal.done } });
      setData({ ...data, goals: data.goals.map((g) => (g.id === goal.id ? updated : g)) });
    } catch (err) {
      setProblem(err.message);
    }
  }

  async function remove(goal) {
    try {
      await api(`/development/goals/${goal.id}`, { method: "DELETE" });
      setData({ ...data, goals: data.goals.filter((g) => g.id !== goal.id) });
    } catch (err) {
      setProblem(err.message);
    }
  }

  const planned = new Set(data.goals.filter((g) => !g.done).map((g) => g.feature));
  const suggestions = (tips?.tips || []).filter((t) => !planned.has(t.feature));
  const open = data.goals.filter((g) => !g.done).length;

  return (
    <Card id="plan" icon={ListChecks} title={own ? "Your development plan" : "Development plan"}
      subtitle={`Goals ${own ? "you work on with your manager" : "the employee works on with their manager"}. ${open} open. Ticking a goal off doesn't change the score: only the work record does.`}>
      {problem && <Callout tone="error">{problem}</Callout>}
      {data.goals.length === 0 ? <EmptyState compact icon={ListChecks} title="No goals yet" text="Add one below, or take one from the tips." /> : (
        <ul className="plan-list">
          {data.goals.map((g) => (
            <li key={g.id} className={g.done ? "done" : ""}>
              <label className="check">
                <input type="checkbox" checked={g.done} disabled={!data.can_change} onChange={() => tick(g)} />
                <span><span className="strong">{g.title}</span>
                  <span className="muted"> · added by {g.added_by}{g.due ? ` · by ${g.due}` : ""}{g.done ? ` · done by ${g.done_by}, ${g.done_at.slice(0, 10)}` : ""}</span></span>
              </label>
              {data.can_change && <Button look="ghost" icon={Trash2} onClick={() => remove(g)} aria-label={`Remove “${g.title}”`} />}
            </li>
          ))}
        </ul>
      )}
      {data.can_change && (
        <>
          {suggestions.length > 0 && (
            <div className="section-gap">
              <p className="muted">From the tips:</p>
              <div className="chip-row">
                {suggestions.map((t) => (
                  <Button key={t.feature} look="secondary" icon={Plus} onClick={() => withAdding(() => add(fromTip(t)))}>{fromTip(t).title}</Button>
                ))}
              </div>
            </div>
          )}
          <form className="form-row section-gap" onSubmit={(e) => { e.preventDefault(); withAdding(() => add({ title: title.trim(), due: due || null })); }}>
            <label className="field">A goal of your own<input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} placeholder="e.g. Lead the next team project" /></label>
            <label className="field">By (optional)<input type="date" value={due} onChange={(e) => setDue(e.target.value)} /></label>
            <Button busy={adding} busyText="Adding…" icon={Plus} disabled={title.trim().length < 3}>Add the goal</Button>
          </form>
        </>
      )}
    </Card>
  );
}
