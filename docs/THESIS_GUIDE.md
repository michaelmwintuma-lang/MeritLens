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

The three decisions a supervisor will ask about (which dataset, what "promotion readiness" means, and how fairness
and proxies are assessed) are answered in full in **section 9**. Use them in the methodology chapter.

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
  that fails isn't saved. Equal opportunity (the true-positive-rate ratio; Hardt et al., 2016) is reported alongside.
- **Proxy analysis:** whether the inputs can stand in for gender, age, education or department, one input at a time
  and all together (section 9.3).
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
| Proxy analysis and equal opportunity | `results/proxy_analysis.json` | `python -m evaluation.proxy_analysis` |
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
- **Removing department didn't remove all of its effect.** Tasks and projects completed differ by department
  (η² 0.27 and 0.18), so the model still recommends 24.7% of Engineering but 7.9% of HR (ratio 0.32). Discuss
  whether that difference reflects real differences in work output or departmental conventions in how work is
  counted, and why department isn't a protected characteristic yet still matters for fairness.
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
- Barocas, S., & Selbst, A. D. (2016). Big data's disparate impact. *California Law Review, 104*(3), 671–732.
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.). Lawrence Erlbaum.
- Colquitt, J. A. (2001). On the dimensionality of organizational justice: A construct validation of a measure.
  *Journal of Applied Psychology, 86*(3), 386–400.
- Equal Employment Opportunity Commission et al. (1978). Uniform Guidelines on Employee Selection Procedures,
  29 C.F.R. § 1607.4(D) (the four-fifths rule).
- Feldman, M., Friedler, S. A., Moeller, J., Scheidegger, C., & Venkatasubramanian, S. (2015). Certifying and
  removing disparate impact. *Proceedings of the 21st ACM SIGKDD International Conference on Knowledge Discovery and
  Data Mining*, 259–268.
- Hardt, M., Price, E., & Srebro, N. (2016). Equality of opportunity in supervised learning. *Advances in Neural
  Information Processing Systems 29*.
- Kumar, R. (2026). Employee Promtion Prediction Dataset (Version 1) [Data set]. Kaggle.
  https://www.kaggle.com/datasets/rohit8527kmr7518/employee-promtion-prediction
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

## 9. Answers to the supervisor's questions

### 9.1 Dataset

**Which dataset.** *Employee Promtion Prediction Dataset* (the misspelling is the dataset's own title), by Rohit
Kumar, on Kaggle: <https://www.kaggle.com/datasets/rohit8527kmr7518/employee-promtion-prediction>.

| | |
|---|---|
| Version | 1, published 14 March 2026 |
| Licence | CC0: Public Domain, so it can be used and redistributed without permission |
| Size | 100,000 employees, 43 columns plus the target `promoted` |
| File | `employee_promotion_prediction.csv` on Kaggle, saved in the project as `backend/data/employee_promotion_dataset_100000.csv` |
| Checked | On 2026-10-10 the project's file was identical in size (52,710,327 bytes) to the one on Kaggle |

Citation: *Kumar, R. (2026). Employee Promtion Prediction Dataset (Version 1) [Data set]. Kaggle.
https://www.kaggle.com/datasets/rohit8527kmr7518/employee-promtion-prediction. Accessed [your access date].*

**How it was made, according to its author:** a simulation of 100,000 employees in seven departments. Promotion
depends on performance, leadership, productivity and behaviour. A promotion budget means only about the top 10% are
promoted. Department affects salary, workload and promotion chances. About 2% of values are outliers. Some factors
that influence promotion, such as managerial support and project visibility, were deliberately left out of the data
to make prediction harder.

**Inputs used: 20, all about performance and development.**

| Group | Inputs |
|---|---|
| Performance | performance score; **change in performance since last year** (this year minus last year, engineered); manager rating; peer feedback; KPI achievement; projects completed; tasks completed; deadline adherence; innovation, leadership, problem-solving and skill-assessment scores |
| Development | training hours last year; certifications; cross-department projects; mentoring sessions |
| Reliability | attendance rate; late days |
| Career stage | years since last promotion; years in current role |

**Columns left out: 22, each with a written reason** (`backend/app/promotion/features.py`):

- **protected characteristics:** gender, age, education level and marital status. Gender, age and education are
  kept aside only for the fairness audit.
- **department:** two people with the same record would get different scores only because of where they work;
- **pay:** salary, salary increase, bonus and stock options, which reflect past decisions and could carry old pay
  gaps forward;
- **not performance:**
  - attitude surveys (engagement, job satisfaction);
  - where someone lives (city tier);
  - working patterns (monthly hours, overtime, meetings, remote ratio), which reward long hours rather than results;
  - team size, contract type, tenure, and internal mobility;
- **the two earlier performance scores,** replaced by the change in performance: the yearly scores correlate at
  0.92, which made a linear model's explanations misleading.

**Limitations of the dataset** (measured with the project's own scripts):

1. **It is synthetic,** as its author states. The project's own checks confirm it is too clean to be real HR data:
   - there are no missing values and no duplicate rows;
   - gender is 50.1% female and 49.9% male;
   - each department holds 14.1–14.5% of employees;
   - the promotion rate is exactly 10.0% for every city tier and both marital statuses.

   Results describe this generated data, not a real organisation.
2. **The exact rule that generated "promoted" isn't published.** The author describes it only in outline, so it
   isn't known which inputs truly caused promotion, or how much. It depends heavily on department (2.0% in Support,
   33.2% in Engineering), as the author's "department effects" would suggest, and hardly at all on gender (9.7% women,
   10.3% men), age (10.0% in both groups) or education (9.9–10.3%).
