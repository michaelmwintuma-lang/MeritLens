# Limitations and future work

An honest account of what the platform does not do, or does only partly, and what would come next. Written to be
adapted for the thesis's "Limitations" and "Future work" sections.

## Limitations

### Data and the model

- **Synthetic data.** The model was trained and is demonstrated on 100,000 made-up employees
  (`backend/data/employee_promotion_dataset_100000.csv`). Its results (ROC-AUC 0.93 on 20,000 unseen test
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
- **Explanations describe the model, not the world.** SHAP shows what moved the model's score; it doesn't prove
  those factors cause promotion. The tips are therefore "what would change the model's view", not guaranteed
  career advice.

### Reporting

- **Rule-based anonymiser.** It reliably removes directory names, emails, phone numbers and calendar dates, but
  misses what its rules don't describe: nicknames, people outside the organisation, first names in lower case,
  addresses written in words, short extensions (developer test set: 87% of details removed; see
  `docs/EVALUATION.md`). The reporter reviews and approves the cleaned text, which is the main safeguard.
- **Writing style can still identify someone.** No anonymiser removes how a person writes, or details only
  colleagues would recognise. The warnings about identifying phrases help, but can't catch everything.
- **Keyword triage.** Triage got 74% right on the developer set and placed 12 of 50 reports lower than they
  needed, including indirect descriptions of threats, unwanted touching and self-harm. It is a suggestion with
  reasons; HR sets the real priority.
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

### The system

- **A prototype, not a production service.** SQLite and a single server suit a demonstration, not many users at
  once. There are no backups, no HTTPS set-up, and no protection against heavy automated traffic beyond simple
  limits on the demo form.
- **Emails go through one Gmail account** with an app password, which has daily sending limits.
- **Windows Smart App Control** blocks parts of the machine-learning libraries on the development computer, so the
  backend runs in WSL (Ubuntu) there. On a normal Linux server this doesn't arise.
- **Pay rises can't be checked for fairness across groups**, because protected characteristics are deliberately
  not stored with employee records. Only percentages are kept, never salaries.
- **Tested mostly by its developer.** 224 automated tests check behaviour and privacy rules, and every page was
  checked in a browser as each role, but usability with real users depends on the user test (`docs/USER_TEST.md`).

## Future work

1. **Collect the external evaluation set** and measure the anonymiser and triage on reports the rules never saw.
2. **Improve triage fairly**: more word forms and phrases, or a trained text classifier, developed on the
   developer set and measured on the external set.
3. **Better name detection**: a named-entity recogniser to catch names outside the directory and nicknames, kept
   alongside the directory list.
4. **Retrain on real data** with an organisation's consent, and extend the fairness checks: accuracy per group,
   combinations of characteristics, and monitoring over time.
5. **Reporting as a service for other organisations**: an API where reports go straight from the employee's
   browser to the reporting service, never through the employer's servers, with HR systems reading cases through
   keys and webhooks.
6. **Production readiness**: PostgreSQL, HTTPS, backups, a transactional email service, and separate
   organisations (multi-tenancy).
7. **Daily digests instead of instant report alerts**, to remove the timing clue.
