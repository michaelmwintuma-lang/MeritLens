// Admin: the user study (docs/USER_TEST.md). Start a session for each participant (a code, never a name), open its
// link in a second window for the facilitator, and when sessions are finished, save them to the evaluation files
// and read the analysis (SUS, the explanation and fairness scales, tasks) on this page.
import { useState } from "react";
import { BarChart3, ClipboardCopy, ExternalLink, FlaskConical, UserPlus } from "lucide-react";
import { api } from "../../api";
import { useAction } from "../../useAction";
import { useLoad } from "../../useLoad";
import { Badge, Button, Callout, Card, EmptyState, LoadError, PageHeader, PageLoading } from "../../components/ui";
import { useToast } from "../../components/Toast";

export default function Study() {
  const { data, error, reload } = useLoad(() => api("/study/sessions"), []);
  const [created, setCreated] = useState(null);
  const [report, setReport] = useState(null);
  const [problem, setProblem] = useState("");
  const [starting, withStarting] = useAction();
  const [analysing, withAnalysing] = useAction();
  const toast = useToast();

  async function start() {
    setProblem("");
    try {
      setCreated(await api("/study/sessions", { method: "POST" }));
      reload();
    } catch (err) {
      setProblem(err.message);
    }
  }

  async function analyse() {
    setProblem("");
    try {
      const res = await api("/study/analyse", { method: "POST" });
      setReport(res.report);
      toast(`Saved ${res.participants} participant${res.participants === 1 ? "" : "s"} and analysed them.`);
    } catch (err) {
      setProblem(err.message);
    }
  }

  const link = created && `${window.location.origin}${created.link}`;
  const header = <PageHeader title="User study" subtitle="Run the user test inside the app: consent, timed tasks and the questionnaire, saved for the analysis. Participants are codes, never names."
    actions={<Button icon={UserPlus} busy={starting} busyText="Starting…" onClick={() => withStarting(start)}>New participant</Button>} />;
  if (error) return <>{header}<LoadError message={error} onRetry={reload} /></>;
  if (!data) return <>{header}<PageLoading /></>;
  const finished = data.filter((s) => s.finished).length;

  return (
    <>
      {header}
      <Callout title="Before you start">
        Check with your supervisor that the study is approved. Participants use the demo accounts and made-up data only.
        To give everyone the same starting point, copy <span className="mono">backend/instance/app.db</span> before the first
        session and copy it back after each one, with the app stopped (docs/USER_TEST.md).
      </Callout>
      {problem && <Callout tone="error">{problem}</Callout>}
      {created && (
        <Card id="link" icon={FlaskConical} title={`Participant ${created.code}`}
          subtitle="Open this link in a second window (or on a second screen) for yourself, the facilitator. The participant uses the main window and signs in as each role when a task says so.">
          <p className="mono study-link">{link}</p>
          <div className="form-actions">
            <a className="btn btn-primary" href={created.link} target="_blank" rel="noreferrer"><ExternalLink size={16} aria-hidden="true" />Open the facilitator's page</a>
            <Button look="secondary" icon={ClipboardCopy} onClick={() => navigator.clipboard?.writeText(link).then(() => toast("Link copied."))}>Copy the link</Button>
          </div>
          <p className="muted section-gap">The link is shown only now. It works for this participant only, and stops working once they finish.</p>
        </Card>
      )}

      <Card flush title="Sessions" subtitle={`${finished} finished of ${data.length}.`}
        actions={<Button look="secondary" icon={BarChart3} busy={analysing} busyText="Analysing…" disabled={!finished} onClick={() => withAnalysing(analyse)}>Save and analyse</Button>}>
        {data.length === 0 ? <EmptyState icon={FlaskConical} title="No sessions yet" text="Start one with “New participant”." /> : (
          <div className="table-wrap auto-height" tabIndex={0} role="region" aria-label="Study sessions"><table>
            <thead><tr><th>Participant</th><th>Started</th><th>Consent</th><th className="num">Tasks</th><th className="num">Questionnaire</th><th>Status</th></tr></thead>
            <tbody>{data.map((s) => (
              <tr key={s.id}><td className="strong">{s.code}</td><td className="num">{s.created_at.replace("T", " ")}</td>
                <td>{s.consented ? "Given" : <span className="muted">Not yet</span>}</td>
                <td className="num">{s.tasks_done} of {s.tasks}</td><td className="num">{s.answers} of {s.items}</td>
                <td>{s.finished ? <Badge tone="success">Finished</Badge> : <Badge>In progress</Badge>}</td></tr>
            ))}</tbody>
          </table></div>
        )}
      </Card>

      {report && (
        <Card id="report" title="Analysis" subtitle="Also saved as results/user_test.md, with the answers in backend/evaluation/.">
          <pre className="study-report">{report}</pre>
        </Card>
      )}
    </>
  );
}
