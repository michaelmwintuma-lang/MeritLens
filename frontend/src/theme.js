// Light or dark appearance. The choice is remembered in this browser only.
import { useEffect, useState } from "react";

const KEY = "theme";

function initialTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch { /* storage unavailable */ }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
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
