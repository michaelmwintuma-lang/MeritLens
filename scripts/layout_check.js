#!/usr/bin/env node
/**
 * Checks that every page fits every screen, from a small phone to a wide monitor, on a throwaway copy of the app:
 *
 *   python scripts/browser_test.py scripts/layout_check.js [folder for screenshots]
 *
 * For each page and each width (320 to 1920 px) it reports:
 * - anything wider than the screen (the page scrolls sideways, or part of it is cut off);
 * - text cut off without an ellipsis;
 * - the open menus (notifications, profile, the phone menu) reaching past the edge of the screen;
 * - on phones, buttons and fields too small to tap (under 32 px) and text under 12 px.
 * A table that scrolls sideways inside its own box is expected on a phone and is not reported.
 * Exits with code 1 if anything is wider than the screen or a menu doesn't fit.
 */
const fs = require("fs");
const path = require("path");
const { goto, openChrome, signIn, sleep, waitFor } = require("./browser");
const { RUN, setUpDemo } = require("./demo_setup");

const SHOTS = process.argv[2] ? path.resolve(__dirname, "..", process.argv[2]) : null;

// [width, height, phone?]
const SCREENS = [[320, 640, true], [360, 740, true], [390, 844, true], [768, 1024, false], [1024, 768, false],
  [1440, 900, false], [1920, 1080, false]];

// [name, who signs in (null: nobody), address, optional script run on the page first]
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
  ["hr-review-cycles", "hr", "/cycles"],
  ["hr-cycle-report", "hr", "/cycles/{cycle}/report"],
  ["hr-teams", "hr", "/teams"],
  ["hr-predict-explain", "hr", "/employees/{employee}", RUN],
  ["hr-employee-new", "hr", "/employees/new"],
  ["hr-employee-import", "hr", "/employees/import"],
  ["hr-nominations", "hr", "/nominations"],
  ["hr-review-pending-correction", "hr", "/nominations/{held}"],
  ["hr-review-approved", "hr", "/nominations/{approved}"],
  ["hr-corrections", "hr", "/corrections"],
  ["hr-feedback-dashboard", "hr", "/feedback"],
  ["hr-decisions", "hr", "/decisions"],
  ["hr-model-registry", "hr", "/models"],
  ["hr-live-fairness", "hr", "/fairness"],
  ["hr-approvals", "hr", "/approvals"],
  ["finance-home", "finance", "/"],
  ["finance-sign-off", "finance", "/finance"],
  ["auditor-home", "auditor", "/"],
  ["auditor-decisions", "auditor", "/decisions"],
  ["auditor-audit-trail", "auditor", "/audit"],
  ["auditor-feedback", "auditor", "/feedback"],
  ["auditor-model", "auditor", "/model"],
  ["admin-home", "admin", "/"],
  ["admin-users", "admin", "/admin/users"],
  ["admin-activity", "admin", "/admin/activity"],
  ["admin-email", "admin", "/admin/email"],
  ["admin-demo-requests", "admin", "/admin/demo-requests"],
  ["admin-user-study", "admin", "/admin/study"],
];

// Runs in the page: what doesn't fit. Returns { overflow, wide, clipped, small, tiny }.
const MEASURE = `(() => {
  const W = innerWidth;
  const name = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    else if (typeof el.className === "string" && el.className.trim()) s += "." + el.className.trim().split(/\\s+/).slice(0, 2).join(".");
    const text = (el.innerText || el.value || el.getAttribute("aria-label") || "").trim().replace(/\\s+/g, " ").slice(0, 40);
    return text ? s + ' "' + text + '"' : s;
  };
  const hidden = (el) => { for (let e = el; e; e = e.parentElement) {
    const st = getComputedStyle(e);
    if (st.display === "none" || st.visibility === "hidden" || e.classList?.contains("visually-hidden")) return true;
    if (e.classList?.contains("sidebar") && !e.classList.contains("open") && innerWidth < 640) return true;
  } return false; };
  // Inside a box that scrolls or clips sideways (a table that scrolls, for example)
  const inScroller = (el) => { for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
    const ox = getComputedStyle(e).overflowX;
    if (ox === "auto" || ox === "scroll" || ox === "hidden" || ox === "clip") return true;
  } return false; };
  const all = [...document.body.querySelectorAll("*")];
  const wide = new Set();
  for (const el of all) {
    if (el.tagName === "svg" || el.closest("svg") && el.tagName !== "svg") continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if ((r.right > W + 1 || r.left < -1) && !inScroller(el) && !hidden(el)) wide.add(el);
  }
  // Only the outermost of each set of nested elements that don't fit
  const outermost = [...wide].filter((el) => !wide.has(el.parentElement)).map((el) => {
    const r = el.getBoundingClientRect(); return name(el) + " [" + Math.round(r.left) + ".." + Math.round(r.right) + "]"; });
  const clipped = [];
  for (const el of all) {
    const st = getComputedStyle(el);
    if (!["hidden", "clip"].includes(st.overflowX) || st.textOverflow === "ellipsis" || hidden(el)) continue;
    if (el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0 && (el.innerText || "").trim()
        && !el.classList.contains("card") && !el.matches(".flush, .table-wrap, .bar-track, .stacked, .contribution-bar, .run-all-track, .scorebar-track"))
      clipped.push(name(el) + " (" + el.scrollWidth + " > " + el.clientWidth + ")");
  }
  const small = [], tiny = [];
  if (W < 640) {
    for (const el of document.querySelectorAll("button, a.btn, input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]), select, [role=menuitem]")) {
      if (hidden(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width && (r.height < 32 || r.width < 32)) small.push(name(el) + " (" + Math.round(r.width) + "x" + Math.round(r.height) + ")");
    }
    const seen = new Set();
    for (const el of all) {
      if (hidden(el) || !el.childNodes.length || ![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
      const size = parseFloat(getComputedStyle(el).fontSize);
      if (size < 12 && !seen.has(size + el.tagName)) { seen.add(size + el.tagName); tiny.push(name(el) + " (" + size + "px)"); }
    }
  }
  return { overflow: document.documentElement.scrollWidth - W, wide: outermost.slice(0, 8), clipped: clipped.slice(0, 8),
    small: small.slice(0, 8), tiny: tiny.slice(0, 5) };
})()`;

