// Light or dark appearance. Until someone uses the toggle, the app follows the computer's own setting (and changes
// with it); a choice made with the toggle is remembered in this browser only.
import { useEffect, useState } from "react";

const KEY = "appearance";
const system = typeof window.matchMedia === "function" ? window.matchMedia("(prefers-color-scheme: dark)") : null;

function saved() {
  try {
    const value = localStorage.getItem(KEY);
    return value === "dark" || value === "light" ? value : null;
  } catch {
    return null; // storage unavailable
  }
}

const fromSystem = () => (system?.matches ? "dark" : "light");

// One shared value, so every toggle on the page stays in step
let current = saved() || fromSystem();
const listeners = new Set();

function apply(theme) {
  current = theme;
  document.documentElement.dataset.theme = theme;
  listeners.forEach((set) => set(theme));
}
apply(current);

// Nothing chosen yet: follow the computer when its setting changes
system?.addEventListener?.("change", () => { if (!saved()) apply(fromSystem()); });

export function useTheme() {
  const [theme, setTheme] = useState(current);
  useEffect(() => {
    listeners.add(setTheme);
    return () => listeners.delete(setTheme);
  }, []);

  function toggle() {
    const next = current === "dark" ? "light" : "dark";
    try { localStorage.setItem(KEY, next); } catch { /* not remembered: fine */ }
    apply(next);
  }

  return { theme, toggle };
}
