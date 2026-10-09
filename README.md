# MeritLens

**An explainable promotion-readiness system and an anonymous misconduct-reporting system, in one web
application.**

A final-year project. The platform supports two HR processes that both depend on trust:

1. **Explainable promotion prediction.** A machine-learning model estimates how ready each employee is for
   promotion and explains every score in plain language: what raised it, what lowered it, and what would help.
   The model only advises. A manager recommends, with stated reasons, HR decides, and Finance signs off the pay
   rise.
2. **Anonymous misconduct reporting.** Members of the organisation report workplace concerns without revealing
   who they are. Identifying details are removed from the text and from attached photos and videos. A language
   model suggests how urgent each report is, and the reporter follows up through a two-way conversation using
   only a case ID and secret key.

The two parts are deliberately kept apart: **no report data is ever used by the promotion model.**

> All employee data is **synthetic** (100,000 made-up employees). No real person's data was used to build or
> evaluate the system.

---

## Contents

1. [What the system does](#1-what-the-system-does)
2. [Architecture and technologies](#2-architecture-and-technologies)
3. [Part 1: Explainable promotion prediction](#3-part-1-explainable-promotion-prediction)
4. [Part 2: Anonymous reporting](#4-part-2-anonymous-reporting)
5. [Privacy, security and ethics by design](#5-privacy-security-and-ethics-by-design)
6. [Evaluation and testing](#6-evaluation-and-testing)
7. [Getting started](#7-getting-started)
8. [Reproducing the results](#8-reproducing-the-results)
9. [Project layout](#9-project-layout)
10. [Limitations and future work](#10-limitations-and-future-work)
11. [Further documentation](#11-further-documentation)

---

## 1. What the system does

### Five roles

| Role | What they can do |
|---|---|
| **Employee** | See their own readiness score, its explanation and tips to improve; try "what-if" changes; see an approved promotion; report a concern anonymously, attach evidence, and follow it up |
| **Manager** | Everything an employee can do for themselves, plus see their team's readiness and recommend team members for promotion with structured reasons and a proposed pay rise |
| **HR** | See all employees; review recommendations alongside the model's view and decide; set the pay-rise policy; keep the decision log; add or import employees; handle anonymous reports (inbox, triage, evidence, conversation, outcome) |
| **Finance** | Sign off the pay rise of each approved promotion, or send it back to HR with a reason; see pay rises signed off this year by department |
| **Admin** | Create, edit, deactivate and delete accounts; assign managers' teams; grant admins read-only access to employee data; view the activity log, email outbox and demo requests |

Administration accounts (admin, HR, finance) and employee accounts (employee, manager) are managed separately. Every role
check is enforced by the backend, not just hidden in the interface.

### Main features

- **Readiness score with explanations**: exact per-input contributions, a second-opinion explanation (LIME), a
  plain-language summary, "what-if" exploration, and realistic tips to reach the threshold.
- **Human-in-the-loop decisions**: structured manager recommendations (four criteria rated 1–5 with real
  examples, a proposed title, start date and pay rise), a written reason required when a manager disagrees with
  the model, and HR's final decision recorded with the model's view at that moment.
- **Pay rises kept separate and bounded**: a percentage within an HR-set policy range (default 5–15%); going
  outside it requires a written reason. Salaries are never stored.
- **Finance sign-off**: an approved promotion's pay rise waits for Finance, who signs it off or sends it back
  to HR with a reason. Nobody is told about the promotion until it is signed off, and every step is kept.
- **Anonymous reports**: 19 categories in four groups; automatic removal of names, emails, phone numbers and
  dates, which the reporter reviews before sending; warnings about phrases that could identify them; a case ID
  and secret key for follow-up.
- **Language-model triage**: a text classifier suggests high, moderate or low priority, with safety rules that can
  raise but never lower it, and shows HR why.
- **Photo and video evidence**: hidden details (location, device, owner, time) are removed before anything is
  saved.
- **Notifications and email**: welcome, security, nomination, decision and team emails, and report alerts that
  reveal only the case ID, category and priority. Reporters are never emailed.
- **Accounts**: profiles with photos, permissions, an activity log (dates only), and a public website with a
  "Book a demo" form.

---

## 2. Architecture and technologies

```
 Browser (React single-page app)
        │  JSON over HTTP, signed login token (JWT)
        ▼
 FastAPI backend ──────────────────────────────────────────────┐
   ├─ accounts/   sign-in, roles, profiles, admin              │
   ├─ promotion/  model, explanations, recommendations, pay    │  SQLite database
   ├─ reporting/  anonymiser, keys, triage model, evidence ────┤  (separate tables for reports,
   ├─ demo/       public "Book a demo" requests                │   never read by promotion code)
   └─ core/       settings, security, email, activity log      │
        │                                                      │
        ├─ models/model.joblib  (trained promotion model)      │
        ├─ instance/evidence/   (cleaned photos and videos) ───┘
        └─ Gmail SMTP, or an outbox folder when no mail server is set
```

| Layer | Technologies |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, SQLite, PyJWT |
| Machine learning | scikit-learn (logistic regression, TF-IDF text classifier), XGBoost, LIME, pandas, NumPy, Matplotlib |
| Evidence cleaning | Pillow (photos), ffmpeg via imageio-ffmpeg (videos) |
| Frontend | React 19, React Router 7, Vite 7, lucide-react icons |
| Testing | pytest (269 tests), headless-browser checks of every page |

---

## 3. Part 1: Explainable promotion prediction

### Data and inputs

- **Dataset:** `backend/data/employee_promotion_dataset_100000.csv` holds 100,000 synthetic employees with 43
  columns. 10% were promoted.
- **Inputs:** the model uses **21 performance and development inputs** only:
  - **Performance:** performance score and its change since last year, manager rating, peer feedback, KPI
    achievement, projects, tasks, deadline adherence, innovation, leadership, problem solving, skill assessment.
  - **Development:** training hours, certifications, cross-department projects, mentoring.
  - **Reliability:** attendance, late days.
  - **Career stage:** years since last promotion, years in current role.
  - **Department.**
- **Deliberately excluded, each with a written reason in `features.py`:**
  - protected characteristics (gender, age, education, marital status), which are kept aside only for the
    fairness check;
  - pay, which could carry old pay gaps forward;
  - attitude surveys;
  - working hours, which would reward long hours over results;
  - location and contract details.

### Method

1. **Split.** The data is split 70% / 10% / 20% into training, validation and test sets (stratified, fixed seed).
2. **Candidates.** Three models are trained: logistic regression, random forest and XGBoost.
3. **Choice.** The model with the best **validation PR-AUC** is chosen, which suits a 10% positive class.
   Logistic regression won, and it is also the easiest to explain exactly.
4. **Threshold.** The decision threshold is set to the best F1 on the validation set: **0.789** (shown as 79%).
5. **Test.** The model is tested **once** on the untouched test set.
6. **Fairness.** A **four-fifths rule** check is run. Only a model that passes becomes the live model.

| Model (validation) | PR-AUC | ROC-AUC |
|---|---|---|
| **Logistic regression (chosen)** | **0.632** | **0.926** |
| XGBoost | 0.626 | 0.922 |
| Random forest | 0.613 | 0.922 |

### Results on the test set (20,000 employees, measured once)

| Metric | Value |
|---|---|
| ROC-AUC | 0.930 |
| PR-AUC | 0.633 (random guessing: 0.10) |
| Precision | 54.2% |
| Recall | 65.5% |
| F1 | 0.593 |
| Accuracy | 91.0% |
| Share recommended | 12.1% |

Confusion matrix: 1,310 true positives, 1,108 false positives, 690 false negatives, 16,892 true negatives.
Curves are in `results/roc_curve.png` and `results/pr_curve.png`.

### Fairness: four-fifths rule (selection rate of each group ÷ highest group's)

| Characteristic | Ratio | Result |
|---|---|---|
| Gender | 0.97 | Passes |
| Age group (under 40 / 40+) | 0.98 | Passes |
| Education | 0.93 | Passes |

### Explanations

| Explanation | How it works |
|---|---|
| **Exact contributions** | For logistic regression, each input's term in the log-odds is exactly its SHAP value, so contributions add up precisely to the score (checked by a test for every demo employee). |
| **LIME (second opinion)** | 2,000 perturbed copies of the record train a local surrogate model. Its fit (R²) is shown, with a caution below 0.5. The median fit was 0.21, so LIME is presented as secondary. |
| **Plain-language summary** | The score versus the threshold, plus the two strongest factors each way, in everyday words and units. |
| **What-if** | The user changes only *improvable* inputs, within realistic ranges, and sees the new score. Nothing is saved. |
| **Tips** | The smallest realistic improvements (at most one standard deviation, never beyond the top 5%) that reach the threshold. They reach it for 82 of the 107 demo employees not yet recommended. |
| **Overall importance** | Each input's average share of the model's effect: performance change 39.5%, department 26.3%, leadership 5.6%… |

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

## 4. Part 2: Anonymous reporting

### What "anonymous" means here

Reporters must be signed in, so only members of the organisation can report. But the account is used for
nothing else: a report has **no user column**. The table below shows what is stored and what is deliberately
left out.

| Stored | Never stored |
|---|---|
| The anonymised text the reporter approved | The reporter's account, name or employee record |
| Category, day received, priority, status, outcome | The original text, exact times, IP address, browser details |
| A hash of the secret key | The key itself |
| Cleaned evidence files under random names | Original file names and photo/video metadata |

Report tables are stored without SQLite's hidden row numbers, so the order of insertion can't be matched against
who was signed in.

### Reporting step by step

1. **Write.** Choose a category and describe what happened, optionally attaching photos and videos.
2. **Check.** The anonymiser replaces names (from the directory), emails, phone numbers and dates with tags such
   as `[PERSON 1]`. It flags phrases that could identify the reporter ("I'm the only woman in my team"). The
   reporter reviews and may edit the text. Edited text is checked again on the server.
3. **Keep the key.** A case ID and secret key are shown **once**. They can be saved on the device, downloaded,
   kept in a password manager, or copied. Five wrong keys lock a case for 15 minutes.
4. **Follow up.** A two-way conversation in which the reporter appears only as "Reporter" and HR as
   "Investigator". Replies are anonymised the same way.

### Language-model triage

- **The model.** A TF-IDF (words, word pairs and word pieces) + logistic-regression classifier, trained on about
  280 labelled example reports that are separate from the evaluation sets. It suggests **high**, **moderate**
  or **low**. Its settings were chosen by 5-fold cross-validation on the training examples only.
- **Safety rules** can raise its suggestion, never lower it:
  - words that clearly suggest danger or self-harm mean at least high;
  - category minimums apply (for example, safety, violence and risk of self-harm are always high).
- **Explanation for HR:**
  - the model's chance for each priority;
  - the words that drove it (found by removing each word in turn);
  - any rule that raised it.

  HR always sets the final priority.

### Evidence: photos and videos

| Type | How it is cleaned |
|---|---|
| **Photos** (JPEG, PNG, WebP, up to 15 MB) | Rebuilt from their pixels alone, so no EXIF, GPS, XMP or comments can survive. Orientation is preserved. |
| **Videos** (MP4, MOV, WebM, up to 100 MB) | Re-packed by ffmpeg keeping only the picture and sound. All metadata and extra tracks (such as camera GPS tracks) are dropped. The reporter can also remove the sound. |

- **Checks on upload:** files are identified by their contents, not their names, and each case can hold up to 6
  files.
- **Who can see them:** only the reporter (with the key) and HR, never from a public folder.
- **Removing them:** the reporter can remove their own files; HR cannot delete evidence.
- **What isn't removed:** what is visible or audible (faces, reflections, voices). The reporter is warned about
  this before uploading.

### Results (developer evaluation set, 50 hand-labelled reports)

| Measure | Result |
|---|---|
| Anonymiser: identifying details removed (recall) | 87% (41 of 47) |
| Anonymiser: replacements that were identifying (precision) | 87% |
| Identifying-phrase warnings (recall / precision) | 91% / 91% |
| Triage accuracy (language model + safety rules) | 66% |
| Urgent reports placed too low | **5** (keyword-only method: 12) |
| High-priority reports caught | 14 of 14 |
| False alarms (placed too high) | 12 (keyword-only method: 1) |

**What this shows:**
- The language model **halves the costly mistake**: urgent reports placed too low fell from 12 to 5.
- The trade-off is more false alarms, because the model was trained on few examples. HR's review absorbs these.
- The developer wrote both the system and this test set, so the results are likely flattered. An external set
  written by others is prepared for a fairer test. Full method and discussion: `docs/EVALUATION.md`.

---

## 5. Privacy, security and ethics by design

- **The model advises and people decide.** Readiness is never an automatic decision. Disagreements between
  managers and the model must be explained in writing and are recorded.
- **Data minimisation:**
  - protected characteristics are not model inputs;
  - pay is recorded only as percentages;
  - reports store no identity;
  - logs record dates, not times.
- **Separation:** promotion code never reads report tables. A test checks this.
- **Separation of duties:** HR decides on a promotion and Finance confirms its cost; neither can do the other's
  part, and Finance sees no model scores or performance ratings.
- **No leaks through side channels:**
  - HR alerts contain no report text;
  - reporters are never emailed;
  - identical error messages and timing hide whether a case ID exists;
  - evidence metadata and file names are removed.
- **Security:**
  - salted PBKDF2-SHA256 password hashing and signed, expiring login tokens;
  - role checks on every request;
  - lock-out after wrong keys;
  - rate limits and a honeypot on the public form;
  - secrets kept in an uncommitted `.env` file.
- **Honesty about limits:** the interface explains what is and isn't removed, LIME's fit is shown, and triage is
  presented as a suggestion with its reasons.

---

## 6. Evaluation and testing

| Evaluation | Where | Status |
|---|---|---|
| Promotion model: test-set metrics, curves, model comparison | `results/metrics.json`, `results/*.png`, `results/model_comparison.json` | Done |
| Fairness (four-fifths rule) | `results/fairness.json` | Done, passes |
| Anonymiser, warnings and triage on labelled reports | `results/reporting_evaluation.md`, `docs/EVALUATION.md` | Developer set done; external set ready to collect |
| Triage model selection (cross-validation on training data only) | `python -m evaluation.choose_priority_model` | Done |
| Usability (tasks + System Usability Scale) | `docs/USER_TEST.md`, `python -m evaluation.user_test` | Kit ready; to run with participants |
| Automated tests | `backend/tests/`, 269 tests | All passing (Windows and WSL) |

The automated tests cover:
- roles and permissions, and the model with its fairness gate;
- the exactness of explanations;
- recommendations, decisions and the pay policy;
- Finance sign-off: nobody is told before it, sending back and resubmitting, the audit trail, and what Finance may see;
- anonymisation, keys and lock-out;
- the separation of reports from promotion;
- triage, including the model's separation from the evaluation sets;
- evidence cleaning, checked byte by byte for GPS, owner and device data;
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
python train.py                                  # trains, compares, tests once, fairness-checks; writes results/
python -m evaluation.choose_priority_model       # cross-validates the triage model's settings (training data only)
python -m evaluation.evaluate_reporting          # anonymiser, warnings and triage → results/reporting_evaluation.md
python -m evaluation.user_test                   # scores the usability test once answers are entered
python -m pytest                                 # the 269 automated tests
```

In WSL: `wsl --cd backend -- ~/venvs/hr-simple/bin/python -m pytest`.

The data split and all models use fixed random seeds, so the results are the same on every run.

---

## 9. Project layout

```
backend/
  app/
    main.py              starts the API and connects the parts
    core/                settings, database, security, roles, emails, activity log
    accounts/            users, sign-in, profiles, permissions, admin
    promotion/           features, training helpers, fairness, explanations, recommendations, pay, records
    reporting/           anonymiser, keys, triage model and its training examples, evidence, conversation
    demo/                public "Book a demo" requests
  train.py               trains, tests and fairness-checks the promotion model
  evaluation/            reporting evaluation, triage model selection, labelled report sets, user-test scoring
  data/                  the synthetic employee dataset (100,000 rows)
  models/                the live promotion model (created by train.py)
  tests/                 269 automated tests
  instance/              database, secret key, outbox, evidence (created automatically, never committed)
frontend/src/
  pages/                 one file per page (promotion/, reporting/, admin/, public/)
  components/            shared parts: layout, explanation widgets, evidence, conversation
  styles.css             the design system (navy and teal, light and dark)
results/                 metrics, fairness, curves and reporting evaluation for the thesis
docs/                    how it works, evaluation, limitations, user test
run.py                   starts everything
```

---

## 10. Limitations and future work

Main limitations (full list: `docs/LIMITATIONS.md`):

- **Synthetic data.** Real use would need retraining on an organisation's own promotion history, with consent.
- **Developer-written test sets.** The reporting evaluation is likely flattered. An external set written by
  others is prepared but not yet collected.
- **Triage trades false alarms for safety.** It was trained on about 280 examples by one author.
- **Rule-based anonymiser.** It misses nicknames, people outside the directory and names written in lower case.
  The reporter's review is the main safeguard.
- **Evidence cleaning can't remove what is seen or heard.** Faces are not blurred automatically.
- **Signing in is required to report**, a deliberate change from the original brief. Trust in anonymity also
  depends on who runs the server.
- **Prototype infrastructure.** It uses SQLite on a single server, with no HTTPS set-up and no backups.

Future work:
1. Collect the external evaluation set.
2. Run the user test.
3. Train triage on more varied examples.
4. Add named-entity recognition for names.
5. Blur faces automatically.
6. Extend fairness checks to department and combinations of characteristics.

---

## 11. Further documentation

| Document | Contents |
|---|---|
| [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md) | Plain-English explanation of every part, step by step, with design decisions and API endpoints |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | How the reporting evaluation works, labelling rules, results and discussion |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | Limitations of the model, reporting, system and evaluation; future work |
| [`docs/USER_TEST.md`](docs/USER_TEST.md) | Usability test kit: consent note, tasks, SUS questionnaire, scoring |
| [`results/reporting_evaluation.md`](results/reporting_evaluation.md) | Generated reporting results, including every mistake |
