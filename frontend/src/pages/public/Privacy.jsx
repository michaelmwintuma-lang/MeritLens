// What the system stores and what it doesn't.
import { PageIntro } from "./parts";

const RULES = [
  ["Reports have no account column", "There is nowhere to record who sent a report, so it can't be looked up later, even by an administrator."],
  ["Only the day is kept", "Reports, messages and the activity log store dates, not times, and the server keeps no log of requests."],
  ["The reporter's key isn't stored", "Only a hash of it is saved, and the website never keeps it in the browser. If the reporter loses the key, nobody can open the case for them."],
  ["Photos and videos are cleaned", "GPS position, device, owner name and the time taken are removed before a file is saved."],
  ["No protected characteristics in the model", "Gender, age, education, department and pay are not inputs. Gender, age and education are used only afterwards, to check the model treats groups fairly."],
  ["Feedback never changes a score", "The promotion model never reads ratings, correction requests or reports. Only a correction HR confirms against evidence changes a record, and every such change is logged."],
  ["Ratings are seen only as totals", "HR and the auditor see how explanations were rated added together, and only from five ratings. Managers never see them."],
  ["Pay is a percentage", "Pay rises are stored only as percentages, never salaries, and never reach the model."],
];

export default function Privacy() {
  return (
    <>
      <PageIntro title="What we store, and what we don't">
        These rules are part of how the data is stored, not just a policy, and the automated tests check each one.
      </PageIntro>

      <dl className="rules-list">
        {RULES.map(([rule, detail]) => <div key={rule}><dt>{rule}</dt><dd>{detail}</dd></div>)}
      </dl>

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
