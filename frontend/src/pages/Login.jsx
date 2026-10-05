// Sign-in page.
import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth";
import { Button, ThemeToggle } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
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
    <div className="center-page">
      <Link to="/" className="back" style={{ position: "fixed", top: 22, left: 24 }}><ArrowLeft size={16} />Back to the website</Link>
      <div style={{ position: "fixed", top: 20, right: 20 }}><ThemeToggle /></div>
      <form className="card narrow" onSubmit={submit}>
        <div className="brand" style={{ padding: "0 0 20px", marginBottom: 22 }}>
          <div className="brand-logo"><ShieldCheck size={20} aria-hidden="true" /></div>
          <div>
            <div className="brand-name">Promotion &amp; Reporting</div>
            <div className="brand-sub">Staff platform</div>
          </div>
        </div>
        <h1 style={{ fontSize: 24 }}>Sign in</h1>
        <p className="muted" style={{ marginTop: 4 }}>Use the account your administrator gave you.</p>
        {error && <p className="alert alert-error" role="alert">{error}</p>}
        <label className="field">Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required autoFocus />
        </label>
        <label className="field">Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </label>
        <Button busy={busy} busyText="Signing in…" style={{ width: "100%", justifyContent: "center" }}>Sign in</Button>
        <p className="muted small" style={{ textAlign: "center", margin: "16px 0 0" }}>New to the platform? <Link to="/demo">Book a demo</Link></p>
      </form>
    </div>
  );
}
