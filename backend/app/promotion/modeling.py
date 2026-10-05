"""The three candidate models, the rule for choosing one, the decision threshold, and test-set metrics."""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from app.promotion.features import RANDOM_STATE, build_preprocessor

LOGISTIC_REGRESSION = "Logistic Regression"
# How close (in validation PR-AUC) logistic regression must be to the best model to be preferred
PREFER_SIMPLE_MARGIN = 0.01


def make_models(positive_share: float) -> dict:
    """
    The three candidates, each behind the same preprocessing. Only ~10% of employees were promoted, so every model
    gives the rare "promoted" class more weight (class weights) instead of copying rows (oversampling).
    """
    negatives_per_positive = (1 - positive_share) / positive_share
    candidates = {
        LOGISTIC_REGRESSION: LogisticRegression(class_weight="balanced", max_iter=2000),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced",
                                                n_jobs=2, random_state=RANDOM_STATE),
        "XGBoost": XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.1, scale_pos_weight=negatives_per_positive,
                                 eval_metric="logloss", n_jobs=2, random_state=RANDOM_STATE),
    }
    return {name: Pipeline([("prepare", build_preprocessor()), ("model", model)]) for name, model in candidates.items()}


def choose_model(val_pr_auc: dict) -> tuple[str, str]:
    """
    Pick the model to use, from each model's PR-AUC on the validation set. Logistic regression is the easiest to
    explain (each feature has one weight), so it is chosen whenever it is within PREFER_SIMPLE_MARGIN of the best.
    Returns the chosen name and the reason in words.
    """
    best = max(val_pr_auc, key=val_pr_auc.get)
    gap = val_pr_auc[best] - val_pr_auc[LOGISTIC_REGRESSION]
    if best == LOGISTIC_REGRESSION:
        return best, "Logistic Regression has the highest validation PR-AUC."
    if gap <= PREFER_SIMPLE_MARGIN:
        return LOGISTIC_REGRESSION, (f"{best} scores highest, but Logistic Regression is only {gap:.4f} behind "
                                     f"(within {PREFER_SIMPLE_MARGIN}), so the easier-to-explain model is chosen.")
    return best, f"{best} is {gap:.4f} ahead of Logistic Regression, more than the {PREFER_SIMPLE_MARGIN} margin."


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
