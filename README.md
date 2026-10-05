# Promotion & Reporting Platform

A final-year project with two separate parts in one web application:

1. **Promotion prediction with explanations.** A machine learning model estimates how ready each employee is
   for promotion and explains why in plain language. HR makes the final decision, not the model.
2. **Anonymous reporting.** Members of the organisation report workplace misconduct. They must be signed in, but
   the report is never linked to their account; they follow up later with a case ID and secret key.

The two parts are kept completely separate: report data is never used by the promotion model.

## Build progress

| Step | What | Status |
|---|---|---|
| 1 | Project setup, database, login and roles | Done |
| 2 | Training script, metrics and fairness check | Done |
| 3 | Prediction and explanation API | Done |
| 4 | Employee, manager and HR promotion pages | Done |
| 5 | Nominations, decisions and decision log | Done |
| 6 | Anonymous report submission, anonymiser and keys | Done |
| 7 | Follow-up conversation and triage | Done |
| 8 | Activity log, tests and documentation | Done |

## Requirements

- Python 3.11
- Node.js 20 or newer

## Installation (once)

```bash
# Backend: a virtual environment with the Python packages
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt      # macOS/Linux: .venv/bin/python -m pip ...
cd ..

# Frontend
cd frontend
npm install
cd ..
```

(With [uv](https://docs.astral.sh/uv/): `uv venv backend/.venv --python 3.11` then
`uv pip install --python backend/.venv/Scripts/python.exe -r backend/requirements.txt`.)

## Running

```bash
python run.py
```

Then open **http://127.0.0.1:5173**. This starts the backend API (port 8000) and the website (port 5173)
together; press Ctrl+C to stop both. After changing backend code, stop it and run it again. The database is created automatically in `backend/instance/app.db`.

## Emails

The platform sends these emails:

| Email | When | To |
|---|---|---|
| Welcome | The admin creates an account | The new person (username and temporary password) |
| Password reset | The admin resets a password | The person |
| Security alert | A password or username changes | The person |
| Nomination received | A manager nominates someone | Every HR account |
| Decision | HR approves or rejects a nomination | The manager, and the employee if approved |
| New report alert | A report arrives | Every HR account: **only** the case ID, category and priority |

Reporters are never emailed about their reports, because that would link them to the report.

### Sending with Gmail

1. Turn on **2-Step Verification** for the Google account that will send the emails.
2. Create an **app password** at <https://myaccount.google.com/apppasswords>.
3. Copy `backend/.env.example` to `backend/.env` and fill in `SMTP_USER` (the Gmail address) and
   `SMTP_PASSWORD` (the 16-letter app password). `backend/.env` is listed in `.gitignore`. Never commit it.
4. Restart the app (`python run.py`).
5. Sign in as the admin, open **Administration → Email**, and send a test email.

Other mail servers work too: set `SMTP_HOST` and `SMTP_PORT` (STARTTLS). `APP_URL` sets the link in the emails
(default `http://127.0.0.1:5173`).

If no mail server is set up, nothing is sent. Each email is saved as a file in `backend/instance/outbox/`, and the
admin can read these on the Email page.

## Demo accounts (fictional)

Created automatically the first time the app starts. Password for all: `demo1234`. Their email addresses are on
`example.org`, a domain reserved for examples, so no real person can receive their emails. To see the emails
arrive, the admin can change these addresses to real ones, for example Gmail aliases such as `you+hr@gmail.com`.

| Username | Role |
|---|---|
| `admin` | Admin |
| `hr` | HR |
| `manager` | Manager |
| `employee` | Employee |

To start again from scratch, stop the app and delete `backend/instance/app.db`.

## The public website and Book a demo

Visitors who aren't signed in see a small website with one page per menu item: Home, Approach, Promotion,
Reporting, Privacy and **Book a demo**. Demo requests are emailed to `DEMO_INBOX` in `backend/.env` (or, if empty,
the Gmail address in `SMTP_USER`); replying to that email answers the visitor. The admin sees them all under
**Administration → Demo requests**.

## Evaluation

- **Promotion model:** `results/metrics.json`, `results/fairness.json` and the curve images, made by `python train.py`.
- **Reporting:** `python -m evaluation.evaluate_reporting` (from `backend`) measures the anonymiser and triage on
  hand-labelled reports and writes `results/reporting_evaluation.md`. Method and findings: `docs/EVALUATION.md`.
- **User test:** a ready-to-run kit (tasks, the System Usability Scale questionnaire, consent note and scoring
  script) in `docs/USER_TEST.md`; `python -m evaluation.user_test` scores the answers.
- **Limitations and future work:** `docs/LIMITATIONS.md`.

## Adding employees

The 120 demo employees come from the synthetic dataset. HR can add real ones on **All employees**: **Add employee**
(a form) or **Import** (a CSV file; download the template on that page). Values are checked; a file with any bad row
is not imported at all. New employees can be scored at once, and the admin links them to a login on the Users page.
See `docs/HOW_IT_WORKS.md`, "Adding real employees", including why real use also means retraining on the
organisation's own promotion history.

## Training the model

```bash
cd backend
.venv\Scripts\python train.py
```

It trains three models, picks one, tests it once, checks fairness and, if it passes, saves
it as the live model (`backend/models/`). Results for the thesis are written to `results/`:

| File | Contents |
|---|---|
| `results/model_comparison.json` | Validation scores of all three models and why one was chosen |
| `results/metrics.json` | Final test-set results: accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix |
| `results/fairness.json` | Four-fifths rule check for gender, age group and education |
| `results/roc_curve.png`, `results/pr_curve.png` | Curves of the final model on the test set |

## Tests

```bash
cd backend
.venv\Scripts\python -m pytest
```

128 tests, covering roles, the model and its fairness check, the explanations, nominations and decisions,
anonymous reporting (including the isolation from the promotion model), the conversation, accounts and
notifications, and the activity log. `docs/HOW_IT_WORKS.md` (step 8) lists what each file proves.

## Project layout

```
backend/
  app/
    main.py            starts the API and connects the parts
    core/              shared basics: settings, database, passwords and login tokens, roles, activity log, emails
    accounts/          users table, sign-in, account management by the admin, who HR is (for emails)
    promotion/         the promotion model: features, training, fairness, explanations, nominations, API
    reporting/         anonymous reports: anonymiser, case IDs and keys, API (kept separate from promotion)
  train.py             trains, tests and fairness-checks the model
  data/                the employee dataset (100,000 synthetic employees)
  models/              the live model (created by train.py)
  tests/               automated tests (pytest)
  instance/            local database and secret key (created automatically, never committed)
frontend/
  src/
    api.js, auth.jsx   talking to the backend, remembering who is signed in
    roles.js           role names and each role's menu
    pages/             one file per page (promotion/ holds the readiness, team and model pages)
    components/        reusable parts (promotion/ holds the score bar, contributions, LIME, what-if, tips)
results/               metrics, fairness results and curve images for the thesis
run.py                 starts everything
docs/HOW_IT_WORKS.md   plain-English explanation of every part
```

## Note for Windows

Windows "Smart App Control" blocks some compiled Python packages. SQLAlchemy is pinned to version 2.0, which
falls back to plain Python when its compiled part is blocked (version 2.1 has no fallback).

Smart App Control can also start blocking parts of pandas and scikit-learn without warning (it happened on
5 October 2026 to files that had loaded fine the day before). If that happens, run the backend in **WSL**
(Ubuntu), where Smart App Control doesn't apply:

1. Once, set up the backend's environment in WSL: `wsl bash backend/setup_wsl.sh`
2. Run `python run.py` as usual. It notices the block and starts the backend in WSL by itself, using the same
   code, database and `.env`. The frontend stays on Windows.

Run the tests there with `wsl --cd backend -- ~/venvs/hr-simple/bin/python -m pytest`.
