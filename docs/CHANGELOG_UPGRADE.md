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
