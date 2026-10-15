// Toasts: a short confirmation in the corner after something is done ("Saved", "Signed off"). They go away after a
// few seconds or when closed, and screen readers hear them once.
import { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, CircleAlert, X } from "lucide-react";

const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);
const SHOW_MS = 6000;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const close = (id) => setToasts((all) => all.filter((t) => t.id !== id));

  /** toast("Saved.") or toast("Couldn't save.", "error") */
  const toast = useCallback((text, tone = "success") => {
    const id = Date.now() + Math.random();
    setToasts((all) => [...all, { id, text, tone }]);
    setTimeout(() => close(id), SHOW_MS);
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}`}>
            {t.tone === "error" ? <CircleAlert size={18} aria-hidden="true" /> : <CheckCircle2 size={18} aria-hidden="true" />}
            <p>{t.text}</p>
            <button type="button" className="icon-btn" onClick={() => close(t.id)} aria-label="Dismiss"><X size={16} aria-hidden="true" /></button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
