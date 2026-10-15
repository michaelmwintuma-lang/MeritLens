#!/usr/bin/env node
/**
 * Screenshots of the main pages for each role, and an accessibility audit (axe-core, WCAG 2.1 A and AA), taken from
 * a throwaway copy of the app:   python scripts/browser_test.py scripts/ui_capture.js docs/screenshots/<folder>
 *
 * For each page: computer screenshots (1366 wide) and phone ones (390 wide), each in light and dark, a check that
 * nothing is wider than the screen, and axe's findings (on the computer in light and dark, and the phone in dark),
 * written to <folder>/axe.json with a summary printed at the end. Before-and-after sets made before the light/dark
 * pairs (docs/screenshots/before-ui) have only "desktop" (light) and "phone" (dark) shots.
 */
const fs = require("fs");
const path = require("path");
const { goto, openChrome, signIn, sleep, waitFor } = require("./browser");
const { RUN, setUpDemo } = require("./demo_setup");

const OUT = path.resolve(__dirname, "..", process.argv[2] || "docs/screenshots/latest");
const AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js";

// [name, who signs in (null: nobody), address, optional script run on the page first]
// {held} and {employee} in an address are filled in from the demo set-up (demo_setup.js).
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

// [width, colour scheme, file suffix, run axe?]
const VIEWS = [[1366, "light", "desktop-light", true], [1366, "dark", "desktop-dark", true],
  [390, "light", "phone-light", false], [390, "dark", "phone-dark", true]];

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
  const ids = await setUpDemo();
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
    for (const [width, scheme, suffix, audited] of VIEWS) {
      await view(c, width, scheme);
      await goto(c, address);
      if (action) {
        await c.evaluate(action);
        await waitFor(c, `!document.querySelector('[aria-busy="true"]')`, 30000);
        await sleep(1500);
      }
      const wider = await shot(c, path.join(OUT, `${name}-${suffix}.webp`), width);
      if (wider) page.overflow[suffix] = wider;
      // Colour contrast differs between the themes, so both are audited
      if (audited) page.axe = [...(page.axe || []), ...(await audit(c)).map((v) => ({ ...v, view: suffix }))];
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
