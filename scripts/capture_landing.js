#!/usr/bin/env node
/**
 * Screenshots of the real app for the public website (frontend/public/landing/), taken from a throwaway copy with
 * the made-up demo data:   python scripts/browser_test.py scripts/capture_landing.js
 *
 * growth.webp  an employee's "My growth" page after running the prediction: the score and what moved it
 * respond.webp the "Respond to this explanation" panel on the same page
 * finance.webp Finance's pay sign-off, with one pay rise open for review (uses the demo set-up, demo_setup.js)
 */
const fs = require("fs");
const path = require("path");
const { goto, openChrome, signIn, sleep, waitFor } = require("./browser");
const { setUpDemo } = require("./demo_setup");

const OUT = path.join(__dirname, "..", "frontend", "public", "landing");
const WIDTH = 1440, HEIGHT = 900;

async function shoot(c, name, scrollY = 0) {
  await c.send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height: HEIGHT, deviceScaleFactor: 1, mobile: false });
  await c.evaluate(`window.scrollTo(0, ${scrollY})`);
  await sleep(400);
  const res = await c.send("Page.captureScreenshot", { format: "webp", quality: 82 });
  fs.writeFileSync(path.join(OUT, `${name}.webp`), Buffer.from(res.result.data, "base64"));
  console.log(`  saved frontend/public/landing/${name}.webp`);
}

const click = (c, selector, text) => c.evaluate(`(() => { const el = [...document.querySelectorAll(${JSON.stringify(selector)})]
  .find((e) => e.innerText.includes(${JSON.stringify(text)})); if (el) el.click(); return !!el; })()`);

(async () => {
  const c = await openChrome();
  try {
    await c.send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height: HEIGHT, deviceScaleFactor: 1, mobile: false });
    await c.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
    await setUpDemo();

    // 1. My growth: run the prediction; show the score and the start of the explanation
    await signIn(c, "employee");
    await goto(c, "/my-readiness");
    await click(c, "button", "Run prediction");
    if (!(await waitFor(c, `document.body.innerText.includes("Respond to this explanation")`, 30000))) throw new Error("no respond panel");
    const top = await c.evaluate(`document.querySelector(".appear").getBoundingClientRect().top + window.scrollY - 88`);
    await shoot(c, "growth", top);
    const panel = await c.evaluate(`[...document.querySelectorAll("section.card")].find((s) => s.innerText.includes("Respond to this explanation")).getBoundingClientRect().top + window.scrollY - 88`);
    await shoot(c, "respond", panel);

    // 2. Finance: the sign-off queue with one pay rise open in the review drawer
    await signIn(c, "finance");
    await goto(c, "/finance");
    await click(c, "button", "Review");
    if (!(await waitFor(c, `document.querySelector(".drawer")`, 10000))) throw new Error("no review drawer");
    await shoot(c, "finance");

  } finally {
    c.close();
  }
})().catch((err) => { console.error(`Capture failed: ${err.message}`); process.exit(1); });
