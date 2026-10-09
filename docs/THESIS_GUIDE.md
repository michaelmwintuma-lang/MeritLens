# Thesis guide

How to write up MeritLens: the problem, the aim, the methods, where every result comes from, what to discuss,
and the figures to use. Every number cited here is in `docs/EVALUATION_RESULTS.md`, with the file and command that
produce it.

**Title:** Design and Development of an Explainable Machine Learning-Based Decision Support System for Employee
Promotion Prediction with an Employee Feedback Channel.

## 1. Problem, aim and objectives

**Problem.** Promotion decisions are often unclear, inconsistent and open to bias, and employees can neither
understand them nor respond to them.

**Aim.** To design, build and test a web-based system that predicts how ready each employee is for promotion,
explains the reasons behind each prediction, and lets employees respond to those explanations.

**Objectives**, one for each stage of the cycle **predict → explain → respond**:

1. **Predict.** Build and test a fair model that predicts promotion readiness from performance and development
   records only, test it on unseen records, and block any model that treats groups unfairly (gender, age,
   education).
2. **Explain.** Explain every prediction in simple language: which factors raised or lowered the score, and the
   smallest realistic improvements that would reach the threshold.
3. **Respond.** Let employees respond to their explanation, by rating it, asking HR to correct a wrong record, or
   reporting an unfair assessment anonymously, while people, not the system, make every final decision.

**Research questions** (suggested):

- RQ1: How accurately can promotion readiness be predicted from performance and development records alone, without
  protected characteristics, pay or department, and does the model pass the four-fifths rule?
- RQ2: Can each prediction be explained exactly and in plain language, and do two independent methods (exact
  contributions and LIME) agree?
- RQ3: Can a feedback channel let employees respond to explanations without feedback or complaints ever changing a
  score?
- RQ4: Do users find the system usable, and the explanations and process fair? This is answered by the usability
  study.

## 2. Suggested chapters

1. **Introduction:** problem, aim, objectives, research questions, scope (synthetic data; decision support, not
   automated decisions).
