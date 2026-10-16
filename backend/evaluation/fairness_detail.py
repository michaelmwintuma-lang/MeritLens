"""
The detailed fairness results on a version's model card: per-group accuracy (true- and false-positive rates,
precision), gender within each age group, and the proxy analysis.

    python -m evaluation.fairness_detail                     the live model
    python -m evaluation.fairness_detail v20261015123029     a registered version (e.g. a candidate)

New versions get the per-group results from train.py; this adds them to a version trained before they existed. The
four-fifths result is worked out again on the same test set and must come out the same (it never changes a verdict).
The proxy analysis (python -m evaluation.proxy_analysis, results/proxy_analysis.json) is added when it was run on
this version.
"""
import json
import sys

import joblib

from app.core.config import RESULTS_DIR
from app.governance import registry
from app.promotion.fairness import fairness_report
from app.promotion.features import MODEL_FEATURES, load_dataset, split_data


def main():
    registry.ensure_live_registered()
    version = sys.argv[1] if len(sys.argv) > 1 else registry.live_version()
    folder = registry.version_dir(version)
    card = json.loads((folder / "card.json").read_text())
    model = joblib.load(folder / "model.joblib")

    _, _, test = split_data(load_dataset())
    recommended = model.predict_proba(test[MODEL_FEATURES])[:, 1] >= card["threshold"]
    fairness = fairness_report(test, recommended)
    if fairness["passes"] != card.get("fairness_passes"):
        sys.exit("The four-fifths result came out differently from the one on the card; nothing was changed.")
    card["fairness"] = fairness

    proxy_file = RESULTS_DIR / "proxy_analysis.json"
    if proxy_file.exists():
        analysis = json.loads(proxy_file.read_text(encoding="utf-8"))
        if analysis.get("model_version") == version:
            card["proxy_analysis"] = registry.proxy_summary(analysis)

    (folder / "card.json").write_text(json.dumps(card, indent=2))
    (folder / "results").mkdir(exist_ok=True)
    (folder / "results" / "fairness.json").write_text(json.dumps(fairness, indent=2), encoding="utf-8")
    if version == registry.live_version():
        (RESULTS_DIR / "fairness.json").write_text(json.dumps(fairness, indent=2), encoding="utf-8")

    for name, check in {**fairness["checks"], **fairness["combinations"]}.items():
        print(f"{name}: selection ratio {check['ratio']}, true-positive-rate ratio {check['true_positive_rate_ratio']}, "
              f"false-positive-rate gap {check['false_positive_rate_gap']}")
    print("proxy analysis:", "added" if "proxy_analysis" in card else "not run on this version (python -m evaluation.proxy_analysis)")


if __name__ == "__main__":
    main()
