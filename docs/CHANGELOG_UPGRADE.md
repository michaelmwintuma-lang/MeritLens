# Upgrade changelog

Every change made while upgrading the platform to the thesis "Explainable machine-learning decision support for
employee promotion, with an employee feedback channel": **predict → explain → respond**. Product name: MeritLens.

## Summary

The system as it stands. The phases below are the history, as it happened: Phases 2–9 also built anonymous
reporting, which was removed afterwards (see "Removal of anonymous reporting" at the end).

- **Predict:** department removed from the model; a monotonic Explainable Boosting Machine chosen by a
  common-sense rule (improving an input never lowers a score), with the four-fifths fairness gate. Test PR-AUC
  0.474 and ROC-AUC 0.883; every group's ratio is at least 0.887.
- **Explain:** exact additive contributions in plain words first, with "Show technical details" for the numbers
  and LIME; tips toward the threshold; "under 1%" instead of "0%".
- **Respond:** rate the explanation, or request a record correction with evidence; HR's correction queue; the
  committee note and hold.
- **Isolation, proven:** byte-for-byte identical predictions after every kind of feedback; static and run-time
  checks.
- **Oversight:** a read-only compliance auditor; the feedback dashboard with small-group protection; the admin
  dashboard with system health and drift.
- **Security fixes:** sign-in lock-out; withdrawn tokens.
- **Site:** a public landing page; one loading and error pattern; no accessibility findings (axe, light and dark);
  pages load on first use; batch scoring.
- **Tests and docs:** 315 tests in about 3 minutes; 6 browser checks; CI; the evaluation results, thesis guide
  and data model; a usability study kit with perceived-fairness items.
- **Redesign (2026-10-15):** model registry with model cards and human release; hash-chained audit trail; live
  fairness at three stages; enforced decision holds; background LIME; data mapping for other organisations;
  PostgreSQL support with isolation enforced by database roles; httpOnly cookie sessions; a typed (TypeScript) API
  layer; a clearer interface. Details in "Redesign" below.

## Redesign (2026-10-15)

Same purpose and the same cycle (predict → explain → respond, people decide). The model, its threshold and every
published result are unchanged: retraining through the new data mapping reproduced them exactly (ROC-AUC 0.8833,
PR-AUC 0.4736, threshold 0.2283, fairness ratios 0.982 / 0.963 / 0.887).

