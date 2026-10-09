// The product's name. Change it here and the website, the app and the browser tab all follow.
// (Emails use APP_NAME in backend/app/core/config.py.)
export const BRAND = "MeritLens";

// Shown in the small square mark: the capital letters of the name ("ML"), or the first letters of its first two
// words for a name written as several words
const capitals = BRAND.replace(/[^A-Z]/g, "");
export const MONOGRAM = capitals.length >= 2 ? capitals.slice(0, 2)
  : BRAND.split(/\s+/).filter((w) => /^[A-Za-z]/.test(w)).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
