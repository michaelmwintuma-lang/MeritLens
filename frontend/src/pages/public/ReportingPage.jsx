// Anonymous reporting: what the reporter sees, how a report travels, and what HR gets.
import { DemoBand, Feature, PageIntro, Steps } from "./parts";

const REPORT_STEPS = [
  ["Write it down", "Describe what happened and choose a category, from harassment and discrimination to safety hazards, fraud and data breaches."],
  ["Check the cleaned version", "Names, emails, phone numbers and dates are replaced before anything is sent. You see and approve exactly what HR will read."],
  ["Keep your key", "You get a case ID and a secret key. Only a scrambled version of the key is stored, so nobody else can open your case."],
  ["Talk it through", "Use the key to read replies and answer questions. HR sees you only as “Reporter”, and you see them as “Investigator”."],
];

export default function ReportingPage() {
  return (
    <>
      <PageIntro eyebrow="Anonymous reporting" title="Speak up without revealing who you are">
        Report harassment, discrimination, bullying, violence, safety hazards, fraud, data breaches and more. Your report is never linked to your
        account, and before anything is sent you see exactly what HR will read.
      </PageIntro>

      <Feature eyebrow="For the person reporting" title="Your words, without your identity"
        text="Details that could point to you are removed automatically, and phrases that might still identify you are flagged so you can change them."
        points={["Names, contacts and dates removed automatically", "Warnings about phrases that could identify you",
          "A private case ID and key to follow up", "Talk with an investigator; neither side sees a name"]}
        photo="speak-up.webp" alt="A person working calmly at their own desk" portrait
        screen="/landing/report.webp" screenAlt="Checking a report before sending: names and dates replaced" />

      <Steps title="From concern to conversation" items={REPORT_STEPS} />

      <Feature flip eyebrow="For HR" title="One clear place to listen and act"
        text="Urgent reports come first, with the warning words marked, and every case has its own two-way conversation."
        points={["Triage with reasons you can read", "A two-way conversation with the reporter", "Status and outcome recorded for every case"]}
        photo="hr-conversation.webp" alt="Colleagues listening to each other in a meeting"
        screen="/landing/case.webp" screenAlt="HR's case page: the report, its priority and the conversation" />

      <DemoBand />
    </>
  );
}
