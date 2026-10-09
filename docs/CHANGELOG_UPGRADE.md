# Upgrade changelog

Every change made while upgrading the platform to the thesis "Explainable machine-learning decision support for
employee promotion, with an employee feedback channel": **predict → explain → respond**. Product name: MeritLens.

## Model (before Phase 1, approved separately)

- Department removed from the model inputs: past promotion rates ranged from 2% to 33% by department, so it
  scored people by where they work.
- A monotonic Explainable Boosting Machine joins the candidates. Only models where improving an input can never
  lower a score are eligible; the EBM was the only one (logistic regression 16.7% violations, random forest
  30.1%, XGBoost 21.9%).
- Explanations use the EBM's own additive terms (still exact); tips test improvements on the model itself.
- Test set: PR-AUC 0.4736 (was 0.6325 with department), ROC-AUC 0.8833, F1 0.4856, threshold 0.2283; the
  four-fifths rule passes.

## Phase 1: review

- `docs/REVIEW.md`: bugs, security, missing features, code quality, UI/UX and measured performance, and the
  decisions taken on its questions.

## Phase 2: remove the bridge

- Checked: this project never had a bridge between reports and promotion scores, so nothing was removed
  (`docs/REVIEW.md`, section 8).

## Phase 3: fix bugs

Each fix has tests; the review's numbers are in brackets.

- **Sign-in lockout (S3):** 5 wrong passwords in a row lock an account for 15 minutes, logged; one message for
  every failed sign-in. **Withdrawn tokens (S4):** a password change, an admin reset or signing out makes
  existing login tokens stop working; a reset also unlocks the account.
- **No report keys in the browser (S1, S2, P4):** "Save on this device", "My report keys", reporter
  notifications and the bulk `/api/reports/updates` endpoint are removed. Keys an earlier version saved are
  listed on "Check my report" until the reporter removes them.
- **Compliance auditor role** (decision 1): read-only decision log, model importance and record histories;
  never reports or individual records. Demo account `auditor` (demo databases only).
- **Only measured numbers on the website (B2, B3):** the landing and promotion pages read every figure from
  the saved results; nothing invented is shown when a result is missing.
- **Ended sessions (B4):** an expired or withdrawn login returns to the sign-in page with a reason.
  **Error boundary (B5):** a page that breaks shows a message and a reload button, not a blank screen.
- **Record history (B7):** every change to a record's model inputs is kept (who, when, old and new values,
  reason, readiness before and after, model version) in an append-only table, shown to HR.
- **Model page (B6):** lists everything the model never uses, read from the code. Tidy-ups (B8, B9, Q4).
- **Docs (B1):** README, HOW_IT_WORKS and LIMITATIONS now describe the EBM with every number re-measured
  (LIME median fit 0.13; tips reach the threshold for 98 of 108 demo employees not yet recommended).
- **Renamed to MeritLens.**
- **Browser checks:** `python scripts/browser_test.py` runs headless-Chrome checks on a throwaway copy of the
  app, including every menu page for all six roles.
- The public summary moved to `app/public/` after the isolation test caught it reading reporting results from
  inside the promotion package.

## Phase 4: the employee feedback channel (predict → explain → **respond**)

A new backend module, `app/feedback`, which the promotion code never imports. Nothing in it changes a score except
HR confirming a record correction, which is logged.

- **Respond panel** on the employee's "My growth" page, after the explanation, with three routes:
  1. *Rate this explanation*: "This explanation was clear" and "This explanation was useful" (1–5), optional
     "seems wrong" / "seems unfair" marks per factor and a comment. Stored with the model version and the score it
     explained; rating the same model's explanation again replaces the earlier rating. HR and the auditor see only
     aggregates (rates withheld below 5 ratings); managers see nothing.
  2. *Correct my record*: pick a value from your own record (the 20 fields HR types in; nothing protected), the
     correct value, evidence in words and optionally a PDF, JPEG or PNG. Your requests and HR's decisions are listed.
  3. *Report anonymously*: opens the report form with "Biased rating or appraisal" chosen. All anonymity
     protections are unchanged.
- **Reporting aligned with the feedback channel:** new reports use five categories (biased rating or appraisal,
  favouritism, discrimination, wrong or missing record, other workplace concern); saved reports keep theirs.
- **HR correction queue** (`/corrections`): confirm with the verified value (the record is corrected, the employee
  re-scored, and who, old and new value, reason, readiness before and after and the model version go to the record
  history and the activity log) or reject with a reason of at least 20 characters, which the employee receives.
  The employee is told by email and in the notification bell.
- **Committee note:** HR's nomination review shows pending corrections for the nominee and can hold the decision
  until they're resolved. A hold is not a decision (never counted as an override) and lifts when the correction is
  decided.
