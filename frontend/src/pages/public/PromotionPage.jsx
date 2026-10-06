// How a promotion decision is made, from the model's score to Finance's sign-off.
import { PageIntro, Screenshot } from "./parts";

export default function PromotionPage() {
  return (
    <>
      <PageIntro title="How a promotion decision is made">
        Nobody is promoted by the model. It gives managers and HR a starting point that they can check and disagree
        with, as long as they say why.
      </PageIntro>

      <ol className="process">
        <li>
          <h3>The model scores readiness</h3>
          <p>
            It uses performance and development data only: ratings, results, training, projects, attendance and time
            in role. A score above 79% counts as recommended. Opening a score shows each factor's contribution, a second
            explanation from a different method (LIME) as a cross-check, and a what-if tool for trying changes.
          </p>
        </li>
        <li>
          <h3>A manager recommends someone</h3>
          <p>
            They rate the person from 1 to 5 on performance, leadership, skills and impact, with a real example for
            each, and propose the new role, a start date and a pay rise. If the model doesn't recommend the person, the
            manager has to explain why they disagree.
          </p>
        </li>
        <li>
          <h3>HR decides</h3>
          <p>
            HR sees the recommendation next to the model's view. Going against the model needs a written reason, and so
            does a pay rise outside the range HR has set.
          </p>
        </li>
        <li>
          <h3>Finance confirms the pay rise</h3>
          <p>
            The manager and employee aren't told until Finance signs off. Finance sees the role, start date and
            percentage, but not the scores or the reasons, and can send it back to HR with a question.
          </p>
        </li>
      </ol>

      <Screenshot src="/landing/finance.webp" alt="Finance's pay sign-off page, with one pay rise open for review">
        What Finance sees: the pay rise, the agreed range and the history so far.
      </Screenshot>

      <p className="body-text">
        Every decision is kept in a log with who made it, when, and what the model said at that moment, so HR can later
        see where people and the model disagreed.
      </p>
    </>
  );
}