| Change | Why |
|---|---|
| **Model registry and human release** (`app/governance/registry.py`, Model registry page). `train.py` registers a candidate with a model card; HR releases it with a note; blocked if it failed fairness; release an older version to roll back; the app switches without a restart. | A model went live the moment training finished. Now a named person approves every release, and every version stays inspectable. |
| **Audit trail** (`app/core/audit.py`, Audit trail page). Append-only, SHA-256 hash-chained events for nominations, decisions (with the model's score, threshold, version and top factors), pay steps, record changes, corrections, holds and model releases; a chain check. | The auditor can rebuild what the model said and what each person did at any time, and prove the record wasn't altered. |
| **Live fairness** (`app/governance/monitoring.py`, Live fairness page). Four-fifths rule on the model's recommendations, managers' nominations and HR's approvals; equality-monitoring data kept apart and never given to the model. | Fairness was checked only on the test set at training time; people can override the model. |
| **Enforced holds** (`app/core/holds.py`). Holds moved from a feedback table to a neutral one; the decision API refuses a held nomination. | A hold was advisory: the API would accept a decision. |
| **Background LIME** (`app/core/jobs.py`). Started, then polled; kept per model version and exact record; warmed after a record change. | LIME (2,000 model calls) held up requests. |
| **Data mapping** (`app/promotion/mapping.py`, `data/mappings/`). `train.py --mapping`. | Retraining on another organisation's export needed code changes. |
| **PostgreSQL** (`deploy/postgres/`). Optional; the promotion code can connect as a role with no access to feedback or equality-monitoring tables. | Many users at once, backups, and isolation enforced by the database too. Not tested against a running server. |
| **Session cookie** (httpOnly, SameSite=Strict, plus a request header against cross-site forgery). The website never sees the token. | The token was in `localStorage`, readable by any script on the page. |
| **TypeScript API layer** (`frontend/src/api.ts`, `auth.tsx`, types generated from `frontend/openapi.json`). `npm run build` type-checks. | Backend/frontend mismatches surface at build time. |
| **Interface.** "Needs your attention" first on every overview; one diverging factor chart; dashed threshold; blue/orange reserved for the model's data, teal only for actions; "not yet recommended" and "not approved" neutral, never red; Inter with tabular numbers. | Clearer, calmer, colour-blind safe; data never looks clickable. |

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

## Phase 8: refactor and performance

Measured on the running app with 120 demo employees, before and after:

| | Before | After |
|---|---|---|
| Employee list (`GET /promotion/employees`) | 0.26 s (review, quiet machine) | 0.02–0.06 s |
| Scoring 5,000 employees | 11.25 s, one at a time | 13 ms, in one call (scores identical) |
| Admin dashboard's drift check | 0.156 s on every load | 0.005 s after the first |
| First download of the website | 482 kB (144 kB gzipped) | 309 kB (99 kB gzipped) |
| Full test suite | 5–9 minutes (30 on a busy machine) | 2 min 7 s, 370 tests |

- **Batch scoring:** the employee and nomination lists score everyone in one call to the model.
- **No row-by-row lookups:** nominations, the decision log and HR's report inbox fetch decisions, pay-rise
  histories, last messages and evidence counts for the whole list at once.
- **Notification bell:** HR's bell asks only for pay rises Finance sent back (`?pay_status=returned`) instead of
  downloading the whole decision log every minute.
- **Pages load on first use** (React lazy loading); only the landing page and sign-in are in the first download.
- **Employee list a page at a time** (50 per page), so a large directory stays quick to use.
- **Drift chance levels** are worked out once and reused.
- **Refactor:** one shared check for "outside the pay policy needs a reason" (it was written out twice); a shared
  `useLoad` hook (load, error, try again; a newer answer always wins) in the list pages.
- **Tests:** password hashing uses 1,000 rounds in tests only (the app keeps 200,000; a test checks it).
- Not split: `routes_decisions.py` stays one file. Its duplication is removed, and its parts (nominating, deciding,
  resubmitting, the log) share helpers closely, so splitting it would add imports without making it clearer.

## Phase 9: tests, results and documentation

- **CI** (`.github/workflows/ci.yml`): backend tests, frontend build and browser checks on every push. Not yet run
  on GitHub (no remote); each step passes locally.
- **Results re-run:** `train.py` reproduced `metrics.json`, `fairness.json` and `model_comparison.json` byte for
  byte; the reporting evaluation differed only in its run date. (Run on a copy, so the live model wasn't replaced.)
- **New result scripts:** `evaluation/evaluate_explanations.py` (exactness, common sense, LIME fit and agreement,
  tips) and `evaluation/export_feedback_measures.py` (the feedback dashboard's measures, for Chapter Four).
- **Usability study kit:** tasks T8–T11 for the feedback channel; eight perceived-fairness statements adapted from
  Colquitt (2001), informational and procedural; scoring with Cronbach's alpha (`evaluation/user_test.py`).
- **Documents:** `EVALUATION_RESULTS.md`, `THESIS_GUIDE.md`, `THREAT_MODEL.md` and `DATA_MODEL.md` (new); README,
  `HOW_IT_WORKS.md` and `LIMITATIONS.md` updated to describe the system as it is, framed as predict → explain →
  respond.

## After Phase 9

- **"Which route is right for you?"** on the "Report anonymously" tab. Because HR never learns who sent a report,
  an anonymous report about one's own rating can only lead to a re-appraisal through HR's own investigation. The
  tab now says so, and points people who want their own record fixed (and are comfortable being known) to
  "Correct my record", with a button that switches to it. Recorded as a limitation and a discussion point.

## Removal of anonymous reporting (2026-10-11)

The thesis now covers only the employee feedback channel (rate the explanation, correct my record); anonymous
reporting is future work. So the feature was removed, and the system matches the thesis.

- **Kept for later:** the last version with the feature is the git tag `with-anonymous-reporting` (commit
  `cee322a`); the work was done on the branch `remove-anonymous-reporting`. The threat model, the reporting
  evaluation and the original review moved to `docs/future-work/`, each with a note.
- **Backend:** `app/reporting` deleted (anonymiser, case keys, the triage model and its 280 examples, evidence
  cleaning, the conversation, HR's inbox), with its router, report emails, activity actions, `REPORTER_ROLES`,
  `EVIDENCE_DIR` and the landing page's reporting facts. From the feedback channel: the re-appraisal from a report,
  and "reports per category" on the dashboard and in its CSV. Ratings, corrections with their PDF/JPEG/PNG
  evidence, the committee note and the hold are unchanged.
- **Database:** at start-up, a database made by the old version loses its three report tables, their
  activity-log entries and its evidence folder (`drop_removed_reporting`); accounts and everything else stay. A test
  covers it.
- **Dependencies:** Pillow and imageio-ffmpeg removed from `requirements.txt` (only reporting used them; matplotlib
  still brings Pillow).
- **Evaluation:** `evaluate_reporting.py`, `choose_priority_model.py`, the two labelled report sets and
  `results/reporting_evaluation.*` deleted.
- **Frontend:** the report pages, their components, the key store and the public "Reporting" page deleted; the
  menus, phone tab bars, notification bell, home pages and landing page updated. "Respond to this explanation"
  offers two routes. The landing page's hero offers "Sign in" and "How it works", and its results show PR-AUC and
  the number of inputs instead of the reporting figures.
- **Tests:** 281 (372 before). `test_isolation.py` now covers feedback only: a harsh rating, a pending and a
  rejected correction and a held decision leave every prediction byte-for-byte identical; a confirmed correction
  changes it and is logged; the static check covers `app.feedback`. The browser checks also confirm that no page
  for any of the six roles mentions reporting, and that its old addresses lead back to the overview.
- **Usability study:** the four reporting tasks were replaced (path to promotion, a team member's explanation, the
  feedback dashboard, checking HR's decision), keeping 11 tasks; question e3 now asks whether people understood
  what they could do if they disagreed with their score.
- **Unchanged, checked:** retraining on a copy reproduced `metrics.json`, `fairness.json` and
  `model_comparison.json` byte for byte; the proxy analysis and the explanation evaluation differed only in the
  model's version label.
- **Also fixed on the way:** the browser checks start their throwaway backend in WSL when Windows blocks Python (as
  `run.py` already did); the landing-page check now waits for the page and fetches each screenshot (it passed
  before only because it read the page before any image was drawn).

## "Run predictions for everyone" (2026-10-11)

- The All employees page (HR) and My team (managers) list people with "Not run yet" until **Run predictions for
  all** is clicked. `POST /api/promotion/employees/predict-all` then scores everyone the user may see with the live
  model, in one call, and returns the model version and the time. Nothing is saved.
- While it runs, a progress bar fills and the rows reveal their real scores from the top, paced over 5 seconds so
  people can watch it work. The model itself answers in milliseconds; the page never shows a fake duration. The
  last run stays while the app is open, with "Run again".
- Tests: the endpoint gives the same scores as the list, a manager scores only their team, Finance can't use it; a
  browser check confirms the progress, the 5-second pace and a score on every row afterwards.

## Left to do (by the project owner)

- **Run the usability study** (`docs/USER_TEST.md`, with ethics approval first). Then run
  `python -m evaluation.user_test` and `python -m evaluation.export_feedback_measures`, and report the numbers
  with the number of participants.
- **Fill in the university, team and supervisors** in `frontend/src/brand.js` (`PROJECT`) for the website's
  footer.
- **Push to GitHub** so CI runs.
- **Change `SMTP_SENDER_NAME`** in your private `backend/.env` to MeritLens if emails should carry the new name.
- **Merge the branch** `remove-anonymous-reporting` into `main` once you've checked it.

## Interface in the style of Apple's (2026-10-15)

| Change | Why |
|---|---|
| **Type:** San Francisco on Apple devices, and Inter (variable, with its optical-size axis) elsewhere; iOS-like scale with large bold titles and tighter tracking. | A professional, highly legible typeface that matches the iOS look on every device. |
| **Colour:** white surfaces; Apple's system palette, using its higher-contrast variants for text. One blue (#0071e3) for everything you can tap; teal and orange only for the model's data; green, amber and red only for status. Dark mode follows iOS (black page, grey surfaces). | Bright and clear, with no colour doing two jobs; every text colour meets WCAG AA. |
| **Components:** iPadOS sidebar with a solid-blue selected row; app-icon tiles (blue-to-indigo gradient); capsule buttons; the iOS segmented control; soft cards without heavy outlines; frosted-glass bars (phone bar, tab bar, website header, notification panel, sign-in card). | The familiar iPhone feel the system was asked to have. |
| **Hover and press:** no more buttons jumping up on hover; a quiet colour change on hover and a spring-like press-down. | Calmer, as on iOS. |
| **No wrapped names:** names, buttons, menu items, role labels, table headers and the first column of every table stay on one line (tables scroll sideways on a phone). | Names were breaking across two lines on phones. |
| **Sign-in page:** a frosted card with the app icon, and a blue capsule button. | Consistent with the rest of the app. |

Checked: 18 pages, desktop and phone, light theme: 0 accessibility findings (axe); all 7 browser checks pass.

## UI/UX overhaul: Montserrat, navy and teal, one design system (2026-10-15)

A presentation-layer upgrade only: the backend, the model, API responses, permissions and every feature's
behaviour are unchanged. It replaces the Apple-style interface above. Details, before and after screenshots and
the page-by-page list: `docs/UI_REVIEW.md`. The design system itself: `docs/HOW_IT_WORKS.md`, under "Design system".

- **Montserrat**, installed locally (no Google Fonts), on a 32/24/20/16/14/12 scale with tabular figures.
- **Navy and teal** tokens for light and dark (`frontend/src/tokens.css`). Dark mode follows the computer until
  the toggle is used.
- **One set of shared components** (header, card, stat tile, badge, buttons, inputs, tabs, table with sorting and
  pages, modal, drawer, toast, callout, empty state, skeleton, error state), with the one-off styles removed.
- **App shell:** a navy sidebar grouped per role, a top bar with breadcrumb, bell and profile menu, an icon rail
  from 640 to 1023px, and a drawer on phones.
- **Key pages redesigned:** My growth (gauge, plain-words card, two-sided factors, checklist), the respond panel
  (two route cards), the HR review (side by side, committee note on top), the correction queue, the feedback
  dashboard (charts), Finance's sign-off (review drawer), admin system health, the landing page and sign-in.
- **Scripts:** `ui_capture.js` covers all 39 pages in light and dark, with demo data from `demo_setup.js`; the new
  `capture_thesis.js` saves the thesis figures.

Checked: `npm run build` (no warnings), 322 backend tests, 7 browser checks, and 0 axe findings on 39 pages in both
themes, with nothing wider than a 390px phone.

