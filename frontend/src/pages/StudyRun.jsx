// The facilitator's page for one user-study session (the link the admin gave): consent, then each task timed with
// its outcome, then the participant's questionnaire. It needs no sign-in, so the participant can sign in as each
// role in the main window meanwhile. Nothing here names the participant.
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle2, Play, Square } from "lucide-react";
import { api } from "../api";
import { useAction } from "../useAction";
import { Badge, Button, Callout, Card, LoadError, PageHeader, PageLoading, Wordmark } from "../components/ui";

const OUTCOMES = [["yes", "Completed alone"], ["help", "With a hint"], ["no", "Not completed"]];
const ROLE = { employee: "employee", manager: "manager", hr: "hr" };

function TaskRunner({ token, task, saved, onSaved }) {
  const [started, setStarted] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [stopped, setStopped] = useState(null);
  const [notes, setNotes] = useState(saved?.notes || "");
  const [error, setError] = useState("");
  const timer = useRef(0);
  useEffect(() => () => clearInterval(timer.current), []);
  const seconds = started ? Math.round(((stopped ?? now) - started) / 1000) : saved?.seconds ?? 0;

  function start() {
    setStarted(Date.now());
    setStopped(null);
    timer.current = setInterval(() => setNow(Date.now()), 500);
  }

  async function finish(completed) {
    clearInterval(timer.current);
    const end = stopped ?? Date.now();
    setStopped(end);
    setError("");
    try {
      await api(`/study/run/${token}/tasks`, { method: "POST", body: { task: task.task, completed, notes,
        seconds: started ? Math.round((end - started) / 1000) : saved?.seconds ?? 0 } });
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card id={`task-${task.task}`} title={`${task.task}: sign in as ${ROLE[task.role]}`}
      actions={saved ? <Badge tone="success" icon={CheckCircle2}>{OUTCOMES.find(([k]) => k === saved.completed)[1]} · {saved.seconds}s</Badge> : null}>
      <p className="study-task">“{task.text}”</p>
      {task.scenario && <Callout title="Scenario card">{task.scenario}</Callout>}
      <p className="muted">Read the task aloud; don't explain how to do it. Start the clock when they begin.</p>
      {error && <Callout tone="error">{error}</Callout>}
      <div className="form-actions">
        {!started || stopped ? <Button icon={Play} look={saved ? "secondary" : "primary"} onClick={start}>{saved ? "Time it again" : "Start the clock"}</Button>
          : <span className="study-clock num" aria-live="off">{seconds}s</span>}
        {started && !stopped && <Button look="ghost" icon={Square} onClick={() => setStopped(Date.now())}>Stop the clock</Button>}
      </div>
      <label className="field section-gap">Notes <span className="muted">(optional: where they hesitated, what they said)</span>
        <input value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} />
      </label>
      <div className="form-actions">
        {OUTCOMES.map(([key, label]) => (
          <Button key={key} look={key === "yes" ? "primary" : "secondary"} disabled={!started && !saved} onClick={() => finish(key)}>{label}</Button>
        ))}
      </div>
    </Card>
  );
}

function Questionnaire({ token, sections, onDone }) {
  const [answers, setAnswers] = useState({});
  const [roles, setRoles] = useState("employee, manager and hr");
  const [comments, setComments] = useState("");
  const [error, setError] = useState("");
  const [sending, withSending] = useAction();
  const total = sections.reduce((n, s) => n + s.items.length, 0);

  async function send(e) {
    e.preventDefault();
    setError("");
    try {
      await api(`/study/run/${token}/finish`, { method: "POST", body: { answers, roles_played: roles, comments: comments.trim() || null } });
      onDone();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={(e) => withSending(() => send(e))}>
      <Callout title="Now the participant answers">Hand over the screen. 1 means strongly disagree, 5 strongly agree. There are no right answers.</Callout>
      {sections.map((section) => (
        <Card key={section.title} title={section.title}>
          {section.items.map((item) => (
            <fieldset key={item.key} className="agree">
              <legend>{item.text}</legend>
              <div className="agree-options">
                <span className="agree-end" aria-hidden="true">Strongly disagree</span>
                {[1, 2, 3, 4, 5].map((n) => (
                  <label key={n} className="agree-option">
                    <input type="radio" name={item.key} value={n} checked={answers[item.key] === n} onChange={() => setAnswers({ ...answers, [item.key]: n })} />
                    <span>{n}</span>
                  </label>
                ))}
                <span className="agree-end" aria-hidden="true">Strongly agree</span>
              </div>
            </fieldset>
          ))}
        </Card>
      ))}
      <Card title="Last question">
        <label className="field">What was the most confusing moment, and what would you change?
          <textarea rows={3} value={comments} onChange={(e) => setComments(e.target.value)} maxLength={2000} />
        </label>
        <label className="field">Roles played (the facilitator fills this in)
          <input value={roles} onChange={(e) => setRoles(e.target.value)} required minLength={2} maxLength={80} />
        </label>
        {error && <Callout tone="error">{error}</Callout>}
        <Button busy={sending} busyText="Saving…" disabled={Object.keys(answers).length < total}>
          Finish ({Object.keys(answers).length} of {total} answered)
        </Button>
      </Card>
    </form>
  );
}

export default function StudyRun() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [step, setStep] = useState("tasks");
  const load = () => api(`/study/run/${token}`).then(setData).catch((err) => setError(err.message));
  useEffect(() => { load(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  async function consent() {
    try {
      await api(`/study/run/${token}/consent`, { method: "POST" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  let body;
  if (error && !data) body = <LoadError message={error} onRetry={load} />;
  else if (!data) body = <PageLoading />;
  else if (data.finished) body = <Card><Callout tone="success" title={`Session ${data.code} is finished.`}>Thank the participant. The admin saves and analyses the results on the User study page.</Callout></Card>;
  else if (!data.consented) {
    body = (
      <Card title="1. Consent" subtitle="Read this aloud to the participant, and continue only if they agree.">
        <p className="quote">{data.consent}</p>
        <Button icon={CheckCircle2} onClick={consent}>The participant agrees</Button>
      </Card>
    );
  } else if (step === "questionnaire") {
    body = <Questionnaire token={token} sections={data.sections} onDone={load} />;
  } else {
    const done = Object.keys(data.done).length;
    body = (
      <>
        <Callout>Tasks in this order: T9 needs T5's request, and T11 needs T9's decision. {done} of {data.tasks.length} recorded.</Callout>
        {data.tasks.map((t) => <TaskRunner key={t.task} token={token} task={t} saved={data.done[t.task]} onSaved={load} />)}
        <div className="form-actions"><Button disabled={done < data.tasks.length} onClick={() => setStep("questionnaire")}>Go to the questionnaire</Button>
          {done < data.tasks.length && <span className="muted">Record every task first.</span>}</div>
      </>
    );
  }

  return (
    <div className="study-page">
      <header className="study-head"><Wordmark small /><span className="muted">User study{data ? ` · participant ${data.code}` : ""}</span></header>
      <main className="study-main" id="main">
        <PageHeader title="Facilitator's page" subtitle="Keep this window for yourself. The participant uses the main window." />
        {body}
      </main>
    </div>
  );
}