3. **Some causes of promotion are missing by design.** The author left factors such as managerial support and
   project visibility out of the data. This sets a ceiling on how accurate any model can be, and partly explains
   the modest PR-AUC (0.474).
4. **A single snapshot.** There are no dates or repeated measurements, so the model can't follow change over time,
   apart from the engineered year-on-year change in performance.
5. **Only binary gender and three education levels are recorded.** There is no ethnicity, disability or other
   protected characteristic, so fairness can be audited for only three.
6. **The groups are uneven:** PhDs are 5.1% of employees, so their rates are less precise than the others'.
7. **The class balance is 10% promoted,** fixed by the simulation's promotion budget. That is why PR-AUC is the main metric (Saito and Rehmsmeier, 2015).
8. **A single, recent, little-used source.** Version 1 of a dataset published in March 2026 by one author, so
   there are few other studies to compare results with. Its simulation hasn't been validated against real HR data.

### 9.2 Definition of promotion readiness

**Definition used.** *Promotion readiness is how closely an employee's current performance and development record
resembles the records of employees who were promoted.* It is learned from the **historical promotion outcome**
(`promoted`, yes or no). The score is a ranking against a threshold chosen on validation data (0.2283), not a
probability.

**Why historical outcomes rather than independently defined criteria:**

- **A model needs a known answer to learn from and be tested against.** The dataset has one: who was promoted.
  Independently defined criteria (for example "ready when performance ≥ 80 and leadership ≥ 4") would need experts
  to set and validate them. Without them, the model would only re-learn rules the researcher wrote, and accuracy
  against those rules would prove nothing.
- **Historical outcomes reflect what the organisation actually rewards,** which is what a decision-support tool must
  first describe.
- **The known weakness is past bias.** Historical outcomes repeat whatever bias past decisions had. Here, the
  outcome depends strongly on department. So the study **constrains** the historical definition instead of
  accepting it as it is:
  - only performance and development inputs are used, with protected characteristics, pay and department removed;
  - monotonic constraints stop the model learning that improving something lowers readiness;
  - the four-fifths fairness gate must pass;
  - the score only advises.

**Independently defined criteria still have a place, in the human decision.** A manager's recommendation rates
four criteria from 1 to 5, each with a real example: performance, leadership, skills and impact. A manager must
write a reason to recommend someone the model doesn't, and HR must write one to decide against the model. So the
system combines the two: the **model** describes the historical pattern, and **people** apply explicit criteria.

**State this limitation plainly:** the definition is partly circular. The model predicts who *would have been*
promoted, not who *should be*. The fairness checks and the human decision exist because of this.

### 9.3 Fairness and bias assessment

**Metric: the selection-rate ratio (disparate-impact ratio).** For each characteristic, take the share of each
group the model recommends (its selection rate), then divide the lowest group's rate by the highest's.

