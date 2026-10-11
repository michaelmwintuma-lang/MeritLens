"""The user-test questionnaires are scored correctly (SUS, and the perceived-fairness scales)."""
import pytest


# ─── The user-test scoring ────────────────────────────────────────────────────
def test_sus_scoring_follows_the_standard_formula():
    from evaluation.user_test import grade, sus_score
    assert sus_score([3] * 10) == 50.0                         # neutral answers
    assert sus_score([5, 1] * 5) == 100.0                       # best possible
    assert sus_score([1, 5] * 5) == 0.0                         # worst possible
    assert grade(68) == "C" and grade(85) == "A+"
    with pytest.raises(ValueError):
        sus_score([3] * 9)


def test_perceived_fairness_scale_scores_and_alpha():
    from evaluation.user_test import FAIRNESS, cronbach_alpha, fairness_section, scale_score
    keys = list(FAIRNESS["Procedural fairness"])
    assert scale_score({"p1": "4", "p2": "5", "p3": "3", "p4": "4"}, keys) == 4.0
    assert scale_score({"p1": "4", "p2": "", "p3": "3", "p4": "4"}, keys) is None   # incomplete: left out
    # Alpha checked by hand: items 1-3 identical across people gives a high alpha; two people is too few
    assert cronbach_alpha([[1, 1, 1], [3, 3, 3]]) is None
    assert round(cronbach_alpha([[1, 1, 2], [3, 3, 3], [5, 5, 4]]), 3) == 0.96  # 3/2 × (1 − 9/25)
    rows = [{**{k: "4" for k in FAIRNESS["Informational fairness"]}, **{k: "5" for k in keys}}] * 3
    text = "\n".join(fairness_section(rows))
    assert "**Procedural fairness**: mean 5.00 from 3 participants" in text and "3 of 3" in text
