// How anonymous reporting works, for the person reporting and for HR.
import { PageIntro, Screenshot } from "./parts";

export default function ReportingPage() {
  return (
    <>
      <PageIntro title="Reporting a concern without giving your name">
        Reporting is part of the employee feedback channel: if an assessment seems unfair, an employee can say so
        without being identified. Staff sign in, so only people in the organisation can report. The report itself
        is never linked to their account.
      </PageIntro>

      <Screenshot src="/landing/report.webp" alt="The report form's check step, with a name, a date and a phone number replaced by tags">
        Before sending, the reporter sees exactly what HR will get. The list of what was removed is shown only to them.
      </Screenshot>

      <section className="prose">
        <h2>After it's sent</h2>
        <p>
          The reporter gets a case ID and a secret key, shown once, to keep in a downloaded receipt or a password
          manager. With those they can read HR's replies and answer them. The website never keeps the key, the server
          stores only a hash of it, and five wrong tries lock the case for 15 minutes.
        </p>
        <p>
          They can attach photos or videos. Location, phone model, owner name and the time taken are stripped from
          each file before it's saved. What's visible or audible can't be removed, so the reporter is asked to check
          for faces, reflections and their own voice.
        </p>
        <p>
          A report can be about a biased rating or appraisal, favouritism, discrimination, a wrong or missing record, or
          any other workplace concern. When HR closes a case finding a rating unfair, they can re-appraise the value
          concerned. That correction is never linked to the report, and the report itself never reaches the
          promotion model.
        </p>
      </section>

      <Screenshot src="/landing/case.webp" alt="HR's view of a case, showing the suggested priority and how sure the model was">
        HR's view of a case: the suggested priority, how sure the model is, and the words that drove it.
      </Screenshot>

      <section className="prose">
        <h2>How urgent is it?</h2>
        <p>
          A text classifier trained on example reports suggests high, moderate or low priority. Some words always raise
          it to high, such as anything suggesting violence or self-harm, and some categories have a minimum. HR sets the
          final priority. Alerts to HR contain the case ID, category and priority, never the text.
        </p>
      </section>
    </>
  );
}
