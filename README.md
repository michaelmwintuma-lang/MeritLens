# MeritLens

**Fair, explainable promotion decisions, with a voice for every employee.**

A final-year project: *Design and Development of an Explainable Machine Learning-Based Decision Support System for
Employee Promotion Prediction with an Employee Feedback Channel.* It follows one cycle:

1. **Predict.** A fairness-checked model estimates how ready each employee is for promotion, from performance and
   development records only: never gender, age, education, department or pay. A model that treats groups unfairly
   (four-fifths rule) is never used.
2. **Explain.** Every score is explained in plain words: what raised it, what lowered it compared with an average
   employee, and the smallest realistic improvements that would reach the threshold. The exact numbers and an
   independent second opinion (LIME) are under "Show technical details".
3. **Respond.** Employees can answer back:
   - rate the explanation, and mark factors that seem wrong or unfair;
   - ask HR to correct a wrong record, with evidence.

**People make every decision, and a complaint never changes a score.** Ratings never reach the model:
a static check, a run-time check and an end-to-end isolation test prove it. Only a record correction that HR
confirms against evidence changes a record; the employee is then re-scored and the change is logged. A manager
recommends, HR decides (going against the model needs a written reason), and Finance signs off the pay rise.

> All employee data is **synthetic**: 100,000 simulated employees from the *Employee Promtion Prediction Dataset* by
> Rohit Kumar on Kaggle (CC0), <https://www.kaggle.com/datasets/rohit8527kmr7518/employee-promtion-prediction>. No real person's data was used to build or
> evaluate the system.

---

## Contents