// Runs in the page: whether an open panel fits on the screen
const FITS = (selector) => `(() => {
  const el = document.querySelector(${JSON.stringify(selector)});
  if (!el) return "not found";
  const r = el.getBoundingClientRect();
  const out = [];
  if (r.left < -1) out.push("left edge at " + Math.round(r.left));
  if (r.right > innerWidth + 1) out.push("right edge at " + Math.round(r.right) + " of " + innerWidth);
  if (r.bottom > innerHeight + 1 && getComputedStyle(el).position === "fixed") out.push("bottom at " + Math.round(r.bottom) + " of " + innerHeight);
  if (r.bottom > innerHeight + 1 && el.scrollHeight <= el.clientHeight + 1 && r.height > innerHeight * 0.6) out.push("taller than the screen (" + Math.round(r.height) + " of " + innerHeight + ")");
  return out.length ? out.join(", ") : "ok";
})()`;

const click = (selector) => `(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (el) { el.click(); return true; } return false; })()`;
const press = (key) => `document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: ${JSON.stringify(key)}, bubbles: true }))`;

async function screen(c, width, height, phone) {
  await c.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: phone });
  await c.send("Emulation.setTouchEmulationEnabled", { enabled: phone });
}

async function shot(c, file) {
  const res = await c.send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(file, Buffer.from(res.result.data, "base64"));
}

/** The menus that open over the page: the notifications, the profile menu and, on a phone, the menu drawer. */
async function checkPanels(c, width, label) {
  const problems = [];
  const panels = [[".bell .icon-btn", ".bell-panel", "notifications"], [".profile-button", ".menu-panel", "profile menu"]];
  for (const [button, panel, what] of panels) {
    if (!(await c.evaluate(click(button)))) continue;
    await sleep(250);
    const fits = await c.evaluate(FITS(panel));
    if (fits !== "ok") problems.push(`${what}: ${fits}`);
    if (SHOTS && width < 640) await shot(c, path.join(SHOTS, `${label}-${width}-${what.replace(/ /g, "-")}.png`));
    await c.evaluate(`document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
    await sleep(100);
  }
  if (width < 640 && await c.evaluate(click(".menu-button"))) {
    await sleep(400);
    const fits = await c.evaluate(FITS(".sidebar"));
    if (fits !== "ok") problems.push(`menu drawer: ${fits}`);
    await c.evaluate(click(".drawer-close"));
    await sleep(300);
  }
  return problems;
}

(async () => {
  if (SHOTS) fs.mkdirSync(SHOTS, { recursive: true });
  const ids = await setUpDemo();
  const report = {};
  let failures = 0;
  let current;
  let c = await openChrome();
  const panelsDone = new Set();
  for (const [name, who, raw, action] of PAGES) {
    const address = raw.replace(/\{(\w+)\}/g, (_, k) => ids[k] ?? "");
    if (who !== current) {
      c.close();
      c = await openChrome();
      await screen(c, 1366, 900, false);
      if (who) await signIn(c, who);
      current = who;
    }
    const found = {};
    for (const [width, height, phone] of SCREENS) {
      await screen(c, width, height, phone);
      await goto(c, address);
      if (action) {
        await c.evaluate(action);
        await waitFor(c, `!document.querySelector('[aria-busy="true"]')`, 30000);
        await sleep(1200);
      }
      const m = await c.evaluate(MEASURE);
      if (!m) { found[width] = { error: "could not measure" }; continue; }
      const entry = {};
      if (m.overflow > 1) entry.overflow = m.overflow;
      for (const k of ["wide", "clipped", "small", "tiny"]) if (m[k].length) entry[k] = m[k];
      if (who && !panelsDone.has(`${who}-${width}`)) {
        panelsDone.add(`${who}-${width}`);
        const p = await checkPanels(c, width, who);
        if (p.length) entry.panels = p;
      }
      if (SHOTS && phone) await shot(c, path.join(SHOTS, `${name}-${width}.png`));
      if (Object.keys(entry).length) found[width] = entry;
      if (entry.overflow || entry.wide || entry.panels) failures++;
    }
    report[name] = found;
    const widths = Object.entries(found);
    console.log(`  ${name.padEnd(30)} ${widths.length ? "" : "fits everywhere"}`);
    for (const [w, e] of widths) {
      for (const [k, v] of Object.entries(e)) console.log(`      ${String(w).padStart(4)}px ${k}: ${Array.isArray(v) ? v.join(" | ") : v}`);
    }
  }
  c.close();
  if (SHOTS) fs.writeFileSync(path.join(SHOTS, "layout.json"), JSON.stringify(report, null, 2));
  console.log(failures ? `\n${failures} page view(s) don't fit the screen.` : "\nEvery page fits every screen.");
  process.exit(failures ? 1 : 0);
})().catch((err) => { console.error(`Layout check failed: ${err.message}`); process.exit(1); });
