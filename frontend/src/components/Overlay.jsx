// Modal and Drawer: a panel over the page. Escape or the close button closes it, Tab stays inside it while open,
// and focus goes back to whatever opened it. The Drawer slides in from the right; the Modal sits in the middle;
// useConfirm asks a yes-or-no question in a Modal.
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Close on Escape and keep Tab inside `box` while it's open. Shared with the sidebar drawer on phones. */
export function useFocusTrap(box, open, onClose) {
  useEffect(() => {
    if (!open) return undefined;
    const opener = document.activeElement;
    (box.current?.querySelector("[data-autofocus]") || box.current?.querySelector(FOCUSABLE))?.focus();
    function onKey(e) {
      if (e.key === "Escape") { e.stopPropagation(); onClose(); return; }
      if (e.key !== "Tab" || !box.current) return;
      const items = [...box.current.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null);
      if (!items.length) return;
      const [first, last] = [items[0], items[items.length - 1]];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
}

function Overlay({ kind, open, onClose, title, subtitle, children }) {
  const box = useRef(null);
  const titleId = useId();
  useFocusTrap(box, open, onClose);
  if (!open) return null;
  return createPortal(
    <div className={`modal-layer ${kind === "drawer" ? "drawer-layer" : ""}`}>
      <div className="scrim" onClick={onClose} aria-hidden="true" />
      <div ref={box} className={kind} role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="overlay-head">
          <div>
            <h2 id={titleId}>{title}</h2>
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} aria-hidden="true" /></button>
        </div>
        <div className="overlay-body">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

export const Modal = (props) => <Overlay kind="modal" {...props} />;
export const Drawer = (props) => <Overlay kind="drawer" {...props} />;

/**
 * Ask before something that can't easily be undone, in a modal instead of the browser's own box:
 *   const [confirm, dialog] = useConfirm();   ...   if (!(await confirm({ title, text, action }))) return;   ...   {dialog}
 * `danger` makes the confirming button red. Resolves true (confirmed) or false (cancelled, Escape, or the scrim).
 */
export function useConfirm() {
  const [ask, setAsk] = useState(null); // { title, text, action, danger, resolve }
  const answer = (value) => { ask?.resolve(value); setAsk(null); };
  const confirm = (question) => new Promise((resolve) => setAsk({ ...question, resolve }));
  const dialog = (
    <Modal open={Boolean(ask)} onClose={() => answer(false)} title={ask?.title || ""}>
      {ask && <>
        <p>{ask.text}</p>
        <div className="form-actions section-gap">
          <button type="button" className={`btn ${ask.danger ? "btn-danger" : "btn-primary"}`} onClick={() => answer(true)} data-autofocus>{ask.action}</button>
          <button type="button" className="btn btn-secondary" onClick={() => answer(false)}>Cancel</button>
        </div>
      </>}
    </Modal>
  );
  return [confirm, dialog];
}
