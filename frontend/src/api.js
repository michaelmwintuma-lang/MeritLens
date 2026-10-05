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
