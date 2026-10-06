// Who uses the system, and what each role sees and does.
import { PageIntro } from "./parts";

const ROLES = [
  ["Employee", "Their own readiness score and what's behind it", "Try what-if changes, report a concern, follow up on it"],
  ["Manager", "Their team's scores", "Recommend someone, with ratings, examples and a proposed pay rise"],
  ["HR", "All employees, recommendations, the decision log and the report inbox", "Decide on promotions, set the pay range, handle reports"],
  ["Finance", "Approved pay rises and the pay range", "Confirm a pay rise or send it back to HR"],
  ["Admin", "Accounts and the activity log", "Create accounts and set managers' teams"],
];

export default function Approach() {
  return (
    <>
      <PageIntro title="Who uses it">
        Five roles, each seeing only what it needs. A manager can't see other teams, Finance doesn't see scores, and
        nobody can see who sent a report.
      </PageIntro>

      <div className="table-wrap roles-table">
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
