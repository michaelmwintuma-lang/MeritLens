#!/usr/bin/env node
/**
 * Screenshots of the main pages for each role, and an accessibility audit (axe-core, WCAG 2.1 A and AA), taken from
 * a throwaway copy of the app:   python scripts/browser_test.py scripts/ui_capture.js docs/screenshots/<folder>
 *
 * For each page: a computer screenshot (1366 wide, light) and a phone one (390 wide, dark), a check that nothing is
 * wider than the screen, and axe's findings, written to <folder>/axe.json with a summary printed at the end.
 */
const fs = require("fs");
const path = require("path");
const { goto, openChrome, signIn, sleep, waitFor } = require("./browser");

const OUT = path.resolve(__dirname, "..", process.argv[2] || "docs/screenshots/latest");
const AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js";

// [name, who signs in (null: nobody), address, optional script run on the page first]
// {nomination}, {held} and {employee} in an address are filled in by setUp() below.
const RUN = `[...document.querySelectorAll("button")].find((b) => b.innerText.includes("Run prediction"))?.click()`;
const PAGES = [
  ["landing", null, "/"],
  ["public-approach", null, "/approach"],
  ["public-promotion", null, "/promotion"],
  ["public-privacy", null, "/privacy"],
  ["public-demo", null, "/demo"],
  ["login", null, "/login"],
  ["employee-home", "employee", "/"],
  ["employee-growth", "employee", "/my-readiness", RUN],
  ["employee-model", "employee", "/model"],
  ["employee-account", "employee", "/account"],
  ["manager-home", "manager", "/"],
  ["manager-team", "manager", "/team"],
  ["manager-employee", "manager", "/employees/{employee}", RUN],
  ["manager-nominations", "manager", "/nominations"],
  ["hr-home", "hr", "/"],
  ["hr-employees", "hr", "/employees"],
  ["hr-predict-explain", "hr", "/employees/{employee}", RUN],
  ["hr-employee-new", "hr", "/employees/new"],
  ["hr-employee-import", "hr", "/employees/import"],
  ["hr-nominations", "hr", "/nominations"],
  ["hr-review-pending-correction", "hr", "/nominations/{held}"],
  ["hr-corrections", "hr", "/corrections"],
  ["hr-feedback-dashboard", "hr", "/feedback"],
  ["hr-decisions", "hr", "/decisions"],
  ["hr-model-registry", "hr", "/models"],
  ["hr-live-fairness", "hr", "/fairness"],
  ["finance-home", "finance", "/"],
  ["finance-sign-off", "finance", "/finance"],
  ["auditor-home", "auditor", "/"],
  ["auditor-decisions", "auditor", "/decisions"],
  ["auditor-audit-trail", "auditor", "/audit"],
  ["auditor-feedback", "auditor", "/feedback"],
  ["model", "auditor", "/model"],
  ["admin-home", "admin", "/"],
  ["admin-users", "admin", "/admin/users"],
  ["admin-activity", "admin", "/admin/activity"],
  ["admin-email", "admin", "/admin/email"],
  ["admin-demo-requests", "admin", "/admin/demo-requests"],
  ["admin-model-registry", "admin", "/models"],
];

const api = (c, path, method = "GET", body) => c.evaluate(`fetch("/api${path}", { method: ${JSON.stringify(method)},
  headers: { "X-Requested-With": "MeritLens", "Content-Type": "application/json" },
  body: ${body ? JSON.stringify(JSON.stringify(body)) : "undefined"} }).then((r) => r.json())`);

/**
 * Demo activity so the review, correction and finance pages have something to show: the manager nominates the demo
 * employee (who then asks HR to correct a value, so HR's review shows the pending-correction note) and a teammate
 * (whom HR approves, so Finance has a pay rise to sign off). Only ever runs against browser_test.py's throwaway copy.
 */
