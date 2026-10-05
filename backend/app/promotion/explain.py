"""
Predictions and their explanations, for one employee at a time.

The live model is logistic regression, so its output is easy to take apart exactly:

    log-odds = base + sum over inputs of  weight × (value − average value)

Each term in that sum is the input's contribution (this equals its SHAP value for a linear model). "base" is
the log-odds of an employee with average values on every input. The contributions add up exactly to the
prediction, so nothing is hidden or approximated.
"""
import json
import math
from functools import cached_property, lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer
from sklearn.linear_model import LogisticRegression

from app.promotion.features import CATEGORICAL_FEATURES, MODEL_FEATURES, NUMERIC_FEATURES
from app.promotion.labels import FEATURE_INFO, IMPROVABLE, UPPER_LIMIT, format_value, label

MODELS = Path(__file__).resolve().parents[2] / "models"
LOW_LIME_FIT = 0.5  # below this R², LIME's simple local model copies the real one poorly
TIPS_MARGIN = 0.01  # log-odds


class ModelNotTrained(Exception):
    """Raised when train.py has not produced a live model yet."""


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def logit(p: float) -> float:
    return math.log(p / (1 - p))


class PromotionModel:
    """The live model, plus everything needed to explain it."""

    def __init__(self):
        if not (MODELS / "model.joblib").exists():
            raise ModelNotTrained("The model hasn't been trained yet. Run 'python train.py' in the backend folder.")
        self.pipeline = joblib.load(MODELS / "model.joblib")
        self.info = json.loads((MODELS / "model_info.json").read_text())
        self.threshold = self.info["threshold"]
        self.stats = self.info["feature_stats"]
        self.background = pd.read_csv(MODELS / "background.csv")

        prepare, model = self.pipeline.named_steps["prepare"], self.pipeline.named_steps["model"]
        if not isinstance(model, LogisticRegression):
            raise ValueError("Exact contributions need the logistic regression model.")
        self.prepare = prepare
        self.weights = model.coef_[0]
        # Which input each prepared column comes from: "numeric__late_days" -> late_days,
        # "department__department_Finance" -> department (the one-hot columns are combined into one item)
        names = prepare.get_feature_names_out()
        self.column_feature = [n.split("__", 1)[1] if n.startswith("numeric__") else "department" for n in names]
        # Average of each prepared column over the training data: 0 for scaled numbers (scaling centres them),
        # and each department's share of employees for the department columns
        shares = self.info["department_shares"]
        self.column_means = np.array([0.0 if n.startswith("numeric__") else shares.get(n.split("department_", 1)[1], 0.0)
                                      for n in names])
        self.base_logodds = float(model.intercept_[0] + self.weights @ self.column_means)
        # Weight of each number in its own units (change in log-odds per 1 unit), used by the tips
        scale = prepare.named_transformers_["numeric"].scale_
        self.unit_weight = {f: self.weights[i] / scale[i] for i, f in enumerate(NUMERIC_FEATURES)}

    # ─── Prediction ────────────────────────────────────────────────────────────
    def score(self, record: dict) -> float:
        """Readiness score between 0 and 1. Above the threshold, the model recommends promotion."""
        return float(self.pipeline.predict_proba(pd.DataFrame([record])[MODEL_FEATURES])[0, 1])

    # ─── SHAP: exact contributions ─────────────────────────────────────────────
    def contributions(self, record: dict) -> list[dict]:
        """Each input's contribution in log-odds, biggest first, with the employee's real value."""
        prepared = self.prepare.transform(pd.DataFrame([record])[MODEL_FEATURES])[0]
        per_column = self.weights * (prepared - self.column_means)
        totals = {}
        for feature, value in zip(self.column_feature, per_column):
            totals[feature] = totals.get(feature, 0.0) + float(value)
        items = [{
            "feature": feature,
            "label": label(feature),
            "value": record[feature],
            "value_display": format_value(feature, record[feature]),
            "contribution": round(total, 4),
            "effect": "raises" if total > 0 else "lowers",
        } for feature, total in totals.items()]
        return sorted(items, key=lambda c: abs(c["contribution"]), reverse=True)

    # ─── LIME: a second opinion ────────────────────────────────────────────────
    def lime(self, record: dict) -> dict:
        """
        LIME builds a small, simple model around this one employee by trying many slightly different versions
        of their record, then reads simple rules from it. It is an independent check on the explanation.
        """
        departments = sorted(self.info["department_shares"])
        dept_index = MODEL_FEATURES.index("department")

        def encode(df):  # department name -> number, as LIME needs numbers only
            out = df[MODEL_FEATURES].copy()
            out["department"] = out["department"].map(departments.index)
            return out.to_numpy(dtype=float)

        def predict(rows):  # numbers back to a table the model understands
            df = pd.DataFrame(rows, columns=MODEL_FEATURES)
            df["department"] = [departments[int(round(v)) % len(departments)] for v in df["department"]]
            return self.pipeline.predict_proba(df)

        explainer = LimeTabularExplainer(
            encode(self.background), feature_names=[label(f) for f in MODEL_FEATURES], class_names=["not promoted", "promoted"],
            categorical_features=[dept_index], categorical_names={dept_index: departments},
            discretize_continuous=True, random_state=42,  # same answer every time for the same employee
        )
        result = explainer.explain_instance(encode(pd.DataFrame([record]))[0], predict, num_features=5, num_samples=2000)
        fit = float(result.score)
        return {
            "rules": [{"rule": rule, "weight": round(float(w), 4), "effect": "raises" if w > 0 else "lowers"}
                      for rule, w in result.as_list()],
            "fit_r2": round(fit, 3),
            "note": (f"LIME's simple model fits poorly here (R² {fit:.2f}), so treat these rules as a rough guide; "
                     "the contributions above are exact.") if fit < LOW_LIME_FIT else None,
        }

    # ─── Plain-language summary ────────────────────────────────────────────────
    def summary(self, score: float, contributions: list[dict]) -> str:
        """A short paragraph anyone can read."""
        position = "above" if score >= self.threshold else "below"
        verdict = "recommends" if score >= self.threshold else "does not yet recommend"
        text = (f"Readiness is {score:.0%}, {position} the {self.threshold:.0%} threshold, so the model {verdict} "
                "promotion.")
        raising = [c for c in contributions if c["contribution"] > 0][:2]
        lowering = [c for c in contributions if c["contribution"] < 0][:2]
        if raising:
            text += f" Compared with an average employee, it is raised mainly by {join(describe(c) for c in raising)}"
            text += f", and lowered mainly by {join(describe(c) for c in lowering)}." if lowering else "."
        elif lowering:
            text += f" Compared with an average employee, it is lowered mainly by {join(describe(c) for c in lowering)}."
        return text

    # ─── What-if ───────────────────────────────────────────────────────────────
    def slider_range(self, feature: str, current: float) -> tuple[float, float]:
        """Realistic range for a what-if slider: what employees in the training data actually had."""
        low, high = self.stats[feature]["min"], self.stats[feature]["max"]
        high = min(high, UPPER_LIMIT.get(FEATURE_INFO[feature]["unit"], high))
        return min(low, current), max(high, current)

    def apply_changes(self, record: dict, changes: dict) -> dict:
        """
        A copy of the record with hypothetical changes. Only improvable inputs may change, within realistic
        ranges. Raising this year's performance score also raises the change since last year by the same amount.
        """
        new = dict(record)
        for feature, value in changes.items():
            if feature not in IMPROVABLE:
                raise ValueError(f"'{feature}' can't be changed in a what-if.")
            low, high = self.slider_range(feature, record[feature])
            if not isinstance(value, (int, float)) or not low <= value <= high:
                raise ValueError(f"{label(feature)} must be between {low:g} and {high:g}.")
            new[feature] = float(value)
        new["performance_change"] = record["performance_change"] + (new["performance_score"] - record["performance_score"])
        return new

    # ─── Tips to improve ───────────────────────────────────────────────────────
    def tips(self, record: dict) -> dict:
        """
        The smallest realistic improvements that would reach the threshold:
        - only inputs a person can work on, and only in the improving direction;
        - only inputs where improving actually raises the score;
        - each by at most one standard deviation, and not past what the top 5% of employees achieve;
        - the inputs with the biggest possible effect first.
        """
        current = self.score(record)
        gap = logit(self.threshold) - logit(current)
        if gap <= 0:
            return {"already_recommended": True, "tips": [], "reaches_threshold": True,
                    "current_score": round(current, 4), "projected_score": round(current, 4)}

        options = []
        for feature in IMPROVABLE:
            direction = FEATURE_INFO[feature]["improve"]
            # Effect of a 1-unit improvement; this year's score also moves the change-since-last-year
            per_unit = direction * self.unit_weight[feature]
            if feature == "performance_score":
                per_unit += self.unit_weight["performance_change"]
            if per_unit <= 0:
                continue  # improving this wouldn't raise the score, so it's never suggested
            stats = self.stats[feature]
            bound = stats["p95"] if direction > 0 else stats["p5"]
            bound = min(bound, UPPER_LIMIT.get(FEATURE_INFO[feature]["unit"], bound))
            room = min(stats["std"], max(0.0, (bound - record[feature]) * direction))
            if FEATURE_INFO[feature]["whole"]:
                room = math.floor(room)
            if room > 0:
                options.append((per_unit * room, feature, per_unit, room, direction))

        # Aim a little past the threshold, so rounding the suggested values can't leave the result just short
        changes, remaining = {}, gap + TIPS_MARGIN
        for _max_gain, feature, per_unit, room, direction in sorted(options, reverse=True):
            if remaining <= 1e-9:  # gap closed (the tolerance ignores floating-point crumbs)
                break
            step = min(room, remaining / per_unit)
            if FEATURE_INFO[feature]["whole"]:
                step = min(room, math.ceil(step))
            changes[feature] = record[feature] + direction * step
            remaining -= per_unit * step

        projected = self.score(self.apply_changes(record, changes)) if changes else current
        return {
            "already_recommended": False,
            "tips": [{"feature": f, "label": label(f), "from": record[f], "to": v,
                      "from_display": format_value(f, record[f]), "to_display": format_value(f, v)}
                     for f, v in changes.items()],
            "reaches_threshold": projected >= self.threshold,
            "current_score": round(current, 4),
            "projected_score": round(projected, 4),
        }

    # ─── Overall importance ────────────────────────────────────────────────────
    @cached_property
    def importance(self) -> list[dict]:
        """Which inputs matter most across all employees: the average size of each input's contribution."""
        prepared = self.prepare.transform(self.background[MODEL_FEATURES])
        per_column = np.abs(self.weights * (prepared - self.column_means))
        totals = {}
        for i, feature in enumerate(self.column_feature):
            totals[feature] = totals.get(feature, 0.0) + per_column[:, i]
        means = {feature: float(np.mean(values)) for feature, values in totals.items()}
        grand_total = sum(means.values())
        rows = []
        for feature, mean in sorted(means.items(), key=lambda kv: kv[1], reverse=True):
            if feature in CATEGORICAL_FEATURES:
                direction = "depends on the department"
            else:
                direction = "higher raises readiness" if self.unit_weight[feature] > 0 else "higher lowers readiness"
            rows.append({"feature": feature, "label": label(feature), "share": round(mean / grand_total, 4),
                         "direction": direction})
        return rows

    # ─── Everything for one employee ───────────────────────────────────────────
    def explain(self, record: dict, with_lime: bool = True) -> dict:
        score = self.score(record)
        contributions = self.contributions(record)
        return {
            "model": self.info["model"],
            "score": round(score, 4),
            "threshold": self.threshold,
            "recommended": score >= self.threshold,
            "average_employee_score": round(sigmoid(self.base_logodds), 4),
            "base_logodds": round(self.base_logodds, 4),
            "contributions": contributions,
            "lime": self.lime(record) if with_lime else None,
            "summary": self.summary(score, contributions),
            "improvable": [{"feature": f, "label": label(f), "value": record[f],
                            "min": self.slider_range(f, record[f])[0], "max": self.slider_range(f, record[f])[1],
                            "whole": FEATURE_INFO[f]["whole"], "improve": FEATURE_INFO[f]["improve"],
                            "unit": FEATURE_INFO[f]["unit"]}
                           for f in IMPROVABLE],
        }


def describe(contribution: dict) -> str:
    """'leadership score (82)' or, for the performance change, 'a 6.1-point drop in performance since last year'."""
    if contribution["feature"] == "performance_change":
        change = contribution["value"]
        return f"a {abs(change):.1f}-point {'rise' if change >= 0 else 'drop'} in performance since last year"
    return f"{mid_sentence(contribution['label'])} ({contribution['value_display']})"


def mid_sentence(text: str) -> str:
    """'Leadership score' -> 'leadership score', but 'KPI achievement' keeps its capitals."""
    return text if text[:2].isupper() else text[0].lower() + text[1:]


def join(parts) -> str:
    parts = list(parts)
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"


@lru_cache(maxsize=1)
def get_model() -> PromotionModel:
    """The live model, loaded once. Restart the API after retraining to load a new one."""
    return PromotionModel()