**Threshold: 0.80, the four-fifths rule.** A model below 0.80 for gender, age group (under 40 / 40+) or education is
never put into use (`backend/app/promotion/fairness.py`, enforced in `train.py`).

**Why this metric and threshold:**

- **It matches the decision the system makes:** who is recommended. Selection rates are what an organisation would
  be held to account for.
- **It is an established benchmark:** the four-fifths rule of the US Uniform Guidelines on Employee Selection
  Procedures (EEOC, 1978), widely used in algorithmic fairness (Feldman et al., 2015).
- **It doesn't rely on the historical labels.** Those could themselves be biased (section 9.2), whereas metrics
  such as equal opportunity treat past promotions as correct.
- **It is simple to explain** to HR and to employees.

**Its limits, to state:**
- 0.80 is a rule of thumb, not a statistical test;
- it says nothing about accuracy within each group;
- it isn't applied to combinations of characteristics, such as older women;
- small groups (PhD, 5.1%) make it noisier.

So **equal opportunity** (Hardt et al., 2016) is also reported: among people who were actually promoted, the share
the model recommends, compared across groups.

**Results on the 20,000 test employees** (`results/fairness.json`, `results/proxy_analysis.json`):

| Characteristic | Selection rates | Selection ratio | True-positive-rate ratio |
|---|---|---|---|
| Gender | female 14.6%, male 14.4% | **0.981** | 0.952 |
| Age group | under 40: 14.8%, 40+: 14.3% | **0.963** | 0.899 |
| Education | Bachelor 14.3%, Master 14.7%, PhD 16.1% | **0.887** | 0.958 |

All three pass. The lowest true-positive-rate ratio is age: the model recommends 62.9% of the promoted under-40s but
56.6% of the promoted 40+. Discuss this, even though it is above 0.80.

**Identifying and assessing proxy variables.** A proxy is an input that carries information about a protected
characteristic, so a model could discriminate through it without ever seeing the characteristic (Barocas and
Selbst, 2016). Three checks (`backend/evaluation/proxy_analysis.py`):

1. **One input at a time,** to find any single input that could act as a proxy:
   - gender and age group: the standardised difference between the groups (Cohen's d; below 0.2 is negligible,
     Cohen, 1988);
   - age in years: the correlation (below 0.1 is negligible);
   - education and department: the share of the input's spread the groups explain (η²; below 0.01 is negligible).
2. **All inputs together,** to find combinations that act as a proxy even when no single input does. Two
   classifiers (logistic regression, and gradient boosting, which finds non-linear combinations) are trained to
   predict each characteristic from the 20 inputs, and scored on the test set by ROC-AUC, where 0.5 means no better
   than guessing.
3. **The model's own output:** how strongly the readiness score is linked to each characteristic, and each group's
   selection and true-positive rates.

**Results:**

| Characteristic | Strongest single link (input) | Predicting it from all 20 inputs (ROC-AUC) | Score's link to it |
|---|---|---|---|
| Gender | d = 0.011 (change in performance) | 0.50 | d = 0.012 |
| Age group / age | d = 0.016; r = 0.011 (innovation score) | 0.50 | r = −0.004 |
| Education | η² = 0.0001 (performance score) | 0.50 | η² = 0.000 |
| Department (not protected; removed as an input) | **η² = 0.27 (tasks completed), 0.18 (projects completed)** | **0.67** | η² = 0.033 |

**What this shows:**

- **None of the 20 inputs is a proxy for gender, age or education,** alone or in combination: every classifier
  scores at the level of guessing. This is why the model's selection rates are so even.
- **Department is partly recoverable.** Tasks and projects completed differ by department, so the model recommends
  24.7% of Engineering but 7.9% of HR (selection ratio 0.32), compared with 33.2% and 2.9% historically. Removing
  department narrowed the gap a lot but didn't close it. Department isn't a protected characteristic, so this
  doesn't fail the fairness gate, but it should be discussed:
  - if one department's work naturally produces more tasks and projects, comparing counts across departments is
    unfair;
  - a fix would be to compare tasks and projects only within a department (within-department percentiles);
    that is future work.
- **On real data, the proxy analysis must be re-run.** In real organisations, proxies are common: hours worked and
  gender, years of experience and age. The script works on any dataset with these columns.
