// Promotion readiness: what an employee sees, and how a promotion decision is made.
import { DemoBand, Feature, PageIntro, Steps } from "./parts";

const DECISION_STEPS = [
  ["The model scores", "Each employee's readiness is worked out from performance and development data only. Gender, age, education and pay are never used."],
  ["A manager nominates", "Managers see their team's readiness and the reasons, then nominate someone with a short explanation of their own."],
  ["HR decides", "HR sees the nomination beside the model's view. If they disagree with the model, they must write down why."],
  ["Everything is logged", "Each decision is kept with who made it, when, what the model said and the reason, so it can be reviewed later."],
];

export default function PromotionPage() {
  return (
    <>
      <PageIntro eyebrow="Promotion readiness" title="Every score comes with its reasons">
        A readiness score on its own isn't fair to anyone. Here, each one shows exactly what raised it and what held it
        back, in everyday language, and people make the decision.
      </PageIntro>

      <Feature eyebrow="For employees and managers" title="See what's behind the number"
        text="Open a readiness score and you see each factor's real value and how much it moved the score, checked by a second, independent method."
        points={["What helps and what holds back, with the real values", "A second, independent explanation as a check",
          "Try changes and see the effect, nothing saved", "Realistic tips to reach the threshold"]}
        photo="growth.webp" alt="A smiling woman working on her laptop" portrait
        screen="/landing/readiness.webp" screenAlt="An employee's readiness page with the factors that raised and lowered the score" />

      <Steps title="How a promotion decision is made" items={DECISION_STEPS} />

      <DemoBand />
    </>
  );
}
