# Threat model

> **Removed feature.** This document describes anonymous reporting, which was removed from this version to keep
> the scope focused on predicting, explaining and responding through the employee feedback channel. It is kept
> for future work. The last version with the feature is the git tag `with-anonymous-reporting`
> (`git checkout with-anonymous-reporting`).

Who might try to misuse the system, what they would try, what stops them, and the automated test that shows it.
Then what isn't stopped: the residual risks.

**What is protected:**
- the anonymity of reporters;
- the integrity of promotion scores, which feedback and complaints must never change;
- the fairness of the model;
- employees' records and feedback, which must reach only the people entitled to them;
- the accountability of decisions.

**Who might attack:**
- an employee trying to raise their own score or see others';
- a manager trying to identify a reporter or see feedback about their team;
- HR or an administrator trying to unmask a reporter;
- an outsider with no account;
- someone with access to a shared computer.

Tests are in `backend/tests/`; browser checks are in `scripts/browser_checks.js`.

## Attacks and defences

### The model and its scores

| # | Attack | Defence | Evidence |
|---|---|---|---|
| 1 | Complain, or rate explanations badly, to push a score up or someone else's down | Ratings and reports are stored apart; nothing in the promotion code reads them; only HR confirming a correction against evidence changes a record | `test_isolation.py::test_feedback_and_reports_never_change_a_prediction_but_a_confirmed_correction_does`; `test_feedback.py::test_a_rating_never_changes_a_score` |
| 2 | Change the promotion code so it quietly reads feedback or reports | A static check fails if any file in `app/promotion` imports or names the feedback or reporting code or tables; a run-time check records the SQL the prediction endpoints run | `test_isolation.py::test_the_promotion_code_never_imports_or_names_feedback_or_reports`, `::test_the_prediction_endpoints_run_no_sql_on_feedback_or_report_tables` |
| 3 | An employee edits their own record | Only HR can add or edit records | `test_feedback.py::test_employees_cant_edit_the_data_the_model_uses`; `test_employee_records.py` |
| 4 | Change a record without trace | Every change to a model input is kept with old and new values, readiness before and after, the reason and the model version; the history can't be changed | `test_employee_records.py::test_an_edit_keeps_old_and_new_values_the_scores_and_the_model_version`, `::test_the_history_cannot_be_changed_or_deleted` |
| 5 | A biased model goes live | Protected characteristics, pay and department are never inputs; the four-fifths check must pass or the model isn't saved | `test_training.py::test_protected_characteristics_and_pay_are_never_model_inputs`, `::test_department_is_not_a_model_input`, `::test_live_model_passed_the_fairness_check_and_predicts` |
| 6 | A model that punishes improvement (more training lowering a score) | Only models with no common-sense violations are eligible; the live model is monotonic | `test_training.py::test_a_model_that_lowers_scores_when_inputs_improve_is_not_eligible`; `test_explanations.py::test_improving_any_input_never_lowers_the_score` |
| 7 | Feedback retrains the model automatically | There is no retraining code path at all: only `train.py`, run by a person | Code review: `app/` has no training code |
| 8 | Decide against the model without accountability | Disagreeing needs a reason of at least 20 characters; every decision stores the model's score, recommendation and version | `test_decisions.py` |

### Who sees what

| # | Attack | Defence | Evidence |
|---|---|---|---|
| 9 | A manager reads ratings or correction requests about their team | Feedback endpoints are for the employee (their own) and HR or the auditor; managers get 403; the committee note is HR-only | `test_feedback.py::test_ratings_are_shown_only_in_aggregate_and_never_to_managers`, `::test_managers_never_see_correction_requests`, `::test_managers_dont_see_the_committee_note` |
| 10 | Read one person's rating from the dashboard by filtering to a small group | Rates withheld below 5 ratings; counts of 1 or 2 shown as "<3"; departments with fewer than 5 people can't be chosen | `test_dashboards.py::test_clarity_and_usefulness_rates_need_at_least_five_ratings`, `::test_departments_with_fewer_than_five_people_cant_be_chosen` |
| 11 | The auditor sees reports, people's records, or changes something | The auditor has read-only access to decisions, the model, record histories and aggregates | `test_auditor.py::test_the_auditor_cannot_see_reports_or_people_or_change_anything` |
| 12 | A manager or employee sees someone else's score | Every promotion endpoint checks who may see whom | `test_explanations.py` (who sees whom), `test_profiles_and_permissions.py` |
| 13 | Someone who isn't an admin manages accounts | Admin-only routes | `test_auth_and_roles.py::test_non_admins_cannot_manage_accounts` |

### Anonymity of reporters

