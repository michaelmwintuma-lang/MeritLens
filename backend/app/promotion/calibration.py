"""
Calibration: when the model gives a score of 30%, are about 30% of such employees really promoted?

Ranking well (ROC-AUC) and being calibrated are different things. A model can put people in the right order yet
say 30% when the true rate is 10%. Calibration decides whether a score may be read as a chance of promotion or only
as a ranking. Measured once, on the test set, with:

- Brier score: the mean squared gap between score and outcome (0 is perfect), compared with always guessing the base
  rate (Brier skill score: the share of that baseline's error the model removes).
- Expected calibration error (ECE): employees are put in ten equal-sized groups by score; in each, the gap between
  the average score and the share actually promoted, weighted by group size. 0.02 means scores are off by about two
  percentage points on average.
- Calibration-in-the-large: the average score against the actual promotion rate.
- Calibration slope and intercept: a logistic regression of the outcome on the score's log-odds. Slope 1 and
  intercept 0 are perfect; a slope below 1 means the scores are too extreme (over-confident), above 1 too timid.
- A reliability table: for each group, the average score, the share promoted and its 95% interval (Wilson).
"""
import math

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

BINS = 10
EPS = 1e-6


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% interval for a share, reliable even for small groups and shares near 0 or 1."""
    if n == 0:
        return 0.0, 1.0
    share = successes / n
    centre = (share + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(share * (1 - share) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def calibration_report(outcome, scores, bins: int = BINS) -> dict:
    y, p = np.asarray(outcome, dtype=float), np.clip(np.asarray(scores, dtype=float), EPS, 1 - EPS)
    base_rate = float(y.mean())
    brier = float(brier_score_loss(y, p))
    brier_baseline = float(brier_score_loss(y, np.full_like(p, base_rate)))

    # Ten equal-sized groups by score (deciles), so every group has enough people to measure its promotion rate
    order = np.argsort(p, kind="stable")
    table, ece = [], 0.0
    for group in np.array_split(order, bins):
        predicted, observed = float(p[group].mean()), float(y[group].mean())
        low, high = wilson_interval(int(y[group].sum()), len(group))
        ece += len(group) / len(p) * abs(predicted - observed)
        table.append({"from": round(float(p[group].min()), 4), "to": round(float(p[group].max()), 4),
                      "count": int(len(group)), "mean_score": round(predicted, 4), "promoted": round(observed, 4),
                      "promoted_low": round(low, 4), "promoted_high": round(high, 4),
                      "within_interval": bool(low <= predicted <= high)})

    log_odds = np.log(p / (1 - p)).reshape(-1, 1)
    fit = LogisticRegression(C=1e6, max_iter=1000).fit(log_odds, y)  # effectively unpenalised
    slope, intercept = float(fit.coef_[0, 0]), float(fit.intercept_[0])
    return {
        "test_size": int(len(y)),
        "base_rate": round(base_rate, 4),
        "mean_score": round(float(p.mean()), 4),
        "brier": round(brier, 4),
        "brier_baseline": round(brier_baseline, 4),
        "brier_skill": round(1 - brier / brier_baseline, 4) if brier_baseline else None,
        "ece": round(ece, 4),
        "slope": round(slope, 3),
        "intercept": round(intercept, 3),
        "bins": table,
        "groups_within_interval": sum(row["within_interval"] for row in table),
        "verdict": verdict(ece, slope),
    }


def verdict(ece: float, slope: float) -> str:
    """
    In words, how far a score may be read as a chance. Thresholds: an average gap under 2 percentage points with a
    slope within 0.8-1.2 is well calibrated; under 5 points is roughly calibrated; otherwise it is a ranking only.
    """
    if ece < 0.02 and 0.8 <= slope <= 1.2:
        return "well calibrated"
    if ece < 0.05:
        return "roughly calibrated"
    return "a ranking, not a chance"


def save_calibration_plot(report: dict, path, name: str) -> None:
    """The reliability diagram: average score against share promoted per group, with the perfect-calibration line."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = report["bins"]
    x = [r["mean_score"] for r in rows]
    y = [r["promoted"] for r in rows]
    err = [[r["promoted"] - r["promoted_low"] for r in rows], [r["promoted_high"] - r["promoted"] for r in rows]]
    top = max(max(x), max(r["promoted_high"] for r in rows)) * 1.08
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.plot([0, top], [0, top], linestyle="--", color="grey", label="Perfectly calibrated")
    ax.errorbar(x, y, yerr=err, fmt="o-", color="#0071e3", ecolor="#8e8e93", capsize=3,
                label=f"{name} (10 groups, 95% intervals)")
    ax.set_xlim(0, top), ax.set_ylim(0, top)
    ax.set_xlabel("Average readiness score in the group")
    ax.set_ylabel("Share actually promoted")
    ax.set_title(f"Calibration, test set (ECE {report['ece']:.3f}, slope {report['slope']:.2f})")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
