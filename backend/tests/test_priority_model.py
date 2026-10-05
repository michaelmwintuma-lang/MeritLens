"""The language model behind triage: how it's trained and explained, and the safety rules that can only raise it."""
import json
from pathlib import Path

import pytest

from app.reporting import priority_model
from app.reporting.triage import triage

EVALUATION = Path(__file__).resolve().parents[1] / "evaluation"


def test_training_examples_are_separate_from_the_evaluation_sets():
    """The model must never be trained on a report it is evaluated on."""
    texts, labels = priority_model.training_data()
    assert len(texts) >= 250 and set(labels) == set(priority_model.LEVELS)
    for name in ("reports_developer.json", "reports_external.json"):
        evaluated = {r["text"].strip().lower() for r in json.loads((EVALUATION / name).read_text(encoding="utf-8"))["reports"]}
        assert not evaluated & {t.strip().lower() for t in texts}, name


def test_the_reading_gives_a_chance_for_every_level_and_the_words_behind_it():
    reading = priority_model.predict("My supervisor mocks my accent and calls me useless in front of customers.")
    assert reading["priority"] == "medium"
    assert set(reading["chances"]) == {"low", "medium", "high"} and sum(reading["chances"].values()) == pytest.approx(1, abs=0.01)
    assert reading["confidence"] == reading["chances"]["medium"]
    assert reading["words"] and all(w["weight"] > 0 for w in reading["words"])
    assert not {"and", "the", "in"} & {w["word"] for w in reading["words"]}  # filler words aren't listed


def test_the_anonymisers_tags_are_ignored():
    assert priority_model.prepare("[PERSON 1] emailed [EMAIL 2] on [DATE 1]").split() == ["emailed", "on"]


@pytest.mark.parametrize("text", [
    "He said that if I speak up he will make sure I regret it, and he knows where I live.",
    "My colleague has given away her things and says she has no reason to live.",
])
def test_it_reads_danger_without_alarm_words(text):
    assert triage(text, "other")["priority"] == "high"


def test_self_harm_is_never_left_to_the_model_alone():
    result = triage("Lately I feel there is no point in going on and I keep thinking about ending things.", "other")
    assert result["priority"] == "high"
    assert any("Raised to high" in r for r in result["reasons"])


def test_the_safety_rules_raise_but_never_lower():
    calm = "The canteen closes early and the coffee machine is broken."
    assert triage(calm, "other")["priority"] == "low"
    assert triage(calm, "safety")["priority"] == "high"                      # category minimum
    assert triage(calm + " Someone brought a knife in.", "other")["priority"] == "high"  # danger word
