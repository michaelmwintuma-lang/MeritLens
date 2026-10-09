/**
 * A small driver for a headless Chrome, used by the browser checks and the screenshot script. It talks to Chrome
 * over the DevTools protocol directly, so it needs no npm packages (Node 22+). The app must be running
 * (python run.py).
 */
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const BASE = process.env.APP_URL || "http://127.0.0.1:5173";
const CHROME = process.env.CHROME_PATH || (process.platform === "win32"
  ? "C:/Program Files/Google/Chrome/Application/chrome.exe" : "google-chrome");
const PASSWORD = process.env.DEMO_PASSWORD || "demo1234";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** A new headless Chrome. Starting can occasionally fail (a busy machine, a port in use), so it tries three times. */
async function openChrome() {
  for (let attempt = 1; ; attempt++) {
    try {
      return await startChrome();
    } catch (err) {
      if (attempt === 3) throw err;
    }
  }
}

async function startChrome() {
  const port = 9300 + Math.floor(Math.random() * 500);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "hr-browser-"));
  const proc = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`, "--window-size=1366,900", "about:blank"], { stdio: "ignore" });
  let wsUrl;
  for (let i = 0; i < 150 && !wsUrl; i++) {  // up to 30 s
    try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page")?.webSocketDebuggerUrl; } catch { /* starting */ }
    if (!wsUrl) await sleep(200);
  }
  if (!wsUrl) {
    proc.kill();
    throw new Error(`Chrome did not start (looked for it at ${CHROME}; set CHROME_PATH to change)`);
  }
  const ws = new WebSocket(wsUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let id = 0;
  const pending = new Map();
  const errors = [];
  ws.addEventListener("message", (e) => {
    const msg = JSON.parse(e.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description?.split("\n")[0] || msg.params.exceptionDetails.text);
  });
  const send = (method, params = {}) => new Promise((r) => { const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  // Run JavaScript in the page. Gives up after 20 s (e.g. if the page navigated away mid-way) instead of hanging.
  const evaluate = async (expression) => {
    const answer = await Promise.race([send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }), sleep(20000)]);
    return answer?.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  return { send, evaluate, errors, close: () => { ws.close(); proc.kill(); } };
}

/** Wait until no "Loading…" text or busy marker has been visible for a moment. */
async function waitIdle(c, maxMs = 15000) {
  const start = Date.now();
  let calm = 0;
  while (Date.now() - start < maxMs) {
    const busy = await c.evaluate(`!!document.querySelector('[aria-busy="true"]') || /Loading…/.test(document.body?.innerText || "")`);
    calm = busy ? 0 : calm + 1;
    if (calm >= 3) return;
    await sleep(250);
  }
}

async function goto(c, pathname) {
  await c.send("Page.navigate", { url: BASE + pathname });
  await sleep(700);
  await waitIdle(c);
}

/** Sign in through the real sign-in page (signing out first, if someone is signed in). */
async function signIn(c, username, password = PASSWORD) {
  let ready = false;
  for (let attempt = 0; attempt < 2 && !ready; attempt++) {
    await goto(c, "/login");
    ready = await waitFor(c, `document.getElementById("login-username")`, 8000);
    if (!ready) await c.evaluate(`localStorage.removeItem("token")`); // someone is signed in: sign out, try again
  }
  if (!ready) throw new Error(`the sign-in page didn't load (at ${await c.evaluate("location.href")})`);
  await c.evaluate(`(() => {
    const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; s.call(el, v); el.dispatchEvent(new Event("input", { bubbles: true })); };
    set(document.getElementById("login-username"), ${JSON.stringify(username)});
    set(document.getElementById("login-password"), ${JSON.stringify(password)});
    document.querySelector("form").requestSubmit();
  })()`);
  for (let i = 0; i < 40; i++) {
    await sleep(250);
    if (!(await c.evaluate("location.pathname")).startsWith("/login")) break;
  }
  await waitIdle(c);
}

/** Wait until a condition (JavaScript, evaluated in the page) is true; returns whether it became true. */
async function waitFor(c, expression, maxMs = 10000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    if (await c.evaluate(`!!(${expression})`)) return true;
    await sleep(200);
  }
  return false;
}

module.exports = { BASE, openChrome, goto, signIn, waitFor, waitIdle, sleep };
