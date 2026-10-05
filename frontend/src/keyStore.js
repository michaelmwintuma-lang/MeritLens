// Keeping report keys on the reporter's own device. Nothing here is ever sent to the server: saving a key on the
// server would link the report to the reporter's account, which is exactly what anonymity rules out.
//
// Keys are kept separately for each account that signs in on this device, so someone else signing in here
// (for example a colleague, or HR) doesn't see them in the app.

let owner = null; // the signed-in account's id, set by auth.jsx
export function setKeyOwner(userId) { owner = userId ?? null; }

const storageKey = (kind) => `${kind}:${owner}`;

function read(kind, fallback) {
  if (owner === null) return fallback;
  try {
    const value = JSON.parse(localStorage.getItem(storageKey(kind)) || "null");
    return value ?? fallback;
  } catch {
    return fallback;
  }
}

function store(kind, value) {
  if (owner === null) return false;
  try {
    localStorage.setItem(storageKey(kind), JSON.stringify(value));
    return true;
  } catch {
    return false; // storage blocked (e.g. private window): the other ways of keeping the key still work
  }
}

/** Keys this account saved on this device: [{ case_id, key, saved_on, note }]. */
export function savedKeys() {
  const list = read("report-keys", []);
  return Array.isArray(list) ? list : [];
}

const write = (list) => store("report-keys", list);

/** What the reporter has already seen of each case: { case_id: { messages, status } }. Used for notifications. */
export const seenCases = () => read("report-seen", {});
export function markSeen(caseId, messages, status) {
  store("report-seen", { ...seenCases(), [caseId]: { messages, status } });
}

/** Save (or update) a case on this device. Returns false if the browser won't store it. */
export function saveKey(caseId, key, note = "") {
  const rest = savedKeys().filter((k) => k.case_id !== caseId);
  return write([{ case_id: caseId, key, note: note.trim(), saved_on: new Date().toISOString().slice(0, 10) }, ...rest]);
}

export function forgetKey(caseId) {
  write(savedKeys().filter((k) => k.case_id !== caseId));
  const { [caseId]: _gone, ...rest } = seenCases();
  store("report-seen", rest);
}

export const isSaved = (caseId) => savedKeys().some((k) => k.case_id === caseId);

/** A small text file with the case ID, key and how to use them. */
export function downloadReceipt(caseId, key) {
  const text = [
    "Anonymous report - keep this private",
    "",
    `Case ID:    ${caseId}`,
    `Secret key: ${key}`,
    "",
    `To follow up, sign in and open "Check my report": ${window.location.origin}/my-report`,
    "",
    "The key can't be recovered if you lose it. Anyone who has both lines can read your case,",
    "so keep this file somewhere only you can open, or delete it once it's in your password manager.",
  ].join("\n");
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: `report-${caseId}.txt` });
  link.click();
  URL.revokeObjectURL(url);
}

/** Password managers: Chrome and Edge can store the pair directly (encrypted, synced to the person's devices). */
export const canUsePasswordManager = () => typeof window.PasswordCredential === "function" && Boolean(navigator.credentials);

export async function saveToPasswordManager(caseId, key) {
  const credential = new window.PasswordCredential({ id: caseId, password: key, name: `Anonymous report ${caseId}` });
  await navigator.credentials.store(credential);
}
