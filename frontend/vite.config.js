import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, calls to /api go to the FastAPI backend on port 8000
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
