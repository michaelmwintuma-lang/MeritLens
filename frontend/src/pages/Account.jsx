// My profile: see your account and work details, update your name, email, phone, job title and photo, and change
// your username and password. New accounts are sent here first, because their password came from the welcome email.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, Lock, Trash2, UserRound } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { ROLE_NAMES } from "../roles";
import { Button, Card, PageHeader } from "../components/ui";
import { useAction } from "../useAction";

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
          <Button type="button" look="plain" icon={Camera} busy={working} busyText="Saving…" onClick={() => input.current.click()}>
            {user.photo ? "Change photo" : "Add a photo"}
          </Button>
          {user.photo && <Button type="button" look="plain" icon={Trash2} onClick={() => withWorking(() => save(null))}>Remove</Button>}
        </div>
        <p className="muted small" style={{ margin: "8px 0 0" }}>Shown in the menu. It's cropped to a square and made small before it's saved.</p>
        {error && <p className="alert alert-error" role="alert" style={{ marginTop: 10 }}>{error}</p>}
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
    <Card title="Your details" subtitle="How you appear to others on the platform, and where emails are sent.">
      <ProfilePhoto />
      <form onSubmit={(e) => withWorking(() => submit(e))} style={{ marginTop: 20 }}>
        {message.text && <p className={`alert ${message.ok ? "alert-success" : "alert-error"}`} role="status">{message.text}</p>}
        <div className="form-row">
          <label className="field">Full name<input value={form.full_name} onChange={set("full_name")} required minLength={2} maxLength={120} autoComplete="name" /></label>
          <label className="field"><span>Job title <span className="muted small">(optional)</span></span><input value={form.job_title} onChange={set("job_title")} maxLength={120} autoComplete="organization-title" /></label>
        </div>
        <div className="form-row">
          <label className="field">Email
            <input type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
            {emailChanging && <span className="field-hint">Your old address will be told about the change, in case it wasn't you.</span>}
          </label>
          <label className="field"><span>Phone <span className="muted small">(optional)</span></span><input type="tel" value={form.phone} onChange={set("phone")} maxLength={40} pattern="[0-9+()\-. ]*" autoComplete="tel" /></label>
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
    <Card title="Work details" subtitle="Set by your organisation. Ask HR or an administrator if something is wrong.">
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
        <label className="field"><span>Your current password <span className="muted small">(to confirm it's you)</span></span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </label>
        <Button busy={working} busyText="Saving…" disabled={username.trim().toLowerCase() === user.username}>Change username</Button>
      </form>
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
      setUser(await api("/auth/change-password", { method: "POST", body: { current_password: current, new_password: next } }));
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
        <PageHeader icon={UserRound} title="Welcome!" subtitle={`${user.full_name} · ${ROLE_NAMES[user.role]}`} />
        <p className="alert alert-info">
          Your account was created by an administrator. Before you continue, please choose your own password. You can
          change your username and update your profile afterwards.
        </p>
        <div className="two-columns"><ChangePassword /><ChangeUsername /></div>
      </>
    );
  }
  return (
    <>
      <PageHeader icon={UserRound} title="My profile" subtitle="Your details, how you sign in, and your work information." />
      <div className="profile-grid">
        <ProfileDetails />
        <WorkDetails />
      </div>
      <h2 className="section-title"><Lock size={18} aria-hidden="true" /> Sign-in and security</h2>
      <div className="two-columns">
        <ChangePassword />
        <ChangeUsername />
      </div>
    </>
  );
}
