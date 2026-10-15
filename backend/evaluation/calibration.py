"""
Calibration of a model on the test set:
    python -m evaluation.calibration                    the live model; also writes results/
    python -m evaluation.calibration v20261015123029    a registered version (e.g. a candidate waiting for release)

Adds the result to that version's model card in the registry (with its plot, so a later release publishes them),
and for the live model also writes results/calibration.json and results/calibration_curve.png. Uses the same
70/10/20 split as training, so the test set is the one the model never saw. See app/promotion/calibration.py for
what each measure means.
"""
import json
import sys

import joblib

from app.core.config import RESULTS_DIR
from app.governance import registry
from app.promotion.calibration import calibration_report, save_calibration_plot
from app.promotion.features import MODEL_FEATURES, TARGET, load_dataset, split_data


def main():
    registry.ensure_live_registered()
    version = sys.argv[1] if len(sys.argv) > 1 else registry.live_version()
    folder = registry.version_dir(version)
    card = json.loads((folder / "card.json").read_text())
    model = joblib.load(folder / "model.joblib")

    _, _, test = split_data(load_dataset())
    report = {"model": card["model"], "model_version": version,
              **calibration_report(test[TARGET], model.predict_proba(test[MODEL_FEATURES])[:, 1])}

    # The version's model card and its results folder
    card["calibration"] = {k: v for k, v in report.items() if k not in ("model", "model_version")}
    (folder / "card.json").write_text(json.dumps(card, indent=2))
    (folder / "results").mkdir(exist_ok=True)
    (folder / "results" / "calibration.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    save_calibration_plot(report, folder / "results" / "calibration_curve.png", card["model"])
    if version == registry.live_version():  # the live model's results are the published ones
        RESULTS_DIR.mkdir(exist_ok=True)
        for name in ("calibration.json", "calibration_curve.png"):
            (RESULTS_DIR / name).write_bytes((folder / "results" / name).read_bytes())

    print(f"{report['model']} {version}{' (live)' if version == registry.live_version() else ''}, "
          f"test set of {report['test_size']:,}:")
    print(f"  Brier {report['brier']} (always guessing {report['base_rate']:.0%}: {report['brier_baseline']}), "
          f"skill {report['brier_skill']}")
    print(f"  ECE {report['ece']} | slope {report['slope']} | intercept {report['intercept']} | "
          f"average score {report['mean_score']} vs promoted {report['base_rate']}")
    print(f"  {report['groups_within_interval']} of 10 groups within their 95% interval -> {report['verdict']}")
    for row in report["bins"]:
        print(f"    scores {row['from']:.3f}-{row['to']:.3f}: average {row['mean_score']:.3f}, promoted "
              f"{row['promoted']:.3f} [{row['promoted_low']:.3f}, {row['promoted_high']:.3f}]")


if __name__ == "__main__":
    main()
