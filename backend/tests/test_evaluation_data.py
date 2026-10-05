"""The labelled reports used in the evaluation are well formed, so a typo in a label can't distort the results."""
import json
from pathlib import Path

import pytest

from app.reporting.routes import CATEGORIES
from app.reporting.triage import LEVELS
from evaluation.evaluate_reporting import SETS, TYPES, evaluate

LABELLED = [(name, json.loads(path.read_text(encoding="utf-8"))["reports"]) for name, path in SETS]


@pytest.mark.parametrize("name,reports", LABELLED)
def test_every_label_matches_its_report(name, reports):
    assert len({r["id"] for r in reports}) == len(reports), "ids must be unique"
    for r in reports:
        assert r["category"] in CATEGORIES and r["priority"] in LEVELS, r["id"]
        for kind, original in r["sensitive"]:
            assert kind in TYPES and original in r["text"], (r["id"], original)  # copied exactly from the text
        for phrase in r["identifying"]:
            assert phrase.lower() in r["text"].lower(), (r["id"], phrase)


def test_the_evaluation_runs_and_counts_every_report():
    reports = LABELLED[0][1]
    result = evaluate(reports)
    assert result["reports"] == len(reports)
    assert sum(sum(row.values()) for row in result["triage"]["confusion"].values()) == len(reports)
    assert result["anonymiser"]["overall"]["labelled"] == sum(len(r["sensitive"]) for r in reports)


# ─── The user-test scoring ────────────────────────────────────────────────────
def test_sus_scoring_follows_the_standard_formula():
    from evaluation.user_test import grade, sus_score
    assert sus_score([3] * 10) == 50.0                         # neutral answers
    assert sus_score([5, 1] * 5) == 100.0                       # best possible
    assert sus_score([1, 5] * 5) == 0.0                         # worst possible
    assert grade(68) == "C" and grade(85) == "A+"
    with pytest.raises(ValueError):
        sus_score([3] * 9)
