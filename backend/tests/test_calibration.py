"""Calibration: the measures behave as they should on data where the right answer is known, and the live model's is
measured and saved."""
import json
from pathlib import Path

import numpy as np
import pytest

from app.promotion.calibration import calibration_report, wilson_interval

RESULTS = Path(__file__).resolve().parents[2] / "results"


def outcomes_for(scores, seed=0):
    """Outcomes drawn with exactly these probabilities: a perfectly calibrated model by construction."""
    return (np.random.default_rng(seed).random(len(scores)) < scores).astype(int)


@pytest.fixture(scope="module")
def scores():
    return np.random.default_rng(1).beta(1.2, 9, size=40_000)  # skewed like the real scores (~10% promoted)


def test_a_perfectly_calibrated_model_is_recognised(scores):
    report = calibration_report(outcomes_for(scores), scores)
    assert report["ece"] < 0.01 and 0.9 < report["slope"] < 1.1 and abs(report["intercept"]) < 0.2
    assert report["verdict"] == "well calibrated" and report["groups_within_interval"] >= 8
    assert report["brier"] < report["brier_baseline"] and report["brier_skill"] > 0


def test_over_confident_scores_get_a_slope_below_one(scores):
    # True chances are the scores; the "model" pushes them towards 0 and 1 (log-odds doubled)
    y = outcomes_for(scores)
    logit = np.log(scores / (1 - scores))
    report = calibration_report(y, 1 / (1 + np.exp(-2 * logit)))
    assert report["slope"] < 0.7 and report["verdict"] != "well calibrated"


def test_scores_that_are_too_high_everywhere_are_caught(scores):
    # e.g. a model trained with class weights: it ranks well but says 30% when the truth is 10%
    y = outcomes_for(scores)
    report = calibration_report(y, np.clip(scores * 3, 0, 0.99))
    assert report["mean_score"] > 2 * report["base_rate"] and report["ece"] > 0.05
    assert report["verdict"] == "a ranking, not a chance"


def test_the_groups_cover_everyone_in_order():
    s = np.linspace(0.01, 0.9, 1000)
    report = calibration_report(outcomes_for(s), s)
    assert sum(r["count"] for r in report["bins"]) == 1000 and len(report["bins"]) == 10
    means = [r["mean_score"] for r in report["bins"]]
    assert means == sorted(means)


def test_wilson_interval():
    low, high = wilson_interval(0, 100)
    assert low == 0 and 0.03 < high < 0.04            # nobody promoted: still not "exactly 0%"
    low, high = wilson_interval(50, 100)
    assert low < 0.5 < high and high - low == pytest.approx(0.19, abs=0.01)


@pytest.mark.skipif(not (RESULTS / "calibration.json").exists(), reason="run python -m evaluation.calibration first")
def test_the_live_model_is_well_calibrated_on_the_test_set():
    report = json.loads((RESULTS / "calibration.json").read_text())
    assert report["test_size"] == 20_000 and report["verdict"] == "well calibrated"
    assert report["ece"] < 0.02 and 0.8 <= report["slope"] <= 1.2


def test_the_model_card_shows_the_calibration(client):
    from tests.conftest import login
    live = next(r for r in client.get("/api/governance/models", headers=login(client, "hr")).json() if r["status"] == "live")
    card = client.get(f"/api/governance/models/{live['version']}", headers=login(client, "auditor")).json()["card"]
    assert card["calibration"]["verdict"] == "well calibrated" and len(card["calibration"]["bins"]) == 10
