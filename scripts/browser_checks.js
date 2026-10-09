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

  /** No dead links or broken pages: every menu page opens for every role, without errors. */
  async "every menu page opens for every role"(c) {
    const problems = [];
    for (const role of ["employee", "manager", "hr", "admin", "finance", "auditor"]) {
      await signIn(c, role);
      if (await c.evaluate("location.pathname") === "/login") { problems.push(`${role}: can't sign in`); continue; }
      const links = await c.evaluate(`[...new Set([...document.querySelectorAll("nav a[href^='/']")].map((a) => a.getAttribute("href")))]`);
      for (const link of links) {
        const before = c.errors.length;
        await goto(c, link);
        const text = await c.evaluate("document.body.innerText");
        const shown = await c.evaluate(`[...document.querySelectorAll(".alert-error")].map((e) => e.innerText).join(" | ")`);
        if (/Not available|Something went wrong on this page/.test(text)) problems.push(`${role} ${link}: page not available or broken`);
        if (shown) problems.push(`${role} ${link}: error shown: ${shown.slice(0, 100)}`);
        if (c.errors.length > before) problems.push(`${role} ${link}: script error: ${c.errors.slice(before).join("; ").slice(0, 120)}`);
      }
      await c.evaluate(`localStorage.removeItem("token")`);
    }
    if (problems.length) throw new Error(`\n    ${problems.join("\n    ")}`);
  },
};

(async () => {
  let failed = 0;
  for (const [name, check] of Object.entries(CHECKS)) {
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
