#!/usr/bin/env node
/**
 * Checks in a real (headless) browser for behaviour the API tests can't see. The app must be running
 * (python run.py), with the demo accounts.
 *
 *   node scripts/browser_checks.js
 *
 * Exits with code 1 if any check fails.
 */
const { goto, openChrome, signIn, waitFor } = require("./browser");

const CHECKS = {
  /** Review B4: an expired or withdrawn login sends the user to the sign-in page with a reason. */
  async "an ended session returns to the sign-in page with a message"(c) {
    await signIn(c, "hr");
    if (await c.evaluate("location.pathname") !== "/") throw new Error("sign-in failed");
    await c.evaluate(`localStorage.setItem("token", "no-longer-valid")`);  // as if it expired or was withdrawn
    await goto(c, "/employees");
    const ok = await waitFor(c, `location.pathname === "/login" && /session has ended/i.test(document.body.innerText)`);
    if (!ok) throw new Error(`stayed on ${await c.evaluate("location.pathname")}: ${(await c.evaluate("document.body.innerText")).slice(0, 120)}`);
  },

  /** Review S1: the website keeps no report keys, and there is no "My report keys" page. */
  async "no report keys page and nothing saved in the browser"(c) {
    await signIn(c, "employee");
    if (await c.evaluate("location.pathname") !== "/") throw new Error("sign-in failed");
    const menu = await c.evaluate("document.body.innerText");
    if (/My report keys/.test(menu)) throw new Error("the menu still offers My report keys");
    await goto(c, "/report-keys");
    if (await c.evaluate("location.pathname") === "/report-keys") throw new Error("the page still exists");
    const stored = await c.evaluate("Object.keys(localStorage).filter((k) => k.startsWith('report-'))");
    if (stored.length) throw new Error(`report data in the browser: ${stored}`);
  },

  /** Phase 4: the three feedback routes, end to end, through the pages a person uses. */
  async "an employee responds to their explanation and HR acts on it"(c) {
    const click = (selector, text) => c.evaluate(`(() => {
      const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find((e) => e.innerText.includes(${JSON.stringify(text)}));
      if (!el) return false; el.click(); return true; })()`);
    const type = (selector, value) => c.evaluate(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      const proto = el.tagName === "SELECT" ? HTMLSelectElement : el.tagName === "TEXTAREA" ? HTMLTextAreaElement : HTMLInputElement;
      Object.getOwnPropertyDescriptor(proto.prototype, "value").set.call(el, ${JSON.stringify(String(value))});
      el.dispatchEvent(new Event(el.tagName === "SELECT" ? "change" : "input", { bubbles: true })); })()`);
    const call = (path, method = "GET", body) => c.evaluate(`fetch("/api${path}", { method: ${JSON.stringify(method)},
      headers: { Authorization: "Bearer " + localStorage.getItem("token"), "Content-Type": "application/json" },
      body: ${body ? JSON.stringify(JSON.stringify(body)) : "undefined"} }).then((r) => r.json())`);

    // The manager nominates the demo employee (the record the employee login is linked to), so HR's review shows
    // the committee note later
    await signIn(c, "employee");
    const me = (await call("/auth/me")).employee_id;
    await signIn(c, "manager");
    const nomination = await call("/promotion/nominations", "POST", {
      employee_id: me, proposed_title: "Senior Analyst", proposed_start: new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10),
      criteria: Object.fromEntries(["performance", "leadership", "skills", "impact"].map((k) => [k, { rating: 4, example: `A clear example of ${k} this year.` }])),
      reason: "Led the migration project this year.", model_disagreement: "Strong client feedback the data doesn't capture.", proposed_raise: 8 });
    if (!nomination.id) throw new Error(`nomination failed: ${JSON.stringify(nomination)}`);

    // 1. Rate the explanation
    await signIn(c, "employee");
    await goto(c, "/my-readiness");
    await click("button", "Run prediction");
    if (!(await waitFor(c, `document.body.innerText.includes("Respond to this explanation")`, 20000))) throw new Error("no respond panel after running the prediction");
    await click(".agree-option span", "4");  // clarity
    await c.evaluate(`document.querySelectorAll('input[name="usefulness"]')[4].click()`);
    await click("button", "Save my rating");
    if (!(await waitFor(c, `document.body.innerText.includes("Your rating is saved")`))) throw new Error("the rating wasn't saved");

    // 2. Ask HR to correct a value
    await click("[role=tab]", "Correct my record");
    if (!(await waitFor(c, `document.querySelector(".respond-body select")`))) throw new Error("no correction form");
    await type(".respond-body select", "projects_completed");
    const current = Number((await c.evaluate(`document.querySelector(".respond-body .field-hint").innerText`)).match(/[\d.]+/)[0]);
    await type('.respond-body input[type="number"]', current + 3);
    await type(".respond-body textarea", "My signed review form lists more completed projects.");
    await click("button", "Send to HR");
    if (!(await waitFor(c, `document.body.innerText.includes("Waiting for HR")`))) throw new Error("the request wasn't listed as waiting");

    // 3. Report anonymously: the link opens the report form with the category chosen
    await click("[role=tab]", "Report anonymously");
    await click("a", "Report an unfair assessment");
    if (!(await waitFor(c, `location.pathname === "/report" && document.querySelector("select")?.value === "biased_rating"`))) {
      throw new Error("the report form didn't open with 'Biased rating or appraisal' chosen");
    }

    // HR: the committee note on the nomination, then the queue
    await signIn(c, "hr");
    await goto(c, `/nominations/${nomination.id}`);
    if (!(await waitFor(c, `document.body.innerText.includes("a record correction is pending")`))) throw new Error("no committee note");
    await click("button", "Hold the decision");
    if (!(await waitFor(c, `document.body.innerText.includes("on hold")`))) throw new Error("the decision wasn't put on hold");
    await goto(c, "/corrections");
    await click("button", "Confirm and correct");
    if (!(await waitFor(c, `document.body.innerText.includes("Nothing waiting")`))) throw new Error("the correction wasn't confirmed");
    const note = await call(`/hr/feedback/nominations/${nomination.id}/note`);
    if (note.deferred) throw new Error("the hold wasn't lifted when the correction was resolved");

    // The employee is told
    await signIn(c, "employee");
    await c.evaluate(`document.querySelector(".bell button").click()`);
    if (!(await waitFor(c, `document.body.innerText.includes("HR corrected your record")`))) throw new Error("no notification for the employee");
  },

  /** No dead links or broken pages: every menu page opens for every role, without errors. */
  async "every menu page opens for every role"(first) {
    const problems = [];
    first.close();
    for (const role of ["employee", "manager", "hr", "admin", "finance", "auditor"]) {
      const c = await openChrome();  // a fresh browser per role, so nothing carries over from the last one
      const roleStarted = Date.now();
      try {
      await signIn(c, role);
      if (await c.evaluate("location.pathname") === "/login") { problems.push(`${role}: can't sign in`); continue; }
      // Open every menu group first: a closed group's pages aren't on the page, so they'd be missed
      await c.evaluate(`document.querySelectorAll('nav .nav-group-head[aria-expanded="false"]').forEach((b) => b.click())`);
      const links = await c.evaluate(`[...new Set([...document.querySelectorAll("nav a[href^='/']")].map((a) => a.getAttribute("href")))]`);
      if (process.env.VERBOSE) console.log(`    ${role}: ${links.length} pages: ${links.join(" ")}`);
      for (const link of links) {
        const before = c.errors.length;
        const started = Date.now();
        await goto(c, link);
        if (process.env.VERBOSE) console.log(`    ${role} ${link}: ${Date.now() - started} ms`);
        const text = await c.evaluate("document.body.innerText");
        const shown = await c.evaluate(`[...document.querySelectorAll(".alert-error")].map((e) => e.innerText).join(" | ")`);
        if (/Not available|Something went wrong on this page/.test(text)) problems.push(`${role} ${link}: page not available or broken`);
        if (shown) problems.push(`${role} ${link}: error shown: ${shown.slice(0, 100)}`);
        if (c.errors.length > before) problems.push(`${role} ${link}: script error: ${c.errors.slice(before).join("; ").slice(0, 120)}`);
      }
      } finally {
        c.close();
        if (process.env.VERBOSE) console.log(`    ${role} done in ${Math.round((Date.now() - roleStarted) / 1000)} s`);
      }
    }
    if (problems.length) throw new Error(`\n    ${problems.join("\n    ")}`);
  },
};

(async () => {
  let failed = 0;
  // Optional: only the checks whose name contains this text, e.g.  node scripts/browser_checks.js "menu page"
  const only = process.argv[2];
  for (const [name, check] of Object.entries(CHECKS).filter(([n]) => !only || n.includes(only))) {
    const c = await openChrome();
    try {
      await check(c);
      console.log(`  pass  ${name}`);
    } catch (err) {
      failed += 1;
      console.log(`  FAIL  ${name}: ${err.message}`);
    } finally {
      c.close();
    }
  }
  console.log(failed ? `\n${failed} browser check(s) failed.` : "\nAll browser checks passed.");
  process.exit(failed ? 1 : 0);
})();
