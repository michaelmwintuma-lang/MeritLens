// Talking to the backend. Every request carries the login token; errors become readable messages.

const TOKEN_KEY = "token";

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* storage unavailable: the user just signs in again next time */ }
}

/** Call the API. Returns the JSON body, or throws an Error with the server's message. */
export async function api(path, { method = "GET", body } = {}) {
  const token = getToken();
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const error = new Error(messageFrom(data) || `Request failed (${res.status})`);
    error.status = res.status;
    error.fields = data?.detail?.fields || {};  // per-field problems, so a form can show each next to its box
    throw error;
  }
  return data;
}

// FastAPI sends {detail: "text"}, {detail: {message, fields}}, or for invalid input {detail: [{msg, loc}, ...]}
function messageFrom(data) {
  if (!data?.detail) return null;
  if (typeof data.detail === "string") return data.detail;
  if (data.detail.message) return data.detail.message;
  return data.detail.map((d) => `${d.loc?.slice(-1)[0] ?? "input"}: ${d.msg}`).join("; ");
}

/** Fetch a protected file (a photo or video) as a Blob, for showing it on the page. */
export async function apiBlob(path, { method = "GET", body } = {}) {
  const token = getToken();
  const res = await fetch(`/api${path}`, {
    method,
    headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(messageFrom(data) || `Couldn't open the file (${res.status})`);
  }
  return res.blob();
}

/**
 * Upload one file with some form fields, reporting progress (0 to 1) as it goes. Returns the JSON answer, or
 * throws an Error with the server's message. (fetch can't report upload progress, so this uses XMLHttpRequest.)
 */
export function uploadFile(path, fields, file, onProgress) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    Object.entries(fields).forEach(([name, value]) => form.append(name, String(value)));
    form.append("file", file, "upload");  // the real file name is never sent: it often contains a name or date
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api${path}`);
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total); };
    xhr.onload = () => {
      let data = null;
      try { data = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new Error(messageFrom(data) || (xhr.status === 413 ? "That file is too big." : `Upload failed (${xhr.status})`)));
    };
    xhr.onerror = () => reject(new Error("The upload was interrupted. Check your connection and try again."));
    xhr.send(form);
  });
}
