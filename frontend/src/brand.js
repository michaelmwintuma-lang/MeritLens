// The product's name. Change it here and the website, the app and the browser tab all follow.
// (Emails use APP_NAME in backend/app/core/config.py.)
export const BRAND = "Promotion & Reporting";

// Shown in the small square mark: the first letters of the first two words ("PR")
export const MONOGRAM = BRAND.split(/\s+/).filter((w) => /^[A-Za-z]/.test(w)).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
