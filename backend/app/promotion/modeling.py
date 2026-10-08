"""The candidate models, the common-sense check, the rule for choosing one, the decision threshold, and test metrics."""
import numpy as np
import pandas as pd
from interpret.glassbox import ExplainableBoostingClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from app.promotion.features import MONOTONE, NUMERIC_FEATURES, RANDOM_STATE, build_preprocessor

EBM = "EBM (monotonic)"
LOGISTIC_REGRESSION = "Logistic Regression"
# Easiest to explain first. The EBM and logistic regression are both "glass boxes": the score is a sum of one term
# per input, so every explanation is exact. The EBM comes first because its monotonic constraints also guarantee
# that improving something never lowers the score. The tree ensembles can only be explained approximately.
EXPLAINABILITY_ORDER = [EBM, LOGISTIC_REGRESSION, "Random Forest", "XGBoost"]
# How close (in validation PR-AUC) an easier-to-explain model must be to the best one to be preferred
PREFER_SIMPLE_MARGIN = 0.01
# The common-sense check moves each input by this many standard deviations in its improving direction
PROBE_STEP_SD = 0.5


def make_models(positive_share: float) -> dict:
    """
    The four candidates, each behind the same preprocessing. Only ~10% of employees were promoted, so the models
    that support it give the rare "promoted" class more weight (class weights) instead of copying rows. The EBM
    has no class weights; the decision threshold, chosen on validation data, makes up for that.
    """
    negatives_per_positive = (1 - positive_share) / positive_share
    candidates = {
        # interactions=0: one term per input and nothing else, so each explanation adds up exactly
        EBM: ExplainableBoostingClassifier(interactions=0, outer_bags=4, n_jobs=2, random_state=RANDOM_STATE,
                                           monotone_constraints=[MONOTONE[f] for f in NUMERIC_FEATURES]),
        LOGISTIC_REGRESSION: LogisticRegression(class_weight="balanced", max_iter=2000),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced",
                                                n_jobs=2, random_state=RANDOM_STATE),
        "XGBoost": XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.1, scale_pos_weight=negatives_per_positive,
                                 eval_metric="logloss", n_jobs=2, random_state=RANDOM_STATE),
    }
    return {name: Pipeline([("prepare", build_preprocessor()), ("model", model)]) for name, model in candidates.items()}


def common_sense_violations(model, data: pd.DataFrame, n_probe: int = 2000) -> dict:
    """
    How often improving one input lowers the score. For a sample of employees, each constrained input is moved half
    a standard deviation in its improving direction (more training, fewer late days); a "violation" is any
    employee whose score then drops. Raising this year's performance score also raises the change since last year,
    as in the what-if. Returns the overall share of violations and the share for each input that had any.
    """
    sample = data[NUMERIC_FEATURES].sample(min(n_probe, len(data)), random_state=RANDOM_STATE)
    before = model.predict_proba(sample)[:, 1]
    per_feature, violations, total = {}, 0, 0
    for feature, direction in MONOTONE.items():
        if direction == 0:
            continue
        step = PROBE_STEP_SD * float(data[feature].std()) * direction
        moved = sample.copy()
        moved[feature] += step
        if feature == "performance_score":
            moved["performance_change"] += step
        wrong = int((model.predict_proba(moved)[:, 1] - before < -1e-9).sum())
        per_feature[feature] = round(wrong / len(sample), 4)
        violations, total = violations + wrong, total + len(sample)
    return {"rate": round(violations / total, 4), "by_input": {f: v for f, v in per_feature.items() if v > 0}}


def choose_model(val_pr_auc: dict, violation_rate: dict | None = None) -> tuple[str, str]:
    """
    Pick the model to use, from each model's validation results:
    1. Common sense first: only models that never lowered a score when an input improved (no violations on the
       validation set) are eligible. If none qualifies, all stay eligible and the reason says so.
    2. Among those, the easiest to explain (EXPLAINABILITY_ORDER) whose PR-AUC is within PREFER_SIMPLE_MARGIN of
       the best eligible model.
    Returns the chosen name and the reason in words.
    """
    violation_rate = violation_rate or {}
    eligible = [name for name in val_pr_auc if violation_rate.get(name, 0.0) == 0.0] or list(val_pr_auc)
    excluded = [name for name in val_pr_auc if name not in eligible]
    best = max(eligible, key=val_pr_auc.get)
    close = [name for name in eligible if val_pr_auc[best] - val_pr_auc[name] <= PREFER_SIMPLE_MARGIN]
    order = lambda name: EXPLAINABILITY_ORDER.index(name) if name in EXPLAINABILITY_ORDER else len(EXPLAINABILITY_ORDER)
    chosen = min(close, key=order)

    reason = ""
    if excluded:
        reason = (f"{', '.join(excluded)} lowered some scores when an input improved, so "
                  f"{'it was' if len(excluded) == 1 else 'they were'} not eligible. ")
    elif violation_rate and all(rate > 0 for rate in violation_rate.values()):
        reason = "Every model lowered some scores when an input improved, so all stayed eligible. "
    if chosen == best:
        reason += f"{chosen} has the highest validation PR-AUC among the eligible models."
    else:
        gap = val_pr_auc[best] - val_pr_auc[chosen]
        reason += (f"{best} scores highest, but {chosen} is only {gap:.4f} behind (within {PREFER_SIMPLE_MARGIN}), "
                   "so the easier-to-explain model is chosen.")
    return chosen, reason


def best_f1_threshold(y_true, scores) -> float:
    """The score cut-off with the highest F1 (balance of precision and recall), found on the validation set."""
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    f1 = 2 * precision * recall / np.clip(precision + recall, 1e-12, None)
    # The last precision/recall pair has no threshold, so it is left out
    return float(thresholds[int(np.argmax(f1[:-1]))])


def test_metrics(y_true, scores, threshold: float) -> dict:
    """Every number reported for the final model, computed once on the test set."""
    predicted = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted).ravel()
    return {
        "threshold": round(threshold, 4),
        "accuracy": round(accuracy_score(y_true, predicted), 4),
        "precision": round(precision_score(y_true, predicted), 4),
        "recall": round(recall_score(y_true, predicted), 4),
        "f1": round(f1_score(y_true, predicted), 4),
        "roc_auc": round(roc_auc_score(y_true, scores), 4),
        "pr_auc": round(average_precision_score(y_true, scores), 4),
        # PR-AUC of a model that guesses at random equals the share of promoted employees
        "pr_auc_baseline": round(float(np.mean(y_true)), 4),
        "share_recommended": round(float(predicted.mean()), 4),
        "confusion_matrix": {"true_positives": int(tp), "false_positives": int(fp),
                             "false_negatives": int(fn), "true_negatives": int(tn)},
        "test_size": int(len(y_true)),
    }
