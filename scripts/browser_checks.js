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
    // The session is withdrawn on the server (as when it expires, or the password is changed elsewhere) while the
    // page is open; then the person moves to another page inside the app
    await c.evaluate(`fetch("/api/auth/logout", { method: "POST", headers: { "X-Requested-With": "MeritLens" } })`);
    await c.evaluate(`history.pushState({}, "", "/employees"); dispatchEvent(new PopStateEvent("popstate"))`);
    const ok = await waitFor(c, `location.pathname === "/login" && /session has ended/i.test(document.body.innerText)`);
    if (!ok) throw new Error(`stayed on ${await c.evaluate("location.pathname")}: ${(await c.evaluate("document.body.innerText")).slice(0, 120)}`);
  },

  /** Phase 4: the two feedback routes, end to end, through the pages a person uses. */
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
      headers: { "X-Requested-With": "MeritLens", "Content-Type": "application/json" },
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
    await click("button[aria-pressed]", "Correct my record");
    if (!(await waitFor(c, `document.querySelector(".respond-body select")`))) throw new Error("no correction form");
    await type(".respond-body select", "projects_completed");
    const current = Number((await c.evaluate(`document.querySelector(".respond-body .field-hint").innerText`)).match(/[\d.]+/)[0]);
    await type('.respond-body input[type="number"]', current + 3);
    await type(".respond-body textarea", "My signed review form lists more completed projects.");
    await click("button", "Send to HR");
    if (!(await waitFor(c, `document.body.innerText.includes("Waiting for HR")`))) throw new Error("the request wasn't listed as waiting");

    // Only these two routes are offered
    const tabs = await c.evaluate(`[...document.querySelectorAll("button[aria-pressed]")].map((b) => b.innerText)`);
    if (JSON.stringify(tabs) !== JSON.stringify(["Rate this explanation", "Correct my record"])) throw new Error(`the respond panel offers ${tabs}`);

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

  /** Phase 5: the dashboards show the live numbers, with filters and small groups protected. */
  async "the feedback dashboard and the admin dashboard show live data"(c) {
    const text = () => c.evaluate("document.body.innerText");
    await signIn(c, "hr");
    await goto(c, "/feedback");
    if (!(await waitFor(c, `document.body.innerText.includes("Factors employees contest")`))) throw new Error("the feedback dashboard didn't load");
    const fromApi = await c.evaluate(`fetch("/api/feedback/dashboard", { headers: { "X-Requested-With": "MeritLens" } }).then((r) => r.json())`);
    // Stat labels are shown in capitals by the style sheet, so compare without regard to case
    if (!new RegExp(`received\\s+${fromApi.corrections.received}\\b`, "i").test(await text())) throw new Error("the corrections count isn't the server's");
    // Filter by a department: the page asks the server again and still shows the dashboard
    const department = fromApi.options.departments[0];
    await c.evaluate(`(() => { const s = [...document.querySelectorAll("select")].find((e) => [...e.options].some((o) => o.text === "All departments"));
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set.call(s, ${JSON.stringify(department)});
      s.dispatchEvent(new Event("change", { bubbles: true })); })()`);
    if (!(await waitFor(c, `document.body.innerText.includes("Factors employees contest") && !document.querySelector(".alert-error")`))) {
      throw new Error("the department filter broke the dashboard");
    }
    await signIn(c, "auditor");
    await goto(c, "/feedback");
    if (!(await waitFor(c, `document.body.innerText.includes("Record corrections")`))) throw new Error("the auditor can't see the feedback dashboard");

    await signIn(c, "admin");
    await goto(c, "/");
    if (!(await waitFor(c, `document.body.innerText.includes("System health") && document.body.innerText.includes("Drift")`))) {
      throw new Error("the admin dashboard has no system health or drift");
    }
    const system = await c.evaluate(`fetch("/api/admin/system", { headers: { "X-Requested-With": "MeritLens" } }).then((r) => r.json())`);
    if (!(await text()).includes(system.model.version)) throw new Error("the admin dashboard doesn't show the live model version");
  },

  /** Phase 6: the landing page describes predict, explain, respond, and its "Sign in" leads to the app. */
  async "the landing page leads to sign-in"(c) {
    await goto(c, "/");
    // Wait until the page has drawn itself, rather than reading it the moment navigation ends
    if (!(await waitFor(c, `document.body.innerText.includes("How it works")`))) throw new Error("the landing page didn't render");
    const text = await c.evaluate("document.body.innerText");
    for (const part of ["Fair, explainable promotion decisions", "How it works", "Predict", "Explain", "Respond",
      "Explainable predictions", "Path to promotion", "Fairness audit", "Employee feedback channel", "Accountable records",
      "People decide", "A complaint never changes a score", "A wrong record can be put right", "People make every decision",
      "Design and Development of an Explainable Machine Learning"]) {
      if (!text.includes(part)) throw new Error(`the landing page is missing "${part}"`);
    }
    // The screenshots load lazily (only when scrolled to), so ask for each one directly and check it is an image
    const images = await c.evaluate(`Promise.all([...document.images].map((i) => fetch(i.src)
      .then((r) => ({ src: i.src, ok: r.ok && (r.headers.get("content-type") || "").startsWith("image/") }))))`);
    if (images.length === 0) throw new Error("the landing page shows no screenshots");
    const broken = images.filter((i) => !i.ok).map((i) => i.src);
    if (broken.length) throw new Error(`images that don't load: ${broken}`);
    if (/anonym|report a concern|reporter/i.test(text)) throw new Error("the landing page still mentions anonymous reporting");
    await c.evaluate(`[...document.querySelectorAll(".intro-actions a")].find((a) => a.innerText.includes("Sign in")).click()`);
    if (!(await waitFor(c, `location.pathname === "/login"`))) throw new Error("Sign in didn't lead to the sign-in page");
    await c.evaluate(`(() => {
      const set = (el, v) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, v); el.dispatchEvent(new Event("input", { bubbles: true })); };
      set(document.getElementById("login-username"), "employee"); set(document.getElementById("login-password"), "demo1234");
      document.querySelector("form").requestSubmit(); })()`);
    if (!(await waitFor(c, `location.pathname === "/" && document.body.innerText.includes("My growth")`))) {
      throw new Error(`after signing in, the employee landed on ${await c.evaluate("location.pathname")}, not their overview`);
    }
  },

  /** "Run predictions for everyone": progress while it runs (about 5 seconds), then every row has its score. */
  async "running predictions for everyone animates, then shows every score"(c) {
    await signIn(c, "hr");
    await goto(c, "/employees");
    if (!(await waitFor(c, `document.body.innerText.includes("Not run yet")`))) throw new Error("the list didn't start as 'not run yet'");
    const started = Date.now();
    await c.evaluate(`[...document.querySelectorAll("button")].find((b) => b.innerText.startsWith("Run predictions for all")).click()`);
    if (!(await waitFor(c, `document.querySelector('[role="progressbar"]')`, 3000))) throw new Error("no progress bar while running");
    if (!(await waitFor(c, `document.querySelectorAll(".just-scored").length > 0 && document.querySelectorAll(".score-pending").length > 0`, 4000))) {
      throw new Error("the rows weren't revealed one by one");
    }
    if (!(await waitFor(c, `document.body.innerText.includes("Predictions for 120 employees")`, 15000))) throw new Error("the run didn't finish");
    const seconds = (Date.now() - started) / 1000;
    if (seconds < 4.5) throw new Error(`the run finished in ${seconds.toFixed(1)} s, not about 5`);
    const missing = await c.evaluate(`[...document.querySelectorAll("tbody tr")].filter((r) => !/\\d+%|under 1%/.test(r.innerText)).length`);
    if (missing) throw new Error(`${missing} rows have no score after the run`);
  },

  /** Phase 8: long lists come a page at a time. */
  async "the employee list shows 50 people at a time"(c) {
    await signIn(c, "hr");
    await goto(c, "/employees");
    await waitFor(c, `document.querySelectorAll("tbody tr").length > 0`);
    const first = await c.evaluate(`document.querySelectorAll("tbody tr").length`);
    if (first !== 50) throw new Error(`the first page shows ${first} rows, not 50`);
    await c.evaluate(`[...document.querySelectorAll(".pager button")].find((b) => b.innerText === "Next").click()`);
    if (!(await waitFor(c, `document.querySelector(".pager").innerText.includes("51–100")`))) throw new Error("Next didn't show 51–100");
  },

  /**
   * No dead links or broken pages: every menu page opens for every role, without errors. Anonymous reporting was
   * removed, so no page may mention it, and its old addresses lead back to the overview.
   */
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
        const mention = text.match(/anonymous|report inbox|reporter|case id|report a concern|report an unfair/i);
        if (mention) problems.push(`${role} ${link}: mentions reporting ("${mention[0]}")`);
      }
      for (const old of ["/report", "/my-report", "/reports"]) {
        await goto(c, old);
        // The app first asks the server who is signed in, then redirects: allow a busy machine a few seconds
        if (!(await waitFor(c, `location.pathname === "/"`, 10000))) problems.push(`${role}: ${old} still opens`);
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
