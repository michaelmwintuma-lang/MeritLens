# Data model

Every table in the database (SQLite by default, `backend/instance/app.db`; or PostgreSQL, `deploy/postgres/`), what
it holds, and who can read and change it.
Browsers never touch the database: every read and write goes through an API route that checks the signed-in role
(`require_roles` in `backend/app/core/security.py`). Tables are grouped by the part of the system that owns them.

**Roles:** employee, manager, HR, admin, finance, auditor (compliance auditor, read-only).

**Never stored anywhere:** marital status, an exact age or birth date, salaries, the time of a sign-in or other
everyday action (the activity log keeps only the day), and IP addresses. Gender, an age band and education are
kept only in `equality_monitoring`, apart from the employee directory, for live fairness totals.

## Accounts and the audit trail (`app/accounts`, `app/core`)

| Table | Holds | Read by | Changed by |
|---|---|---|---|
| `users` | One row per login: username, name, email, password hash (PBKDF2), role, active, must-change-password, linked employee record, profile details, the admin's "can view employee data" permission, wrong-password count and lock time, token version (raised on password change, reset and sign-out) | Each user sees themselves; the admin sees all | The user (own profile and password); the admin (accounts, resets, permissions); sign-in (wrong-password count and lock) |
| `activity_log` | Important actions: day (never the time), who, what, details. | Admin | Written by the routes as actions happen. Entries are never edited, except that deleting an account removes the link to it (the name stays). |
| `demo_requests` | "Book a demo" requests from the website | Admin | Anyone can send one (rate-limited); the admin ticks them off |
| `audit_events` | The audit trail: each nomination, decision (with the model's score, threshold, version and top factors), pay step, record change, correction, hold and model release, with who, exactly when, and a SHA-256 hash chained to the event before. Never holds what an employee wrote. | Auditor, admin | Appended by the routes as things happen; **never changed or deleted** (refused by the code; with PostgreSQL, by the database roles) |
| `decision_holds` | A promotion decision put on hold: which nomination, why (a fixed code), by whom, when, and when and why it was lifted. Nothing an employee wrote. | HR; the decision code (to refuse a held decision) | HR (hold, resume); lifted by itself when the correction is decided |

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
| `correction_requests` | A request to correct one value in a work record: the value, what the record said, what was asked, the evidence (a note, and optionally a file stored under a random name), and HR's decision: status, verified value, reason, readiness before and after, a link to the `record_changes` row. (`source` is always `employee`; an earlier version also had HR-opened re-appraisals.) | The employee (their own; never HR's note on a re-appraisal); HR all; never managers | Employees (create, attach a file); HR (confirm or reject, open a re-appraisal) |


Holds used to be kept here (`nomination_deferrals`), where the decision code couldn't read them. They moved to
`decision_holds`; an older database's holds are moved across and the old table dropped on start
(`move_deferrals_to_holds` in `backend/app/core/database.py`).

## Governance (`app/governance`)

| Table | Holds | Read by | Changed by |
|---|---|---|---|
| `model_releases` | Every release of a model version: version, the version it replaced, who released it, when, and their note | HR, admin, auditor (Model registry) | HR (release); never edited |
| `equality_monitoring` | Gender, age band (under 40 / 40+) and education per employee, for live fairness only. **The promotion code never reads it** (static and run-time checks; with PostgreSQL, its role has no access). Never shown per person; groups under 5 never shown. | The live fairness check, in aggregate only | Filled for the demo employees from the synthetic dataset |

## Removed: anonymous reporting

An earlier version had three more tables (`reports`, `report_messages`, `report_evidence`) for anonymous
reporting. That feature was removed; when the app starts on a database made by the earlier version, it drops
those tables, their activity-log entries and their evidence folder (`drop_removed_reporting` in
`backend/app/core/database.py`).

## Files outside the database

| Where | Holds |
|---|---|
| `backend/models/` | The live model, its information (threshold, inputs, version, training statistics, the list of departments) and the 2,000-employee training sample used for LIME, importance and drift |
| `backend/models/registry/<version>/` | Every trained version: its model files, model card (`card.json`) and results. Released into `backend/models/` and `results/` by HR (not committed) |
| `results/` | The live model's results, and the evaluation scripts' (`docs/EVALUATION_RESULTS.md`) |
| `backend/instance/correction_evidence/` | Documents attached to correction requests, served only through the API, never cached |
| `backend/instance/outbox/` | Emails saved instead of sent when no mail server is set up |
| `backend/instance/secret.key` | The key that signs login tokens (or `APP_SECRET_KEY`) |

`backend/instance/` and `backend/.env` are never committed.
