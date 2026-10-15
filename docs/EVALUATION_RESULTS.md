# Evaluation results

Every result of the system, with the file it comes from and the command that reproduces it. No number here was
typed in by hand: each is copied from a file written by a script. Re-running `train.py` reproduces
`metrics.json`, `fairness.json` and `model_comparison.json` byte for byte (checked on 2026-10-09, and again on
2026-10-11 after anonymous reporting was removed); the proxy analysis and the explanation evaluation also gave the
same results, apart from the model's version label.

All employee data is **synthetic** (100,000 made-up employees). The results describe the system on this data, not
on a real organisation.

The platform follows one cycle, and the results follow it too: **predict → explain → respond**.

---

## 0. The dataset

**Source:** Kumar, R. (2026). *Employee Promtion Prediction Dataset* (Version 1) [Data set]. Kaggle, CC0.
<https://www.kaggle.com/datasets/rohit8527kmr7518/employee-promtion-prediction>. The project's copy is
`backend/data/employee_promotion_dataset_100000.csv`, identical in size (52,710,327 bytes) to the Kaggle file.

| Measure | Value |
|---|---|
| Employees | 100,000 (43 columns plus `promoted`) |
| Promoted | 10.0% |
| Missing values / duplicate rows | 0 / 0 |
| Gender | 50.1% female, 49.9% male; promoted 9.7% and 10.3% |
| Age | 22–59; 47.1% under 40, 52.9% 40+; promoted 10.0% in both |
| Education | Bachelor 64.8%, Master 30.1%, PhD 5.1%; promoted 9.9%, 10.1%, 10.3% |
| Department | 7 departments, 14.1–14.5% each; promoted from 2.0% (Support) to 33.2% (Engineering) |
| City tier, marital status | promoted exactly 10.0% in every group (a sign of simulated data) |
| Correlation of this year's and last year's performance | 0.918 |

The choice of dataset, inputs and exclusions, with their justification, is in `docs/THESIS_GUIDE.md`, section 9.1.

## 1. Predict: the promotion model

**Source:** `results/model_comparison.json`, `results/metrics.json`, `results/fairness.json`
**Reproduce:** `cd backend && python train.py`

### Inputs

20 performance and development inputs. Excluded, each with a written reason in `backend/app/promotion/features.py`:
- gender, age, education and marital status, which are used only for the fairness audit;
- department;
- pay;
- attitude surveys;
- working hours;
- location and contract details.

### Model choice

The data was split 70% / 10% / 20% into training, validation and test sets, stratified, with seed 42. Four models
were trained.

Every candidate went through a **common-sense check** on 2,000 validation employees. Each input a person can
improve was moved half a standard deviation in its improving direction. A model counted a violation whenever a
score dropped. Only models with no violations were eligible.

| Model | Validation PR-AUC | Validation ROC-AUC | Common-sense violations | Eligible |
|---|---|---|---|---|
| **EBM, monotonic (chosen)** | 0.4671 | 0.8806 | **0%** | **yes** |
| XGBoost | 0.4699 | 0.8777 | 21.9% | no |
| Logistic regression | 0.4618 | 0.8793 | 16.7% | no |
| Random forest | 0.4528 | 0.8769 | 30.1% | no |

The decision threshold is **0.2283**, the best F1 on the validation set.

### Test set (20,000 employees, measured once)

| ROC-AUC | PR-AUC | Precision | Recall | F1 | Accuracy | Share recommended |
|---|---|---|---|---|---|---|
| 0.8833 | 0.4736 (random: 0.10) | 0.4102 | 0.5950 | 0.4856 | 0.8740 | 14.5% |

Confusion matrix: 1,190 true positives, 1,711 false positives, 810 false negatives, 16,289 true negatives.

**The cost of fairness.** An earlier model used logistic regression *with* department. It reached PR-AUC 0.6325 and
ROC-AUC 0.9295, but it scored people by where they work: past promotion rates ranged from 2% (Support) to 33%
(Engineering). Removing department is what most of the drop reflects.

### Calibration (test set)

Source: `results/calibration.json`, `results/calibration_curve.png`; `python -m evaluation.calibration`.

| Brier score | Always guessing 10% | Brier skill | ECE (10 groups) | Slope | Intercept | Average score vs promoted |
|---|---|---|---|---|---|---|
| 0.0677 | 0.0900 | 0.248 | 0.0056 | 0.998 | -0.013 | 10.07% vs 10.0% |

| Score group | Average score | Actually promoted (95% interval) |
|---|---|---|
| 0.000-0.001 | 0.0% | 0.1% (0.0-0.3) |
| 0.001-0.004 | 0.2% | 0.1% (0.0-0.4) |
| 0.004-0.009 | 0.6% | 0.3% (0.1-0.6) |
| 0.009-0.019 | 1.4% | 1.1% (0.8-1.7) |
| 0.019-0.034 | 2.6% | 1.8% (1.3-2.5) |
| 0.034-0.056 | 4.4% | 4.5% (3.7-5.6) |
| 0.056-0.096 | 7.4% | 7.6% (6.5-8.8) |
| 0.096-0.164 | 12.6% | 13.5% (12.1-15.1) |
| 0.164-0.306 | 22.5% | 23.7% (21.9-25.6) |
| 0.306-0.965 | 48.9% | 47.2% (45.1-49.4) |

**Well calibrated.** Scores can be read as rates: of employees scoring around the 23% threshold, about 23-24% were
promoted. 8 of 10 groups fall within their 95% interval; the two that don't are among the lowest scores (e.g. 2.6%
predicted, 1.8% promoted), small over-estimates where almost nobody is promoted. The EBM was trained without class
weights, which is why its scores stay on the scale of the real outcome. This is calibration to past decisions in
synthetic data: a score is a rate for similar employees, not a promise about one person.

