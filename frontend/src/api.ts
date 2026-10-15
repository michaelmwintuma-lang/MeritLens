// Talking to the backend. Sign-in travels in an httpOnly session cookie the browser sends by itself: this code
// never sees or stores the login token, so a script injected into the page couldn't steal it. Every request carries
// X-Requested-With, which the backend requires for changes made with the cookie (another site can't add it).
// Types come from the backend's contract (openapi.json -> api-types.ts, `npm run gen:api`).
import type { components } from "./api-types";

export type Schemas = components["schemas"];
export type User = Schemas["UserOut"];
export type ModelVersion = Schemas["ModelVersionOut"];
export type ModelCard = Schemas["ModelCardOut"];
export type Fairness = Schemas["FairnessOut"];
export type AuditPage = Schemas["AuditPageOut"];
export type ChainCheck = Schemas["VerifyOut"];

// Sent when the server says the session is no longer valid (expired, signed out elsewhere, password changed)
export const SESSION_ENDED = "session-ended";
const WEBSITE = { "X-Requested-With": "MeritLens" };

export interface ApiError extends Error {
  status?: number;
  fields: Record<string, string>; // per-field problems, so a form can show each next to its box
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
interface Options { method?: Method; body?: unknown }

/** Call the API. Returns the JSON body, or throws an ApiError with the server's message. */
export async function api<T = any>(path: string, { method = "GET", body }: Options = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: { ...WEBSITE, ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  // A request the server no longer accepts the session for: sign out here too, once, in one place
  if (res.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new Event(SESSION_ENDED));
  if (!res.ok) throw toError(data, res.status, `Request failed (${res.status})`);
  return data as T;
}

/**
 * Call an endpoint that works in the background (it answers 202 while working): keep asking every `everyMs` until
 * it answers 200. The first request may start the work (POST); the following ones only ask (GET).
 */
export async function apiWhenReady<T = any>(path: string, { start = "POST", everyMs = 400, timeoutMs = 120_000 }:
  { start?: Method; everyMs?: number; timeoutMs?: number } = {}): Promise<T> {
  const deadline = Date.now() + timeoutMs;
  let method: Method = start;
  for (;;) {
    const res = await fetch(`/api${path}`, { method, credentials: "same-origin", headers: WEBSITE });
    const data = await res.json().catch(() => null);
    if (res.status === 200) return data as T;
    if (res.status !== 202) throw toError(data, res.status, `Request failed (${res.status})`);
    if (Date.now() > deadline) throw toError(null, 504, "This is taking longer than usual. Please try again.");
    await new Promise((r) => setTimeout(r, everyMs));
    method = "GET";
  }
}

// FastAPI sends {detail: "text"}, {detail: {message, fields}}, or for invalid input {detail: [{msg, loc}, ...]}
function messageFrom(data: any): string | null {
  if (!data?.detail) return null;
  if (typeof data.detail === "string") return data.detail;
  if (data.detail.message) return data.detail.message;
  return data.detail.map((d: any) => `${d.loc?.slice(-1)[0] ?? "input"}: ${d.msg}`).join("; ");
}

function toError(data: any, status: number, fallback: string): ApiError {
  const error = new Error(messageFrom(data) || fallback) as ApiError;
  error.status = status;
  error.fields = data?.detail?.fields || {};
  return error;
}

/** Fetch a protected file (a photo or a document) as a Blob, for showing it on the page. */
export async function apiBlob(path: string, { method = "GET", body }: Options = {}): Promise<Blob> {
  const res = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: { ...WEBSITE, ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw toError(await res.json().catch(() => null), res.status, `Couldn't open the file (${res.status})`);
  return res.blob();
}

/**
 * Upload one file with some form fields, reporting progress (0 to 1) as it goes. Returns the JSON answer, or
 * throws an Error with the server's message. (fetch can't report upload progress, so this uses XMLHttpRequest.)
 */
export function uploadFile<T = any>(path: string, fields: Record<string, unknown>, file: Blob,
  onProgress?: (share: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    Object.entries(fields).forEach(([name, value]) => form.append(name, String(value)));
    form.append("file", file, "upload");  // the real file name is never sent: it often contains a name or date
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api${path}`);
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-Requested-With", WEBSITE["X-Requested-With"]);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total); };
    xhr.onload = () => {
      let data: any = null;
      try { data = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as T);
      else reject(toError(data, xhr.status, xhr.status === 413 ? "That file is too big." : `Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("The upload was interrupted. Check your connection and try again."));
    xhr.send(form);
  });
}

// ─── Typed calls for sign-in and governance (checked against the backend's contract) ────────────────────────────
export const auth = {
  me: () => api<User>("/auth/me"),
  login: (body: Schemas["LoginIn"]) => api<Schemas["LoginOut"]>("/auth/login", { method: "POST", body }),
  logout: () => api<{ signed_out: boolean }>("/auth/logout", { method: "POST" }),
};

export const governance = {
  models: () => api<ModelVersion[]>("/governance/models"),
  model: (version: string) => api<ModelCard>(`/governance/models/${version}`),
  release: (version: string, body: Schemas["ReleaseIn"]) =>
    api<ModelCard>(`/governance/models/${version}/release`, { method: "POST", body }),
  fairness: () => api<Fairness>("/governance/fairness"),
  audit: (params: { event?: string; subject_type?: string; subject_id?: string; page?: number } = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => [k, String(v)])).toString();
    return api<AuditPage>(`/governance/audit${query ? `?${query}` : ""}`);
  },
  verify: () => api<ChainCheck>("/governance/audit/verify"),
};
