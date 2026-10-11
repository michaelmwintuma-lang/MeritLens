// Who uses the system, and what each role sees and does.
import { PageIntro } from "./parts";

const ROLES = [
  ["Employee", "Their own readiness score and what's behind it", "Try what-if changes; rate the explanation, or ask HR to correct their record"],
  ["Manager", "Their team's scores", "Recommend someone, with ratings, examples and a proposed pay rise"],
  ["HR", "All employees, recommendations, the decision log, record corrections and the feedback dashboard", "Decide on promotions, confirm or reject record corrections, set the pay range"],
  ["Finance", "Approved pay rises and the pay range", "Confirm a pay rise or send it back to HR"],
  ["Admin", "Accounts, the activity log and the system's health", "Create accounts and set managers' teams"],
  ["Compliance auditor", "The decision log, the model and its fairness, and the feedback dashboard (totals only)", "Check decisions; read-only, never sees one person's feedback"],
];

export default function Approach() {
  return (
    <>
      <PageIntro title="Who uses it">
        Six roles, each seeing only what it needs. A manager can't see other teams, Finance doesn't see scores, and
        feedback about explanations is shown to HR only as totals.
      </PageIntro>

      <div className="table-wrap roles-table" tabIndex={0}>
        <table>
          <thead><tr><th>Role</th><th>Sees</th><th>Does</th></tr></thead>
          <tbody>
            {ROLES.map(([role, sees, does]) => <tr key={role}><td className="strong">{role}</td><td>{sees}</td><td>{does}</td></tr>)}
          </tbody>
        </table>
      </div>

      <p className="body-text">
        The model never makes a decision on its own. Managers and HR can disagree with it, and when they do they write
        down why. Those reasons are kept with the decision.
      </p>
    </>
  );
}
