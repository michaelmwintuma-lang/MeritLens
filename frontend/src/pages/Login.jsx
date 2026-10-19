// Sign-in page: the wordmark, then a clean centred form.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Eye, EyeOff, Lock, Mail, ShieldCheck, UserRound } from "lucide-react";
import { useAuth } from "../auth";
import { Button, Wordmark } from "../components/ui";
import { BRAND, TAGLINE } from "../brand";
import "./login.css";

export default function Login() {
  const { login, notice } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [code, setCode] = useState("");
  const [needsCode, setNeedsCode] = useState(false); // two-factor sign-in: the password was right
  const [byEmail, setByEmail] = useState(false);     // ...and the code was emailed (not from an authenticator app)
  const [info, setInfo] = useState("");              // where the code went
  const [retryIn, setRetryIn] = useState(0);         // seconds until a new code may be sent
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (retryIn <= 0) return undefined;
    const timer = setTimeout(() => setRetryIn(retryIn - 1), 1000);
    return () => clearTimeout(timer);
  }, [retryIn]);

  // The server asked for a code (the next step, not an error): note how it was sent
  function askForCode(err) {
    setNeedsCode(true);
    setByEmail(err.codeMethod === "email");
    if (err.codeMethod === "email") setInfo(err.message);
    setRetryIn(err.retryIn || 0);
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password, needsCode ? code : undefined);  // the app then moves on from /login (App.jsx: AfterSignIn)
    } catch (err) {
      if (err.codeRequired && !needsCode) {
        askForCode(err);
        return;
      }
      if (err.retryIn !== undefined) setRetryIn(err.retryIn);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // Signing in again without a code sends a new one (the server allows one a minute)
  async function sendNewCode() {
    setBusy(true);
    setError("");
    setCode("");
    try {
      await login(username, password);
    } catch (err) {
      if (err.codeRequired) askForCode(err);
      else setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <Link to="/" className="login-back"><ArrowLeft size={16} aria-hidden="true" />Back to the website</Link>

      <main className="login-main">
        <div className="login-logo"><Wordmark /></div>
        <form className="login-box" onSubmit={submit} aria-labelledby="login-title">
          <h1 id="login-title">Sign in</h1>
          <p className="login-sub">Welcome back to {BRAND}.</p>

          {notice && !error && !info && <p className="login-notice" role="status">{notice}</p>}
          {info && !error && <p className="login-notice" role="status">{info}</p>}
          {error && <p className="login-error" role="alert">{error}</p>}

          <label className="login-field" htmlFor="login-username">Username</label>
          <div className="login-input">
            <UserRound size={18} aria-hidden="true" />
            <input id="login-username" value={username} onChange={(e) => setUsername(e.target.value)}
              autoComplete="username" placeholder="e.g. jane.doe" required autoFocus />
          </div>

          <label className="login-field" htmlFor="login-password">Password</label>
          <div className="login-input">
            <Lock size={18} aria-hidden="true" />
            <input id="login-password" type={showPassword ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" placeholder="••••••••" required />
            <button type="button" className="login-eye" onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
              {showPassword ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
            </button>
          </div>

          {needsCode && (
          <>
            <label className="login-field" htmlFor="login-code">
              {byEmail ? "Sign-in code from your email" : "Code from your authenticator app"}
            </label>
            <div className="login-input">
              {byEmail ? <Mail size={18} aria-hidden="true" /> : <ShieldCheck size={18} aria-hidden="true" />}
              <input id="login-code" value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric"
                autoComplete="one-time-code" pattern="[0-9 ]{6,7}" placeholder="123 456" required autoFocus />
            </div>
            {byEmail && (
              <p className="login-resend">
                {retryIn > 0
                  ? <span aria-live="polite">You can send a new code in {retryIn} s.</span>
                  : <>Didn't get it? Check your spam folder, or{" "}
                    <button type="button" onClick={sendNewCode} disabled={busy}>send a new code</button>.</>}
              </p>
            )}
          </>
        )}
        <Button busy={busy} busyText="Signing in…" className="login-btn">{needsCode ? "Confirm and sign in" : "Sign in"}</Button>
          <p className="login-foot">New to the platform? <Link to="/demo">Book a demo</Link></p>
        </form>
        <p className="login-tagline">{TAGLINE}</p>
      </main>
    </div>
  );
}
