// The product's name. Change it here and the website, the app and the browser tab all follow.
// (Emails use APP_NAME in backend/app/core/config.py.)
export const BRAND = "MeritLens";

// The one-line promise on the landing page
export const TAGLINE = "Fair, explainable promotion decisions, with a voice for every employee.";

// The project behind it, for the website's footer. Fill in what applies: anything left empty is simply not shown.
export const PROJECT = {
  title: "Design and Development of an Explainable Machine Learning-Based Decision Support System for Employee "
    + "Promotion Prediction with an Employee Feedback Channel",
  university: "",
  team: [],        // e.g. ["Ada Lovelace", "Alan Turing"]
  supervisors: [], // e.g. ["Dr Grace Hopper"]
};

// Shown in the small square mark: the capital letters of the name ("ML"), or the first letters of its first two
// words for a name written as several words
const capitals = BRAND.replace(/[^A-Z]/g, "");
export const MONOGRAM = capitals.length >= 2 ? capitals.slice(0, 2)
  : BRAND.split(/\s+/).filter((w) => /^[A-Za-z]/.test(w)).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
