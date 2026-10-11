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
const PAGES = [
  ["landing", null, "/"],
  ["login", null, "/login"],
  ["employee-home", "employee", "/"],
  ["employee-growth", "employee", "/my-readiness", `[...document.querySelectorAll("button")].find((b) => b.innerText.includes("Run prediction"))?.click()`],
  ["manager-team", "manager", "/team"],
  ["hr-home", "hr", "/"],
  ["hr-employees", "hr", "/employees"],
  ["hr-corrections", "hr", "/corrections"],
  ["hr-feedback-dashboard", "hr", "/feedback"],
  ["hr-decisions", "hr", "/decisions"],
  ["auditor-home", "auditor", "/"],
  ["model", "auditor", "/model"],
  ["finance-home", "finance", "/"],
  ["admin-home", "admin", "/"],
  ["admin-users", "admin", "/admin/users"],
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
  const results = {};
  let current = undefined;
  let c = await openChrome();
  for (const [name, who, address, action] of PAGES) {
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
