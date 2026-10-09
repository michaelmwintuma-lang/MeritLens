#!/usr/bin/env node
/**
 * Screenshots of the real app for the public website (frontend/public/landing/), taken from a throwaway copy with
 * the made-up demo data:   python scripts/browser_test.py scripts/capture_landing.js
 *
 * growth.webp  an employee's "My growth" page after running the prediction: the score and what moved it
 * respond.webp the "Respond to this explanation" panel on the same page
 * report.webp  the report form's check step, with names, a date and a phone number replaced by tags
 * case.webp    HR's view of that case
 */
const fs = require("fs");
const path = require("path");
const { goto, openChrome, signIn, sleep, waitFor } = require("./browser");

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
const type = (c, selector, value) => c.evaluate(`(() => { const el = document.querySelector(${JSON.stringify(selector)});
  const proto = el.tagName === "SELECT" ? HTMLSelectElement : el.tagName === "TEXTAREA" ? HTMLTextAreaElement : HTMLInputElement;
  Object.getOwnPropertyDescriptor(proto.prototype, "value").set.call(el, ${JSON.stringify(value)});
  el.dispatchEvent(new Event(el.tagName === "SELECT" ? "change" : "input", { bubbles: true })); })()`);

(async () => {
  const c = await openChrome();
  try {
    await c.send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height: HEIGHT, deviceScaleFactor: 1, mobile: false });
    await c.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });

    // 1. My growth: run the prediction; show the score and the start of the explanation
    await signIn(c, "employee");
    await goto(c, "/my-readiness");
    await click(c, "button", "Run prediction");
    if (!(await waitFor(c, `document.body.innerText.includes("Respond to this explanation")`, 30000))) throw new Error("no respond panel");
    const top = await c.evaluate(`document.querySelector(".appear").getBoundingClientRect().top + window.scrollY - 24`);
    await shoot(c, "growth", top);
    const panel = await c.evaluate(`[...document.querySelectorAll("section.card")].find((s) => s.innerText.includes("Respond to this explanation")).getBoundingClientRect().top + window.scrollY - 24`);
    await shoot(c, "respond", panel);

    // 2. The report form's check step
    const directory = await c.evaluate(`fetch("/api/auth/me", { headers: { Authorization: "Bearer " + localStorage.getItem("token") } }).then((r) => r.json())`);
    if (!directory.username) throw new Error("not signed in");
    await goto(c, "/report");
    await waitFor(c, `document.querySelector("select option[value='biased_rating']")`);
    await type(c, "select", "biased_rating");
    await type(c, "textarea", "At my appraisal on 12 March, Mo Manager marked me down for two projects that were "
      + "never assigned to me. When I asked about it he said to call him on 07700 900123 instead of putting it in writing.");
    await click(c, "button", "Check what will be sent");
    if (!(await waitFor(c, `document.body.innerText.includes("[PERSON")`, 20000))) throw new Error("the check step didn't show tags");
    await shoot(c, "report", 0);

    // Send it, so HR has a case to show
    await c.evaluate(`[...document.querySelectorAll("input[type=checkbox]")].forEach((b) => { if (!b.checked) b.click(); })`);
    await click(c, "button", "Send");
    await waitFor(c, `/R-[A-Z2-9]{4}-[A-Z2-9]{4}/.test(document.body.innerText)`, 20000);
    const caseId = (await c.evaluate("document.body.innerText")).match(/R-[A-Z2-9]{4}-[A-Z2-9]{4}/)?.[0];
    if (!caseId) throw new Error("the report wasn't sent");

    // 3. HR's view of the case
    await signIn(c, "hr");
    await goto(c, `/reports/${caseId}`);
    await waitFor(c, `document.body.innerText.includes("Why this priority")`);
    await shoot(c, "case", 0);
  } finally {
    c.close();
  }
})().catch((err) => { console.error(`Capture failed: ${err.message}`); process.exit(1); });