1. [What the system does](#1-what-the-system-does)
2. [Architecture and technologies](#2-architecture-and-technologies)
3. [Predict and explain](#3-predict-and-explain)
4. [Respond: the employee feedback channel](#4-respond-the-employee-feedback-channel)
5. [Privacy, security and ethics by design](#5-privacy-security-and-ethics-by-design)
6. [Evaluation and testing](#6-evaluation-and-testing)
7. [Getting started](#7-getting-started)
8. [Reproducing the results](#8-reproducing-the-results)
9. [Project layout](#9-project-layout)
10. [Limitations and future work](#10-limitations-and-future-work)
11. [Further documentation](#11-further-documentation)

---

## 1. What the system does

### Six roles

| Role | What they can do |
|---|---|
| **Employee** | On "My growth": see their readiness score, why, and their path to promotion; try "what-if" changes; rate the explanation, or ask HR to correct their record; see an approved promotion |
| **Manager** | Everything an employee can do for themselves, plus see their team's readiness and recommend team members for promotion with structured reasons and a proposed pay rise |
| **HR** | See all employees; review recommendations alongside the model's view (with a committee note, and a hold, while a correction is pending) and decide; confirm or reject record corrections; see the feedback dashboard; set the pay-rise policy; keep the decision log; add or import employees |
| **Finance** | Sign off the pay rise of each approved promotion, or send it back to HR with a reason; see pay rises signed off this year by department |
| **Admin** | Create, edit, deactivate and delete accounts; assign managers' teams; grant admins read-only access to employee data; see system health (model, fairness gate, drift, email) and the activity log, email outbox and demo requests |
| **Compliance auditor** | Read-only: the decision log, the model and its fairness, record histories and the feedback dashboard (totals only); never individual records or feedback |

Administration accounts (admin, HR, finance, auditor) and employee accounts (employee, manager) are managed
separately. Every role
check is enforced by the backend, not just hidden in the interface.

### Main features

- **Readiness score with explanations**: a plain-language summary, what raised and lowered the score, the path to
  promotion (realistic tips), "what-if" exploration, and, under "Show technical details", the exact contributions
  and a second opinion (LIME).
- **Employee feedback channel**: rate the explanation, or request a record correction with evidence; HR's
  correction queue; a committee note on nominations, with a hold while a correction is pending; a feedback
  dashboard with small-group protection.
- **Human-in-the-loop decisions**: structured manager recommendations (four criteria rated 1–5 with real
  examples, a proposed title, start date and pay rise), a written reason required when a manager disagrees with
  the model, and HR's final decision recorded with the model's view at that moment.
- **Pay rises kept separate and bounded**: a percentage within an HR-set policy range (default 5–15%); going
  outside it requires a written reason. Salaries are never stored.
- **Finance sign-off**: an approved promotion's pay rise waits for Finance, who signs it off or sends it back
  to HR with a reason. Nobody is told about the promotion until it is signed off, and every step is kept.
- **Notifications and email**: welcome, security, nomination, decision, correction and team emails, and a
  notification bell for what needs attention.
- **Accounts and oversight**: profiles with photos, permissions, sign-in lock-out after 5 wrong passwords, an
  activity log (dates only), an admin dashboard with system health and drift, and a public landing page.

---

## 2. Architecture and technologies

```
            ┌──────────────── OFFLINE: the model's life cycle ─────────────────┐
 HR export ─► data mapping ─► train.py: compare, common-sense ─► model registry ─► HR reads the
 (CSV)        (data/mappings)  check, threshold, fairness gate    (version + model   model card and
                                                                   card; blocked if   releases it
                                                                   unfair)            (or rolls back)
            └──────────────────────────────────────────────────────────┬──────┘
                                                                       │ released version only
 Browser (React app; API layer in TypeScript, typed from openapi.json) ▼
        │  JSON over HTTP; sign-in in an httpOnly, SameSite=Strict session cookie
        ▼
 FastAPI backend (one service, separate modules) ─────────────────────────────┐
   ├─ accounts/    sign-in, roles, profiles, admin                             │
   ├─ promotion/   model, explanations, recommendations, decisions, pay        │  SQLite (default)
   │      ▲ never imports feedback/ or governance/ (checked)                   │  or PostgreSQL
   │      └ reads only the neutral decision_holds table to refuse held decisions│  (promotion code can
   ├─ feedback/    ratings, corrections, dashboard; places and lifts holds ────┤   use its own role with
   ├─ governance/  model registry and release, live fairness, audit-trail API  │   no access to feedback)
   ├─ core/        settings, security, email, activity log, holds,             │
   │               audit trail (append-only, hash-chained), background jobs    │
   ├─ public/      landing-page facts from results/                            │
   └─ demo/        public "Book a demo" requests                               │
        │  background worker: LIME second opinions, kept per model version + record
        ├─ models/  the live model; models/registry/ every version with its card
        └─ Gmail SMTP, or an outbox folder when no mail server is set
```

| Layer | Technologies |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, SQLite (default) or PostgreSQL, PyJWT |
| Machine learning | InterpretML (monotonic Explainable Boosting Machine), scikit-learn (logistic regression, random forest), XGBoost, LIME, pandas, NumPy, Matplotlib |
| Frontend | React 19, React Router 7, Vite 7, TypeScript (API layer, generated from the backend's OpenAPI contract), lucide-react icons |
| Testing | pytest (322 tests), headless-Chrome checks and axe-core accessibility audits, GitHub Actions CI |

**Why it is built this way.** One backend with clearly separated modules is right for one organisation's HR
team: simpler to run, test and reason about than many services. The redesign keeps that, and adds what a
professional deployment needs: a model goes live only through a named person (registry and release), every
decision is in a tamper-evident trail, fairness is checked on live decisions too, slow work runs in the
background, sign-in can't be stolen by page scripts, and a held decision is refused by the server, not just
hidden. The database can enforce feedback isolation too (PostgreSQL roles: `deploy/postgres/`).

---

## 3. Predict and explain

### Data and inputs

- **Dataset:** `backend/data/employee_promotion_dataset_100000.csv` holds 100,000 synthetic employees with 43
  columns. 10% were promoted.
- **Inputs:** the model uses **20 performance and development inputs** only:
  - **Performance:** performance score and its change since last year, manager rating, peer feedback, KPI
    achievement, projects, tasks, deadline adherence, innovation, leadership, problem solving, skill assessment.
  - **Development:** training hours, certifications, cross-department projects, mentoring.
  - **Reliability:** attendance, late days.
  - **Career stage:** years since last promotion, years in current role.
- **Deliberately excluded, each with a written reason in `features.py`:**
  - protected characteristics (gender, age, education, marital status), which are kept aside only for the
    fairness check;
  - **department**: past promotion rates ranged from 2% (Support) to 33% (Engineering), so with it two people
    with the same record would score differently only because of where they work;
  - pay, which could carry old pay gaps forward;
  - attitude surveys;
  - working hours, which would reward long hours over results;
  - location and contract details.

### Method

1. **Split.** The data is split 70% / 10% / 20% into training, validation and test sets (stratified, fixed seed).
2. **Candidates.** Four models are trained: a **monotonic Explainable Boosting Machine (EBM)**, logistic
   regression, random forest and XGBoost.
3. **Common-sense check.** On the validation set, each input a person can improve (and the change in
   performance) is moved half a standard deviation in its improving direction for 2,000 employees. A model is
   eligible only if no score ever drops.
4. **Choice.** Among eligible models, the easiest to explain whose **validation PR-AUC** is within 0.01 of the
   best. Only the EBM was eligible: its monotonic constraints rule such drops out.
5. **Threshold.** The decision threshold is set to the best F1 on the validation set: **0.2283** (shown as 23%).
6. **Test.** The model is tested **once** on the untouched test set.
7. **Fairness.** A **four-fifths rule** check is run. Only a model that passes becomes the live model.

| Model (validation) | PR-AUC | ROC-AUC | Scores that dropped when an input improved |
|---|---|---|---|
| **EBM, monotonic (chosen)** | **0.4671** | **0.8806** | **0%** |
| XGBoost | 0.4699 | 0.8777 | 21.9% |
| Logistic regression | 0.4618 | 0.8793 | 16.7% (more peer feedback, problem solving or training always lowered the score) |
| Random forest | 0.4528 | 0.8769 | 30.1% |

### Results on the test set (20,000 employees, measured once)

| Metric | Value |
|---|---|
| ROC-AUC | 0.883 |
| PR-AUC | 0.474 (random guessing: 0.10) |
| Precision | 41.0% |
| Recall | 59.5% |
| F1 | 0.486 |
| Accuracy | 87.4% |
| Share recommended | 14.5% |

Confusion matrix: 1,190 true positives, 1,711 false positives, 810 false negatives, 16,289 true negatives.
Curves are in `results/roc_curve.png` and `results/pr_curve.png`.

**Why these are lower than the earlier logistic regression (PR-AUC 0.633):** most of that model's accuracy came
from department. Past promotions favoured some departments strongly, so a model that knows the department
predicts *past decisions* better, by repeating that pattern. Leaving department out is the fairer choice,
and the numbers above are what it costs.

### Fairness: four-fifths rule (selection rate of each group ÷ highest group's)

| Characteristic | Ratio | Result |
|---|---|---|
| Gender | 0.982 | Passes |
| Age group (under 40 / 40+) | 0.963 | Passes |
| Education | 0.887 | Passes |

### Explanations

| Explanation | How it works |
|---|---|
| **Exact contributions** | The EBM adds up one learned curve per input. Each input's contribution is its term for this employee minus its average term, so contributions add up precisely to the score (checked by a test for every demo employee). For an additive model this equals its SHAP value. |
| **LIME (second opinion)** | 2,000 perturbed copies of the record train a local surrogate model. Its fit (R²) is shown, with a caution below 0.5. On the 120 demo employees the median fit was 0.13 (84% below 0.5), so LIME is presented as secondary. |
| **Plain-language summary** | The score versus the threshold, plus the two strongest factors each way, in everyday words and units. |
| **What-if** | The user changes only *improvable* inputs, within realistic ranges, and sees the new score. Nothing is saved. |
| **Tips** | The smallest realistic improvements (at most one standard deviation, never beyond the top 5%) that reach the threshold, each tried on the model itself. They reach it for 98 of the 108 demo employees not yet recommended. |
| **Overall importance** | Each input's average share of the model's effect: change in performance 51.5%, projects 10.7%, tasks 6.9%, performance score 4.7%, leadership 4.5%… |

### From score to decision

1. **The model advises:** it gives a readiness score and its explanation.
2. **A manager recommends**, using a structured form:
   - performance, leadership, skills and impact are each rated 1–5 with a concrete example;
   - a proposed title, start date and pay rise;
   - a written reason (at least 20 characters) is required if the model does not recommend the person.
3. **HR decides:** approve or reject, setting the final pay rise within policy (or outside it, with a written
   reason). Each decision is stored with the model's view at that moment, so the **decision log** shows
   where people and the model disagreed.
4. **Finance signs off the pay rise.** Until then the promotion isn't final: the manager sees "Being
   finalised", and the employee sees nothing. Finance can instead send the rise back to HR with a reason (at
   least 20 characters); HR revises it and resubmits. Only after sign-off are the manager and employee told.
   Every step (sent, sent back, resubmitted, signed off), with who, when and the percentage, is kept as an
   audit trail. Finance sees only what a pay decision needs, not the model's score or the reasons for the
   promotion. A rejection is final at once and never goes to Finance.

---

## 4. Respond: the employee feedback channel

On their own "My growth" page, below the explanation, an employee finds **Respond to this explanation** with two
routes. Neither changes a score.

| Route | What happens |
|---|---|
| **Rate this explanation** | "This explanation was clear" and "This explanation was useful" (1–5), optional "seems wrong" / "seems unfair" marks per factor, and a comment. Stored with the model version and the score explained. HR and the auditor see only totals (rates from 5 ratings up); managers never see them. |
| **Correct my record** | Pick a value from your own record, the value you believe is right, and evidence (a note, and optionally a PDF, JPEG or PNG). HR confirms with the verified value, or rejects with a reason you receive. Confirming corrects only that value, re-scores you, and logs who, old and new value, reason, readiness before and after, and the model version. You are told by email and in the notification bell. |

- **Committee note:** while a correction is pending for a nominee, HR's review says so and HR can hold the decision
  until it's resolved. A hold is not a decision and never counts as an override. While it holds, the server
  refuses a decision; it lifts by itself when the correction is decided, or HR can take it off hold.
- **Feedback dashboard** (HR and auditor):
  - clarity and usefulness rates;
  - contest share per factor;
  - correction requests (received, confirmed, rejected, pending; confirmation rate; time to decide);
  - the committee's override rate, with reasons.

  It has filters for dates, department (groups of 5 or more) and model version, and a CSV export. Small counts show
  as "<3".
- **Isolation, proven:**
  - `tests/test_isolation.py` records every prediction answer, adds ratings, corrections and a held decision, and
    checks every answer is byte-for-byte identical;
  - then a confirmed correction must change the prediction and be logged;
  - a static check forbids the promotion code from importing or naming the feedback code, or the
    equality-monitoring data;
  - a run-time check records the SQL the prediction endpoints run;
  - with PostgreSQL, the promotion code's database role has no access to those tables at all.

### Governance: model releases, the audit trail and live fairness

| Feature | Who | What it does |
|---|---|---|
| **Model registry** | HR releases; admin and auditor read | `train.py` registers each trained model as a *candidate* with a **model card** (data and mapping, method, test results, fairness, intended use, limitations). It goes live only when an HR person reads the card and releases it with a written note; the app switches without a restart. A model that failed the fairness check is *blocked* and can never be released. Releasing an older version rolls back. |
| **Audit trail** | Auditor and admin, read-only | Every nomination, decision (with the model's score, threshold, version and top factors at that moment), pay step, record change, correction, hold and model release. Append-only and **hash-chained**: "Check the chain" proves nothing was changed or deleted. Never copies what an employee wrote. |
| **Live fairness** | HR, admin, auditor | The four-fifths rule on today's directory and decisions, at three stages: what the **model** recommends, whom **managers** nominate, whom **HR** approves. Shows where a gap appears. Uses equality-monitoring data kept apart from the directory, never given to the model; groups under 5 are never shown. |

A confidential route for reporting an unfair assessment was built in an earlier version and removed to keep the
scope focused. It is future work: see `docs/future-work/` and the git tag `with-anonymous-reporting`.

---

## 5. Privacy, security and ethics by design

- **The model advises and people decide.** Readiness is never an automatic decision. Disagreements between
  managers and the model must be explained in writing and are recorded.
- **Data minimisation:**
  - protected characteristics are not model inputs. Gender, an age band (not an age) and education are kept in a
    separate equality-monitoring table, used only for live fairness totals;
  - pay is recorded only as percentages;
  - the activity log records dates, not times (the audit trail keeps times for decisions, not for sign-ins).
- **Separation:** promotion code never reads feedback or equality-monitoring tables. Static, run-time and
  end-to-end tests check this (`backend/tests/test_isolation.py`); with PostgreSQL, so do database roles.
- **Accountability:** a model goes live only when a named HR person releases it; every decision-relevant event is in
  a hash-chained, append-only audit trail.
- **Separation of duties:** HR decides on a promotion and Finance confirms its cost; neither can do the other's
  part, and Finance sees no model scores or performance ratings.
- **Privacy of feedback:** ratings are seen only as totals, from 5 ratings up, and never by managers; correction
  evidence is stored under random names and shown only to the employee and HR.
- **Security:**
  - salted PBKDF2-SHA256 password hashing (200,000 rounds), and signed, expiring login tokens that stop working
    on a password change, a reset or signing out;
  - the website's sign-in lives in an httpOnly, SameSite=Strict cookie that page scripts can't read, and
    state-changing requests made with it must carry a header another site can't add (cross-site request forgery);
  - lock-out after 5 wrong passwords;
  - role checks on every request;
  - rate limits and a honeypot on the public form;
  - secrets kept in an uncommitted `.env` file.
- **Honesty about limits:** LIME's fit is shown, the score's calibration is measured before it is described as a rate, and
  every number on the website is measured.

---

## 6. Evaluation and testing

| Evaluation | Where | Status |
|---|---|---|
| Promotion model: test-set metrics, curves, model comparison | `results/metrics.json`, `results/*.png`, `results/model_comparison.json` | Done |
| Fairness (four-fifths rule) | `results/fairness.json` | Done, passes |
| Calibration (does a score of 30% mean about 30%?) | `results/calibration.json`, `results/calibration_curve.png` | Done: well calibrated (ECE 0.0056, slope 0.998) |
| Proxies for gender, age, education and department; equal opportunity | `results/proxy_analysis.json` | Done |
| Explanations: exactness, common sense, LIME fit and agreement, tips | `results/explanation_evaluation.json` | Done |
| Feedback channel in use: clarity, contest share, corrections | `python -m evaluation.export_feedback_measures` | Script ready; numbers come from use |
| Usability and perceived fairness (11 tasks, SUS, Colquitt-based items) | `docs/USER_TEST.md`, `python -m evaluation.user_test` | Kit ready; to run with participants |
| Automated tests | `backend/tests/`, 322 tests | All passing |
| Browser checks and accessibility (axe-core, light and dark) | `python scripts/browser_test.py` | 6 checks passing; 0 accessibility findings on 15 pages |
| Continuous integration | `.github/workflows/ci.yml` | Tests, build and browser checks on every push |

Every number, with its source: **`docs/EVALUATION_RESULTS.md`**.

The automated tests cover:
- roles and permissions, and the model with its fairness gate;
- the exactness of explanations;
- recommendations, decisions and the pay policy;
- Finance sign-off: nobody is told before it, sending back and resubmitting, the audit trail, and what Finance may see;
- the feedback channel, and the separation of feedback from promotion;
- dashboards with small-group protection, and system health with drift;
- emails, accounts, profiles and the activity log.

`docs/HOW_IT_WORKS.md` lists what each test file proves.

---

## 7. Getting started

### Requirements

- Python 3.11
- Node.js 20 or newer

### Install (once)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt     # macOS/Linux: .venv/bin/python -m pip ...
cd ..

# Frontend
cd frontend
npm install
cd ..
```

With [uv](https://docs.astral.sh/uv/): `uv venv backend/.venv --python 3.11`, then
`uv pip install --python backend/.venv/Scripts/python.exe -r backend/requirements.txt`.

### Run

```bash
python run.py
```

Open **http://127.0.0.1:5173**. This starts the API (port 8000) and the website (port 5173) together; press
Ctrl+C to stop both. The database is created on first start in `backend/instance/app.db`, with 120 demo
employees drawn from the synthetic dataset.

### Demo accounts (fictional)

The password for all of them is `demo1234`. Their emails use `example.org`, which can't reach anyone.

| Username | Role |
|---|---|
| `admin` | Admin |
| `hr` | HR |
| `manager` | Manager |
| `employee` | Employee |
| `finance` | Finance |
| `auditor` | Compliance auditor |

To start from scratch, stop the app and delete `backend/instance/app.db`.

### Email (optional)

Without a mail server, every email is saved to `backend/instance/outbox/` and shown on the admin's Email page.
To send real email through Gmail:

1. Turn on 2-Step Verification.
2. Create an **app password** at <https://myaccount.google.com/apppasswords>.
3. Copy `backend/.env.example` to `backend/.env`, then fill in `SMTP_USER` and `SMTP_PASSWORD`.
   **Never commit `.env`.**
4. Restart the app and send a test email from **Administration → Email**.

`DEMO_INBOX` sets where "Book a demo" requests go, and `APP_URL` sets the link used in emails.

### Note for Windows

Windows **Smart App Control** can block compiled parts of pandas and scikit-learn. If that happens:

1. Once, run `wsl bash backend/setup_wsl.sh` to set up the backend in WSL (Ubuntu).
2. Run `python run.py` as usual. It detects the block and runs the backend in WSL automatically, using the same
   code, database and `.env`.

SQLAlchemy is pinned to 2.0 because it falls back to pure Python when its compiled part is blocked.

---

## 8. Reproducing the results

All commands run from the `backend` folder (on Windows, use `.venv\Scripts\python`):

```bash
python train.py                                  # trains, compares, tests once, fairness-checks; registers a candidate
python train.py --mapping data/mappings/X.json   # the same, on another organisation's export (see example_other_organisation.json)
python -m evaluation.calibration                 # calibration of the live model (or a version: ... calibration v2026...)
python -m evaluation.proxy_analysis              # proxies for gender, age, education, department; equal opportunity
python -m evaluation.evaluate_explanations       # exactness, common sense, LIME and tips → results/explanation_evaluation.json
python -m evaluation.export_feedback_measures    # the feedback dashboard's measures → results/feedback_measures.json
python -m evaluation.user_test                   # scores the usability test once answers are entered
python -m pytest                                 # the 322 automated tests, in about 5 minutes
python export_openapi.py                         # the API contract → frontend/openapi.json (then: npm run gen:api)
```

`train.py` never changes the live model: it registers the new version in `backend/models/registry/`, and its
results become `results/` only when HR releases it (Model registry page). The very first model, when none is live,
goes live directly so the app can start.

In WSL: `wsl --cd backend -- ~/venvs/hr-simple/bin/python -m pytest`.

The data split and all models use fixed random seeds, so the results are the same on every run (checked on
2026-10-09: re-running reproduced every committed result).

From the project folder, the browser checks and screenshots run against a throwaway copy of the app, never your
database:

```bash
python scripts/browser_test.py                                        # 6 checks in headless Chrome
python scripts/browser_test.py scripts/ui_capture.js docs/screenshots/latest   # screenshots + accessibility audit
python scripts/browser_test.py scripts/capture_landing.js             # the website's screenshots
```

---

## 9. Project layout

```
backend/
  app/
    main.py              starts the API and connects the parts
    core/                settings, database, security, roles, emails, activity log, audit trail, holds, jobs
    accounts/            users, sign-in, profiles, permissions, admin
    promotion/           features, data mapping, training helpers, fairness, explanations, drift, decisions, pay
    feedback/            ratings, record corrections, committee note, feedback dashboard
    governance/          model registry and release, live fairness (equality monitoring), audit-trail API
    public/              facts for the landing page, read from results/
    demo/                public "Book a demo" requests
  train.py               trains, tests and fairness-checks a model, and registers it with its model card
  export_openapi.py      writes the API contract the frontend's types come from
  evaluation/            explanation evaluation, proxy analysis, feedback export, user test
  data/                  the synthetic employee dataset (100,000 rows); mappings/ for other organisations' data
  models/                the live promotion model; registry/ every trained version (not committed)
  tests/                 322 automated tests
  instance/              database, secret key, outbox, correction evidence (created automatically, never committed)
deploy/postgres/         running on PostgreSQL, with database roles that enforce the isolation
frontend/
  openapi.json           the API contract (from export_openapi.py); src/api-types.ts is generated from it
  src/api.ts, auth.tsx   the typed API layer and sign-in (TypeScript)
  src/pages/             one file per page (promotion/, feedback/, governance/, admin/, finance/, public/)
  src/components/        shared parts: layout, explanation widgets, feedback panels, attention panel, dashboards
  src/styles.css         the design system (Apple-style): white, one blue for actions, teal/orange only for the model's data
results/                 metrics, fairness, curves, proxy analysis and explanation evaluation for the thesis
docs/                    how it works, evaluation results, thesis guide, data model, user test; future-work/
scripts/                 browser checks, screenshots and accessibility audits (headless Chrome, no npm packages)
.github/workflows/       continuous integration
run.py                   starts everything
```

---

## 10. Limitations and future work

Main limitations (full list: `docs/LIMITATIONS.md`):

- **Synthetic data.** Real use would need retraining on an organisation's own promotion history, with consent.
- **Prototype infrastructure.** It runs on SQLite by default, on a single server, with no HTTPS set-up and no
  backups. PostgreSQL is supported (`deploy/postgres/`) but was not tested against a running server here.

- **No real use yet.** The feedback channel's measures, usability and perceived fairness still have to be
  collected in the user study.
- **Fairness costs accuracy.** Leaving department out lowered test PR-AUC from 0.633 to 0.474. That is the price of
  not scoring people by where they work.

Future work:
1. Run the user test, with the feedback-channel tasks and fairness questions.
2. A confidential route for reporting unfair assessments (removed from this version to keep the scope focused;
   see git tag `with-anonymous-reporting` and `docs/future-work/`).
3. Compare tasks and projects completed within each department, so department doesn't come back through them.
4. Extend fairness checks to combinations of characteristics.

---

## 11. Further documentation

| Document | Contents |
|---|---|
| [`docs/THESIS_GUIDE.md`](docs/THESIS_GUIDE.md) | **Start here for the thesis:** aim, objectives, methods, where each result comes from, discussion, figures, references |
| [`docs/EVALUATION_RESULTS.md`](docs/EVALUATION_RESULTS.md) | Every result, with its source file and command |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Every table, what it holds, and who can read and change it |
| [`docs/CHANGELOG_UPGRADE.md`](docs/CHANGELOG_UPGRADE.md) | Every change made in the upgrade, phase by phase |
| [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md) | Plain-English explanation of every part, step by step, with design decisions and API endpoints |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | Limitations of the data, model, feedback channel, system and evaluation; future work |
| [`docs/USER_TEST.md`](docs/USER_TEST.md) | Usability and perceived-fairness study kit: consent note, 11 tasks, SUS, Colquitt-based items, scoring |
| [`docs/screenshots/PHASE7.md`](docs/screenshots/PHASE7.md) | Before and after screenshots of 15 pages, with accessibility audits |
| [`docs/future-work/`](docs/future-work/README.md) | Anonymous reporting, removed from this version: its threat model, evaluation and the original review |