async function setUp() {
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
    const rows = Array.isArray(team) ? team : team.items || team.employees || [];
    const mate = rows.map((e) => e.id).find((id) => id !== ids.employee);
    ids.held = (await nominate(ids.employee)).id;
    const approved = mate && (await nominate(mate)).id;
    await signIn(c, "employee");
    await goto(c, "/my-readiness");
    await c.evaluate(RUN);
    await sleep(4000);
    const fields = await api(c, "/feedback/fields");
    const field = fields.find((f) => f.name === "projects_completed") || fields[0];
    await api(c, "/feedback/corrections", "POST", { field: field.name, requested_value: Number(field.current || 0) + 3,
      note: "My signed review form lists more completed projects." });
    await api(c, "/feedback/ratings", "POST", { clarity: 4, usefulness: 5, flagged: {}, comment: "Clear, thank you." });
    await signIn(c, "hr");
    await api(c, `/hr/feedback/nominations/${ids.held}/defer`, "POST", {});
    if (approved) await api(c, `/promotion/nominations/${approved}/decision`, "POST",
      { decision: "approve", reason: "Strong case from the manager.", approved_raise: 8 });
  } catch (err) {
    console.log(`  (demo set-up incomplete: ${err.message})`);
  } finally {
    c.close();
  }
  return ids;
}

async function view(c, width, scheme) {
  await c.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: scheme }] });
  await c.send("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
}

async function shot(c, file, width) {
  const size = (await c.send("Page.getLayoutMetrics")).result.cssContentSize;
  const height = Math.min(Math.ceil(size.height), 6000);
  const res = await c.send("Page.captureScreenshot", { format: "webp", quality: 80, captureBeyondViewport: true,
    clip: { x: 0, y: 0, width, height, scale: 1 } });
  fs.writeFileSync(file, Buffer.from(res.result.data, "base64"));
  return Math.ceil(size.width) > width + 1 ? Math.ceil(size.width) : null;  // wider than the screen?
}

let axeSource = null;
async function audit(c) {
  axeSource ||= await (await fetch(AXE_URL)).text();
  if (!(await c.evaluate("!!window.axe"))) await c.evaluate(`${axeSource}\n;true`);
  return c.evaluate(`axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] } })
    .then((r) => r.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length,
      examples: v.nodes.slice(0, 3).map((n) => n.target.join(" ")) })))`);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const ids = await setUp();
  const results = {};
  let current = undefined;
  let c = await openChrome();
  for (const [name, who, raw, action] of PAGES) {
    const address = raw.replace(/\{(\w+)\}/g, (_, k) => ids[k] ?? "");
    if (who !== current) {  // a fresh browser for each person
      c.close();
      c = await openChrome();
      await view(c, 1366, "light");
      if (who) await signIn(c, who);
      current = who;
    }
    const page = { overflow: {} };
    for (const [width, scheme, suffix] of [[1366, "light", "desktop"], [390, "dark", "phone"]]) {
      await view(c, width, scheme);
      await goto(c, address);
      if (action) {
        await c.evaluate(action);
        await waitFor(c, `!document.querySelector('[aria-busy="true"]')`, 30000);
        await sleep(1500);
      }
      const wider = await shot(c, path.join(OUT, `${name}-${suffix}.webp`), width);
      if (wider) page.overflow[suffix] = wider;
      // Audited in both: light on a computer, dark on a phone (colour contrast differs between the themes)
      page.axe = [...(page.axe || []), ...(await audit(c)).map((v) => ({ ...v, view: suffix }))];
    }
    results[name] = page;
    const issues = page.axe.reduce((n, v) => n + v.nodes, 0);
    console.log(`  ${name.padEnd(24)} axe: ${page.axe.length} rule(s), ${issues} element(s)` +
      (Object.keys(page.overflow).length ? `  WIDER THAN THE SCREEN: ${JSON.stringify(page.overflow)}` : ""));
  }
  c.close();
  fs.writeFileSync(path.join(OUT, "axe.json"), JSON.stringify(results, null, 2));
  const all = Object.values(results).flatMap((p) => p.axe);
  const byRule = {};
  for (const v of all) byRule[v.id] = (byRule[v.id] || 0) + v.nodes;
  console.log(`\nAccessibility findings by rule: ${JSON.stringify(byRule)}`);
  console.log(`Saved to ${path.relative(process.cwd(), OUT)}`);
})().catch((err) => { console.error(`Capture failed: ${err.message}`); process.exit(1); });
