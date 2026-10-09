import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Calls to /api go to the FastAPI backend on port 8000. API_URL points them elsewhere (the browser checks run a
// throwaway copy of the app, as a production build served by `vite preview`, on other ports: scripts/browser_test.py).
const proxy = { "/api": process.env.API_URL || "http://127.0.0.1:8000" };

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, proxy },
  preview: { host: "127.0.0.1", proxy },
});
