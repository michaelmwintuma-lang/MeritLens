"""
Public facts for the landing page: the model's tested results and fairness check, read from results/.
Nothing about any person is included, so no sign-in is needed.
"""
import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/public", tags=["public"])
RESULTS = Path(__file__).resolve().parents[3] / "results"


@router.get("/summary")
def summary():
    """The numbers the landing page shows, straight from the last training run (or null if not trained yet)."""
    try:
        metrics = json.loads((RESULTS / "metrics.json").read_text())
        fairness = json.loads((RESULTS / "fairness.json").read_text())
    except (OSError, ValueError):
        return {"trained": False}
    return {
        "trained": True,
        "model": metrics["model"],
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metrics["pr_auc"],
        "pr_auc_baseline": metrics["pr_auc_baseline"],
        "test_size": metrics["test_size"],
        "fairness_passes": fairness["passes"],
        "lowest_fairness_ratio": min(check["ratio"] for check in fairness["checks"].values()),
    }
