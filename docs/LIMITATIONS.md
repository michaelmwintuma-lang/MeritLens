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
- **Group fairness, not individual fairness.** The four-fifths rule on recommendation rates is the gate. Each
  group's accuracy (true- and false-positive rates, precision) and gender within each age group are now reported
  on the model card, but they inform rather than block a release, and none of these checks says whether the model
  is fair to an individual. Combinations beyond gender and age group aren't checked.
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
- **A second HR person is optional.** With FOUR_EYES=1, a correction that moves someone across the threshold waits
  for a second HR person; it is off by default because the demo has one HR account, and corrections that don't
  cross the threshold are always decided by one person (logged with who).
- **Small groups limit what the dashboard can show.** Rates need 5 ratings and departments 5 people, so a small
  organisation sees few numbers. This trades detail for privacy.
- **Rating comments are free text.** They are never shown, not even in aggregate, but they are stored, and an
  employee could name someone in one.
- **A hold is placed by HR, not automatically.** Since the redesign the server refuses a decision while it is on
  hold (the hold lives in a neutral table the decision code may read). But a pending correction doesn't put a
  nomination on hold by itself: HR chooses to, after reading the committee note.

### Governance

- **Live fairness needs equality-monitoring data.** It is filled in for the 120 demo employees from their rows of
  the synthetic dataset; employees HR adds or imports have none, so they are left out (never guessed). A real
  deployment would collect it voluntarily, with "prefer not to say", and explain its purpose.
- **Live fairness on a small directory says little.** With 120 employees and a handful of decisions, most stages
  show "not enough data yet". Groups under 5 are never shown, by design.
- **A second approver for releases is optional.** A release needs a named HR person and a written note; with
  FOUR_EYES=1 a second HR person must also approve it. It is off by default (the demo has one HR account). Before
  releasing, HR sees what would change for today's employees.
- **The audit trail proves, it doesn't prevent.** Its hash chain shows that an event was changed or deleted, and
  where; with SQLite, someone with access to the database file could still change it (the chain would show it).
  With PostgreSQL, the app's roles can't change or delete events (`deploy/postgres/grants.sql`), though the
  tables' owner could grant itself back that right.
- **The background worker lives inside the API process.** LIME runs on one worker thread; its results are kept in
  memory and are lost when the API restarts (they are simply worked out again). A larger deployment would use a
  task queue such as Redis with RQ or Celery behind the same functions.

### The system

- **Deployment is written but not yet run end to end.** `deploy/` holds a Docker Compose set-up (PostgreSQL, the
  API, and Caddy for HTTPS) and the CI builds its images, and the CI runs the tests on PostgreSQL too, but neither
  Docker nor PostgreSQL was available where it was written, so a real deployment should be tried on a test server
  first. Backups (nightly, checksummed, with restore: `docs/BACKUPS.md`), migrations, structured logs and error
  alerts are in place and tested on SQLite. There is still no protection against heavy automated traffic beyond
  limits on sign-in and the demo form, and one API process (the timer runs inside it).
- **Only the API layer is TypeScript.** Types are generated from the backend's OpenAPI contract and checked on every
  build, but the pages are still JavaScript, so a page can still misuse an answer the API layer leaves loosely
  typed (many older endpoints describe their answers only loosely).
- **Emails go through one Gmail account** with an app password, which has daily sending limits.
- **Windows Smart App Control** blocks parts of the machine-learning libraries on the development computer, so the
  backend runs in WSL (Ubuntu) there. On a normal Linux server this doesn't arise.
- **Pay-rise fairness compares averages only.** Live fairness compares the average promotion pay rise per group
  (groups with 5 or more rises). It doesn't adjust for role or level, and only percentages are kept, never
  salaries.
- **Tested mostly by its developer.** 400 automated tests and 11 browser checks verify behaviour and privacy
  rules, and an accessibility audit found nothing on 45 pages. But usability and perceived fairness with real users
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
4. **Retrain on real data** with an organisation's consent (the data mapping in `backend/data/mappings/` is the
   way in), and test individual fairness and more combinations of characteristics.
5. **Production readiness**: run the Docker deployment and the PostgreSQL tests for real, a task queue for the
   background work (so the API can run several processes), a transactional email service, and separate
   organisations (multi-tenancy).
