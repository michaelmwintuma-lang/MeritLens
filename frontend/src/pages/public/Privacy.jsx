// What the system stores and what it doesn't, people's rights over it, and how long it is kept.
import { useEffect, useState } from "react";
import { api } from "../../api";
import { PageIntro } from "./parts";

const RIGHTS = [
  ["See everything held about you", "Anyone signed in can download a copy of all their data (My profile → Your data): their record, scores, ratings, correction requests and the decisions about them."],
  ["Have a wrong record corrected", "Ask HR to correct a value, with evidence; HR checks it and tells you the outcome, with a reason."],
  ["An explanation, and a person deciding", "Every score comes with its reasons in plain words. The model only advises: every promotion decision is made by a person, and recorded with who made it."],
  ["Be removed after you leave", "HR erases the personal data of someone who has left. Past decisions stay in the log under a pseudonym, as the record of who decided what."],
];
const PERIODS = { rating_comments: "Comments written when rating an explanation (the 1 to 5 answers stay, for totals)",
  notifications: "Notifications in the bell", email_log: "The email delivery log (who, what subject, when)",
  activity_log: "The activity log (who did what, by day)" };
const span = (days) => (days % 365 === 0 ? `${days / 365} year${days === 365 ? "" : "s"}` : days % 30 === 0 ? `${days / 30} months` : `${days} days`);

const RULES = [
  ["Only the day is kept", "The activity log stores dates, not times, and the server keeps no log of requests."],
  ["Correction evidence stays private", "Documents attached to a correction request are stored under random names and shown only to the employee and HR."],
  ["No protected characteristics in the model", "Gender, age, education, department and pay are not inputs. Gender, age and education are used only afterwards, to check the model treats groups fairly."],
  ["Feedback never changes a score", "The promotion model never reads ratings or correction requests. Only a correction HR confirms against evidence changes a record, and every such change is logged."],
  ["Ratings are seen only as totals", "HR and the auditor see how explanations were rated added together, and only from five ratings. Managers never see them."],
  ["Scores are kept only for review cycles", "Outside a review cycle a readiness score is worked out when it's needed and not stored. When HR opens a cycle, each person's score is saved with the exact inputs and model version it came from, so a promotion round can be checked later; during the cycle it changes only through a logged record change."],
  ["Emails keep only who, what and when", "Each email is logged so it can be retried if it fails. Once delivered, its content is erased: only the recipient, the subject and the time remain. Emails never contain scores or records."],
  ["Pay is a percentage", "Pay rises are stored only as percentages, never salaries, and never reach the model."],
];

export default function Privacy() {
  const [periods, setPeriods] = useState(null);
  useEffect(() => { api("/privacy/retention").then(setPeriods).catch(() => {}); }, []);
  return (
    <>
      <PageIntro title="What we store, and what we don't">
        These rules are part of how the data is stored, not just a policy, and the automated tests check each one.
      </PageIntro>

      <dl className="rules-list">
        {RULES.map(([rule, detail]) => <div key={rule}><dt>{rule}</dt><dd>{detail}</dd></div>)}
      </dl>

      <h2>Your rights</h2>
      <dl className="rules-list">
        {RIGHTS.map(([rule, detail]) => <div key={rule}><dt>{rule}</dt><dd>{detail}</dd></div>)}
      </dl>

      {periods && (
        <>
          <h2>How long things are kept</h2>
          <dl className="rules-list">
            {Object.entries(PERIODS).map(([key, label]) => <div key={key}><dt>{span(periods[key])}</dt><dd>{label}, then removed automatically.</dd></div>)}
            <div><dt>Kept</dt><dd>The audit trail of decisions is never pruned: it is the record of who decided what, and its tamper-evident chain must stay whole.</dd></div>
          </dl>
        </>
      )}

      <section className="note-band">
        <h2>About the data in this demo</h2>
        <p>
          The model was trained on synthetic employee data: none of it describes a real person. An organisation using
          the system would retrain it on its own promotion history, and it would only go live if it passed the same
          fairness check.
        </p>
      </section>
    </>
  );
}
