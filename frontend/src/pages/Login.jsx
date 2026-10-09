// Sign-in page.
import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Eye, EyeOff, Lock, UserRound } from "lucide-react";
import { useAuth } from "../auth";
import { BrandMark, Button } from "../components/ui";
import { BRAND } from "../brand";
import "./login.css";

export default function Login() {
  const { login, notice } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-lights" aria-hidden="true"><span /><span /><span /><span /></div>
      <Link to="/" className="login-back"><ArrowLeft size={16} aria-hidden="true" />Back to the website</Link>

      <form className="login-box" onSubmit={submit}>
        <div className="login-logo"><BrandMark /></div>
        <h1>Welcome back</h1>
        <p className="login-sub">Sign in to {BRAND}.</p>

        {notice && !error && <p className="login-error" role="status">{notice}</p>}
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
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        <Button busy={busy} busyText="Signing in…" className="login-btn">Sign in</Button>
        <p className="login-foot">New to the platform? <Link to="/demo">Book a demo</Link></p>
      </form>
    </div>
  );
}
