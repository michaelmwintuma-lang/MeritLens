"""
Fairness check with the four-fifths rule.

For each group (e.g. women and men) we compute the share the model recommends for promotion (the selection rate).
If any group's rate is below 80% of the highest group's rate, the model fails the check.

Alongside the rule (which alone decides pass or fail), each group's accuracy is reported, so a model that selects
groups at similar rates but is more often wrong for one of them can be seen:
- true-positive rate: of the people actually promoted, the share the model recommends (equal opportunity);
- false-positive rate: of the people not promoted, the share the model still recommends;
- precision: of the people the model recommends, the share actually promoted.
The same check is also run on combinations (gender within each age group), where a gap can hide behind two
characteristics that each pass on their own. Combinations are reported, not used to block a release.
"""
import numpy as np
import pandas as pd

FOUR_FIFTHS = 0.8
MIN_COMBINED_GROUP = 30  # combinations smaller than this in the test set are too small to judge


def age_group(age: pd.Series) -> pd.Series:
    """Two age groups: under 40, and 40 or over."""
    return np.where(age < 40, "under 40", "40+")


def share(numerator: pd.Series, mask: pd.Series) -> float | None:
    return round(float(numerator[mask].mean()), 4) if mask.any() else None


def ratio_of(values) -> float | None:
    values = [v for v in values if v is not None]
    if not values:
        return None
    return round(min(values) / max(values), 4) if max(values) > 0 else 1.0


def check_attribute(groups, recommended, actually_promoted, min_group: int = 1) -> dict:
    """
    Selection rate and accuracy per group, the ratio of the lowest to the highest selection rate (and of the
    true-positive rates), and whether the selection ratio passes. Groups under min_group are left out.
    """
    frame = pd.DataFrame({"group": np.asarray(groups), "recommended": np.asarray(recommended).astype(int),
                          "promoted": np.asarray(actually_promoted).astype(int)})
    per_group = {}
    for name, rows in frame.groupby("group"):
        if len(rows) < min_group:
            continue
        promoted, recommended_ = rows["promoted"] == 1, rows["recommended"] == 1
        per_group[str(name)] = {
            "employees": int(len(rows)),
            "selection_rate": round(float(rows["recommended"].mean()), 4),
            "actual_promotion_rate": round(float(rows["promoted"].mean()), 4),  # for context: what really happened
            "true_positive_rate": share(rows["recommended"], promoted),
            "false_positive_rate": share(rows["recommended"], ~promoted),
            "precision": share(rows["promoted"], recommended_),
        }
    ratio = ratio_of(g["selection_rate"] for g in per_group.values())
    fprs = [g["false_positive_rate"] for g in per_group.values() if g["false_positive_rate"] is not None]
    return {"groups": per_group, "ratio": ratio, "passes": bool(ratio is not None and ratio >= FOUR_FIFTHS),
            "true_positive_rate_ratio": ratio_of(g["true_positive_rate"] for g in per_group.values()),
            "false_positive_rate_gap": round(max(fprs) - min(fprs), 4) if fprs else None}


def fairness_report(test_df: pd.DataFrame, recommended) -> dict:
    """Run the check for gender, age group and education on the test set, and on gender within each age group."""
    promoted = test_df["promoted"]
    ages = age_group(test_df["age"])
    checks = {
        "gender": check_attribute(test_df["gender"], recommended, promoted),
        "age_group": check_attribute(ages, recommended, promoted),
        "education": check_attribute(test_df["education_level"], recommended, promoted),
    }
    combined = pd.Series(test_df["gender"].astype(str).to_numpy()) + ", " + pd.Series(ages).astype(str)
    combinations = {"gender_and_age_group": check_attribute(combined, recommended, promoted, MIN_COMBINED_GROUP)}
    return {"rule": f"each group's selection rate must be at least {FOUR_FIFTHS:.0%} of the highest group's",
            "checks": checks, "passes": all(c["passes"] for c in checks.values()),
            "combinations": combinations,
            "combinations_note": f"Reported, not used to block a release; combinations under {MIN_COMBINED_GROUP} people "
                                 "in the test set are left out."}
