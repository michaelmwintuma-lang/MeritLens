# Data model

Every table in the database (SQLite, `backend/instance/app.db`), what it holds, and who can read and change it.
Browsers never touch the database: every read and write goes through an API route that checks the signed-in role
(`require_roles` in `backend/app/core/security.py`). Tables are grouped by the part of the system that owns them.

**Roles:** employee, manager, HR, admin, finance, auditor (compliance auditor, read-only).

**Never stored anywhere:** gender, age, education, marital status, salaries, who sent a report, the time a report or
message was sent (only the day), IP addresses, and report keys (only their hash).

## Accounts and the audit trail (`app/accounts`, `app/core`)

| Table | Holds | Read by | Changed by |
|---|---|---|---|
| `users` | One row per login: username, name, email, password hash (PBKDF2), role, active, must-change-password, linked employee record, profile details, the admin's "can view employee data" permission, wrong-password count and lock time, token version (raised on password change, reset and sign-out) | Each user sees themselves; the admin sees all | The user (own profile and password); the admin (accounts, resets, permissions); sign-in (wrong-password count and lock) |
| `activity_log` | Important actions: day (never the time), who, what, details. Nothing a reporter does is recorded. | Admin | Written by the routes as actions happen. Entries are never edited, except that deleting an account removes the link to it (the name stays). |
| `demo_requests` | "Book a demo" requests from the website | Admin | Anyone can send one (rate-limited); the admin ticks them off |

## Predict and decide (`app/promotion`)

| Table | Holds | Read by | Changed by |
|---|---|---|---|
| `employees` | Name, department, manager, and the work record: the model's 20 inputs, as JSON | HR all; a manager their team; an employee themselves; an admin with permission (read-only). The auditor reads none. | HR (add, edit, import) |
| `record_changes` | Every change to a work record's model inputs: who, when, each old and new value, the reason, readiness before and after, model version, and whether HR edited it or confirmed a correction | HR, auditor | Written when HR edits a record or confirms a correction; **never edited or deleted** |
| `nominations` | A manager's recommendation: role, start date, ratings with examples, reason, proposed pay rise (a percentage), and the reason for disagreeing with the model if it didn't recommend the person | HR all; a manager their own | Managers (create); HR (decide) |
| `decisions` | HR's decision on a nomination, with the model's score, threshold, recommendation and **version** at that moment, whether HR agreed, the reason (required to disagree), the pay rise and Finance's status | HR, auditor; a manager sees their own nominations' outcomes | HR (decide, resubmit a pay rise); Finance (status) |
| `pay_reviews` | Every step of a pay rise through Finance: submitted, returned, resubmitted, signed off | HR, Finance | Written by those steps; never edited |
| `pay_policy` | The range a promotion pay rise should fall in | HR, managers | HR |

## Respond: the employee feedback channel (`app/feedback`)

**The promotion code never reads these tables.** A static check and an isolation test enforce this
(`backend/tests/test_isolation.py`).

| Table | Holds | Read by | Changed by |
|---|---|---|---|
| `explanation_ratings` | An employee's rating of their explanation: clarity and usefulness (1–5), factors marked "seems wrong" or "seems unfair", an optional comment, the model version, and the score it explained (worked out on the server). One per employee per model version. | The employee (their own); HR and the auditor **in aggregate only** (rates withheld below 5 ratings); never managers | The employee (create or replace) |
| `correction_requests` | A request to correct one value in a work record: the value, what the record said, what was asked, the evidence (a note, and optionally a file stored under a random name), and HR's decision: status, verified value, reason, readiness before and after, a link to the `record_changes` row. Re-appraisals (`source = reappraisal`) **hold no link to the report** they came from. | The employee (their own; never HR's note on a re-appraisal); HR all; never managers | Employees (create, attach a file); HR (confirm or reject, open a re-appraisal) |
| `nomination_deferrals` | A promotion decision put on hold while a correction is pending: when, by whom, and when and why it was lifted | HR | HR (hold, resume); lifted by itself when the correction is decided |

## Anonymous reporting (`app/reporting`)

The promotion code never reads these tables. They hold no user, account or employee column, no times (only
days), and no hidden row order: SQLite's `WITHOUT ROWID`, so the order reports arrived in can't be recovered.

| Table | Holds | Read by | Changed by |
|---|---|---|---|
| `reports` | Case ID (random), category, the anonymised text the reporter approved, the day, the key's hash, suggested and set priority, status, outcome, wrong-key count and lock time | HR; the reporter with the case ID and key | The reporter (create); HR (priority, status, outcome) |
| `report_messages` | The conversation: "reporter" or "investigator", text, day, a running number | HR; the reporter with the key | Both sides (append only) |
| `report_evidence` | Photos and videos, with location, device, owner and time removed; random file names; the day | HR; the reporter with the key | The reporter (add, remove while the case is open) |

## Files outside the database

| Where | Holds |
|---|---|
| `backend/models/` | The live model, its information (threshold, inputs, version, training statistics, the list of departments) and the 2,000-employee training sample used for LIME, importance and drift |
| `results/` | The results the training and evaluation scripts wrote (`docs/EVALUATION_RESULTS.md`) |
| `backend/instance/evidence/`, `backend/instance/correction_evidence/` | Report evidence and correction evidence, served only through the API, never cached |
| `backend/instance/outbox/` | Emails saved instead of sent when no mail server is set up |
| `backend/instance/secret.key` | The key that signs login tokens (or `APP_SECRET_KEY`) |

`backend/instance/` and `backend/.env` are never committed.
