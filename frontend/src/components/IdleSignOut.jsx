// Signing out after a while without use, so a computer left signed in doesn't stay open to anyone passing. After
// IDLE_MINUTES without a key press, click, scroll or touch, a warning gives WARN_SECONDS to stay; then the session
// ends (on the server too) and the sign-in page explains why.
import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth";
import { Modal } from "./Overlay";

const IDLE_MINUTES = 30;
const WARN_SECONDS = 120;
const EVENTS = ["keydown", "pointerdown", "wheel", "touchstart"];

export default function IdleSignOut() {
  const { logout } = useAuth();
  const [left, setLeft] = useState(null); // seconds until sign-out, while warning
  const last = useRef(Date.now());

  useEffect(() => {
    const active = () => { if (left == null) last.current = Date.now(); };
    EVENTS.forEach((e) => window.addEventListener(e, active, { passive: true }));
    const timer = setInterval(() => {
      const idle = (Date.now() - last.current) / 1000;
      const remaining = Math.ceil(IDLE_MINUTES * 60 + WARN_SECONDS - idle);
      if (remaining <= 0) logout();
      else if (remaining <= WARN_SECONDS) setLeft(remaining);
    }, 1000);
    return () => { EVENTS.forEach((e) => window.removeEventListener(e, active)); clearInterval(timer); };
  }, [left, logout]);

  function stay() {
    last.current = Date.now();
    setLeft(null);
  }

  return (
    <Modal open={left != null} onClose={stay} title="Are you still there?">
      <p>For your security, you'll be signed out in <strong className="num">{left}</strong> seconds because nothing has happened for a while.</p>
      <div className="form-actions section-gap">
        <button type="button" className="btn btn-primary" onClick={stay} data-autofocus>Stay signed in</button>
        <button type="button" className="btn btn-secondary" onClick={logout}>Sign out now</button>
      </div>
    </Modal>
  );
}
