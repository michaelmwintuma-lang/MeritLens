"""Step 2 tests: model inputs, the data split, the model-choice rule, the threshold, fairness, and saved results."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from app.promotion.fairness import age_group, check_attribute
from app.promotion.features import EXCLUDED, FAIRNESS_ONLY, MODEL_FEATURES, TARGET, load_dataset, split_data
from app.promotion.modeling import LOGISTIC_REGRESSION, best_f1_threshold, choose_model

BACKEND = Path(__file__).resolve().parents[1]
RESULTS = BACKEND.parent / "results"
MODELS = BACKEND / "models"


@pytest.fixture(scope="module")
def data():
    return load_dataset()


# ─── Model inputs ─────────────────────────────────────────────────────────────
def test_protected_characteristics_and_pay_are_never_model_inputs():
    for column in ["gender", "age", "education_level", "marital_status", "salary", "salary_increase_percent",
                   "bonus_last_year", "stock_options"]:
        assert column not in MODEL_FEATURES
    assert set(FAIRNESS_ONLY) <= set(EXCLUDED)


def test_every_column_is_either_used_or_excluded_with_a_reason(data):
    accounted = set(MODEL_FEATURES) | set(EXCLUDED) | {TARGET, "employee_id"}
    assert set(data.columns) == accounted
    assert not set(MODEL_FEATURES) & set(EXCLUDED)


def test_performance_change_replaces_the_yearly_scores(data):
    row = data.iloc[0]
    assert row["performance_change"] == pytest.approx(row["performance_score"] - row["performance_last_year"])
    assert "performance_last_year" not in MODEL_FEATURES and "performance_two_years_ago" not in MODEL_FEATURES


# ─── Split ────────────────────────────────────────────────────────────────────
def test_split_is_70_10_20_stratified_and_disjoint(data):
    train, val, test = split_data(data)
    assert (len(train), len(val), len(test)) == (70_000, 10_000, 20_000)
    for part in (train, val, test):
        assert part[TARGET].mean() == pytest.approx(data[TARGET].mean(), abs=0.002)
    ids = [set(p["employee_id"]) for p in (train, val, test)]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])


def test_split_is_reproducible(data):
    first, second = split_data(data), split_data(data)
    assert list(first[2]["employee_id"]) == list(second[2]["employee_id"])


# ─── Choosing the model ───────────────────────────────────────────────────────
def test_logistic_regression_is_preferred_when_within_the_margin():
    chosen, reason = choose_model({LOGISTIC_REGRESSION: 0.640, "Random Forest": 0.645, "XGBoost": 0.648})
    assert chosen == LOGISTIC_REGRESSION and "within" in reason


def test_a_clearly_better_model_wins():
    chosen, _ = choose_model({LOGISTIC_REGRESSION: 0.60, "Random Forest": 0.62, "XGBoost": 0.65})
    assert chosen == "XGBoost"


def test_best_f1_threshold_separates_clean_data():
    y = np.array([0, 0, 0, 0, 1, 1])
    scores = np.array([0.1, 0.2, 0.3, 0.4, 0.8, 0.9])
    threshold = best_f1_threshold(y, scores)
    assert ((scores >= threshold) == y.astype(bool)).all()


# ─── Fairness ─────────────────────────────────────────────────────────────────
def test_four_fifths_rule_passes_and_fails_correctly():
    groups = ["a"] * 10 + ["b"] * 10
    promoted = [0] * 20
    # a: 5 of 10 recommended (50%), b: 4 of 10 (40%) -> ratio 0.8 -> passes
    assert check_attribute(groups, [1] * 5 + [0] * 5 + [1] * 4 + [0] * 6, promoted)["passes"]
    # b: 3 of 10 (30%) -> ratio 0.6 -> fails
    result = check_attribute(groups, [1] * 5 + [0] * 5 + [1] * 3 + [0] * 7, promoted)
    assert not result["passes"] and result["ratio"] == pytest.approx(0.6)


def test_age_groups():
    assert list(age_group(pd.Series([25, 39, 40, 61]))) == ["under 40", "under 40", "40+", "40+"]


# ─── Saved results (after running train.py) ───────────────────────────────────
needs_training = pytest.mark.skipif(not (MODELS / "model_info.json").exists(), reason="run train.py first")


@needs_training
def test_saved_threshold_and_metrics_load_correctly():
    info = json.loads((MODELS / "model_info.json").read_text())
    metrics = json.loads((RESULTS / "metrics.json").read_text())
    assert 0 < info["threshold"] < 1 and info["threshold"] == metrics["threshold"]
    assert info["features"] == MODEL_FEATURES
    for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "pr_auc_baseline", "confusion_matrix"]:
        assert key in metrics
    assert metrics["pr_auc"] > metrics["pr_auc_baseline"]
    assert sum(metrics["confusion_matrix"].values()) == metrics["test_size"]
    for image in ["roc_curve.png", "pr_curve.png"]:
        assert (RESULTS / image).stat().st_size > 0


@needs_training
def test_live_model_passed_the_fairness_check_and_predicts(data):
    assert json.loads((RESULTS / "fairness.json").read_text())["passes"]
    model = joblib.load(MODELS / "model.joblib")
    scores = model.predict_proba(data[MODEL_FEATURES].head(5))[:, 1]
    assert ((scores >= 0) & (scores <= 1)).all()
