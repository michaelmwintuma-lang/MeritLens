// Run something slow (a request to the server) and know while it's running, so its button can show it.
import { useState } from "react";

export function useAction() {
  const [busy, setBusy] = useState(false);
  async function run(task) {
    setBusy(true);
    try {
      return await task();
    } finally {
      setBusy(false);
    }
  }
  return [busy, run];
}
