"""
Proxy analysis: could the model's 20 inputs stand in for gender, age, education or department, even though none of
these is an input?   python -m evaluation.proxy_analysis   (from the backend folder; results/proxy_analysis.json)

Three checks, on the same 70/10/20 split as training (the test set for the model checks):

1. One input at a time: how strongly each input is linked to each characteristic.
   - gender, age group: standardised mean difference (Cohen's d) between the two groups; |d| < 0.2 is negligible.
   - age (in years): Pearson correlation r; |r| < 0.1 is negligible.
   - education, department: eta squared (share of the input's variance explained by the groups); < 0.01 negligible.
2. All inputs together: can a classifier predict the characteristic from the 20 inputs? Trained on the training set,
   measured on the test set by ROC-AUC (0.5 = no better than guessing; one-vs-rest macro average for several groups).
   Both a linear model and gradient boosting (which finds non-linear combinations) are tried; the higher AUC counts.
   An AUC near 0.5 means the inputs carry no usable trace of the characteristic, so the model can't use it as a proxy.
3. The model itself, on the test set: selection rate (share recommended) and true-positive rate (share of the
   people actually promoted whom the model recommends) for each group, with the lowest-to-highest ratio of each,
   and how strongly the readiness score is linked to each characteristic.
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.promotion.explain import get_model
from app.promotion.fairness import age_group
from app.promotion.features import MODEL_FEATURES, load_dataset, split_data

RESULTS = Path(__file__).resolve().parents[2] / "results"
GROUPS = {"gender": "gender", "age_group": "age_group", "education": "education_level", "department": "department"}


def cohens_d(x: pd.Series, groups: pd.Series) -> float:
    a, b = (x[groups == g] for g in sorted(groups.unique()))
    pooled = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / pooled) if pooled else 0.0


def eta_squared(x: pd.Series, groups: pd.Series) -> float:
    total = ((x - x.mean()) ** 2).sum()
    between = sum(len(v) * (v.mean() - x.mean()) ** 2 for _, v in x.groupby(groups))
    return float(between / total) if total else 0.0


def predictability(train: pd.DataFrame, test: pd.DataFrame, column: str) -> dict:
    """Test-set ROC-AUC of predicting `column` from the 20 inputs, with a linear model and with gradient boosting."""
    out = {}
    for name, model in [("logistic_regression", make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))),
                        ("gradient_boosting", HistGradientBoostingClassifier(random_state=42))]:
        model.fit(train[MODEL_FEATURES], train[column])
        proba = model.predict_proba(test[MODEL_FEATURES])
        if proba.shape[1] == 2:
            auc = roc_auc_score(test[column] == model.classes_[1], proba[:, 1])
        else:
            auc = roc_auc_score(test[column], proba, multi_class="ovr", average="macro")
        out[name] = round(float(auc), 4)
    out["highest"] = max(out.values())
    return out


def rates(groups: pd.Series, recommended: np.ndarray, promoted: pd.Series) -> dict:
    per_group, sel, tpr = {}, [], []
    for g in sorted(groups.unique()):
        mask = (groups == g).to_numpy()
        s = float(recommended[mask].mean())
        t = float(recommended[mask & (promoted == 1).to_numpy()].mean())
        per_group[str(g)] = {"selection_rate": round(s, 4), "true_positive_rate": round(t, 4)}
        sel.append(s), tpr.append(t)
    return {"groups": per_group, "selection_ratio": round(min(sel) / max(sel), 4),
            "true_positive_rate_ratio": round(min(tpr) / max(tpr), 4)}


def analyse() -> dict:
    df = load_dataset()
    df["age_group"] = age_group(df["age"])
    train, _, test = split_data(df)

    per_input = []
    for f in MODEL_FEATURES:
        per_input.append({
            "input": f,
            "gender_d": round(cohens_d(df[f], df["gender"]), 4),
            "age_group_d": round(cohens_d(df[f], df["age_group"]), 4),
            "age_r": round(float(df[f].corr(df["age"])), 4),
            "education_eta2": round(eta_squared(df[f], df["education_level"]), 4),
            "department_eta2": round(eta_squared(df[f], df["department"]), 4),
        })
    largest = {
        "gender_abs_d": max(per_input, key=lambda r: abs(r["gender_d"])),
        "age_group_abs_d": max(per_input, key=lambda r: abs(r["age_group_d"])),
        "age_abs_r": max(per_input, key=lambda r: abs(r["age_r"])),
        "education_eta2": max(per_input, key=lambda r: r["education_eta2"]),
        "department_eta2": max(per_input, key=lambda r: r["department_eta2"]),
    }

    together = {key: predictability(train, test, column) for key, column in GROUPS.items()}

    model = get_model()
    scores = np.array(model.scores(test[MODEL_FEATURES].to_dict("records")))
    recommended = (scores >= model.threshold).astype(int)
    on_model = {key: rates(test[column].reset_index(drop=True), recommended, test["promoted"].reset_index(drop=True))
                for key, column in GROUPS.items()}
    score_link = {
        "gender_d": round(cohens_d(pd.Series(scores), test["gender"].reset_index(drop=True)), 4),
        "age_r": round(float(np.corrcoef(scores, test["age"])[0, 1]), 4),
        "education_eta2": round(eta_squared(pd.Series(scores), test["education_level"].reset_index(drop=True)), 4),
        "department_eta2": round(eta_squared(pd.Series(scores), test["department"].reset_index(drop=True)), 4),
    }
    label_rates = {key: df.groupby(column)["promoted"].mean().round(4).to_dict() for key, column in GROUPS.items()}

    return {"model_version": model.version, "test_employees": len(test),
            "historical_promotion_rate_by_group": label_rates,
            "one_input_at_a_time": {"largest": largest, "all": per_input},
            "all_inputs_together_auc": together,
            "model_on_test_set": on_model, "score_link_to_characteristic": score_link}


def main():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = analyse()
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "proxy_analysis.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("one_input_at_a_time",)}
    summary["largest_single_links"] = result["one_input_at_a_time"]["largest"]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
