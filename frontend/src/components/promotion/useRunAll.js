// "Run predictions for everyone": asks the live model to score every employee the user may see, and paces the
// result over RUN_MS so people can watch it work through the list. The model itself answers in milliseconds; the
// pace is only for the display, and the page never claims the run took longer than it did.
import { useEffect, useRef, useState } from "react";
import { api } from "../../api";

export const RUN_MS = 5000;

// The last run, kept while the app is open, so coming back to the page shows it instead of "not run yet"
let lastRun = null;

export function useRunAll(userId) {
  const [run, setRun] = useState(() => (lastRun?.userId === userId
    ? { status: "done", progress: 1, result: lastRun.result, error: "" }
    : { status: "idle", progress: 0, result: null, error: "" }));
  const frame = useRef(0);
  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  async function start() {
    const outcome = { result: null, error: "" };
    const started = performance.now();
    setRun({ status: "running", progress: 0, result: null, error: "" });
    api("/promotion/employees/predict-all", { method: "POST" })
      .then((result) => { outcome.result = result; setRun((s) => ({ ...s, result })); })
      .catch((err) => { outcome.error = err.message || "The predictions couldn't be run."; });

    // Move through the list over RUN_MS; if the answer is somehow slower, wait at 99% until it arrives
    await new Promise((resolve) => {
      const tick = (now) => {
        if (outcome.error) return resolve();
        const progress = Math.min((now - started) / RUN_MS, outcome.result ? 1 : 0.99);
        setRun((s) => ({ ...s, progress }));
        if (progress < 1) frame.current = requestAnimationFrame(tick);
        else resolve();
      };
      frame.current = requestAnimationFrame(tick);
    });

    if (outcome.error) {
      setRun({ status: "error", progress: 0, result: null, error: outcome.error });
      return;
    }
    lastRun = { userId, result: outcome.result };
    setRun({ status: "done", progress: 1, result: outcome.result, error: "" });
  }

  return [run, start];
}
