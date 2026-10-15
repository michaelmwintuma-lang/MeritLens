import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Calls to /api go to the FastAPI backend on port 8000. API_URL points them elsewhere (the browser checks run a
// throwaway copy of the app, as a production build served by `vite preview`, on other ports: scripts/browser_test.py).
const proxy = { "/api": process.env.API_URL || "http://127.0.0.1:8000" };

// The production build's security headers (deploy/Caddyfile sets the same in a real deployment). Not in development:
// Vite's live reloading needs inline scripts the policy would block. Inline styles are allowed for computed widths.
const SECURITY_HEADERS = {
  "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    + "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "same-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, proxy },
  preview: { host: "127.0.0.1", proxy, headers: SECURITY_HEADERS },
});
