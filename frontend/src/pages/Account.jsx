// My profile: see your account and work details, update your name, email, phone, job title and photo, and change
// your username and password. New accounts are sent here first, because their password came from the welcome email.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Camera, Lock, Trash2 } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { ROLE_NAMES } from "../roles";
import { Button, Callout, Card, PageHeader } from "../components/ui";
import { useAction } from "../useAction";
import { useToast } from "../components/Toast";

const PHOTO_SIZE = 256; // pixels: big enough for the sidebar and profile, small enough to store

/** Shrink a chosen picture to a square, small image in the browser, so only a few kilobytes are uploaded. */
function shrinkPhoto(file) {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith("image/")) return reject(new Error("Please choose a picture (JPG, PNG or WebP)."));
    const image = new Image();
    image.onload = () => {
      const side = Math.min(image.width, image.height);
      const canvas = Object.assign(document.createElement("canvas"), { width: PHOTO_SIZE, height: PHOTO_SIZE });
      canvas.getContext("2d").drawImage(image, (image.width - side) / 2, (image.height - side) / 2, side, side, 0, 0, PHOTO_SIZE, PHOTO_SIZE);
      URL.revokeObjectURL(image.src);
      resolve(canvas.toDataURL("image/webp", 0.85));
    };
    image.onerror = () => reject(new Error("That picture couldn't be read. Try a different file."));
    image.src = URL.createObjectURL(file);
  });
}

