"""
Train the promotion model:   python train.py   (from the backend folder)
On another organisation's data:   python train.py --mapping data/mappings/my_mapping.json

1. Load the data through a mapping (data/mappings/*.json: which column holds each input) and split it 70 / 10 / 20
   (training / validation / test).
2. Train a monotonic Explainable Boosting Machine (EBM), Logistic Regression, Random Forest and XGBoost, and
   check each for common sense: does improving an input ever lower someone's score?
3. Choose one: only models with no common-sense violations are eligible; among them, the easiest to explain whose
   validation PR-AUC is within 0.01 of the best.
4. Choose the decision threshold with the best F1 on the validation set.
5. Test the chosen model once on the test set.
6. Check fairness (four-fifths rule).
7. Register the result in the model registry (models/registry/<version>/) with its model card. It does NOT go live:
   a named HR person reads the card and releases it in the app (Model registry). A model that failed the fairness
   check is registered as blocked and can never be released. Only the very first model, when there is no live
   model at all, is released here, so the app can start.
"""
import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")  # draw images to files, no window
import matplotlib.pyplot as plt
from sklearn.metrics import PrecisionRecallDisplay, RocCurveDisplay, average_precision_score, roc_auc_score

from app.core.config import MODELS_DIR
from app.governance import registry
from app.promotion.fairness import fairness_report
from app.promotion.features import MODEL_FEATURES, NUMERIC_FEATURES, TARGET, split_data
from app.promotion.mapping import DEFAULT_MAPPING, load_mapped, load_mapping
from app.promotion.modeling import (best_f1_threshold, choose_model, common_sense_violations, make_models,
                                    test_metrics)

BACKEND = Path(__file__).resolve().parent


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def save_curves(y_true, scores, name: str, folder: Path) -> None:
    """ROC curve and precision-recall curve of the final model on the test set."""
    for display, file in ((RocCurveDisplay, "roc_curve.png"), (PrecisionRecallDisplay, "pr_curve.png")):
        fig, ax = plt.subplots(figsize=(5, 4.5))
        display.from_predictions(y_true, scores, name=name, ax=ax)
        if display is PrecisionRecallDisplay:
            ax.axhline(y_true.mean(), linestyle="--", color="grey", label=f"Random guess ({y_true.mean():.2f})")
            ax.legend(loc="upper right")
        else:
            ax.plot([0, 1], [0, 1], linestyle="--", color="grey", label="Random guess (0.50)")
            ax.legend(loc="lower right")
        ax.set_title(f"{'ROC' if display is RocCurveDisplay else 'Precision-recall'} curve, test set")
        fig.tight_layout()
        fig.savefig(folder / file, dpi=150)
        plt.close(fig)


def reference_statistics(train) -> dict:
    """
    Facts about the training data that the explanations need: each input's average (the "average employee"
    that explanations compare against), its spread, and its realistic range (5th to 95th percentile).
    """
    stats = {}
    for column in NUMERIC_FEATURES:
        values = train[column]
        stats[column] = {"mean": round(float(values.mean()), 6), "std": round(float(values.std()), 6),
                         "p5": round(float(values.quantile(0.05)), 4), "p95": round(float(values.quantile(0.95)), 4),
                         "min": round(float(values.min()), 4), "max": round(float(values.max()), 4)}
    # Department is not a model input; the list is kept only so the record form can check what it is given
    return {"feature_stats": stats, "departments": sorted(train["department"].unique().tolist())}


def note_registration(card: dict, status: str) -> None:
    """Add "a model was registered" to the audit trail, if the app's database exists (training never fails on it)."""
    try:
        from app.core import audit
        from app.core.database import SessionLocal, engine
        audit.AuditEvent.__table__.create(engine, checkfirst=True)
        with SessionLocal() as db:
            audit.append(db, "model_registered", None, "model", card["version"],
                         {"status": status, "fairness_passes": card["fairness_passes"],
                          "roc_auc": card["test_results"]["roc_auc"], "data": (card.get("mapping") or {}).get("name")},
                         model_version=card["version"])
            db.commit()
    except Exception as error:  # noqa: BLE001
        print(f"   (not added to the audit trail: {error})")


