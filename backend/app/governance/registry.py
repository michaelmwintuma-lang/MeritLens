"""
The model registry: every trained model version, its model card, and a human release step.

Training (train.py) never changes the live model by itself. It registers a *candidate* in
backend/models/registry/<version>/ with everything needed to judge it:

    model.joblib, model_info.json, background.csv   the model itself, exactly as it would be served
    card.json                                       the model card: data, mapping, method, test results,
                                                    fairness, intended use and limitations
    results/                                        metrics, fairness, model comparison and curves

A candidate that failed the fairness check is *blocked*: it can never be released. One that passed waits for a
named HR person to read its card and release it with a written note. Releasing copies it into the live folder
(backend/models/) and its results into results/, records who released it, why and what it replaced (in the
database and the audit trail), and the app switches to it without a restart. An older version can be released
again the same way, which is how a release is rolled back.
"""
import json
import os
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit, jobs
from app.core.config import MODEL_REGISTRY_DIR, MODELS_DIR, RESULTS_DIR
from app.governance.models import ModelRelease
from app.promotion.models import ReviewCycle
from app.promotion.explain import reload_model, version_of

MODEL_FILES = ("model.joblib", "model_info.json", "background.csv")
RESULT_FILES = ("metrics.json", "fairness.json", "model_comparison.json", "calibration.json", "roc_curve.png",
                "pr_curve.png", "calibration_curve.png")
MIN_NOTE = 20

INTENDED_USE = (
    "Decision support for promotion readiness: it advises managers and HR, who make every decision. Not for "
    "automatic decisions, pay, dismissal or any use outside promotion readiness.")
LIMITATIONS = [
    "It predicts past promotion decisions in its training data, not true readiness, and can carry their habits.",
    "Its results describe its training data only; another organisation's data needs retraining and checking.",
    "Group fairness (four-fifths rule) is checked per characteristic, not for combinations or individuals.",
    "Explanations describe the model, not causes: a tip is what would change the model's view.",
]


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def live_version() -> str | None:
    info = read_json(MODELS_DIR / "model_info.json")
    return version_of(info) if info else None


def version_dir(version: str) -> Path:
    if not version.startswith("v") or not version[1:].isdigit():
        raise ValueError("Not a model version.")
    return MODEL_REGISTRY_DIR / version


def make_card(info: dict, metrics: dict, fairness: dict, comparison: dict | None, data: dict | None,
              mapping: dict | None, calibration: dict | None = None) -> dict:
    """The model card: everything a person needs to judge a model before it is used."""
    return {
        "version": info["version"], "model": info["model"], "trained_at": info["trained_at"],
        "why_this_model": info.get("reason"), "threshold": info["threshold"],
        "threshold_rule": "the best F1 on the validation set", "inputs": info["features"],
        "data": data, "mapping": mapping,
        "test_results": metrics, "fairness": fairness, "calibration": calibration,
        "model_comparison": comparison,
        "fairness_passes": bool(fairness and fairness.get("passes")),
        "intended_use": INTENDED_USE, "limitations": LIMITATIONS,
    }


def register(source_dir: Path, results_dir: Path, card: dict) -> Path:
    """
    Store a newly trained version (its files are in source_dir and results_dir) in the registry. Used by train.py.
    Returns the version's folder.
    """
    target = version_dir(card["version"])
    (target / "results").mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        if (source_dir / name).exists():
            shutil.copy2(source_dir / name, target / name)
    for name in RESULT_FILES:
        if (results_dir / name).exists():
            shutil.copy2(results_dir / name, target / "results" / name)
    (target / "card.json").write_text(json.dumps(card, indent=2))
    return target


def proxy_summary(analysis: dict) -> dict:
    """What the model card shows of the proxy analysis: can the inputs stand in for a characteristic?"""
    together = analysis["all_inputs_together_auc"]
    return {
        "test_employees": analysis["test_employees"],
        # How well a classifier predicts each characteristic from all inputs together (0.5 = guessing)
        "predictability_auc": {k: v["highest"] for k, v in together.items()},
        "largest_single_links": analysis["one_input_at_a_time"]["largest"],
        "score_link_to_characteristic": analysis["score_link_to_characteristic"],
    }


def ensure_live_registered() -> None:
    """
    A live model trained before the registry existed is registered once, from the live folder and results/, so the
    registry always lists the version in use.
    """
    version = live_version()
    if version is None or (version_dir(version) / "card.json").exists():
        return
    info = {**read_json(MODELS_DIR / "model_info.json"), "version": version}
    metrics, fairness = read_json(RESULTS_DIR / "metrics.json"), read_json(RESULTS_DIR / "fairness.json")
    calibration = read_json(RESULTS_DIR / "calibration.json")
    if calibration and calibration.get("model_version") != version:
        calibration = None  # measured for another version: not this one's
    card = make_card(info, metrics or {}, fairness or {}, read_json(RESULTS_DIR / "model_comparison.json"),
                     {"note": "Trained before the model registry existed; data: the Kaggle dataset in backend/data."},
                     None, {k: v for k, v in calibration.items() if k not in ("model", "model_version")} if calibration else None)
    card["registered_note"] = "Registered automatically: this version was live before the model registry existed."
    proxy = read_json(RESULTS_DIR / "proxy_analysis.json")
    if proxy and proxy.get("model_version") == version:
        card["proxy_analysis"] = proxy_summary(proxy)
    register(MODELS_DIR, RESULTS_DIR, card)


