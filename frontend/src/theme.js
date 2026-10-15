// Light (white) or dark appearance. White is the default for everyone, whatever the computer's own setting; dark is
// there for whoever switches it on, and that choice is remembered in this browser only.
import { useEffect, useState } from "react";

// A new key: choices saved before white became the default (including "follow the computer") don't carry over
const KEY = "appearance";

function initialTheme() {
  try {
    if (localStorage.getItem(KEY) === "dark") return "dark";
  } catch { /* storage unavailable */ }
  return "light";
}

// One shared value, so every toggle on the page stays in step
let current = initialTheme();
const listeners = new Set();
document.documentElement.dataset.theme = current;

export function useTheme() {
  const [theme, setTheme] = useState(current);
  useEffect(() => {
    listeners.add(setTheme);
    return () => listeners.delete(setTheme);
  }, []);

  function toggle() {
    current = current === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = current;
    try { localStorage.setItem(KEY, current); } catch { /* not remembered: fine */ }
    listeners.forEach((set) => set(current));
  }

  return { theme, toggle };
}