2. **Literature review:**
   - promotion decisions and bias;
   - explainable AI, covering additive glass-box models (EBM), SHAP and LIME;
   - algorithmic fairness, including the four-fifths rule;
   - actionable recourse;
   - organisational justice (Colquitt's informational and procedural justice);
   - voice and anonymous reporting.
3. **Methodology:** sections 3 and 4 below.
4. **Results:** section 5 below.
5. **Discussion:** section 6 below.
6. **Conclusion and future work:** limitations from `docs/LIMITATIONS.md` and the residual risks in
   `docs/THREAT_MODEL.md`.

## 3. Methodology: predict and explain

- **Data:** 100,000 synthetic employees (`backend/data/`); 10% were promoted. 20 inputs. Every column left out has a
  written reason (`backend/app/promotion/features.py`).
- **Excluded inputs:**
  - protected characteristics, which are used only for the fairness audit;
  - pay;
  - **department**, which scored people by where they work (past promotion rates from 2% to 33%).
- **Split:** 70/10/20, stratified, seed 42. The test set is used once.
- **Candidates:** a monotonic Explainable Boosting Machine (EBM), logistic regression, random forest and XGBoost.
- **Selection rule:**
  1. A common-sense check: improving an input a person controls must never lower a score.
  2. Then validation PR-AUC.
  3. Then the easiest to explain within 0.01.

  Explain why PR-AUC suits a 10% positive class (Saito and Rehmsmeier, 2015).
- **Threshold:** best F1 on validation.
- **Fairness gate:** the four-fifths rule (EEOC, 1978) for gender, age group and education, on the test set. A model
  that fails isn't saved.
- **Explanations:**
  - exact additive contributions from the EBM's terms (Lou et al., 2013; Nori et al., 2019), equal to SHAP values
    for an additive model (Lundberg and Lee, 2017);
  - LIME as an independent second opinion, with its fit (Ribeiro et al., 2016);
  - a plain-language summary;
  - a what-if tool;
  - tips: the smallest realistic improvements, related to actionable recourse (Ustun et al., 2019; Wachter et al.,
    2017).
- **Drift:** the population stability index per input, judged against what chance alone gives a group of that size.

## 4. Methodology: respond, and keeping it apart from the model

- **Three routes** on the employee's own page:
  1. rate the explanation (clear? useful? 1–5; factors that seem wrong or unfair);
  2. ask HR to correct a value in the record, with evidence;
  3. report an unfair assessment anonymously.
- **HR's correction queue:**
  - confirm with the verified value: the record is corrected, the employee re-scored, and everything is logged;
  - or reject with a reason the employee receives.
- **The committee note,** with an option to hold a decision until a correction is resolved. A hold is not a decision
  and never counts as an override.
- **Re-appraisal** after a report is closed as "rating found unfair". It creates a normal correction with no link to
  the report.
- **Isolation by design:**
  - feedback and reporting live in their own modules and tables;
  - the promotion code never imports or names them, which a static check enforces;
  - at run time the prediction endpoints run no SQL on those tables;
  - an end-to-end test shows predictions are byte-for-byte identical after every kind of feedback, and change only
    after a confirmed correction.
- **Aggregates only:** the feedback dashboard withholds rates below 5 ratings, shows counts of 1–2 as "<3", and
  limits department filters to groups of at least 5.
- **Evaluation of use:** the usability study (`docs/USER_TEST.md`):
  - 11 tasks;
  - SUS (Brooke, 1996; Sauro, 2011);
  - eight perceived-fairness statements adapted from Colquitt (2001).

  Plan 5–8 participants (Nielsen and Landauer, 1993) and obtain ethics approval first.

## 5. Results: what to report, and where it comes from

| Result | Source file | Command |
|---|---|---|
| Model comparison and the common-sense check | `results/model_comparison.json` | `python train.py` |
| Test-set metrics and confusion matrix | `results/metrics.json` | same |
| ROC and precision-recall curves | `results/roc_curve.png`, `results/pr_curve.png` | same |
| Fairness (four-fifths rule) | `results/fairness.json` | same |
| Explanations: exactness, common sense, LIME fit and agreement, tips | `results/explanation_evaluation.json` | `python -m evaluation.evaluate_explanations` |
| Reporting: anonymiser and triage | `results/reporting_evaluation.md` | `python -m evaluation.evaluate_reporting` |
| Feedback channel in use: clarity, contest share, corrections | `results/feedback_measures.json` | `python -m evaluation.export_feedback_measures` (after the study) |
| Usability and perceived fairness | `results/user_test.md` | `python -m evaluation.user_test` (after the study) |
| Tests, browser checks, accessibility, performance | `docs/EVALUATION_RESULTS.md`, section 5 | `python -m pytest`; `python scripts/browser_test.py` |

All commands run from `backend/`, except `scripts/…`, which run from the project folder.

## 6. Discussion points

- **Fairness costs accuracy, and it should.** Removing department lowered test PR-AUC from 0.633 to 0.474. Discuss
  what a model that predicts past decisions well is actually learning.
- **The most accurate model was not eligible.** XGBoost had the highest validation PR-AUC (0.4699), but lowered
  scores when an input improved in 21.9% of checks. Logistic regression did so in 16.7%, because of negative weights
  on correlated inputs. Explanations and tips from such a model would mislead.
- **One input dominates.** Change in performance accounts for about half of the model's effect. That is good for
  actionable advice, but discuss the dependence on a single measure.
- **LIME fits poorly here** (median R² 0.135), yet its top rule names a top-five exact factor for 90.8% of
  employees. Discuss why exact additive explanations are preferable when available.
- **Isolation as a design property.** It is shown by tests rather than claimed, and it limits what the feedback
  channel can do: voice without the power to change scores, except through verified corrections.
- **Anonymity versus redress.** An anonymous report protects the reporter, but HR can't know whose rating it means:
  a re-appraisal follows only from HR's own investigation. Someone who wants their own rating fixed must give up
  anonymity and use "Correct my record". Discuss this trade-off (the page states it to employees), and whether an
  opt-in "reveal myself to HR" would be worth weakening the anonymity promise.
- **Small-group protection** trades detail for privacy.
- **Drift and chance.** With 20 inputs checked at the 95% level, about one flag is expected by chance.
- **Synthetic data.** All results describe this dataset. Real use would need retraining, and the fairness gate
  passing, on the organisation's own history.

## 7. Figures to include

- The cycle: predict → explain → respond (the landing page's "How it works").
- ROC and PR curves (`results/`).
- An employee's "My growth" page and the respond panel (`frontend/public/landing/growth.webp`, `respond.webp`).
- HR's correction queue, and the committee note on a nomination (from `docs/screenshots/phase7-after/`, or capture
  new ones).
- The feedback dashboard (`docs/screenshots/phase7-after/hr-feedback-dashboard-desktop.webp`).
- Architecture: React → FastAPI (promotion | feedback | reporting) → SQLite, with the isolation boundary marked.

## 8. References

- Brooke, J. (1996). SUS: A "quick and dirty" usability scale. In P. W. Jordan et al. (Eds.), *Usability Evaluation
  in Industry* (pp. 189–194). Taylor & Francis.
- Colquitt, J. A. (2001). On the dimensionality of organizational justice: A construct validation of a measure.
  *Journal of Applied Psychology, 86*(3), 386–400.
- Equal Employment Opportunity Commission et al. (1978). Uniform Guidelines on Employee Selection Procedures,
  29 C.F.R. § 1607.4(D) (the four-fifths rule).
- Lou, Y., Caruana, R., Gehrke, J., & Hooker, G. (2013). Accurate intelligible models with pairwise interactions.
  *Proceedings of the 19th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 623–631.
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural
  Information Processing Systems 30*.
- Nielsen, J., & Landauer, T. K. (1993). A mathematical model of the finding of usability problems. *Proceedings of
  the INTERACT '93 and CHI '93 Conference on Human Factors in Computing Systems*, 206–213.
- Nori, H., Jenkins, S., Koch, P., & Caruana, R. (2019). InterpretML: A unified framework for machine learning
  interpretability. *arXiv:1909.09223*.
- Ribeiro, M. T., Singh, S., & Guestrin, C. (2016). "Why should I trust you?": Explaining the predictions of any
  classifier. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*,
  1135–1144.
- Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when
  evaluating binary classifiers on imbalanced datasets. *PLOS ONE, 10*(3), e0118432.
- Sauro, J. (2011). *A Practical Guide to the System Usability Scale*. Measuring Usability LLC.
- Ustun, B., Spangher, A., & Liu, Y. (2019). Actionable recourse in linear classification. *Proceedings of the
  Conference on Fairness, Accountability, and Transparency (FAT\*)*, 10–19.
- Wachter, S., Mittelstadt, B., & Russell, C. (2017). Counterfactual explanations without opening the black box:
  Automated decisions and the GDPR. *Harvard Journal of Law & Technology, 31*(2), 841–887.

Check each reference against the original before submitting. The population stability index has no single
original source; cite a credit-scoring text you have access to, or describe it as standard practice.
