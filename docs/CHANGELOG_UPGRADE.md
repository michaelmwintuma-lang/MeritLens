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
