// Keeping a report's case ID and key: only ways that stay with the reporter. The website itself never stores a
// key. It used to offer "save on this device", but the saved list was labelled with the account's id, so anyone
// with access to the browser could see which account held which case (docs/REVIEW.md, S1).

let owner = null; // the signed-in account's id, set by auth.jsx; used only to find keys saved by that old version
export function setKeyOwner(userId) { owner = userId ?? null; }

/** Keys this account saved in this browser with the old version: [{ case_id, key, saved_on, note }]. */
export function legacyKeys() {
  if (owner === null) return [];
  try {
    const list = JSON.parse(localStorage.getItem(`report-keys:${owner}`) || "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

/** Remove those old keys (and what the old notifications remembered) from this browser. */
export function removeLegacyKeys() {
  if (owner === null) return;
  try {
    localStorage.removeItem(`report-keys:${owner}`);
    localStorage.removeItem(`report-seen:${owner}`);
  } catch { /* storage unavailable: nothing to remove */ }
}

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
