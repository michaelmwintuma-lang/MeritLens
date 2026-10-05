"""
Choose the priority classifier's settings fairly: by 5-fold cross-validation on the TRAINING examples only.
The evaluation sets (reports_developer.json, reports_external.json) are not read here, so choosing settings can't
tune the model to them.

Run from the backend folder:  python -m evaluation.choose_priority_model
Then copy the best settings into SETTINGS in app/reporting/priority_model.py.

Scored by macro F1 (each level counts equally), and by how often a report is put BELOW its true level, the costly
mistake.
"""
import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from app.reporting.priority_model import LEVELS, build, training_data


def main():
    texts, labels = training_data()
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
    truth = np.array([LEVELS.index(l) for l in labels])
    print(f"{len(texts)} training examples: " + ", ".join(f"{l} {labels.count(l)}" for l in LEVELS))
    print(f"{'char pieces':<12}{'C':>6}{'macro F1':>10}{'accuracy':>10}{'too low':>9}")
    results = []
    for char in (False, True):
        for C in (1.0, 3.0, 10.0, 30.0):
            guess = cross_val_predict(build(C=C, char=char), texts, labels, cv=folds)
            g = np.array([LEVELS.index(x) for x in guess])
            row = (f1_score(labels, guess, average="macro"), float(np.mean(g == truth)), int(np.sum(g < truth)), char, C)
            results.append(row)
            print(f"{str(char):<12}{C:>6}{row[0]:>10.3f}{row[1]:>10.3f}{row[2]:>9}")
    best = max(results, key=lambda r: (round(r[0], 3), -r[2]))
    print(f"\nBest: char={best[3]}, C={best[4]} (macro F1 {best[0]:.3f}, {best[2]} put too low)")


if __name__ == "__main__":
    main()