| # | Attack | Defence | Evidence |
|---|---|---|---|
| 14 | Look up who sent a report | The tables have no user column, no times, and no hidden row order; there is nothing to look up, for any role, including administrators | `test_reporting.py::test_nothing_about_the_reporter_is_stored`, `::test_reports_have_no_hidden_order` |
| 15 | Read the activity log to match a sign-in to a report | Nothing a reporter does is logged; the log keeps only days | `test_activity.py::test_nothing_a_reporter_does_is_logged`, `::test_only_the_day_is_kept_never_the_time` |
| 16 | Read report keys from a shared browser | The website never keeps report keys: no "save on this device" and no polling of saved keys | Browser check "no report keys page and nothing saved in the browser"; `test_accounts_and_notifications.py::test_there_is_no_bulk_check_of_saved_cases` |
| 17 | Link a re-appraisal to the report that triggered it | The correction stores no case ID, and neither does the activity log | `test_feedback.py::test_a_case_closed_as_rating_found_unfair_opens_a_normal_correction_with_no_link_to_it` |
| 18 | Names, emails, phones or dates in the text identify the reporter | The anonymiser replaces them; the reporter checks the result; text that still identifies someone is refused | `test_reporting.py::test_text_that_still_identifies_someone_is_refused` |
| 19 | Photo or video metadata identifies the reporter | Location, device, owner and time are removed; the original file name is never kept | `test_evidence.py::test_a_photo_loses_its_location_device_and_owner`, `::test_the_original_file_name_is_never_kept` |
| 20 | Guess a case key | Keys are random 16 characters and stored only as a hash; 5 wrong keys lock the case for 15 minutes; one message for every failure | `test_reporting.py::test_five_wrong_keys_lock_the_case_for_15_minutes`, `::test_wrong_case_and_wrong_key_get_the_same_answer` |

### Accounts and sessions

| # | Attack | Defence | Evidence |
|---|---|---|---|
| 21 | Guess passwords | 5 wrong passwords lock the account for 15 minutes; one message for every failure, so nobody learns whether an account exists or is locked; PBKDF2 with 200,000 rounds | `test_auth_and_roles.py::test_five_wrong_passwords_lock_the_account_for_15_minutes`, `::test_wrong_password_and_unknown_user_get_the_same_message`, `::test_the_app_hashes_with_200000_rounds_unless_told_otherwise` |
| 22 | Keep using a stolen login after the password is changed | Tokens carry a version that goes up on password change, admin reset and sign-out | `test_auth_and_roles.py::test_changing_the_password_signs_out_other_devices_but_not_this_one`, `::test_an_admin_password_reset_signs_the_person_out`, `::test_signing_out_withdraws_the_token` |
| 23 | A deactivated account keeps working | The role and active status are read from the database on every request | `test_auth_and_roles.py::test_deactivated_accounts_are_locked_out_at_once` |
| 24 | Upload a disguised file as evidence | Files are recognised by their contents (photos and videos for reports; PDF, JPEG and PNG for corrections), size-limited, stored under random names, and served only through the API | `test_evidence.py::test_only_real_photos_and_videos_are_accepted`; `test_feedback.py::test_evidence_files_are_pdf_jpeg_or_png_and_only_hr_and_the_employee_see_them` |
| 25 | A demo login with a known password appears in a real deployment | Demo accounts are added only to an empty database, or to a demo database whose admin still has the demo address | `test_auditor.py::test_an_existing_demo_database_gets_the_auditor_account_but_a_real_one_does_not` |

## Residual risks

What these defences do **not** stop. These belong in the thesis's limitations.

1. **Whoever runs the server** could change the code to record more, such as who sent which request. Anonymity
   depends on the server being run as published. Reporting requires sign-in, so every reporting request carries
   the user's login token, although it is never stored.
2. **Timing.** HR's email about a new report arrives moments after it is sent. Someone who knows who was at a
   computer then could narrow down the reporter.
3. **Small organisations.** On a day only one person signs in, the activity log (days only) could still point at
   the author of that day's report.
4. **Writing style and content.** No anonymiser removes how someone writes or details only colleagues would
   recognise. The warnings help but can't catch everything. Faces and voices in evidence aren't blurred.
5. **The anonymiser's misses.** It removed 87% of identifying details on the developer's set. Nicknames, people
   outside the directory and spelled-out emails slip through. The reporter's own review is the main safeguard.
6. **Bias the inputs carry.** Manager ratings and other inputs can carry bias of their own. The four-fifths check
   is per characteristic, not for combinations such as older women, and measures recommendation rates, not
   accuracy for each group.
7. **Retraining is manual.** Drift is shown, but if nobody acts on it, the model ages.
8. **HR can confirm their own re-appraisal.** There is no rule that a second person must confirm it. Every
   confirmation is logged with who made it.
9. **Locking someone out.** Anyone who knows a username or case ID can lock that account or case for 15 minutes
   with wrong attempts. This is the price of the lockout.
10. **Evidence files and the database are not encrypted on disk.** Anyone who can read the server's disk can read
    them.
11. **Comments in ratings** are free text. An employee could name someone in them. They are never shown, not even
    in aggregate, but they are stored.
12. **The system is not deployed.** There is no HTTPS, backup or monitoring set-up. Those would be needed before
    real use.
13. **A held decision can still be made through the API.** The hold is enforced by the page, not the server,
    because the decision code belongs to the promotion module, which by the isolation rule may not read feedback
    tables. A decision made this way is still logged with the model's view and, if it disagrees, a written reason.
