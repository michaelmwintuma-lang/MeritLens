/**
 * Demo activity for the screenshot scripts, so the review, correction, feedback and finance pages have something to
 * show. Only ever run against browser_test.py's throwaway copy of the app (never your real database):
 * - the manager nominates the demo employee, who then rates their explanation (flagging one factor) and asks HR to
 *   correct a value, so HR's review shows the pending-correction note; HR holds that decision;
 * - the manager nominates a teammate, whom HR approves, so Finance has a pay rise to sign off.
 * Returns { employee, held, approved }: the demo employee's record and the two nominations.
 */
const { goto, openChrome, signIn, sleep } = require("./browser");

const RUN = `[...document.querySelectorAll("button")].find((b) => b.innerText.includes("Run prediction"))?.click()`;

const api = (c, path, method = "GET", body) => c.evaluate(`fetch("/api${path}", { method: ${JSON.stringify(method)},
  headers: { "X-Requested-With": "MeritLens", "Content-Type": "application/json" },
  body: ${body ? JSON.stringify(JSON.stringify(body)) : "undefined"} }).then((r) => r.json())`);

async function setUpDemo() {
  const c = await openChrome();
  const ids = {};
  try {
    const nominate = (employee_id) => api(c, "/promotion/nominations", "POST", {
      employee_id, proposed_title: "Senior Analyst", proposed_start: new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10),
      criteria: Object.fromEntries(["performance", "leadership", "skills", "impact"].map((k) => [k, { rating: 4, example: `A clear example of ${k} this year.` }])),
      reason: "Led the migration project this year.", model_disagreement: "Strong client feedback the data doesn't capture.", proposed_raise: 8 });
    await signIn(c, "employee");
    ids.employee = (await api(c, "/auth/me")).employee_id;
    await signIn(c, "manager");
    const team = await api(c, "/promotion/employees");
    const mate = (team.employees || []).map((e) => e.id).find((id) => id !== ids.employee);
    ids.held = (await nominate(ids.employee)).id;
    ids.approved = mate && (await nominate(mate)).id;

    await signIn(c, "employee");
    await goto(c, "/my-readiness");
    await c.evaluate(RUN);
    await sleep(4000);
    const fields = await api(c, "/feedback/fields");
    const field = fields.find((f) => f.name === "projects_completed") || fields[0];
    await api(c, "/feedback/ratings", "POST", { clarity: 4, usefulness: 5, comment: "Clear, thank you.",
      flagged: [{ feature: field.name, kind: "wrong" }] });
    await api(c, "/feedback/corrections", "POST", { field: field.name, requested_value: Number(field.current || 0) + 3,
      note: "My signed review form lists more completed projects." });

    await signIn(c, "hr");
    await api(c, `/hr/feedback/nominations/${ids.held}/defer`, "POST", {});
    if (ids.approved) {
      await api(c, `/promotion/nominations/${ids.approved}/decision`, "POST",
        { decision: "approve", reason: "Strong case from the manager.", approved_raise: 8 });
    }
  } catch (err) {
    console.log(`  (demo set-up incomplete: ${err.message})`);
  } finally {
    c.close();
  }
  return ids;
}

module.exports = { RUN, setUpDemo };
