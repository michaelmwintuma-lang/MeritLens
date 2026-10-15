// Entry point: mounts the app.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./auth";
import App from "./App";
import { ToastProvider } from "./components/Toast";
// Montserrat, installed locally (npm), so no font is loaded from Google's servers
import "@fontsource-variable/montserrat";
import "./styles.css";
import "./theme"; // applies the saved light/dark choice before the first paint

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