def main():
    parser = argparse.ArgumentParser(description="Train, test and register a promotion model.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING,
                        help="which columns of the HR export hold each input (default: the Kaggle dataset)")
    args = parser.parse_args()

    print("1. Loading the data through the mapping and splitting it")
    mapping = load_mapping(args.mapping)
    data = load_mapped(mapping)
    train, val, test = split_data(data)
    print(f"   {mapping['name']}")
    print(f"   train {len(train):,} | validation {len(val):,} | test {len(test):,} | "
          f"promoted {train[TARGET].mean():.1%} / {val[TARGET].mean():.1%} / {test[TARGET].mean():.1%}")
    print(f"   {len(MODEL_FEATURES)} model inputs; protected characteristics and pay are not among them")

    print("2. Training four models and checking each for common sense")
    models, comparison = make_models(train[TARGET].mean()), {}
    for name, model in models.items():
        model.fit(train[MODEL_FEATURES], train[TARGET])
        scores = model.predict_proba(val[MODEL_FEATURES])[:, 1]
        violations = common_sense_violations(model, val)
        comparison[name] = {"val_pr_auc": round(average_precision_score(val[TARGET], scores), 4),
                            "val_roc_auc": round(roc_auc_score(val[TARGET], scores), 4),
                            "common_sense_violations": violations["rate"],
                            "violations_by_input": violations["by_input"]}
        print(f"   {name:<20} validation PR-AUC {comparison[name]['val_pr_auc']:.4f}  ROC-AUC "
              f"{comparison[name]['val_roc_auc']:.4f}  common-sense violations {violations['rate']:.1%}")

    print("3. Choosing the model")
    chosen, reason = choose_model({name: m["val_pr_auc"] for name, m in comparison.items()},
                                  {name: m["common_sense_violations"] for name, m in comparison.items()})
    model = models[chosen]
    print(f"   {chosen}: {reason}")
    comparison_doc = {"validation": comparison, "chosen": chosen, "reason": reason,
                      "rule": "no common-sense violations on validation, then the easiest to explain within 0.01 "
                              "PR-AUC of the best"}

    print("4. Choosing the decision threshold (best F1 on validation)")
    threshold = best_f1_threshold(val[TARGET], model.predict_proba(val[MODEL_FEATURES])[:, 1])
    print(f"   threshold = {threshold:.4f}")

    print("5. Testing once on the test set")
    test_scores = model.predict_proba(test[MODEL_FEATURES])[:, 1]
    metrics = {"model": chosen, **test_metrics(test[TARGET], test_scores, threshold)}
    print(f"   accuracy {metrics['accuracy']} | precision {metrics['precision']} | recall {metrics['recall']} | "
          f"F1 {metrics['f1']} | ROC-AUC {metrics['roc_auc']} | PR-AUC {metrics['pr_auc']} (random {metrics['pr_auc_baseline']})")

    print("6. Fairness check (four-fifths rule) on the test set")
    fairness = fairness_report(test, test_scores >= threshold)
    for attribute, check in fairness["checks"].items():
        rates = ", ".join(f"{g} {v['selection_rate']:.1%}" for g, v in check["groups"].items())
        print(f"   {attribute:<10} ratio {check['ratio']:.3f} {'PASS' if check['passes'] else 'FAIL'}  ({rates})")

    print("7. Registering the model with its model card")
    trained_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    info = {"model": chosen, "reason": reason, "threshold": round(threshold, 4), "features": MODEL_FEATURES,
            "trained_at": trained_at, "version": "v" + "".join(ch for ch in trained_at if ch.isdigit())[:14],
            **reference_statistics(train)}
    card = registry.make_card(info, metrics, fairness, comparison_doc,
                              {"rows": len(data), "train": len(train), "validation": len(val), "test": len(test),
                               "promotion_rate": round(float(data[TARGET].mean()), 4)}, mapping)
    with tempfile.TemporaryDirectory() as staging:
        staging = Path(staging)
        (staging / "results").mkdir()
        joblib.dump(model, staging / "model.joblib")
        save_json(staging / "model_info.json", info)
        # A sample of training employees, used by LIME and for model-wide importance
        train[MODEL_FEATURES].sample(2000, random_state=42).to_csv(staging / "background.csv", index=False)
        save_json(staging / "results" / "metrics.json", metrics)
        save_json(staging / "results" / "fairness.json", fairness)
        save_json(staging / "results" / "model_comparison.json", comparison_doc)
        save_curves(test[TARGET], test_scores, chosen, staging / "results")
        folder = registry.register(staging, staging / "results", card)
    print(f"   registered {info['version']} in {folder.relative_to(BACKEND).as_posix()}/")

    if not fairness["passes"]:
        note_registration(card, "blocked")
        print("\n   BLOCKED: the model fails the four-fifths rule for at least one group. It can never be released;")
        print("   the live model is unchanged.")
        return
    if registry.live_version() is None:  # no live model at all: the first one goes live so the app can start
        for name in registry.MODEL_FILES:
            (MODELS_DIR / name).write_bytes((folder / name).read_bytes())
        for name in registry.RESULT_FILES:
            target = registry.RESULTS_DIR / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((folder / "results" / name).read_bytes())
        note_registration(card, "first model, released by train.py")
        print("\nDone: this is the first model, so it is now live.")
        return
    note_registration(card, "candidate")
    print("\nDone: the model passed the fairness check and waits for release. An HR user reads its model card and")
    print("releases it in the app (Model registry); until then, the live model is unchanged.")


if __name__ == "__main__":
    main()
