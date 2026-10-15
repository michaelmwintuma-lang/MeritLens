#!/usr/bin/env node
/**
 * The thesis figures, as PNG at 1600px wide in the light theme, from a throwaway copy of the app with the made-up
 * demo data:   python scripts/browser_test.py scripts/capture_thesis.js
 *
 * Saved to docs/screenshots/thesis/:
 *   fig4_3_my_growth.png                      an employee's My growth page: the score, the explanation and the tips
 *   fig4_4_respond_panel.png                  the "Respond to this explanation" panel
 *   fig4_5_hr_correction_queue.png            HR's record-correction queue
 *   fig4_6_hr_review_pending_correction.png   HR's review of a nomination, with the pending-correction note and hold
 *   fig4_7_feedback_dashboard.png             the feedback dashboard
 *   landing_page.png                          the public landing page
 */
const fs = require("fs");
const path = require("path");
const { goto, openChrome, signIn, sleep, waitFor } = require("./browser");
const { setUpDemo } = require("./demo_setup");

const OUT = path.join(__dirname, "..", "docs", "screenshots", "thesis");
const WIDTH = 1600;

async function light(c) {
  await c.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }, { name: "prefers-reduced-motion", value: "reduce" }] });
  await c.send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height: 1000, deviceScaleFactor: 1, mobile: false });
}

/** Save part of the page: from the top of `from` to the bottom of `to` (CSS selectors, or null for the whole page). */
async function save(c, name, from = null, to = from) {
  await sleep(600);
  const box = await c.evaluate(`(() => {
    const find = (s) => document.querySelector(s);
    if (!${JSON.stringify(from)}) return { y: 0, height: Math.ceil(document.documentElement.scrollHeight) };
    const top = find(${JSON.stringify(from)}).getBoundingClientRect().top + scrollY - 24;
    const bottom = find(${JSON.stringify(to)}).getBoundingClientRect().bottom + scrollY + 24;
    return { y: Math.max(0, Math.floor(top)), height: Math.ceil(bottom - Math.max(0, top)) };
  })()`);
  const res = await c.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true,
    clip: { x: 0, y: box.y, width: WIDTH, height: Math.min(box.height, 8000), scale: 1 } });
  fs.writeFileSync(path.join(OUT, `${name}.png`), Buffer.from(res.result.data, "base64"));
  console.log(`  saved docs/screenshots/thesis/${name}.png`);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const ids = await setUpDemo();
  let c = await openChrome();
  try {
    await light(c);
    await goto(c, "/");
    await waitFor(c, `document.body.innerText.includes("How it works")`);
    await c.evaluate(`Promise.all([...document.images].map((i) => i.complete ? 0 : new Promise((r) => { i.loading = "eager"; i.onload = i.onerror = r; })))`);
    await save(c, "landing_page");

    // The employee: My growth, worked out as the page opens
    await signIn(c, "employee");
    await light(c);
    await goto(c, "/my-readiness");
    if (!(await waitFor(c, `document.body.innerText.includes("Respond to this explanation") && document.querySelector(".checklist")`, 30000))) throw new Error("My growth didn't finish");
    await save(c, "fig4_3_my_growth", ".page-header", "#tips");
    await save(c, "fig4_4_respond_panel", "#respond");
    c.close();

    // HR: the review with its pending correction, the queue, the dashboard
    c = await openChrome();
    await signIn(c, "hr");
    await light(c);
    await goto(c, `/nominations/${ids.held}`);
    if (!(await waitFor(c, `document.body.innerText.includes("a record correction is pending")`, 20000))) throw new Error("no committee note");
    await save(c, "fig4_6_hr_review_pending_correction");
    await goto(c, "/corrections");
    await waitFor(c, `document.querySelector(".change")`, 20000);
    await save(c, "fig4_5_hr_correction_queue");
    await goto(c, "/feedback");
    await waitFor(c, `document.body.innerText.includes("Factors employees contest")`, 20000);
    await save(c, "fig4_7_feedback_dashboard");
  } finally {
    c.close();
  }
})().catch((err) => { console.error(`Capture failed: ${err.message}`); process.exit(1); });
