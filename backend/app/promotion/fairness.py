"""
Fairness check with the four-fifths rule.

For each group (e.g. women and men) we compute the share the model recommends for promotion (the selection rate).
If any group's rate is below 80% of the highest group's rate, the model fails the check.
"""
import numpy as np
import pandas as pd

FOUR_FIFTHS = 0.8


def age_group(age: pd.Series) -> pd.Series:
    """Two age groups: under 40, and 40 or over."""
    return np.where(age < 40, "under 40", "40+")


def check_attribute(groups, recommended, actually_promoted) -> dict:
    """Selection rate per group, the ratio of the lowest to the highest rate, and whether it passes."""
    frame = pd.DataFrame({"group": np.asarray(groups), "recommended": np.asarray(recommended),
                          "promoted": np.asarray(actually_promoted)})
    per_group = {}
    for name, rows in frame.groupby("group"):
        per_group[str(name)] = {
            "employees": int(len(rows)),
            "selection_rate": round(float(rows["recommended"].mean()), 4),
            "actual_promotion_rate": round(float(rows["promoted"].mean()), 4),  # for context: what really happened
        }
    rates = [g["selection_rate"] for g in per_group.values()]
    ratio = min(rates) / max(rates) if max(rates) > 0 else 1.0
    return {"groups": per_group, "ratio": round(ratio, 4), "passes": bool(ratio >= FOUR_FIFTHS)}


def fairness_report(test_df: pd.DataFrame, recommended) -> dict:
    """Run the check for gender, age group and education on the test set."""
    promoted = test_df["promoted"]
    checks = {
        "gender": check_attribute(test_df["gender"], recommended, promoted),
        "age_group": check_attribute(age_group(test_df["age"]), recommended, promoted),
        "education": check_attribute(test_df["education_level"], recommended, promoted),
    }
    return {"rule": f"each group's selection rate must be at least {FOUR_FIFTHS:.0%} of the highest group's",
            "checks": checks, "passes": all(c["passes"] for c in checks.values())}
