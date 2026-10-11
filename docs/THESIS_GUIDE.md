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
3. **Respond.** Let employees respond to their explanation, by rating it and by asking HR to correct a wrong
   record, while people, not the system, make every final decision.

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
   - employee voice: how being heard, and being able to correct the record, affects perceived fairness.
3. **Methodology:** sections 3 and 4 below, with the dataset, the definition of readiness and the fairness method
   justified in section 9.
4. **Results:** section 5 below.
5. **Discussion:** section 6 below.
6. **Conclusion and future work:** the limitations and future work in `docs/LIMITATIONS.md`. A confidential route
   for reporting unfair assessments is future work (built, then removed to keep the scope focused; see
   `docs/future-work/`).

## 3. Methodology: predict and explain

The three decisions a supervisor will ask about (which dataset, what "promotion readiness" means, and how fairness
and proxies are assessed) are answered in full in **section 9**, each with its justification, the alternatives
considered, its limitations and suggested wording. Use them in the methodology chapter.

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

- **Two routes** on the employee's own page:
  1. rate the explanation (clear? useful? 1–5; factors that seem wrong or unfair);
  2. ask HR to correct a value in the record, with evidence.
- **HR's correction queue:**
  - confirm with the verified value: the record is corrected, the employee re-scored, and everything is logged;
  - or reject with a reason the employee receives.
- **The committee note,** with an option to hold a decision until a correction is resolved. A hold is not a decision
  and never counts as an override.
- **Isolation by design:**
  - feedback lives in its own module and tables;
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
- **Voice without anonymity.** Both routes are made under the employee's own name. That makes a correction
  possible (HR knows whose record to check) but may deter someone who fears consequences. A confidential route was
  built and then removed to keep the scope focused; discuss it as future work, including the trade-off it raises:
  an anonymous report can't tell HR whose rating to fix.
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
- Architecture: React → FastAPI (promotion | feedback) → SQLite, with the isolation boundary marked.

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

## 9. Methodological decisions and their justification (the supervisor's questions)

This section answers the supervisor's three questions: which dataset, what "promotion readiness" means, and how
fairness and proxies are assessed. Each answer has the same parts:

- **Decision:** what the study does.
- **Justification:** each reason, why it matters, and the evidence for it.
- **Alternatives considered:** what else could have been done, and why it wasn't.
- **Limitations:** what the decision can't do. State these in the thesis.
- **Suggested wording:** a paragraph to adapt for the methodology chapter. Rewrite it in your own words.

Every number comes from the project's scripts (`docs/EVALUATION_RESULTS.md`).

### 9.1 Dataset

#### Decision