### Fairness (four-fifths rule, test set)

| Characteristic | Selection rates | Ratio | Result |
|---|---|---|---|
| Gender | female 14.6%, male 14.4% | 0.982 | pass |
| Age group | under 40: 14.8%, 40+: 14.2% | 0.963 | pass |
| Education | Bachelor 14.3%, Master 14.7%, PhD 16.1% | 0.887 | pass |

A model that fails this check is never saved as the live model.

### Equal opportunity and proxies

**Source:** `results/proxy_analysis.json`
**Reproduce:** `cd backend && python -m evaluation.proxy_analysis`

**Equal opportunity** (true-positive-rate ratio): gender 0.952, age group 0.899, education 0.958.

**Proxies for gender, age and education: none.** The strongest single link is |d| = 0.016 for age group (Cohen's d,
where under 0.2 is negligible). Classifiers given all 20 inputs predict each of the three at a ROC-AUC of 0.50, no
better than guessing.

**Department** (removed as an input) **is partly recoverable:**
- through tasks completed (η² 0.27) and projects completed (0.18);
- predicting department from the 20 inputs reaches ROC-AUC 0.67;
- the model recommends 24.7% of Engineering against 7.9% of HR (selection ratio 0.32), where historically it was
  33.2% against 2.9%.

### Drift (admin dashboard, live)

The population stability index (PSI) compares each input in today's 120-person directory with the training sample.
For the demo directory, the largest PSI is 0.183 (problem-solving score), against 0.135 that chance alone reaches
for a group of 120.

Two of the 20 inputs are above their chance level. That is about what chance produces when 20 inputs are each
checked at the 95% level, and the 120 people do come from the same data. Code: `backend/app/promotion/drift.py`.

## 2. Explain: the explanations

**Source:** `results/explanation_evaluation.json`
**Reproduce:** `cd backend && python -m evaluation.evaluate_explanations`
**Sample:** the 120 demo employees, all from the test set.

| Measure | Result |
|---|---|
| Exactness: largest gap between "base + contributions" and the model's own log-odds | 0.000347. Contributions are rounded to 4 decimals, so a gap of up to 0.001 is expected. |
| Common sense: "improve one input by one standard deviation" checks (17 inputs × 120 employees) | 2,040 checks, **0** lowered a score |
| LIME's fit to the model around each employee (R²) | median 0.135; 84.2% below 0.5 |
| LIME's top rule names one of the five largest exact contributions | 90.8% of employees |
| The tips reach the threshold (employees not yet recommended) | 98 of 108 (90.7%) |

LIME's fit is low, so LIME is shown only as a second opinion, under "Show technical details". The main explanation
is the exact contributions. Most employees are far from the threshold, where the model's curve is flat, which gives
a local linear model little to fit.

Overall importance, as the share of the model's effect: change in performance since last year 51.5%, projects
10.7%, tasks 6.9%, performance score 4.7%, leadership 4.5%. Source: `/api/promotion/importance`, shown on "How the
model works".

## 3. Respond: the employee feedback channel

### Behaviour (automated tests)

`backend/tests/test_feedback.py` (28 tests) and `backend/tests/test_isolation.py` (4 tests) check that:
- ratings and correction requests never change a score;
- only a correction HR confirms changes the record, and it is logged;
- managers never see ratings or corrections.

The isolation test recorded every prediction answer before and after adding a harsh rating, a pending and a
rejected correction, and a decision held for the correction. Every answer was byte-for-byte identical. A confirmed correction
then changed the prediction, and the change was logged.

### Measures from use

**Source:** the feedback dashboard, or `results/feedback_measures.json`
**Reproduce:** `cd backend && python -m evaluation.export_feedback_measures`

The script exports the clarity rate, usefulness rate, contest share per factor, correction confirmation rate, mean
time to decide and the committee's override rate.

**No real use has happened yet.** On 2026-10-09 the database held 0 ratings and 0 correction requests, so these
numbers are to be collected during the usability study (section 5) and reported with the number of participants.

## 4. Software quality

| Check | Result | How |
|---|---|---|
| Backend tests | 322 passed | `cd backend && python -m pytest`, in about 5 minutes |
| Browser checks: sessions, the feedback channel end to end, dashboards, landing page, pagination, every menu page for six roles (with no mention of the removed reporting) | 7 passed | `python scripts/browser_test.py`, against a throwaway copy of the app |
| Accessibility: axe-core, WCAG 2.1 A/AA, 39 pages, light and dark themes | 0 findings | `python scripts/browser_test.py scripts/ui_capture.js docs/screenshots/<folder>` |
| Pages wider than a phone screen (390 px) | none | same script |

Performance, measured on the running app with 120 demo employees (`docs/CHANGELOG_UPGRADE.md`, Phase 8):

| Measure | Before | After |
|---|---|---|
| Employee list | 0.26 s | 0.02–0.06 s |
| Scoring 5,000 employees | 11.25 s (one at a time) | 13 ms (one call) |
| Website's first download | 482 kB | 309 kB |

## 5. Usability and perceived fairness (to be collected)

**Method:** `docs/USER_TEST.md`:
- 11 tasks, including the three feedback routes and HR deciding on a correction;
- the System Usability Scale;
- eight perceived-fairness statements adapted from Colquitt (2001), four informational and four procedural.

**Score:** `cd backend && python -m evaluation.user_test`. This writes `results/user_test.md`, with Cronbach's alpha
from three participants up.

**No participants have taken part yet**, so there are no usability or perceived-fairness results. Report them with
the number of participants once collected.