def card(version: str) -> dict | None:
    return read_json(version_dir(version) / "card.json")


def status_of(version: str, live: str | None, released: set[str], card_data: dict) -> str:
    if version == live:
        return "live"
    if not card_data.get("fairness_passes"):
        return "blocked"
    return "retired" if version in released else "candidate"


def releases(db: Session) -> list[ModelRelease]:
    return list(db.scalars(select(ModelRelease).order_by(ModelRelease.released_at.desc(), ModelRelease.id.desc())))


def list_versions(db: Session) -> list[dict]:
    """Every registered version, newest first, with its status and headline results."""
    live, history = live_version(), releases(db)
    released = {r.version for r in history}
    last_release = {}
    for r in reversed(history):
        last_release[r.version] = r
    rows = []
    if MODEL_REGISTRY_DIR.exists():
        for folder in MODEL_REGISTRY_DIR.iterdir():
            data = read_json(folder / "card.json")
            if not data:
                continue
            metrics, fairness = data.get("test_results") or {}, data.get("fairness") or {}
            ratios = [c["ratio"] for c in fairness.get("checks", {}).values()]
            release = last_release.get(data["version"])
            rows.append({
                "version": data["version"], "model": data["model"], "trained_at": data["trained_at"],
                "status": status_of(data["version"], live, released, data), "threshold": data["threshold"],
                "roc_auc": metrics.get("roc_auc"), "pr_auc": metrics.get("pr_auc"),
                "fairness_passes": data.get("fairness_passes", False),
                "lowest_fairness_ratio": min(ratios) if ratios else None,
                "released_by": release.released_by_name if release else None,
                "released_at": release.released_at.isoformat(timespec="seconds") if release else None,
                "data_name": (data.get("mapping") or {}).get("name") or (data.get("data") or {}).get("note"),
            })
    return sorted(rows, key=lambda r: r["trained_at"], reverse=True)


def _copy_atomically(source: Path, target: Path) -> None:
    """Copy to a temporary name next to the target, then swap it in, so a reader never sees half a file."""
    temporary = target.with_name(f".{target.name}.incoming")
    shutil.copy2(source, temporary)
    os.replace(temporary, target)


def check_release(db: Session, version: str, note: str) -> dict:
    """
    The checks before a release, returning the version's card. Refused for a version that failed the fairness check,
    while a review cycle is open, for the version already live, or without a note of at least MIN_NOTE characters.
    """
    data = card(version)
    if data is None:
        raise LookupError("No such model version.")
    if not data.get("fairness_passes"):
        raise PermissionError("This version failed the fairness check, so it can never be released.")
    open_cycle = db.scalar(select(ReviewCycle).where(ReviewCycle.status == "open"))
    if open_cycle is not None:
        raise PermissionError(f"The review cycle “{open_cycle.name}” is open. Close it before releasing a model, so "
                              "everyone in a cycle is scored by the same model.")
    if version == live_version():
        raise ValueError("This version is already live.")
    if len(note.strip()) < MIN_NOTE:
        raise ValueError(f"Please say why you are releasing it, in at least {MIN_NOTE} characters.")
    return data


def release(db: Session, version: str, user, note: str) -> ModelRelease:
    """Make a registered version the live model, after the checks (check_release). The caller commits."""
    data = check_release(db, version, note)
    previous = live_version()
    folder = version_dir(version)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # The model's info file goes last: it names the live version, so it changes only once the rest is in place
    for name in ("background.csv", "model.joblib", "model_info.json"):
        _copy_atomically(folder / name, MODELS_DIR / name)
    for name in RESULT_FILES:
        if (folder / "results" / name).exists():
            _copy_atomically(folder / "results" / name, RESULTS_DIR / name)
    entry = ModelRelease(version=version, previous_version=previous, released_by=user.id,
                         released_by_name=user.full_name, note=note.strip())
    db.add(entry)
    audit.append(db, "model_released", user, "model", version,
                 {"previous_version": previous, "note": note.strip(), "fairness_passes": True,
                  "roc_auc": (data.get("test_results") or {}).get("roc_auc")}, model_version=version)
    reload_model()
    jobs.clear()  # second opinions worked out by the old model no longer apply
    return entry


def release_history(db: Session, version: str | None = None) -> list[dict]:
    return [{"version": r.version, "previous_version": r.previous_version, "released_by": r.released_by_name,
             "released_at": r.released_at.isoformat(timespec="seconds"), "note": r.note}
            for r in releases(db) if version is None or r.version == version]
