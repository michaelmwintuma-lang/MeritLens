# Limitations and future work

An honest account of what the platform does not do, or does only partly, and what would come next. Written to be
adapted for the thesis's "Limitations" and "Future work" sections.

## Limitations

### Data and the model

- **Synthetic data.** The model was trained and is demonstrated on 100,000 made-up employees
  (`backend/data/employee_promotion_dataset_100000.csv`). Its results (ROC-AUC 0.88 on 20,000 unseen test
  employees; every group above 80% of the highest recommendation rate) describe how it does on this data, not on a
  real organisation. Real use would need retraining on the organisation's own history, with the four-fifths
  check passing on its own people before going live.
- **Past decisions carry past bias.** A model trained on who *was* promoted learns the habits of past decisions,
  including unfair ones. Leaving gender, age, education and pay out of the inputs, and checking group rates, reduces
  this but cannot remove it: other inputs (e.g. training hours, leadership scores given by managers) can carry bias
  of their own.
- **Group fairness, one check.** The four-fifths rule compares recommendation rates between groups. It doesn't
  show whether the model is equally *accurate* for each group, or fair to individuals, and it checks each
  characteristic separately rather than in combination (e.g. older women).
- **Fairness costs accuracy.** Department was removed from the model because it scored people by where they work.
  Test PR-AUC fell from 0.633 (an earlier logistic regression with department) to 0.474. The model predicts past
  decisions less well because it no longer repeats their departmental pattern.
- **Department partly comes back through two inputs.** Tasks and projects completed differ by department, so the
  model still recommends 24.7% of Engineering but 7.9% of HR, although department isn't an input
  (`results/proxy_analysis.json`). Comparing those counts within each department would reduce this.
- **The dataset is a single simulation.** Kumar (2026), *Employee Promtion Prediction Dataset*, Kaggle, CC0. Its
  author deliberately left some causes of promotion (such as managerial support) out of the data, which limits how
  accurate any model can be, and the simulation hasn't been validated against real HR data.
- **One input dominates.** Change in performance since last year accounts for about half of the model's effect.
- **Monotonic constraints are a design choice.** The model can never lower a score when an input a person can
  improve goes up. That rules out patterns the data might hold, such as diminishing or negative returns at the
  extremes.
- **Drift is noisy for small groups.** For a directory of 120, chance alone reaches a PSI of about 0.14–0.16 on
  some inputs. The check compares against that, but with 20 inputs, about one may still be flagged by chance.
- **Explanations describe the model, not the world.** The exact contributions (equal to SHAP values) show what moved the model's score; it doesn't prove
  those factors cause promotion. The tips are therefore "what would change the model's view", not guaranteed
  career advice.

### The feedback channel

- **No real use yet.** Its measures (clarity and usefulness rates, contest shares, correction confirmation rate,
  time to decide) come from use, and the database holds none yet; they are to be collected in the user study.
- **Feedback informs people, not the model.** By design, ratings never reach the model, and nothing
  retrains automatically. Feedback changes scores only through corrections HR confirms; systematic complaints about
  a factor show on the dashboard, but acting on them (for example retraining without a contested input) is a human
  decision.
- **No confidential route.** Rating an explanation and asking for a correction are both done under the employee's
  own name. That lets HR fix the right record, but someone who fears consequences may stay silent. A confidential
  route was built and then removed to keep the scope focused (see Future work).
- **One HR person decides each correction.** There is no second-person rule; every decision is logged with who
  made it.
- **Small groups limit what the dashboard can show.** Rates need 5 ratings and departments 5 people, so a small
  organisation sees few numbers. This trades detail for privacy.
- **Rating comments are free text.** They are never shown, not even in aggregate, but they are stored, and an
  employee could name someone in one.
- **A hold on a decision is advisory.** The promotion code can't read the feedback tables (that is the isolation
  rule), so it can't refuse a decision while a correction is pending. The page hides the decision form while a
  decision is held, but the API would accept a decision.

### The system

- **A prototype, not a production service.** SQLite and a single server suit a demonstration, not many users at
  once. There are no backups, no HTTPS set-up, and no protection against heavy automated traffic beyond simple
  limits on the demo form.
- **Emails go through one Gmail account** with an app password, which has daily sending limits.
- **Windows Smart App Control** blocks parts of the machine-learning libraries on the development computer, so the
  backend runs in WSL (Ubuntu) there. On a normal Linux server this doesn't arise.
- **Pay rises can't be checked for fairness across groups**, because protected characteristics are deliberately
  not stored with employee records. Only percentages are kept, never salaries.
- **Tested mostly by its developer.** 281 automated tests and 6 browser checks verify behaviour and privacy rules,
  and an accessibility audit found nothing on 15 pages. But usability and perceived fairness with real users
  depend on the user test (`docs/USER_TEST.md`).
- **CI hasn't run on GitHub yet.** The workflow is written and each of its steps passes locally, but the
  repository has no remote.

## Future work

1. **A confidential route for reporting unfair assessments** (removed from this version to keep the scope focused;
   see git tag with-anonymous-reporting). It was built with an anonymiser, case keys, a triage model, evidence
   cleaning and a two-way conversation; its design, threat model and evaluation are in `docs/future-work/`. The
   main open question is the trade-off between anonymity and redress: an anonymous report can't tell HR whose
   rating to fix.
2. **Run the user study**, with the feedback-channel tasks and the perceived-fairness questions, and report the
   feedback dashboard's measures from it.
3. **Compare tasks and projects within each department**, so department doesn't come back into the scores through
   them (`results/proxy_analysis.json`).
4. **Retrain on real data** with an organisation's consent, and extend the fairness checks: accuracy per group,
   combinations of characteristics, and monitoring over time.
5. **Production readiness**: PostgreSQL, HTTPS, backups, a transactional email service, and separate
   organisations (multi-tenancy).
