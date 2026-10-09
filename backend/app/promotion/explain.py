"""
Predictions and their explanations, for one employee at a time.

The live model is additive: a monotonic Explainable Boosting Machine (EBM) adds up one learned curve per input
(logistic regression, the fallback, adds up one straight line per input). So its output is easy to take apart
exactly:

    log-odds = base + sum over inputs of  (the input's term for this employee − its average term)

Each part of that sum is the input's contribution: how much this employee's value moves the score compared with
an average employee (for an additive model this equals the input's SHAP value). "base" is the log-odds of that
average employee. The contributions add up exactly to the prediction, so nothing is hidden or approximated.
"""
import json
import math
from functools import cached_property, lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer
from interpret.glassbox import ExplainableBoostingClassifier
from sklearn.linear_model import LogisticRegression

from app.promotion.features import MODEL_FEATURES
from app.promotion.labels import FEATURE_INFO, IMPROVABLE, UPPER_LIMIT, format_value, label

MODELS = Path(__file__).resolve().parents[2] / "models"
LOW_LIME_FIT = 0.5  # below this R², LIME's simple local model copies the real one poorly
TIPS_MARGIN = 0.01  # log-odds
TIP_STEPS = 20      # how finely the tips try out improvements of an input that isn't counted in whole numbers


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
        # A short name for this trained model, stored with every score that is recorded (e.g. "v20261008222710")
        self.version = self.info.get("version") or "v" + "".join(ch for ch in self.info["trained_at"] if ch.isdigit())[:14]
        self.stats = self.info["feature_stats"]
        self.background = pd.read_csv(MODELS / "background.csv")

        self.prepare, self.model = self.pipeline.named_steps["prepare"], self.pipeline.named_steps["model"]
        if isinstance(self.model, ExplainableBoostingClassifier):
            if any(len(term) != 1 for term in self.model.term_features_):
                raise ValueError("Exact contributions need an EBM without interaction terms.")
            self.intercept = float(np.ravel(self.model.intercept_)[0])
        elif isinstance(self.model, LogisticRegression):
            self.intercept = float(self.model.intercept_[0])
        else:
            raise ValueError("Exact contributions need an additive model (EBM or logistic regression).")
        # Each input's average term over the training sample: the "average employee" that explanations compare with
        self.average_terms = self.terms(self.background).mean(axis=0)
        self.base_logodds = self.intercept + float(self.average_terms.sum())

    def terms(self, records: pd.DataFrame) -> np.ndarray:
        """Each input's term in the log-odds, one row per record and one column per input (MODEL_FEATURES order)."""
        prepared = self.prepare.transform(records[MODEL_FEATURES])
        if isinstance(self.model, ExplainableBoostingClassifier):
            return np.asarray(self.model.eval_terms(prepared), dtype=float)
        return prepared * self.model.coef_[0]

    # ─── Prediction ────────────────────────────────────────────────────────────
    def score(self, record: dict) -> float:
        """Readiness score between 0 and 1. Above the threshold, the model recommends promotion."""
        return float(self.pipeline.predict_proba(pd.DataFrame([record])[MODEL_FEATURES])[0, 1])

    # ─── SHAP: exact contributions ─────────────────────────────────────────────
    def contributions(self, record: dict) -> list[dict]:
        """Each input's contribution in log-odds, biggest first, with the employee's real value."""
        centred = self.terms(pd.DataFrame([record]))[0] - self.average_terms
        totals = {feature: float(value) for feature, value in zip(MODEL_FEATURES, centred)}
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
        def predict(rows):  # LIME works on plain numbers; the model wants a table
            return self.pipeline.predict_proba(pd.DataFrame(rows, columns=MODEL_FEATURES))

        explainer = LimeTabularExplainer(
            self.background[MODEL_FEATURES].to_numpy(dtype=float), feature_names=[label(f) for f in MODEL_FEATURES],
            class_names=["not promoted", "promoted"], discretize_continuous=True,
            random_state=42,  # same answer every time for the same employee
        )
        row = pd.DataFrame([record])[MODEL_FEATURES].to_numpy(dtype=float)[0]
        result = explainer.explain_instance(row, predict, num_features=5, num_samples=2000)
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
        text = (f"Readiness is {as_percent(score)}, {position} the {self.threshold:.0%} threshold, so the model {verdict} "
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
        - the inputs with the biggest possible effect first, each improved only as far as needed.
        The model's curves needn't be straight lines, so each improvement is tried out on the model itself. As the
        model is additive, the gains from different inputs simply add up.
        """
        current = self.score(record)
        gap = logit(self.threshold) - logit(current)
        if gap <= 0:
            return {"already_recommended": True, "tips": [], "reaches_threshold": True,
                    "current_score": round(current, 4), "projected_score": round(current, 4)}

        # Every improvement worth trying: (input, new value)
        trials = []
        for feature in IMPROVABLE:
            direction, stats = FEATURE_INFO[feature]["improve"], self.stats[feature]
            bound = stats["p95"] if direction > 0 else stats["p5"]
            bound = min(bound, UPPER_LIMIT.get(FEATURE_INFO[feature]["unit"], bound))
            room = min(stats["std"], max(0.0, (bound - record[feature]) * direction))
            if FEATURE_INFO[feature]["whole"]:
                steps = range(1, math.floor(room) + 1)
            else:
                steps = [room * i / TIP_STEPS for i in range(1, TIP_STEPS + 1)] if room > 0 else []
            trials += [(feature, record[feature] + direction * step) for step in steps]
        if not trials:
            return self._tips_result(record, current, {})

        # All of them scored in one go; the gain is the rise in log-odds each would bring on its own
        tried = pd.DataFrame([self.apply_changes(record, {f: v}) for f, v in trials])
        scores = np.clip(self.pipeline.predict_proba(tried[MODEL_FEATURES])[:, 1], 1e-12, 1 - 1e-12)
        gains = np.log(scores / (1 - scores)) - logit(current)
        options = {}
        for (feature, value), gain in zip(trials, gains):
            options.setdefault(feature, []).append((value, float(gain)))

        # Aim a little past the threshold, so rounding can't leave the result just short
        changes, remaining = {}, gap + TIPS_MARGIN
        for feature, tried_values in sorted(options.items(), key=lambda kv: max(g for _, g in kv[1]), reverse=True):
            if remaining <= 1e-9:  # gap closed (the tolerance ignores floating-point crumbs)
                break
            useful = [(value, gain) for value, gain in tried_values if gain > 1e-9]
            if not useful:
                continue  # improving this wouldn't raise the score, so it's never suggested
            enough = [(value, gain) for value, gain in useful if gain >= remaining]
            value, gain = enough[0] if enough else max(useful, key=lambda vg: vg[1])
            changes[feature] = value
            remaining -= gain
        return self._tips_result(record, current, changes)

    def _tips_result(self, record: dict, current: float, changes: dict) -> dict:
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
        """
        Which inputs matter most across all employees: the average size of each input's contribution. The direction
        comes from the shape of the input's curve, read across its realistic range.
        """
        centred = np.abs(self.terms(self.background) - self.average_terms)
        means = dict(zip(MODEL_FEATURES, centred.mean(axis=0)))
        grand_total = sum(means.values())
        return [{"feature": feature, "label": label(feature), "share": round(float(mean / grand_total), 4),
                 "direction": self.direction(feature)}
                for feature, mean in sorted(means.items(), key=lambda kv: kv[1], reverse=True)]

    def direction(self, feature: str) -> str:
        """'higher raises readiness', 'higher lowers readiness', 'depends on the level' or 'no effect'."""
        grid = self.background[feature].quantile(np.linspace(0.01, 0.99, 25)).to_numpy()
        rows = pd.DataFrame([self.background[MODEL_FEATURES].median()] * len(grid))
        rows[feature] = grid
        steps = np.diff(self.terms(rows)[:, MODEL_FEATURES.index(feature)])
        if np.all(np.abs(steps) < 1e-9):
            return "no effect"
        if np.all(steps >= -1e-9):
            return "higher raises readiness"
        if np.all(steps <= 1e-9):
            return "higher lowers readiness"
        return "depends on the level"

    # ─── Everything for one employee ───────────────────────────────────────────
    def explain(self, record: dict, with_lime: bool = True) -> dict:
        score = self.score(record)
        contributions = self.contributions(record)
        return {
            "model": self.info["model"],
            "model_version": self.version,
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


def as_percent(share: float) -> str:
    """'23%', or 'under 1%' for something above zero that would round to 0% (as on the website)."""
    return "under 1%" if 0 < share < 0.005 else f"{share:.0%}"


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
