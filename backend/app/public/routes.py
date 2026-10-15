"""
Public facts for the landing page: the model's tested results and its fairness check, read from the files the
training script wrote. Nothing about any person is included, so no sign-in is needed. A number that hasn't been
measured yet is left out, never filled in.
"""
import json
from pathlib import Path

from fastapi import APIRouter

from app.core.config import MODELS_DIR as MODELS, RESULTS_DIR as RESULTS

router = APIRouter(prefix="/api/public", tags=["public"])


def read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


@router.get("/summary")
def summary():
    """The numbers the landing page shows, straight from the last training and evaluation runs."""
    metrics, fairness, info = read(RESULTS / "metrics.json"), read(RESULTS / "fairness.json"), read(MODELS / "model_info.json")
    if not (metrics and fairness and info):
        return {"trained": False}
    return {
        "trained": True,
        "model": metrics["model"],
        "inputs": len(info["features"]),
        "threshold": info["threshold"],
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metrics["pr_auc"],
        "pr_auc_baseline": metrics["pr_auc_baseline"],
        "test_size": metrics["test_size"],
        "fairness_passes": fairness["passes"],
        "lowest_fairness_ratio": min(check["ratio"] for check in fairness["checks"].values()),
    }
