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
