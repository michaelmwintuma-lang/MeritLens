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
- **The dataset's origin is unverified.** Its Kaggle page, author and licence aren't recorded in the project.
- **One input dominates.** Change in performance since last year accounts for about half of the model's effect.
- **Monotonic constraints are a design choice.** The model can never lower a score when an input a person can
  improve goes up. That rules out patterns the data might hold, such as diminishing or negative returns at the
  extremes.
- **Drift is noisy for small groups.** For a directory of 120, chance alone reaches a PSI of about 0.14–0.16 on
  some inputs. The check compares against that, but with 20 inputs, about one may still be flagged by chance.
- **Explanations describe the model, not the world.** The exact contributions (equal to SHAP values) show what moved the model's score; it doesn't prove
  those factors cause promotion. The tips are therefore "what would change the model's view", not guaranteed
  career advice.

### Reporting

- **Rule-based anonymiser.** It reliably removes directory names, emails, phone numbers and calendar dates, but
  misses what its rules don't describe: nicknames, people outside the organisation, first names in lower case,
  addresses written in words, short extensions (developer test set: 87% of details removed; see
  `docs/EVALUATION.md`). The reporter reviews and approves the cleaned text, which is the main safeguard.
- **Writing style can still identify someone.** No anonymiser removes how a person writes, or details only
  colleagues would recognise. The warnings about identifying phrases help, but can't catch everything.
- **Triage leans towards caution, and learned from few examples.** The language model was trained on about 280
  example reports written by the developer. On the developer test set it put far fewer urgent reports too low
  than the old keyword list (5 of 50 instead of 12; every high-priority report caught), but it also raised more
  false alarms (12 instead of 1), so overall accuracy fell from 74% to 66%. It sometimes reacts to topic words
  ("night shift", "security") rather than meaning. It is a suggestion with reasons; HR sets the real priority.
- **The self-harm phrases in the safety rules were added after the developer test set had been seen**, so they
  flatter its one self-harm report. They were kept because a missed self-harm report is the worst possible
  mistake; the external set is the fair measure.
- **Cleaning evidence removes hidden details, not what can be seen or heard.** Location, device, owner and time
  are removed from photos and videos, but a face, a reflection, a view from someone's desk or a voice can still
  identify the reporter. The reporter is warned and can remove the sound from videos or delete a file, but faces
  aren't blurred automatically. Evidence files are stored unencrypted on the server, like the database.
- **Evaluated mainly on the developer's own reports.** The developer wrote both the rules and the main test set,
  which likely flatters the results. A set written by others (`reports_external.json`) is the fairer test.
- **Sign-in is required to report.** This differs from the original brief (which asked for reporting without
  signing in). It was chosen so only members of the organisation can report, while the report is never linked to
  the account. Trust in that promise depends on how the system is run: whoever controls the server could, in
  principle, change the code to record more.
- **Timing.** HR's email alert arrives moments after a report is sent. Someone who also knows who was at a
  computer at that moment could narrow down the reporter. Only dates are stored, but the alert itself is a
  timestamp.
- **The activity log records sign-ins** (by date only). On a day when only one person signed in, that alone could
  point at the author of a report sent that day.

### The feedback channel

- **No real use yet.** Its measures (clarity and usefulness rates, contest shares, correction confirmation rate,
  time to decide) come from use, and the database holds none yet; they are to be collected in the user study.
- **Feedback informs people, not the model.** By design, ratings and reports never reach the model, and nothing
  retrains automatically. Feedback changes scores only through corrections HR confirms; systematic complaints about
  a factor show on the dashboard, but acting on them (for example retraining without a contested input) is a human
  decision.
- **Anonymity and redress pull against each other.** An anonymous report can't tell HR whose rating it's about,
  and the reporter can't say so even if they wish (the conversation refuses names). So an anonymous report about
  one's *own* rating changes that rating only if HR's own investigation finds it. The page explains the choice:
  "Correct my record" fixes your own record directly but isn't anonymous; reporting anonymously protects you but
  depends on HR's investigation. An opt-in way to reveal oneself to HR was not built, because it would weaken the
  promise that nothing can link a report to a person.
- **One HR person can confirm their own re-appraisal.** There is no second-person rule; every confirmation is
  logged with who made it.
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
- **Tested mostly by its developer.** 372 automated tests and 7 browser checks verify behaviour and privacy rules,
  and an accessibility audit found nothing on 17 pages. But usability and perceived fairness with real users
  depend on the user test (`docs/USER_TEST.md`).
- **CI hasn't run on GitHub yet.** The workflow is written and each of its steps passes locally, but the
  repository has no remote.

## Future work

1. **Collect the external evaluation set** and measure the anonymiser and triage on reports the rules never saw.
2. **Improve triage fairly**: more and more varied training examples, ideally written by other people, to reduce
   false alarms; then measure on the external set, which the model never saw.
3. **Blur faces in photos** automatically before HR sees them, with the reporter choosing what to keep.
4. **Better name detection**: a named-entity recogniser to catch names outside the directory and nicknames, kept
   alongside the directory list.
5. **Retrain on real data** with an organisation's consent, and extend the fairness checks: accuracy per group,
   combinations of characteristics, and monitoring over time.
5. **Reporting as a service for other organisations**: an API where reports go straight from the employee's
   browser to the reporting service, never through the employer's servers, with HR systems reading cases through
   keys and webhooks.
6. **Production readiness**: PostgreSQL, HTTPS, backups, a transactional email service, and separate
   organisations (multi-tenancy).
7. **Daily digests instead of instant report alerts**, to remove the timing clue.