function ProfilePhoto() {
  const { user, setUser } = useAuth();
  const input = useRef(null);
  const [error, setError] = useState("");
  const [working, withWorking] = useAction();

  async function save(photo) {
    setError("");
    try {
      setUser(await api("/auth/profile/photo", { method: "PUT", body: { photo } }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function choose(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    try {
      await save(await shrinkPhoto(file));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="profile-photo">
      {user.photo ? <img src={user.photo} alt="Your profile" /> : <div className="profile-initial" aria-hidden="true">{user.full_name.charAt(0)}</div>}
      <div>
        <div className="row">
          <Button type="button" look="secondary" icon={Camera} busy={working} busyText="Saving…" onClick={() => input.current.click()}>
            {user.photo ? "Change photo" : "Add a photo"}
          </Button>
          {user.photo && <Button type="button" look="ghost" icon={Trash2} onClick={() => withWorking(() => save(null))}>Remove</Button>}
        </div>
        <p className="muted section-gap">Shown in the menu. It's cropped to a square and made small before it's saved.</p>
        {error && <Callout tone="error" className="section-gap">{error}</Callout>}
        <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => withWorking(() => choose(e))} />
      </div>
    </div>
  );
}

function ProfileDetails() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({ full_name: user.full_name, email: user.email || "", phone: user.phone || "", job_title: user.job_title || "" });
  const [message, setMessage] = useState({ text: "", ok: true });
  const [working, withWorking] = useAction();
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const emailChanging = form.email.trim().toLowerCase() !== (user.email || "");

  async function submit(e) {
    e.preventDefault();
    try {
      setUser(await api("/auth/profile", { method: "PATCH", body: { ...form, email: form.email || null } }));
      setMessage({ text: emailChanging ? "Saved. A note has been sent to your old email address, in case it wasn't you." : "Saved.", ok: true });
    } catch (err) {
      setMessage({ text: err.message, ok: false });
    }
  }

  return (
    <Card title="Your details">
      <ProfilePhoto />
      <form onSubmit={(e) => withWorking(() => submit(e))} className="section-gap">
        {message.text && <Callout tone={message.ok ? "success" : "error"} role="status">{message.text}</Callout>}
        <div className="form-row">
          <label className="field">Full name<input value={form.full_name} onChange={set("full_name")} required minLength={2} maxLength={120} autoComplete="name" /></label>
          <label className="field"><span>Job title <span className="muted">(optional)</span></span><input value={form.job_title} onChange={set("job_title")} maxLength={120} autoComplete="organization-title" /></label>
        </div>
        <div className="form-row">
          <label className="field">Email
            <input type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
            {emailChanging && <span className="field-hint">Your old address will be told about the change, in case it wasn't you.</span>}
          </label>
          <label className="field"><span>Phone <span className="muted">(optional)</span></span><input type="tel" value={form.phone} onChange={set("phone")} maxLength={40} pattern="[0-9+()\-. ]*" autoComplete="tel" /></label>
        </div>
        <Button busy={working} busyText="Saving…">Save details</Button>
      </form>
    </Card>
  );
}

function WorkDetails() {
  const { user } = useAuth();
  const [work, setWork] = useState(null);
  useEffect(() => { api("/auth/profile").then((p) => setWork(p.work)).catch(() => setWork({})); }, []);
  const rows = [
    ["Role", ROLE_NAMES[user.role]],
    ["Username", user.username],
    work?.department && ["Department", work.department],
    work?.employee_id && ["Employee number", work.employee_id],
    work?.department && ["Manager", work.manager || "Not set yet"],
    work?.team_size !== undefined && ["Team", `${work.team_size} ${work.team_size === 1 ? "person" : "people"}`],
    user.role === "admin" && ["Employee data", user.can_view_employees ? "May view (read-only)" : "No access"],
    user.created_at && ["Account created", user.created_at.slice(0, 10)],
  ].filter(Boolean);
  return (
    <Card title="Work details" subtitle="Kept by HR. Ask them if something is wrong.">
      <dl className="details-list">
        {rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>
    </Card>
  );
}

function ChangeUsername() {
  const { user, setUser } = useAuth();
  const [username, setUsername] = useState(user.username);
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState({ text: "", ok: true });

  const [working, withWorking] = useAction();

  async function submit(e) {
    e.preventDefault();
    try {
      setUser(await api("/auth/change-username", { method: "POST", body: { current_password: password, new_username: username } }));
      setPassword("");
      setMessage({ text: "Username changed. Use it the next time you sign in.", ok: true });
    } catch (err) {
      setMessage({ text: err.message, ok: false });
    }
  }

  return (
    <Card title="Username" subtitle="What you type to sign in. Letters, numbers, dots, dashes and underscores.">
      <form onSubmit={(e) => withWorking(() => submit(e))}>
        {message.text && <p className={`alert ${message.ok ? "alert-success" : "alert-error"}`} role="status">{message.text}</p>}
        <label className="field">New username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required minLength={2} pattern="[a-zA-Z0-9._\-]+" autoComplete="username" />
        </label>
        <label className="field"><span>Your current password <span className="muted">(to confirm it's you)</span></span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </label>
        <Button busy={working} busyText="Saving…" disabled={username.trim().toLowerCase() === user.username}>Change username</Button>
      </form>
    </Card>
  );
}

/** Routine emails as they happen, or one digest each morning. Account emails always come at once. */
function EmailPreference() {
  const { user, setUser } = useAuth();
  const [error, setError] = useState("");
  const toast = useToast();
  const mode = user.email_mode || "instant";

  async function choose(next) {
    setError("");
    try {
      setUser(await api("/auth/preferences", { method: "PUT", body: { email_mode: next } }));
      toast(next === "daily" ? "You'll get one email a day, each morning." : "You'll get each email as it happens.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card id="emails" icon={Bell} title="Emails" subtitle="Your notification bell always shows everything as it happens. Choose how emails arrive.">
      {error && <Callout tone="error">{error}</Callout>}
      <fieldset className="agree">
        <legend className="visually-hidden">How emails arrive</legend>
        <div className="choices">
          <label className="check"><input type="radio" name="email_mode" checked={mode === "instant"} onChange={() => choose("instant")} /> Each email as it happens</label>
          <label className="check"><input type="radio" name="email_mode" checked={mode === "daily"} onChange={() => choose("daily")} /> One digest each morning</label>
        </div>
      </fieldset>
      <p className="muted">Emails about your account (sign-in details, password, username or email address changes) always arrive at once.</p>
    </Card>
  );
}

function ChangePassword() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [message, setMessage] = useState({ text: "", ok: true });
  const firstTime = user.must_change_password;

  const [working, withWorking] = useAction();

  async function submit(e) {
    e.preventDefault();
    if (next !== repeat) return setMessage({ text: "The new passwords don't match.", ok: false });
    try {
      // Changing the password signs out every other device; this one gets a new session cookie
      const res = await api("/auth/change-password", { method: "POST", body: { current_password: current, new_password: next } });
      setUser(res.user);
      setCurrent(""); setNext(""); setRepeat("");
      if (firstTime) navigate("/");
      else setMessage({ text: "Password changed.", ok: true });
    } catch (err) {
      setMessage({ text: err.message, ok: false });
    }
  }

  return (
    <Card title="Password" subtitle="At least 8 characters. Don't reuse a password from another site.">
      <form onSubmit={(e) => withWorking(() => submit(e))}>
        {message.text && <p className={`alert ${message.ok ? "alert-success" : "alert-error"}`} role="status">{message.text}</p>}
        <label className="field">{firstTime ? "Temporary password (from your welcome email)" : "Current password"}
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" required />
        </label>
        <label className="field">New password
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" minLength={8} required />
        </label>
        <label className="field">Repeat new password
          <input type="password" value={repeat} onChange={(e) => setRepeat(e.target.value)} autoComplete="new-password" minLength={8} required />
        </label>
        <Button busy={working} busyText="Saving…">Save password</Button>
      </form>
    </Card>
  );
}

export default function Account() {
  const { user } = useAuth();
  if (user.must_change_password) {
    // First sign-in: only the password matters until it's chosen
    return (
      <>
        <PageHeader title="Welcome!" subtitle={`${user.full_name} · ${ROLE_NAMES[user.role]}`} />
        <Callout title="Choose your own password to continue">
          Your account was created by an administrator. You can change your username and update your profile afterwards.
        </Callout>
        <div className="two-columns"><ChangePassword /><ChangeUsername /></div>
      </>
    );
  }
  return (
    <>
      <PageHeader title="My profile" subtitle="Your details, photo, password and username." />
      <div className="profile-grid">
        <ProfileDetails />
        <div className="stack">
          <WorkDetails />
          <EmailPreference />
        </div>
      </div>
      <h2 className="section-title"><Lock size={18} aria-hidden="true" /> Sign-in and security</h2>
      <div className="two-columns">
        <ChangePassword />
        <ChangeUsername />
      </div>
    </>
  );
}
