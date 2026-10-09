"""
Drift: are the employees being scored today still like the ones the model learned from?

For each input, the population stability index (PSI) compares the share of the current employee directory in each
of ten bins with the share of the training sample in the same bins (the bins are the training sample's deciles):

    PSI = sum over bins of (current share − training share) × ln(current share / training share)

A common rule of thumb: below 0.1 the input is stable, 0.1 to 0.25 has shifted moderately, above 0.25 has shifted
a lot and the model's scores for it are less trustworthy (retraining should be considered by people; the system
never retrains by itself). Only the employee directory is read.

PSI is noisy for small groups: 120 employees drawn from the very same data as the training sample can reach 0.18
by chance alone. So for each input the PSI that chance alone gives a group of this size is measured too (the 95th
percentile over random samples of the training data), and an input counts as shifted only if it is above both.
"""
import numpy as np
import pandas as pd

STABLE, SHIFTED = 0.1, 0.25
MIN_RECORDS = 30   # fewer current records than this can't show drift reliably
EPSILON = 1e-4     # an empty bin would make the logarithm infinite


def psi(training: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """The population stability index of one input."""
    edges = np.unique(np.quantile(training, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:  # the input hardly varies in training: nothing to compare
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    expected = np.histogram(training, edges)[0] / len(training)
    actual = np.histogram(current, edges)[0] / len(current)
    expected, actual = np.clip(expected, EPSILON, None), np.clip(actual, EPSILON, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def level(value: float, chance: float = 0.0) -> str:
    """How far an input has moved, counting only what chance alone can't explain."""
    if value < max(STABLE, chance):
        return "stable"
    return "moderate shift" if value <= max(SHIFTED, chance) else "large shift"


def chance_psi(training: np.ndarray, size: int, repeats: int = 40, seed: int = 0) -> float:
    """The PSI that a random group of this size from the training data itself reaches (95th percentile)."""
    rng = np.random.default_rng(seed)
    values = [psi(training, rng.choice(training, size, replace=False)) for _ in range(repeats)]
    return float(np.quantile(values, 0.95))


def drift_report(background: pd.DataFrame, records: list[dict], features: list[str]) -> dict:
    """PSI for every input, the largest first, with the level chance alone reaches, and an overall status."""
    if len(records) < MIN_RECORDS:
        return {"records": len(records), "status": "too few records",
                "note": f"At least {MIN_RECORDS} employees are needed to measure drift.", "inputs": []}
    current = pd.DataFrame(records)
    size = min(len(records), len(background) - 1)
    rows = []
    for f in features:
        training = background[f].to_numpy(float)
        value, chance = psi(training, current[f].to_numpy(float)), chance_psi(training, size)
        rows.append({"feature": f, "psi": round(value, 4), "chance_psi": round(chance, 4), "level": level(value, chance)})
    rows.sort(key=lambda r: -r["psi"])
    order = ["stable", "moderate shift", "large shift"]
    return {"records": len(records), "max_psi": rows[0]["psi"], "status": max((r["level"] for r in rows), key=order.index),
            "shifted": [r["feature"] for r in rows if r["level"] != "stable"], "inputs": rows,
            "note": (f"Each input is compared with what chance alone gives {len(records)} people. With {len(rows)} inputs "
                     f"checked this way, about {len(rows) * 5 // 100} may cross that line by chance even when nothing "
                     "changed, so one or two shifted inputs are a reason to look, not proof of drift.")}