**The dataset.** *Employee Promtion Prediction Dataset* (the misspelling is the dataset's own title), by Rohit
Kumar, on Kaggle: <https://www.kaggle.com/datasets/rohit8527kmr7518/employee-promtion-prediction>.

| | |
|---|---|
| Version | 1, published 14 March 2026 |
| Licence | CC0: Public Domain, so it can be used and redistributed without permission |
| Size | 100,000 employees, 43 columns plus the target `promoted` (1 = promoted, 0 = not) |
| File | `employee_promotion_prediction.csv` on Kaggle, saved in the project as `backend/data/employee_promotion_dataset_100000.csv` |
| Checked | On 2026-10-10 the project's file was identical in size (52,710,327 bytes) to the one on Kaggle |

**Citation:** Kumar, R. (2026). *Employee Promtion Prediction Dataset* (Version 1) [Data set]. Kaggle.
https://www.kaggle.com/datasets/rohit8527kmr7518/employee-promtion-prediction. Accessed [your access date].

**How it was made, according to its author:**
- a simulation of 100,000 employees in seven departments;
- promotion depends on performance, leadership, productivity and behaviour;
- a promotion budget means only about the top 10% are promoted;
- department affects salary, workload and promotion chances;
- about 2% of values are outliers;
- some factors that influence promotion, such as managerial support and project visibility, were deliberately left
  out of the data to make prediction harder.

#### Justification: why this dataset

| Reason | Why it matters | Evidence |
|---|---|---|
| It holds the information a promotion decision needs | The model can be built from performance and development only, and still has protected characteristics to audit fairness with | 43 columns: performance over three years, productivity, skills and development, leadership, reliability, and gender, age and education |
| It has a promotion outcome | Supervised learning needs a known answer to learn from and to test against (section 9.2) | The `promoted` column, for every employee |
| It is large | Enough employees for separate training, validation and test sets, and for reliable rates in each group | 100,000 employees, so 20,000 in the test set and about 1,000 PhDs among them |
| It is synthetic | Real HR records are confidential; a simulated dataset needs no consent or ethics approval to model, and no real person can be harmed or identified | The author describes it as "100,000 synthetic employee records" |
| It is openly licensed | It can be used, shared and published with the code | CC0: Public Domain |
| It was made for this kind of research | Its author lists "fairness and bias analysis" and "explainable AI for HR decisions" as intended uses | The dataset's description on Kaggle |

**Alternatives considered:**
- **Real HR data from an organisation** would be more realistic, but it is confidential, needs consent and ethics
  approval, and couldn't be published with the project.
- **The older Kaggle "HR Analytics: Employee Promotion Data"** (Kaggle, `arashnic/hr-ana`) has fewer
  performance and development measures (no peer feedback, leadership, attendance, mentoring or year-on-year
  performance), so it supports less useful explanations and tips.

#### Decision: the 20 inputs used

| Group | Inputs |
|---|---|
| Performance | performance score; **change in performance since last year** (this year minus last year, engineered); manager rating; peer feedback; KPI achievement; projects completed; tasks completed; deadline adherence; innovation, leadership, problem-solving and skill-assessment scores |
| Development | training hours last year; certifications; cross-department projects; mentoring sessions |
| Reliability | attendance rate; late days |
| Career stage | years since last promotion; years in current role |

#### Justification: what is used and what is left out

**The principle:** an input is used only if it describes **how well someone works or develops**, the things a fair
promotion decision should rest on. Every column left out has a written reason in `backend/app/promotion/features.py`.

| Columns left out (22) | Reason | Evidence or source |
|---|---|---|
| Gender, age, education level, marital status | Protected characteristics: deciding on them is discrimination. Gender, age and education are kept aside only to **audit** fairness. | Fairness by "unawareness"; section 9.3 checks that no input stands in for them |
| Department | Two people with the same record would get different scores only because of where they work | Historical promotion rates range from 2.0% (Support) to 33.2% (Engineering). Department was the earlier model's second-largest influence (26%) |
| Salary, salary increase, bonus, stock options | Pay reflects past decisions, so it could carry old pay gaps into promotions. Pay rises are decided separately, as percentages. | The system never stores salaries |
| Engagement, job satisfaction | Surveys of attitudes, not measures of performance | |
| Average monthly hours, overtime, meeting hours | Reward long hours rather than results, and disadvantage people with caring duties | |
| Remote-work ratio, contract type, city tier, team size | Working arrangements and circumstances, not performance | |
| Years at company, internal mobility | Tenure is already covered by years in role and since last promotion; mobility isn't performance | |
| Performance last year, performance two years ago | Replaced by "change in performance since last year". The three yearly scores move together so closely that a model splits their effect in confusing ways, making explanations misleading | The scores correlate at 0.92 |

**Why add "change in performance":** it says something the scores alone don't: whether someone is improving. It is
also the strongest signal, at 51.5% of the model's effect.

#### Limitations of the dataset

Measured with the project's own scripts:

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
7. **The class balance is 10% promoted,** fixed by the simulation's promotion budget. That is why PR-AUC is the main
   metric (Saito and Rehmsmeier, 2015).
8. **A single, recent, little-used source.** Version 1 of a dataset published in March 2026 by one author, so there
   are few other studies to compare results with. Its simulation hasn't been validated against real HR data.

#### Suggested wording

> This study uses the Employee Promotion Prediction Dataset (Kumar, 2026), a publicly available, CC0-licensed
> synthetic dataset of 100,000 employee records with a binary promotion outcome, of whom about 10% were promoted.
> A synthetic dataset was chosen because real HR records are confidential and could not be published or used without
> consent. Of its 43 attributes, 20 describing performance, development, reliability and career stage were used as
> model inputs. Protected characteristics (gender, age, education and marital status) were excluded from the model
> and retained only to audit fairness. Department, pay, attitude surveys and working patterns were also excluded,
> because they describe circumstances rather than how well someone works, and could carry past inequalities into
> the model. The three yearly performance scores (correlation 0.92) were replaced by the current score and its change
> since last year. The data's main limitations are that it is simulated, that its promotion rule is unpublished, and
> that its author deliberately omitted some causes of promotion.

### 9.2 Definition of promotion readiness

#### Decision

*Promotion readiness is how closely an employee's current performance and development record resembles the records
of employees who were promoted.*

- It is learned from the **historical promotion outcome** (`promoted`, yes or no).
- The model gives a score between 0 and 1. At or above the threshold (0.2283, chosen as the best F1 on validation
  data), it recommends promotion.
- The score is a **ranking**, not a probability of promotion.

#### Justification: why historical outcomes

| Reason | Why it matters | Evidence |
|---|---|---|
| A model needs a known answer to learn from and to be tested against | Without one, accuracy can't be measured, and claims about the model can't be checked | `promoted` is recorded for all 100,000 employees, so the model can be tested on 20,000 it has never seen (ROC-AUC 0.883, PR-AUC 0.474) |
| Self-defined criteria would make the results circular | If the researcher writes "ready = performance ≥ 80 and leadership ≥ 4" and trains a model on it, the model only re-learns the researcher's rule, and its accuracy proves nothing | |
| Historical outcomes show what the organisation actually rewards | A decision-support tool must first describe current practice before it can help improve it | The dataset's promotions depend on performance, leadership and productivity (Kumar, 2026) |
| It is the established approach | Promotion and HR prediction studies learn from recorded outcomes | |

#### Justification: how the weakness of historical outcomes is controlled

**The weakness:** historical outcomes repeat whatever bias past decisions had. Here the outcome depends strongly
on department (2.0% to 33.2%). So the study **constrains** the historical definition rather than accepting it as it
is:

| Control | What it prevents | Evidence |
|---|---|---|
| Only performance and development inputs (department, pay and protected characteristics removed) | Scores based on who someone is or where they work | Section 9.1; no input is a proxy for gender, age or education (section 9.3) |
| Monotonic constraints | Learning that improving something (more training, fewer late days) lowers readiness | 0 of 2,040 checks lowered a score |
| The four-fifths fairness gate | A model that treats groups unequally being used | All three ratios ≥ 0.887 |
| The model only advises | The score becoming the decision | Managers recommend, HR decides, and disagreeing with the model needs a written reason |

**Independently defined criteria are used, in the human decision.** A manager's recommendation rates four
criteria from 1 to 5, each with a real example: performance, leadership, skills and impact. So the system combines
both definitions: the **model** describes the historical pattern, and **people** apply explicit criteria.

**Alternatives considered:**
- **Independently defined criteria as the target** would need HR experts to define and validate them, and the
  results would only reproduce the researcher's own rules.
- **Expert ratings as the target** would need real experts to rate employees; none are available for a synthetic
  dataset.
- **A probability of promotion** isn't possible to claim: the model is trained to rank, and its scores aren't
  calibrated, so the score is presented as a ranking against a threshold.

#### Limitations

- **The definition is partly circular.** The model predicts who *would have been* promoted, not who *should be*.
  The fairness checks and the human decision exist because of this.
- **It inherits whatever drove past promotions,** including causes the data doesn't contain.

#### Suggested wording

> Promotion readiness is defined as the degree to which an employee's current performance and development record
> resembles those of employees who were promoted, learned from the historical promotion outcome. A historical
> outcome was chosen because a supervised model needs a known answer to learn from and be evaluated against;
> criteria defined by the researcher would have made the evaluation circular. Because historical outcomes can encode
> past bias, the definition is constrained: only performance and development inputs are used, the model may never
> lower readiness when an improvable input rises, a fairness gate must be passed, and the score only supports a
> decision that people make using explicit criteria. The score is therefore interpreted as a ranking against a
> threshold, not as a probability, and the study acknowledges that it predicts who would have been promoted rather
> than who should be.

### 9.3 Fairness and bias assessment

#### Decision

**Metric: the selection-rate ratio** (also called the disparate-impact ratio).
1. For each group, the selection rate is the share of the group the model recommends.
2. The ratio is the lowest group's selection rate divided by the highest group's.

**Threshold: 0.80, the four-fifths rule.**
- It is applied to gender, age group (under 40 / 40+) and education, on the 20,000 test employees.
- A model below 0.80 for any of them is never put into use (`backend/app/promotion/fairness.py`, enforced in
  `train.py`).

**Also reported: equal opportunity** (Hardt et al., 2016). Among people who were actually promoted, it compares the
share the model recommends (the true-positive rate) across groups.

#### Justification: why this metric

| Reason | Why it matters | Evidence or source |
|---|---|---|
| It measures the decision the system actually makes | The system's output is a recommendation; who gets recommended is what employees experience and what an organisation is accountable for | |
| It doesn't trust the historical labels | Past promotions may be biased (section 9.2). Metrics built on them, such as equal opportunity, treat past decisions as correct; the selection ratio doesn't | |
| It is an established benchmark in employment | It comes from employment-selection practice, and is widely used in algorithmic fairness research | EEOC (1978); Feldman et al. (2015) |
| It is simple to explain | HR and employees can understand "each group is recommended at a similar rate" | |

**Why equal opportunity as well:** the selection ratio could be met by recommending people at random within each
group. Equal opportunity checks that the model finds deserving people *equally well* in every group.

#### Justification: why 0.80

| Reason | Why it matters | Evidence or source |
|---|---|---|
| It is the established line for adverse impact | A recognised standard is more defensible than a number chosen by the researcher | Four-fifths rule, EEOC (1978), 29 C.F.R. § 1607.4(D) |
| It allows some difference from noise | Groups are never exactly equal in a finite sample, especially small ones such as PhDs (5.1%) | |
| It is commonly used in fairness research | Results can be compared with other studies | Feldman et al. (2015) |

**Alternatives considered:**
- **Statistical parity difference** (the gap between rates, rather than their ratio) has no established threshold
  in employment.
- **Equalised odds and calibration by group** rely on the historical labels being fair. Equal opportunity is
  reported instead of gated for the same reason.
- **A stricter threshold (0.90)** would have no recognised standard behind it. The results show how the model
  would fare anyway: gender and age are above 0.90, and education is just below (0.887).

#### Results

On the 20,000 test employees (`results/fairness.json`, `results/proxy_analysis.json`):

| Characteristic | Selection rates | Selection ratio | Equal-opportunity ratio |
|---|---|---|---|
| Gender | female 14.6%, male 14.4% | **0.981** | 0.952 |
| Age group | under 40: 14.8%, 40+: 14.3% | **0.963** | 0.899 |
| Education | Bachelor 14.3%, Master 14.7%, PhD 16.1% | **0.887** | 0.958 |

All three pass. The weakest result is age on equal opportunity: the model recommends 62.9% of the promoted
under-40s but 56.6% of the promoted over-40s. That passes, but discuss it.

#### Decision: how proxies are identified and assessed

**What a proxy is:** an input that carries information about a protected characteristic, so a model could
discriminate through it without ever seeing the characteristic (Barocas and Selbst, 2016). For example, part-time
hours could stand in for gender. Removing gender, age and education from the inputs is not enough: it must be
checked that nothing else carries them.

Three checks (`backend/evaluation/proxy_analysis.py`, `python -m evaluation.proxy_analysis`):

| Check | What it finds | Measure and threshold | Why this measure |
|---|---|---|---|
| 1. Each input on its own | A single input that differs between groups | Gender and age group: Cohen's d (under 0.2 is negligible). Age in years: correlation r (under 0.1 is negligible). Education and department: η², the share of an input's spread explained by the groups (under 0.01 is negligible) | Each measure suits its type of characteristic (two groups, a number, several groups), and each has standard thresholds (Cohen, 1988) |
| 2. All 20 inputs together | Combinations that reveal a characteristic even when no single input does | Two classifiers predict the characteristic from the 20 inputs and are scored on the test set by ROC-AUC (0.5 = guessing, 1.0 = perfect) | This is the direct test: if a classifier can't recover the characteristic, the promotion model can't use it either. Gradient boosting finds non-linear combinations a linear model would miss. Testing on unseen data avoids overstating it |
| 3. The model's own output | Whether the scores themselves follow a characteristic | The same measures, applied to the readiness score; plus selection and true-positive rates per group | Checks the end result, not only the inputs |

**Why department is checked too:** department isn't a protected characteristic, but it was removed as an input
because of its large effect, so it must be confirmed that it doesn't come back through other inputs.

#### Results

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
- **On real data, the proxy analysis must be re-run.** In real organisations proxies are common, such as hours
  worked and gender, or years of experience and age. The script works on any dataset with these columns.

#### Limitations

- **0.80 is a rule of thumb, not a statistical test.**
- **The metric says nothing about accuracy within each group.** Equal opportunity partly covers this.
- **Combinations of characteristics** (such as older women) aren't checked.
- **Only three characteristics can be audited,** because the dataset records no others.
- **Small groups (PhDs, 5.1%) make rates noisier.**

#### Suggested wording

> Fairness is assessed with the selection-rate (disparate-impact) ratio: the lowest group's recommendation rate
> divided by the highest group's, for gender, age group and education on the held-out test set. A model with a
> ratio below 0.80, the four-fifths rule of the Uniform Guidelines on Employee Selection Procedures (EEOC, 1978),
> is never deployed. This metric was chosen because it measures the decision the system actually makes, does not
> assume the historical promotion labels are fair, and is an established standard in employment selection. Equal
> opportunity (Hardt et al., 2016) is reported alongside it. To detect proxy variables, each input's association
> with each protected characteristic was measured (Cohen's d, correlation and η², with conventional negligibility
> thresholds), and two classifiers were trained to predict each characteristic from all inputs together, evaluated
> by ROC-AUC on unseen data. Neither classifier predicted gender, age or education better than chance (ROC-AUC
> 0.50), indicating no proxies; department, which had been excluded, remained partly predictable (ROC-AUC 0.67)
> through tasks and projects completed.
