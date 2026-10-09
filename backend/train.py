"""
Train the promotion model:   python train.py   (from the backend folder)

1. Load the data and split it 70 / 10 / 20 (training / validation / test).
2. Train a monotonic Explainable Boosting Machine (EBM), Logistic Regression, Random Forest and XGBoost, and
   check each for common sense: does improving an input ever lower someone's score?
3. Choose one: only models with no common-sense violations are eligible; among them, the easiest to explain whose
   validation PR-AUC is within 0.01 of the best.
4. Choose the decision threshold with the best F1 on the validation set.
5. Test the chosen model once on the test set; save metrics and curve images to results/.
6. Check fairness (four-fifths rule). Only a model that passes becomes the live model in models/.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")  # draw images to files, no window
import matplotlib.pyplot as plt
from sklearn.metrics import PrecisionRecallDisplay, RocCurveDisplay, average_precision_score, roc_auc_score

from app.promotion.fairness import fairness_report
from app.promotion.features import MODEL_FEATURES, NUMERIC_FEATURES, TARGET, load_dataset, split_data
from app.promotion.modeling import (best_f1_threshold, choose_model, common_sense_violations, make_models,
                                    test_metrics)

BACKEND = Path(__file__).resolve().parent
RESULTS = BACKEND.parent / "results"
MODELS = BACKEND / "models"


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))
    print(f"   saved {path.relative_to(BACKEND.parent).as_posix()}")


def save_curves(y_true, scores, name: str) -> None:
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
        fig.savefig(RESULTS / file, dpi=150)
        plt.close(fig)
        print(f"   saved results/{file}")


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


def main():
    RESULTS.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)

    print("1. Loading and splitting the data")
    train, val, test = split_data(load_dataset())
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
    save_json(RESULTS / "model_comparison.json", {"validation": comparison, "chosen": chosen, "reason": reason,
                                                     "rule": "no common-sense violations on validation, then the "
                                                             "easiest to explain within 0.01 PR-AUC of the best"})

    print("4. Choosing the decision threshold (best F1 on validation)")
    threshold = best_f1_threshold(val[TARGET], model.predict_proba(val[MODEL_FEATURES])[:, 1])
    print(f"   threshold = {threshold:.4f}")

    print("5. Testing once on the test set")
    test_scores = model.predict_proba(test[MODEL_FEATURES])[:, 1]
    metrics = {"model": chosen, **test_metrics(test[TARGET], test_scores, threshold)}
    print(f"   accuracy {metrics['accuracy']} | precision {metrics['precision']} | recall {metrics['recall']} | "
          f"F1 {metrics['f1']} | ROC-AUC {metrics['roc_auc']} | PR-AUC {metrics['pr_auc']} (random {metrics['pr_auc_baseline']})")
    save_json(RESULTS / "metrics.json", metrics)
    save_curves(test[TARGET], test_scores, chosen)

    print("6. Fairness check (four-fifths rule) on the test set")
    fairness = fairness_report(test, test_scores >= threshold)
    for attribute, check in fairness["checks"].items():
        rates = ", ".join(f"{g} {v['selection_rate']:.1%}" for g, v in check["groups"].items())
        print(f"   {attribute:<10} ratio {check['ratio']:.3f} {'PASS' if check['passes'] else 'FAIL'}  ({rates})")
    save_json(RESULTS / "fairness.json", fairness)

    if not fairness["passes"]:
        print("\n   WARNING: the model fails the four-fifths rule for at least one group.")
        print("   It has NOT been saved as the live model. The previous live model (if any) is unchanged.")
        return

    joblib.dump(model, MODELS / "model.joblib")
    trained_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_json(MODELS / "model_info.json", {
        "model": chosen, "reason": reason, "threshold": round(threshold, 4), "features": MODEL_FEATURES,
        "trained_at": trained_at, "version": "v" + "".join(ch for ch in trained_at if ch.isdigit())[:14],
        **reference_statistics(train),
    })
    # A sample of training employees, used by LIME and for model-wide importance (step 3)
    train[MODEL_FEATURES].sample(2000, random_state=42).to_csv(MODELS / "background.csv", index=False)
    print("   saved backend/models/background.csv")
    print("\nDone: the model passed the fairness check and is now the live model.")


if __name__ == "__main__":
    main()
