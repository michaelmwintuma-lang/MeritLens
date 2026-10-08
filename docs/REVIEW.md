# Review before the upgrade (Phase 1)

Reviewed on 2026-10-08: every backend module, the main frontend pages, the tests, the docs, and the running app
(`python run.py`: API on :8000, web on http://127.0.0.1:5173).

**Tests at the time of review:** `cd backend && .venv\Scripts\python -m pytest` → **277 passed**. That is the 269 of
the original suite plus 8 added with the model change described in section 0.

**Severity:** **High** breaks the thesis's rules or a feature, or puts people at real risk. **Medium** is wrong or
misleading behaviour, or a risk that needs a determined insider. **Low** is polish.

## How the upgrade plan maps onto this project

The upgrade plan was written for the Firebase version of the project. This project does the same jobs with
different parts:

| The plan says | In this project |
|---|---|
| `npm run test:backend`, `npm run test:e2e` | `pytest` in `backend/`. The API tests call every endpoint through FastAPI's test client, so they are the end-to-end tests. There are no browser tests. |
| `npm run dev:all` | `python run.py` |
| Cloud Functions with role checks | FastAPI routes with `require_roles` (`app/core/security.py`) |
| Firestore rules and collections | SQLite tables (SQLAlchemy models), with every read and write going through role-checked routes. Browsers never touch the database. |
| ML service prediction endpoints | `app/promotion/explain.py` and `app/promotion/routes.py` (the same server) |
| The anonymous portal `/voice` | `/report`, `/my-report` and `/report-keys` (staff sign in first; the report is never linked to the account) |
| Compliance auditor role | **Does not exist.** The roles are employee, manager, HR, admin and finance (see question 1). |
| `docs/THESIS_GUIDE.md`, `THREAT_MODEL.md`, `EVALUATION_RESULTS.md`, `DATA_MODEL.md` | Don't exist yet. The equivalents are `README.md`, `docs/HOW_IT_WORKS.md`, `docs/EVALUATION.md` and `docs/LIMITATIONS.md`. |

## 0. Already changed in this session (model)

Committed as `95d4aa4` and `1102b7f`, with your approval ("drop department, use the monotonic EBM"):

- **Department was a model input (High, fixed).** Past promotion rates range from 2% (Support) to 33%
  (Engineering), so two people with the same record scored very differently only because of their department.
  Department is now excluded, with the reason recorded in `features.py`. A test checks that department never
  changes a score.
- **Logistic regression broke common sense (High, fixed).** It had negative weights on peer feedback,
  problem-solving and training hours: more of any of these always *lowered* readiness. Training now checks every
  candidate model and only lets through models with zero violations:

  | Model | Validation PR-AUC | Times improving an input lowered a score |
  |---|---|---|
  | EBM (monotonic), chosen | 0.4671 | 0% |
  | Logistic Regression | 0.4618 | 16.7% |
  | Random Forest | 0.4528 | 30.1% |
  | XGBoost | 0.4699 | 21.9% |

- **Test set, re-measured once:** PR-AUC **0.4736** (it was 0.6325 with department; random guessing scores 0.10),
  ROC-AUC 0.8833, F1 0.4856, threshold 0.2283. The four-fifths rule passes (gender 0.982, age 0.963, education
  0.887). The old score was higher mainly because the model learned the department pattern.

## 1. Bugs and incorrect logic

| # | Severity | Where | Problem | Root cause |
|---|---|---|---|---|
| B1 | High | `README.md`, `docs/HOW_IT_WORKS.md`, `docs/LIMITATIONS.md`, `docs/EVALUATION.md` | The docs describe logistic regression, 21 inputs including department, ROC-AUC 0.93 and PR-AUC 0.632. None of this is true any more. | The docs were written for the old model (section 0). |
| B2 | High | `frontend/src/pages/public/Home.jsx:37,57-60` | The landing page says "21 measures" (now 20). When no model is trained, it shows **made-up numbers** (0.93, 93%, 20,000) as if they were measured. | Hard-coded fallbacks instead of "not measured yet". |
| B3 | High | `frontend/src/pages/public/PromotionPage.jsx:17` | "A score above 79% counts as recommended" is hard-coded; the real threshold is now 23%. | The threshold was copied into the text instead of read from `/api/public/summary`. |
| B4 | Medium | `frontend/src/api.js`, `auth.jsx` | When a login expires (after 8 hours), every page shows "Please sign in." as an error, and the user stays on a broken page. | 401 answers are not handled in one place. |
| B5 | Medium | `frontend/src/App.jsx` | One error while drawing a page leaves a blank white screen with no message. | No error boundary. |
| B6 | Medium | `pages/promotion/ModelOverview.jsx` | "What it never looks at" leaves out department, city and the other excluded inputs. "2,000 employees" is hard-coded. | Text not updated; the number isn't read from the model. |
| B7 | Medium | `routes_records.py: edit_record` | An HR edit to a record writes only "Edited an employee's record". Old and new values, and the score before and after, are not kept. A score can change without a trace of why. | The activity log stores only a short note. |
| B8 | Low | `app/accounts/models.py:17`, `roles.js:1`, `routes_admin.py:63` | Comments say "four roles" or "employee, manager, hr or admin", and the error message says "Admin and HR" while finance is also refused. | Finance was added later. |
| B9 | Low | `backend/app/promotion/labels.py` | `department` is still listed as a feature. It is harmless (never used by the model), but confusing. | Left over from the old model. |

## 2. Security and anonymity

| # | Severity | Where | Problem |
|---|---|---|---|
| S1 | Medium | `keyStore.js` | Report keys are kept in the browser under `report-keys:<user id>`. Anyone with access to that browser profile (a shared PC, IT support) can read which account holds which case ID and key: a direct link from reporter to report. |
| S2 | Medium | `NotificationBell.jsx`, `/api/reports/updates` | Every minute, the reporter's browser sends its saved case IDs and keys together with the login token. The server doesn't record this, but anonymity rests only on nobody adding request logging. Documented in `LIMITATIONS.md`; worth stating in the threat model. |
| S3 | Medium | `routes_auth.py: login` | No limit on wrong passwords per account (reports have a lockout; sign-in doesn't). |
| S4 | Medium | `security.py` | Login tokens stay valid for 8 hours after a password change, a reset or a sign-out; there is no way to withdraw them. A deactivated account *is* blocked at once (good). |
| S5 | Low | `reporting/routes.py: open_case` | Anyone who knows a case ID can lock that case for 15 minutes with 5 wrong keys, keeping the reporter out. |
| S6 | Low | `roles.py: REPORTER_ROLES` | Finance (and HR) staff can't report at all, so a finance employee has no anonymous channel. |
| S7 | — | whole app | **Good:** role checks are on the server for every route; reports store no user, time or row order; the reporter is never emailed; there is no way to unmask a reporter; a test checks that predictions don't change when reports are added. |

## 3. Missing against the thesis (to build in Phase 4 and 5)

- **There is no "bridge":** nothing links reports to promotion scores (`git grep` finds no bridge, rater-bias or
  retaliation code). Phase 2 will only confirm this and record it in the docs.
- **No explanation rating, no record-correction request, no HR correction queue, no committee note, and no
  re-appraisal path** (objective 3).
- **The report form has no promotion-focused categories**: "Biased rating or appraisal", "Favouritism" and "Wrong or
  missing record" don't exist yet ("Abuse of power or favouritism" and "Discrimination" do). There is no outcome
  "rating found unfair".
- **The isolation test covers reports only.** It doesn't cover ratings, correction requests, conversations or
  outcomes, and there is no static check that the promotion code never imports `app.reporting`. (It doesn't
  today: checked by hand.)
- **No feedback dashboard; the admin home has 4 counts but no system health** (model version, training date,
  fairness gate, drift).
- **The explanation page shows the technical parts to everyone.** Exact contributions and LIME sit next to the
  plain summary, even on an employee's own page; there is no "Show technical details".

## 4. Code quality

| # | Where | Problem |
|---|---|---|
| Q1 | `routes_decisions.py` (381 lines) | Pay policy, nominations, decisions, resubmission, the log and "my promotions" all in one file. The "outside the pay policy" check is copied twice (`decide`, `resubmit`). |
| Q2 | `routes.py`, `routes_decisions.py` | `employee.full_name` and `department` dictionaries are built by hand in 7 places. |
| Q3 | `reporting/routes.py` | Category lists, outcomes, the key code and the routes are in one module that `routes_hr.py` and `routes_evidence.py` import from; the categories would sit better in their own file. |
| Q4 | `mailer.send_to_many` | Never called (dead code). |
| Q5 | `frontend` | No linter is set up and there are no frontend tests. |

## 5. UI/UX and accessibility

| # | Where | Problem |
|---|---|---|
| U1 | All pages | Loading is the word "Loading…" only; errors are a red line with no way to retry. |
| U2 | `Readiness.jsx` | For an employee, the page leads with log-odds tables and LIME rules. The plain summary is there, but the technical parts aren't tucked away. "Compared with an average employee" is explained only in small print. |
| U3 | `Readiness.jsx` | Tips wait for LIME to finish (they are independent), so the page fills in more slowly than it needs to. |
| U4 | `ModelOverview.jsx` | No empty state if the model isn't trained (it shows a raw error). |
| U5 | Design | Light and dark themes exist and the layout has 9 breakpoints with a phone tab bar. **No accessibility audit has been run yet** (planned for Phase 7, with axe). |

## 6. Performance (measured on the running app, 120 demo employees)

| Endpoint | Time |
|---|---|
| `GET /promotion/employees` (score everyone) | 0.26 s |
| `GET /promotion/employees/{id}` (with LIME) | 0.25 s |
| `POST .../predict` | 0.04 s |
| `POST .../lime` | 0.14 s |
| `GET .../tips` | 0.01 s |
| `GET /promotion/importance` | 0.22 s (first call, then cached) |

| # | Where | Problem |
|---|---|---|
| P1 | `GET /promotion/employees` | Scores people one at a time, about 2 ms each, which would be about 10 s for 5,000. One batched model call would do it. There is no pagination. |
| P2 | `describe`, `log_entry`, `summary` (inbox) | Several database lookups per row (N+1). Fine at demo size, slow when large. |
| P3 | `NotificationBell.jsx` | HR's bell downloads the **whole decision log** every 60 s, just to find "sent back" pay rises. |
| P4 | `/api/reports/updates` | Each saved key is checked with 200,000-round PBKDF2 (≈0.1 s), up to 20 keys, every minute per reporter. |
| P5 | `/api/admin/users` | Returns every user's profile photo (up to 300 kB each) in the list. |
| P6 | Frontend bundle | One 443 kB file (133 kB gzipped): every page, including the admin pages and the public site, loads at once. No lazy loading. |

## 7. Decisions (answered 2026-10-08)

1. **Compliance auditor:** add a read-only `auditor` role. It sees the dashboards, the decision log, the model and
   its fairness, and only aggregated feedback. It never sees report texts or names in reports, and it can't edit
   anything.
2. **Reporting is aligned with the feedback channel.** New reports use the five promotion-focused categories:
   "Biased rating or appraisal", "Favouritism", "Discrimination", "Wrong or missing record" and "Other workplace
   concern". Old reports keep showing their original category.
3. **No report keys are kept in the browser.** The "My report keys" page, saving keys on the device and the
   reporter notifications that polled saved keys are removed (S1, S2, P4). Reporters keep their key by
   downloading the receipt or using their password manager. Keys already saved in a browser are shown once, so
   they can be kept elsewhere, and then removed from it.
4. **Sign-in lockout:** an account is locked for 15 minutes after 5 wrong passwords in a row (S3).

## 8. Phase 2: the bridge

No "bridge" exists in this project. `git grep` finds no bridge, rater-bias, retaliation-monitor or
`RATER_BIAS_MIN_CASES` code, settings, tests or docs. The git history has no such commits. The promotion code
(`backend/app/promotion`) has no reference to the reporting module or its tables. There is no combined fairness
overview that reads report data. Nothing had to be removed. The isolation guarantees are extended in Phase 4
(isolation test and static import check).
