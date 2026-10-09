"""
Evaluate the explanations on the 120 demo employees (taken from the test set, never seen in training):
python -m evaluation.evaluate_explanations      (from the backend folder; results/explanation_evaluation.json)

- Exactness: the largest gap between base + sum of contributions and the model's own log-odds.
- Common sense: for every employee and every input a person can improve, does improving it by one standard deviation
  ever lower the score?
- LIME (the second opinion): its fit (R²) to the model around each employee; median and share below 0.5.
- Agreement: how often LIME's top rule names one of the five largest exact contributions.
- Tips: for employees not yet recommended, how often the suggested steps reach the threshold.
"""
import json
import statistics
from pathlib import Path

from app.promotion.explain import LOW_LIME_FIT, get_model, logit
from app.promotion.features import NUMERIC_FEATURES
from app.promotion.labels import FEATURE_INFO, IMPROVABLE
from app.promotion.seed import demo_rows

RESULTS = Path(__file__).resolve().parents[2] / "results"


def evaluate() -> dict:
    model = get_model()
    records = [{f: float(row[f]) for f in NUMERIC_FEATURES} for row in demo_rows()]

    gaps, violations, checks = [], 0, 0
    fits, agree, tips = [], 0, []
    for record in records:
        contributions = model.contributions(record)
        score = model.score(record)
        gaps.append(abs(model.base_logodds + sum(c["contribution"] for c in contributions) - logit(score)))

        for feature in IMPROVABLE:
            step = FEATURE_INFO[feature]["improve"] * model.stats[feature]["std"]
            better = record | {feature: record[feature] + step}
            if feature == "performance_score":
                better["performance_change"] += step
            checks += 1
            violations += model.score(better) < score - 1e-9

        lime = model.lime(record)
        fits.append(lime["fit_r2"])
        top_five = {c["label"] for c in contributions[:5]}
        agree += any(label in lime["rules"][0]["rule"] for label in top_five)

        if score < model.threshold:
            tips.append(model.tips(record)["reaches_threshold"])

    return {
        "model": model.info["model"], "model_version": model.version, "employees": len(records),
        "exactness": {"largest_gap_log_odds": round(max(gaps), 6),
                      "note": "contributions are rounded to 4 decimals; 20 of them can differ by up to 0.001 in total"},
        "common_sense": {"checks": checks, "violations": violations},
        "lime": {"median_fit_r2": round(statistics.median(fits), 3),
                 "share_below_0_5": round(sum(f < LOW_LIME_FIT for f in fits) / len(fits), 3),
                 "top_rule_names_a_top_five_factor": round(agree / len(records), 3)},
        "tips": {"not_yet_recommended": len(tips), "reach_threshold": sum(tips),
                 "share": round(sum(tips) / len(tips), 3) if tips else None},
    }


def main():
    result = evaluate()
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "explanation_evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
