"""
Public facts for the landing page: the model's tested results, its fairness check and the reporting evaluation,
read from the files the training and evaluation scripts wrote. Nothing about any person is included, so no sign-in
is needed. A number that hasn't been measured yet is left out (null), never filled in.
"""
import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/public", tags=["public"])
RESULTS = Path(__file__).resolve().parents[3] / "results"
MODELS = Path(__file__).resolve().parents[2] / "models"


def read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def reporting_facts() -> dict:
    """The anonymiser's and triage's results on the developer evaluation set (backend/evaluation/)."""
    evaluation = read(RESULTS / "reporting_evaluation.json")
    try:
        developer = evaluation["developer"]
        return {"anonymiser_recall": developer["anonymiser"]["overall"]["recall"],
                "urgent_caught": developer["triage"]["confusion"]["high"]["high"],
                "urgent_total": developer["triage"]["per_class"]["high"]["count"]}
    except (TypeError, KeyError):
        return {"anonymiser_recall": None, "urgent_caught": None, "urgent_total": None}


@router.get("/summary")
def summary():
    """The numbers the landing page shows, straight from the last training and evaluation runs."""
    metrics, fairness, info = read(RESULTS / "metrics.json"), read(RESULTS / "fairness.json"), read(MODELS / "model_info.json")
    if not (metrics and fairness and info):
        return {"trained": False, **reporting_facts()}
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
        **reporting_facts(),
    }
