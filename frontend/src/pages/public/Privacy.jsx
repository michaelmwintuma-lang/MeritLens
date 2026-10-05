// Privacy by design: the promises, and where the demo data comes from.
import { CalendarDays, EyeOff, FileLock2, KeyRound, Lock, Scale } from "lucide-react";
import { Cards, DemoBand, PageIntro } from "./parts";

const PROMISES = [
  { icon: EyeOff, title: "No identity with reports", text: "Reports have no column for who sent them. Not hidden: simply never stored." },
  { icon: FileLock2, title: "Details removed first", text: "Names, emails, phone numbers and dates are replaced before anything is sent, and the reporter checks the result." },
  { icon: KeyRound, title: "Only you hold the key", text: "Follow-ups use a case ID and a secret key. Only a hash is kept, so not even an administrator can read it." },
  { icon: CalendarDays, title: "Dates, not times", text: "Only the day is kept, and the server keeps no request log, so a report can't be matched to a sign-in." },
  { icon: Scale, title: "Checked for fairness", text: "The model is tested so every gender, age group and education level is recommended at a fair rate." },
  { icon: Lock, title: "Kept apart", text: "Report data never reaches the promotion model. Tests prove the predictions are identical either way." },
];

export default function Privacy() {
  return (
    <>
      <PageIntro eyebrow="Privacy by design" title="Promises the system keeps, by how it's built">
        Privacy here isn't a policy someone has to remember: it's how the system stores (and doesn't store) data. Each
        promise below is checked by automated tests.
      </PageIntro>

      <section className="section-block">
        <Cards items={PROMISES} />
      </section>

      <section className="note-band">
        <h2>About the data in this demo</h2>
        <p>
          The model was trained and is demonstrated on synthetic (made-up) employee data. No real person's record is
          used. An organisation using the platform would train it on its own history, and it would go live only if it
          passed the same fairness check.
        </p>
      </section>

      <DemoBand />
    </>
  );
}