- **Re-appraisal:** a case closed as "Rating found unfair" lets HR open a correction for the affected value. The
  case is checked but its ID is stored nowhere with the correction; the employee doesn't see HR's note.
- **Isolation test** (`tests/test_isolation.py`): the explanation (as HR, the manager and the employee see it),
  tips, a what-if and everyone's scores are byte-for-byte identical after ratings, corrections, a held decision and
  four reports with conversations and outcomes; a confirmed correction then changes the prediction and is logged.
  **Static check:** nothing in `app/promotion` imports or names the feedback or reporting code or tables.
  **Run-time check:** the prediction endpoints run no SQL on those tables.
- The employee's "My readiness" is now "My growth".

## Phase 5: dashboards

- **Feedback dashboard** (`/feedback`, HR and the compliance auditor), every number computed on the server from
  the database: clarity and usefulness rates (share rating 4 or 5; withheld below 5 ratings), contest share per
  factor (sorted bars), correction requests received/confirmed/rejected/pending with the confirmation rate and mean
  time to decide, anonymous reports per promotion category (dates only; counts of 1–2 shown as "<3"), and the
  committee's override rate with the written reasons. Filters: date range, department (only departments with at
  least 5 people) and model version. CSV export of the same numbers. Never names, comments or report texts.
- **Decisions record the model version** they were made with (empty for older decisions).
- **Admin dashboard** (the admin's home): active/locked/new accounts, accounts by role, quick actions, system health
  (API, model version, training date and a timed test prediction, fairness gate, email), recent activity, and
  **drift**: the population stability index of each input between the training sample and today's directory,
  judged against the PSI that chance alone gives a group of that size. (For the 120 demo employees, who come from
  the same data, chance alone reaches up to 0.16 for some inputs; two inputs are just above it, which the page
  explains is expected when 20 inputs are checked.)
- **Role homes:** HR sees corrections waiting and links to the queue and dashboard; employees a "Respond to your
  explanation" card with their requests; the auditor the share of explanations rated clear and the dashboard.

## Phase 6: public landing page

- **Landing page at `/`** (sign-in stays at `/login`): the promise "Fair, explainable promotion decisions, with a
  voice for every employee", two actions (*Sign in*; *Report a concern anonymously*, which goes through sign-in
  straight to the report form), **How it works** (Predict → Explain → Respond), six features (explainable
  predictions with exact contributions equal to SHAP values and LIME, path to promotion, fairness audit, employee
  feedback channel, anonymous reporting, people decide), the trust section (a complaint never changes a score, no
  one can unmask a reporter, people make every decision), the measured results, and a footer with the project
  title. The university, team and supervisors appear once filled in (`frontend/src/brand.js`); none were invented.
- No stock images or testimonials: screenshots of the real app with made-up demo data, retaken with
  `python scripts/browser_test.py scripts/capture_landing.js`.
- The reporting, "Who uses it" and privacy pages now describe the feedback channel, the five categories, the
  auditor role, and keys never kept in the browser.
- Fixes found on the way: a score below 0.5% read "0%" (now "under 1%"), and signing in from "Report a concern
  anonymously" landed on the overview instead of the report form.
- The browser checks now run against a production build (`vite preview`), which never reloads a page mid-check.

## Phase 7: UI/UX and accessibility

- **The explanation page reads in plain words first**, for every role: the score with "readiness is compared with
  an average employee", what raised and lowered it, the path to promotion (tips, now before the what-if), the
  what-if, and the respond panel; the exact numbers, LIME and the model's details are under **"Show technical
  details"**. On the employee's own "My growth" page the prediction runs as the page opens and the bars carry no
  log-odds numbers. LIME and the tips run at the same time.
- **One loading and error pattern**: a spinner announced to screen readers, and errors with a "Try again" button,
  on every page and panel (19 places). HR's nomination review no longer spins forever when only the explanation
  fails to load.
- **Accessibility**: segmented controls are a group of toggle buttons (they claimed to be tabs without arrow-key
  support); tables that scroll sideways on a phone can be reached with the keyboard. axe-core (WCAG 2.1 A/AA) on
  17 pages in light and dark themes: no findings (`docs/screenshots/PHASE7.md`).
- **Before/after screenshots** of 17 pages on a computer and a phone: `docs/screenshots/phase7-before`,
  `phase7-after`, made with `scripts/ui_capture.js`. Nothing is wider than a phone's screen.
- The existing design (teal, light and dark themes, phone tab bar) is kept; the "indigo for promotion" colour of
  the plan doesn't exist in this design, so no colour scheme was changed.
