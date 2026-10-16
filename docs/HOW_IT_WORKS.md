# How It Works

A plain-English explanation of every part of the system and why it was built that way. One section is added per
build step.

## Step 1: Accounts, signing in and roles

### What it does

Every person who uses the platform has an account with a username, a password and exactly one **role**. Step 1
built four (Employee, Manager, HR, Admin); Finance and the compliance auditor came later. The role decides what
they can see and do.

| Role | Can do |
|---|---|
| Employee | See their own readiness score, explanation and tips |
| Manager | See their team's scores; nominate team members |
| HR | See all employees; decide on nominations |
| Admin | Create accounts; view the activity log |

Only an **admin** can create accounts, for any of the six roles. Nobody can sign themselves up. A new account
gets a random **temporary password**, which the admin passes on. The first time the person signs in, they must
choose their own password before they can do anything else. If someone forgets their password, the admin gives
them a new temporary one. The admin can also **deactivate** an account, which locks the person out at once.

### How signing in works

1. The person types their username and password on the sign-in page.
2. The backend looks up the username and checks the password (see "Passwords" below).
3. If both are right, the backend returns a **token**: a short piece of text, digitally signed by the server,
   that says "this is user number 5" and expires after 8 hours. A **JWT** (JSON Web Token) is a standard
   format for this.
4. The website keeps the token and sends it with every later request. The backend checks the signature, so a
   token can't be forged or edited.

A wrong password and an unknown username give exactly the same message ("Wrong username or password"), so
nobody can use the sign-in page to find out which usernames exist.

### Passwords

Passwords are never stored. The backend stores a **hash**: the result of a one-way calculation
(PBKDF2-SHA256, repeated 200,000 times to make guessing slow). To check a password, the same calculation is
run on what the person typed and the two results are compared. Each password gets its own random **salt**
(extra random characters mixed in), so two people with the same password get different hashes.

This uses only Python's built-in `hashlib`, so there is no extra library to explain or install.

### Role checks happen on the backend

The website shows each role only its own menu, but that is just for convenience: anyone could send requests to
the backend directly. So **every backend endpoint checks the role itself**. For example, the account
endpoints are wrapped in `require_roles("admin")`: any other role gets "403 Forbidden", whatever the website
shows.

On every request the backend also re-reads the user from the database, rather than trusting what the token
says about them. That is why deactivating an account, or changing someone's role, takes effect immediately,
even for a token issued earlier.

### The database

The data is stored in **SQLite**: a database kept in a single file (`backend/instance/app.db`), so there is no
database server to install. **SQLAlchemy** maps each table to a Python class; step 1 has one table:

| Column | Meaning |
|---|---|
| `id` | Number that identifies the account |
| `username` | What the person signs in with (unique, lower case) |
| `full_name` | Shown on screen |
| `password_hash` | The hash, never the password |
| `role` | employee, manager, hr or admin |
| `is_active` | False when the admin has deactivated the account |
| `must_change_password` | True until the person replaces their temporary password |
| `employee_id` | The employee record this login belongs to (used from step 3) |
| `created_at` | When the account was created |

### Why the code is organised this way

```
backend/app/core/       basics every part needs (database, security, roles)
backend/app/accounts/   accounts and signing in
backend/app/promotion/  (step 2 onwards) the promotion model and its explanations
backend/app/feedback/   (step 9) the employee feedback channel
```

Promotion and feedback are **separate packages with separate tables**. The promotion code never imports anything
from the feedback package, and a test proves that feedback can't reach the model (step 9).

### How it was tested

`backend/tests/test_auth_and_roles.py` (19 tests) checks that:

- passwords are hashed with a salt and verified correctly;
- each demo account can sign in, and the password hash is never sent back;
- a wrong password and an unknown username get the same answer;
- requests without a valid token are refused;
- HR, managers and employees cannot list or create accounts (403);
- the admin can create an account for every role, and the new person can sign in with the temporary password;
- usernames are unique, roles must be one of the four, and an employee record can have only one login;
- a deactivated account is locked out at once, even with a token issued before;
- the admin cannot deactivate their own account;
- the admin can reset a forgotten password.

## Step 2: Training the promotion model, its results and the fairness check

Everything in this step is done by one script, `backend/train.py`, using helpers in `backend/app/promotion/`.
All numbers below come from running it (`results/*.json`).

### The data

`backend/data/employee_promotion_dataset_100000.csv`: 100,000 synthetic (made-up) employees with 43 columns.
The column `promoted` says whether each was promoted (1) or not (0). 10% were promoted, so a model that
guessed at random would find promoted employees only 10% of the time.

### Which information the model may use

The model only sees **performance and development** information (20 inputs, listed in
`app/promotion/features.py`):

| Group | Inputs |
|---|---|
| Performance | performance score, change in performance since last year, manager rating, peer feedback, KPI achievement, projects completed, tasks completed, deadline adherence, innovation, leadership, problem solving, skill assessment |
| Development | training hours, certifications, cross-department projects, mentoring sessions |
| Reliability | attendance rate, late days |
| Career stage | years since last promotion, years in current role |

Every other column is left out **with a written reason** (the `EXCLUDED` list in `features.py`, checked by a
test so no column is forgotten):

- **Protected characteristics** (gender, age, education, marital status) are never model inputs. Gender, age and
  education are kept aside only to check fairness afterwards.
- **Department.** Past promotion rates differ hugely by department: Engineering 33%, Sales 11%, Marketing 9%,
  Finance 8%, Operations 4.5%, HR 3%, Support 2%. A model given the department learns "being in Engineering
  raises your chance", so two people with the same record would get different scores only because of where they
  work. A test checks that department never changes a score.
- **Pay** (salary, raises, bonus, stock) records how someone has already been valued, and could carry old pay
  gaps into promotion decisions.
- **Attitude surveys** (engagement, job satisfaction) measure how someone feels, not how they perform.
- **Working hours** (monthly hours, overtime, meetings, remote ratio) would reward long hours rather than
  results, and disadvantage people with caring duties.
- Where someone lives (city tier), team size, contract type and tenure at the company are not about the work.

**Why "change since last year" instead of three yearly scores.** The dataset has performance scores for this
year, last year and two years ago. They move together very closely, so a model given all three splits their
effect in confusing ways (for example a large positive effect for one year and a large negative one for
another), which would make the explanations misleading. Two clearer facts replace them: this year's score, and
how much it changed since last year.

### The three parts of the data

| Part | Size | Used for |
|---|---|---|
| Training | 70,000 | Fitting the models |
| Validation | 10,000 | The common-sense check, choosing the model and the decision threshold |
| Test | 20,000 | Measuring the final model, **once**, at the very end |

The split is **stratified** (each part has the same 10% promotion rate) and fixed with `random_state=42`, so
it's the same every run. Keeping the test set untouched until the end means the reported results are an honest
estimate of how the model does on employees it has never seen.

### Four models, a common-sense check, one chosen

| Model | Validation PR-AUC | Validation ROC-AUC | Scores that dropped when an input improved |
|---|---|---|---|
| **EBM, monotonic** (chosen) | **0.4671** | **0.8806** | **0%** |
| XGBoost | 0.4699 | 0.8777 | 21.9% |
| Logistic Regression | 0.4618 | 0.8793 | 16.7% |
| Random Forest | 0.4528 | 0.8769 | 30.1% |

- The **Explainable Boosting Machine (EBM)** learns one curve per input and adds them up. Its curves can bend
  (for example, diminishing returns), yet each prediction still splits exactly into one part per input.
  **Monotonic** means that for every input a person can improve, the curve is only allowed to go one way: more
  training, more projects or fewer late days can never lower the score.
- **Logistic Regression** gives each input one straight-line weight. Here it learned *negative* weights for peer
  feedback, problem solving and training hours (side effects of inputs that move together), so more of any of
  them always lowered the score.
- **Random Forest** and **XGBoost** combine hundreds of decision trees; they can be accurate but are harder to
  explain, and they have no such guarantee.

Because only 10% were promoted, logistic regression, random forest and XGBoost give the rare "promoted" cases more
weight (**class weights**) rather than copying them (oversampling). The EBM has no class weights; the threshold
below makes up for that.

**The common-sense check.** For 2,000 validation employees, each input a person can improve (and the change in
performance) is moved half a standard deviation in its improving direction, one at a time; raising this year's
performance score also raises the change since last year. A "violation" is any employee whose score then drops.
The table's last column is the share of such cases.

**How the model is chosen.** Only models with **no** violations are eligible. Among them, the models are
compared by **PR-AUC** (area under the precision-recall curve) on the validation set, and the easiest to explain
within 0.01 of the best is chosen. PR-AUC is used because it focuses on how well the model finds the rare
promoted employees; accuracy would look good even for a model that never recommends anyone (90% correct). Only
the EBM was eligible, so it was chosen. (XGBoost scored 0.003 higher, but lowered scores in 21.9% of cases.)

### The decision threshold

The model gives each employee a score between 0 and 1. The **threshold** is the cut-off at or above which the
model recommends promotion. It is chosen on the validation set as the value with the best **F1 score** (a balance
between precision and recall): **0.2283**.

The score is **calibrated**: it can be read as the share of employees like this who were promoted in the past data.
Measured on the test set (`python -m evaluation.calibration`), the average gap between score and actual rate
(expected calibration error) is 0.0056, the calibration slope 0.998: of employees scoring around 23%, about 23-24%
were promoted. It describes past decisions in that (synthetic) data, not a promise about a person's future, and what
matters for a recommendation is still whether a score is above or below the threshold.

### Results on the test set (measured once)

| Measure | Result | Meaning |
|---|---|---|
| ROC-AUC | 0.8833 | How often a promoted employee is ranked above a non-promoted one (0.5 = coin flip) |
| PR-AUC | 0.4736 | How well promoted employees are found (random guessing: 0.10) |
| Accuracy | 0.8740 | Share of all employees classified correctly |
| Precision | 0.4102 | Of those the model recommends, the share actually promoted |
| Recall | 0.5950 | Of those actually promoted, the share the model recommends |
| F1 | 0.4856 | Balance of precision and recall |
| Share recommended | 14.5% | The real promotion rate is 10% |

Confusion matrix (20,000 test employees): 1,190 correctly recommended, 1,711 recommended but not promoted, 810
promoted but not recommended, 16,289 correctly not recommended.

Curves: `results/roc_curve.png` and `results/pr_curve.png`.

**Compared with the earlier model.** An earlier version used logistic regression *with* department and reached
PR-AUC 0.6325 and ROC-AUC 0.9295. Most of the difference is department: it predicts past decisions well because
past decisions favoured some departments. Leaving it out costs accuracy at copying the past, and is the fairer
choice for a system that should judge people on their work.

### Fairness check (four-fifths rule)

For each group the script measures the **selection rate**: the share of the group the model recommends. The
**four-fifths rule**, a common test for unfair impact, requires every group's rate to be at least 80% of the
highest group's rate. If any check fails, the script prints a warning and does **not** save the model as the
live model.

| Attribute | Selection rates | Ratio (lowest / highest) | Result |
|---|---|---|---|
| Gender | Female 14.6%, Male 14.4% | 0.982 | Pass |
| Age group | Under 40: 14.8%, 40+: 14.2% | 0.963 | Pass |
| Education | Bachelor 14.3%, Master 14.7%, PhD 16.1% | 0.887 | Pass |

The model passed, so it was saved as the live model (`backend/models/model.joblib`, with its threshold, inputs
and version in `model_info.json`). `results/fairness.json` also records each group's real promotion rate for
comparison, and `results/model_comparison.json` the common-sense check of every candidate.

### How it was tested

`backend/tests/test_training.py` (17 tests) checks that:

- protected characteristics, pay and department are never model inputs, and every column is either used or
  excluded with a reason;
- the performance-change feature is calculated correctly and replaces the yearly scores;
- the split is 70/10/20, stratified, without overlap, and the same every run;
- the model-choice rule excludes models that lowered scores when an input improved, prefers the EBM over
  logistic regression when both are eligible and close, keeps every model eligible if none passes, and
  otherwise picks the clearly better model;
- the threshold search finds the right cut-off on simple data;
- the four-fifths rule passes at exactly 80% and fails below it, and age groups are assigned correctly;
- after training, the saved threshold and metrics load and agree, the curve images exist, the live model was
  chosen with no common-sense violations, passed the fairness check, and produces scores between 0 and 1.

## Step 3: Predictions and explanations

Code: `backend/app/promotion/` (`explain.py` does the work, `routes.py` is the API, `labels.py` names and units).

### The employee directory

The app needs employees to show. It uses **120 employees from the test part of the dataset**, so the model has
never seen any of them in training. The dataset has no names, so each gets a made-up one. The demo manager
manages 12 of them, and the demo employee login is linked to one of those 12.

The `employees` table stores only what the app needs: name, department, manager, and the work record that the
model uses. **Gender, age, education and pay are not stored in the app at all**; they are only used offline, by
`train.py`, for the fairness check.

### Who may see what

Checked by the backend on every request (`can_see` in `routes.py`):

| Role | Sees |
|---|---|
| HR | Every employee |
| Manager | Only their own team |
| Employee | Only themselves |
| Admin | None of it (admins manage accounts, not promotions), unless given "can view employee data" (read-only) |
| Compliance auditor | No individual employees: the decision log, the model's overall importance and the record histories |

### What the API returns for one employee

**Readiness score.** The model's score, shown as a percentage, and whether it reaches the threshold (23%).
As explained in step 2, it is calibrated against past promotions (a score of 23% matches about 23 promoted in 100), but it is not a promise.

**Exact contributions.** The EBM adds up one learned term per input:

```
log-odds = base + sum over inputs of  (this employee's term − the average term)
```

Each part of the sum is that input's **contribution**: how much it pushes this employee's score up or down
compared with an average employee. For an additive model like this, that is exactly what SHAP calculates, so
no approximation is needed. "base" is the log-odds of the average employee (the average of every input's term
over 2,000 training employees; their score: 2.0%). Because the parts add up exactly to the model's output, the
explanation is complete: there's nothing the model used that isn't shown. A test checks this for all 120 demo
employees. Every value is shown in its normal unit ("90.5%", "4.1 / 5", "13 years").

**LIME, a second opinion.** LIME works differently: it creates 2,000 slightly altered copies of the employee's
record, asks the model to score them, fits a small simple model to those answers, and reads rules from it (for
example "Change in performance since last year <= -1.94 lowers readiness"). Its **fit (R²)** says how well that
simple model copies the real one around this employee. Below 0.5, a note says to treat the rules as a rough
guide.

In practice, LIME's fit is low for most employees here (median 0.13 over the 120 demo employees; 84% below 0.5).
That's expected: most employees are far from the threshold, where the model's curve is flat and a simple local
model has little to fit. This is why the exact contributions are the main explanation, and LIME is shown only as
a second opinion, with its fit.

**Plain-language summary.** Built from the score, the threshold and the two biggest contributions each way. For
the demo employee login:

> Readiness is 0%, below the 23% threshold, so the model does not yet recommend promotion. Compared with an
> average employee, it is raised mainly by attendance (95.1%) and cross-department projects (4), and lowered
> mainly by a 2.8-point drop in performance since last year and KPI achievement (42.2%).

**What-if.** The user changes some inputs and gets the new score and explanation. Only **improvable** inputs
(things a person can work on, such as training hours or late days) can be changed, within the range real
employees had. Years in role, years since promotion and the protected characteristics can't be. Nothing is
saved. Raising this year's performance score also raises "change since last year" by the same amount, because
that is how the change is calculated.

**Tips to improve.** The smallest realistic improvements that would reach the threshold:

1. Only improvable inputs, and only in the improving direction (more training, fewer late days).
2. Only inputs where improving actually raises the score (with the monotonic model, improving never lowers it).
3. Each input by at most one standard deviation, and not past what the top 5% of employees achieve
   (and never past natural limits such as 100%).
4. The inputs with the biggest possible effect first, each only as far as needed. The model's curves needn't be
   straight lines, so each step is tried on the model itself.

For the 108 demo employees not yet recommended, the tips reach the threshold for 98. For the other 10, the tips
show the most realistic progress, and the projected score says how far it gets.

**Overall importance.** Across 2,000 training employees: the average size of each input's contribution, as a
share of the total. The direction is read from the shape of the input's curve.

| Input | Share of the model's effect | Direction |
|---|---|---|
| Change in performance since last year | 51.5% | higher raises readiness |
| Projects completed | 10.7% | higher raises readiness |
| Tasks completed | 6.9% | higher raises readiness |
| Performance score | 4.7% | higher raises readiness |
| Leadership score | 4.5% | higher raises readiness |
| Years since last promotion | 3.8% | higher lowers readiness |

### Points to discuss in the thesis

- **One input dominates.** Change in performance since last year accounts for about half of the model's
  effect, so for many people one tip (raise this year's performance) goes a long way.
- **Department was removed** (step 2): with it, about a quarter of the old model's effect came from where
  someone works. The model now judges only the work record; the cost in accuracy is reported in step 2.
- **Years since last promotion lowers readiness.** In this data, people who have waited a long time are less
  likely to be promoted. The model reproduces that pattern; it doesn't judge whether it's fair. It is left
  unconstrained, and isn't something a person can change, so it never appears in tips.

### API endpoints

| Method and path | Who | Returns |
|---|---|---|
| `GET /api/promotion/employees` | HR, manager, employee | The employees they may see, with scores |
| `GET /api/promotion/employees/{id}` | Same, for their visible employees | Score, contributions, LIME, summary, what-if options, model version |
| `POST /api/promotion/employees/{id}/what-if` | Same | Score and contributions with the changes applied |
| `GET /api/promotion/employees/{id}/tips` | Same | Tips and the projected score |
| `GET /api/promotion/importance` | HR, manager, employee, auditor | Overall importance, and everything the model never uses with the reason |

### How it was tested

`backend/tests/test_explanations.py` (24 tests) checks that:

- the contributions add up exactly to the model's output, for all 120 demo employees;
- department is not an input, two people with the same record get the same score whatever their department,
  and values are in their real units;
- improving any improvable input never lowers the score (50 training employees, every input);
- LIME returns rules and a fit score, with a note exactly when the fit is below 0.5;
- the summary states the score and the threshold;
- a what-if changes the score but saves nothing; changing this year's performance also changes the change
  since last year; non-improvable inputs and impossible values are refused;
- across all 120 employees, tips only use improvable inputs, only in the improving direction, by at most one
  standard deviation, within natural limits, and never lower the score;
- overall importance covers all 20 inputs, adds up to 100%, and its directions follow the constraints;
- the model page lists everything the model never uses;
- HR sees all 120 employees, a manager only their 12, an employee only themselves, and the admin nothing.

## Step 4: The promotion pages

Code: `frontend/src/pages/promotion/` (pages) and `frontend/src/components/promotion/` (the parts of an
explanation, one file each).

### Which pages each role gets

| Role | Menu | What it shows |
|---|---|---|
| Employee | My growth · How the model works | Their own score, explanation, path to promotion, what-if, and the respond panel (step 9) |
| Manager | My team · How the model works | Their team with scores; click a name for the full explanation |
| HR | All employees · How the model works | Everyone (50 per page), with search, department filter and "recommended only"; click a name for the full explanation |
| Auditor | Decision log · Feedback dashboard · How the model works | No individual employees: decisions, the model and totals only |
| Admin | Users | No promotion pages: admins manage accounts, not promotions |

The website hides pages a role can't use, but the real protection is the backend (step 3): even if someone
typed a page address or called the API directly, they would only get data their role allows.

### The readiness page

One page, used both for "My growth" and when HR or a manager opens an employee. It reads in plain words first,
top to bottom answering the questions a person naturally asks:

1. **Where do I stand?** The score as a percentage on a 0–100% bar, with the threshold marked, and
   "Recommended" or "Not yet recommended" in words. Below it, the plain-language summary, and "Your readiness is
   compared with an average employee. Scores match past promotions closely: of employees scoring around 23%, about 23 in 100 were promoted. It describes past decisions, so it isn't a promise:
   the model only advises, and people make the decision." A score above zero that rounds to 0% reads "under 1%".
2. **Why?** Two short lists: what raised the score and what lowered it, compared with an average employee, each
   with the person's real value and a bar for the size of the effect. On the employee's own page the bars carry
   no numbers; HR and managers see each contribution's size.
3. **Path to promotion** (tips). Numbered steps ("Increase leadership score from 46.3 to 50.0"), followed by a
   sentence on where they lead: above the threshold, or how much closer.
4. **What if?** A slider for each improvable factor, set to the person's current value and limited to the
   range real employees had. "See the new score" asks the backend; nothing is saved. "Reset" puts everything
   back.
5. **Respond to this explanation** (the employee's own page only; step 9).
6. **Show technical details** (folded away): the model and its version, every factor's exact contribution in a
   table (they add up to the score), and LIME's rules with its fit and the warning when the fit is low.

On "My growth" the prediction runs as the page opens; HR and managers click "Run prediction" and watch its steps.
LIME and the tips are worked out at the same time.

### Design choices

- **Never colour alone.** "Recommended" is written as a word; raising and lowering factors are in separate,
  labelled lists with ▲ and ▼; the threshold is a line with a label. Blue and orange are used for up and down
  because they stay distinguishable for people with the common forms of colour blindness.
- **Real units everywhere.** "90.5%", "4.1 / 5", "42 hours", never the scaled numbers the model works with.
- **The exact numbers are one click away**, not hidden, so the explanation can be checked.
- **One page for everyone**, so an employee and HR see the same explanation of the same score.

### Something to discuss: long tip lists for low scores

For someone far below the threshold (a score near 0%), the tips can list many small steps (15 for the demo
employee), because each factor may move only one realistic step. The tips then say honestly that they would
raise the score (here to 70%) but not all the way to the threshold. That is a property of the rule "at most one
realistic step per factor", which keeps every suggestion achievable.

### How it was checked

Walking through the pages in a browser as each role:

- **Employee:** sees their own readiness. A what-if raising the performance score by 10 points shows the new
  score (0% to 12%). Opening the HR list shows "Not available".
- **Manager:** sees exactly their 12 team members, and can open each one's full explanation.
- **HR:** sees all 120; "recommended only" narrows it to the 13 above the threshold.
- **Admin:** has no promotion pages in the menu.

There were no errors in the browser console. The backend tests (49) still pass.

## Step 5: Nominations, decisions and the decision log

Code: `backend/app/promotion/routes_decisions.py` (API), the `Nomination` and `Decision` tables in
`backend/app/promotion/models.py`, and the pages `Nominations.jsx`, `ReviewNomination.jsx` and `DecisionLog.jsx`.

### How a promotion decision happens

1. **A manager nominates** someone on their own team, from that person's readiness page, with a short reason
   (at least 10 characters). A person can have only one nomination waiting at a time.
2. **HR reviews** the nomination on one page: the manager's reason, the model's current score with its
   explanation, and a link to the full explanation, what-if and tips.
3. **HR decides**: approve or reject. The model only advises; HR's decision is final.
4. **If HR disagrees with the model** (approves someone it doesn't recommend, or rejects someone it does), a
   reason of **at least 20 characters** is required. The page says when this applies and counts the characters;
   the backend enforces the same rule, so it can't be skipped.
5. **The decision is logged**: who decided, when, approve or reject, the model's score and recommendation *at
   that moment*, whether HR agreed with the model, and the reason.

### Why record the model's view with each decision

The model may be retrained later, and an employee's record may change. Saving the score and recommendation at
the time of the decision means the log always shows what HR actually saw when deciding. It also lets anyone
reviewing the log see how often HR followed or overruled the model, and read why each time.

### The tables

**nominations**: who was nominated, by which manager, the reason, the status (pending, approved or rejected)
and the date.

**decisions** (the decision log): one row per decided nomination:

| Column | Meaning |
|---|---|
| `decided_by`, `decided_at` | Which HR user decided, and when |
| `decision` | approve or reject |
| `model_score`, `model_threshold` | The model's score and threshold at that moment |
| `model_recommended` | Whether the model recommended promotion then |
| `agrees_with_model` | Whether HR's decision matched the model |
| `reason` | HR's reason (required when disagreeing) |

### Who can do what

| Action | Who |
|---|---|
| Nominate | Managers, only for their own team |
| See nominations | HR: all; managers: the ones they made |
| Decide | HR only, once per nomination |
| Read the decision log | HR only |

### Managers' teams

A manager sees, and can nominate, only the employees on their team. The admin decides who is on each team: on
the Users page, each manager account has a **Team** button that opens a list of all employees to tick. Ticking
someone on another manager's team moves them; unticking someone leaves them without a manager. The admin sees
names and departments only, never scores, because admins manage accounts, not promotions. When creating an
account, the admin now picks the employee record from a list instead of typing its number.

### How it was tested

`backend/tests/test_decisions.py` (17 tests) checks that:

- a manager can nominate a team member, but not someone outside their team; employees, HR and the admin can't
  nominate at all;
- a nomination needs a real reason, and a person can't have two waiting at once;
- HR sees all nominations, a manager only their own, an employee none;
- agreeing with the model needs no reason; disagreeing needs at least 20 characters, in both directions
  (approving someone not recommended, and rejecting someone recommended);
- only HR can decide, and only once;
- the decision log records who, when, the decision, the model's score and recommendation, and the reason;
  only HR can read it;
- the admin can set a manager's team (and sees no scores); teams can only be given to manager accounts, only by
  the admin, and only with real employees.

A browser walkthrough confirmed the whole flow: the manager nominated a team member, HR opened it, chose
"approve" against the model, the save button stayed disabled until the reason reached 20 characters, and the
decision appeared in the log as "Differs from the model" with the model's score at the time.

## Steps 6 and 7: removed

Steps 6 and 7 built anonymous reporting (the anonymiser, case keys, triage, the conversation and
HR's report inbox). It was removed from this version to keep the scope focused; see `docs/future-work/` and the
git tag `with-anonymous-reporting`.

## Review cycles: running a promotion round

Code: `backend/app/promotion/cycles.py` (how a cycle works), `routes_cycles.py` (its API), the tables `review_cycles`
and `cycle_scores` (`models.py`), and the page `frontend/src/pages/promotion/ReviewCycles.jsx`. Tests:
`tests/test_cycles.py`.

Without a cycle, a readiness score is worked out when someone asks for it and is not stored. That is simple and
private, but a promotion round needs more. Lists started as "Not run yet", a score could move between a manager's
nomination and HR's decision, and nothing showed afterwards what the model had said to everyone. A **review cycle**
fixes this:

1. **HR opens a cycle** (Promotion → Review cycles) with a name such as "2026 mid-year", the last day managers may
   nominate, and an optional note. The live model scores **everyone at once**. Each score is saved with the exact
   inputs it came from and the model version, so it can always be reproduced. The opening is in the audit trail,
   and every manager with a team gets an email: their team's size, how many the model recommends, and the
   deadline (no names or scores).
2. **The lists show the saved scores straight away**: All employees, My team, and the overviews, under a "Review
   cycle" banner. Someone added to the directory during the cycle is scored into it with the same model.
3. **A saved score changes only through a logged record change.** When HR edits a record, or confirms a record
   correction, the person's cycle score follows. The score at opening is kept beside it, and the record change
   (with its reason, in the record history and the audit trail) is linked. Nothing else moves a score mid-cycle.
4. **The same model for everyone in a cycle.** A new model version can't be released while a cycle is open
   (`app/governance/registry.py` refuses it). Close the cycle first.
5. **Nominations belong to the cycle**, and so do HR's decisions on them. After the deadline the server refuses
   new nominations for that cycle, and the manager's form says so.
6. **HR closes the cycle** once every nomination in it is decided; the page says what is still waiting. Scores then
   go back to being worked out on demand until the next cycle opens. Closed cycles stay exactly as they were.

### The cycle page (HR; the auditor sees totals only)

- **Headline:** the model version and threshold, the deadline and days left, how many scores were updated by a
  record change, and who was added late.
- **KPI tiles:** people scored, recommended, nominated (and "recommended, not nominated"), and decided (approved,
  and how many went against the model).
- **The nomination pipeline** (approved, not approved, waiting for HR, on hold) and a **department breakdown**.
- **Recommended, not nominated** (HR only): a prompt to check, never a to-do list, because the model only advises.
- **Since the last cycle:** for the people in both cycles, who crossed the threshold each way, the average change,
  and (HR only) who rose and fell the most.
- **Fairness in this cycle:** the four-fifths check on this cycle's saved scores, and the nominations and
  decisions made in it (`GET /api/governance/fairness?cycle_id=…`).
- **Export CSV** (HR only): one row per person, with their score, the score at opening, and what happened to any
  nomination.

### Helping people act on time

- **Overviews:** HR is told when no cycle is open, while one is open, and when every nomination is decided and the
  cycle is ready to close. Managers are told a cycle is open and when to recommend by.
- **Notification bell:** during a cycle, before its deadline, managers see how many team members the model
  recommends who aren't nominated yet.
- **Readiness over time:** an employee's page (My growth, and the same page for HR and their manager) shows their
  saved score in every cycle, as a chart with the threshold marked and as a list.

### Who sees what

| | HR | Manager | Employee | Auditor | Finance, Admin |
|---|---|---|---|---|---|
| Which cycle is open, its deadline | ✓ | ✓ | ✓ | ✓ | ✓ |
| Open and close a cycle, export it | ✓ | | | | |
| A cycle's progress | ✓ (with names) | | | ✓ (totals only) | |
| An employee's scores over time | ✓ | their team | their own | | |

### API

| Endpoint | Who | What |
|---|---|---|
| `GET /api/promotion/cycles/current` | everyone signed in | the open cycle, or null |
| `GET /api/promotion/cycles` | HR, auditor | every cycle with its headline totals |
| `POST /api/promotion/cycles` | HR | open a cycle: `{name, nominations_close?, note?}` |
| `GET /api/promotion/cycles/{id}` | HR, auditor | its progress (the auditor's has no names) |
| `POST /api/promotion/cycles/{id}/close` | HR | close it (refused while a nomination is waiting) |
| `GET /api/promotion/cycles/{id}/export.csv` | HR | one row per person |
| `GET /api/promotion/employees/{id}/trend` | as for that person's score | their saved score in each cycle |

### Points to discuss in the thesis

- **Storing scores is a trade-off.** Without cycles, nothing is stored, which is the most private choice. With
  cycles, each score is kept so a round can be audited and reproduced, and decisions are compared against a stable
  number. The data kept is the score, the inputs the model already uses, and the model version: no feedback, and no
  protected characteristics.
- **Stability against correctness.** Freezing scores completely would ignore a correction HR confirmed against
  evidence; letting scores drift with every model change would make a round impossible to compare. The rule chosen
  (only logged record changes move a score; no model releases mid-cycle) keeps both.

## Teams and reporting lines

Code: `backend/app/promotion/teams.py` (the rules), `routes_teams.py` (the API), the table `team_covers`, the page
`frontend/src/pages/promotion/Teams.jsx` and `components/promotion/Cover.jsx`. Tests: `tests/test_teams.py`.

**One manager per person, deliberately.** Every employee has at most one manager, so every recommendation has
exactly one accountable person. A manager's account can be linked to their own employee record, and that record has
a manager too, so reporting lines chain upwards (an org chart). From that, three kinds of access:

| | What the manager sees | May recommend them? |
|---|---|---|
| **Own team** (direct reports) | Scores and explanations | Yes |
| **A team they cover** for a manager who is away | Scores and explanations, for those dates only | Yes |
| **Further down the line** (a skip-level view) | Scores and explanations, read-only | No: only that person's own manager |

**HR owns reporting lines; the admin owns accounts.** HR's **Teams** page (Promotion → Teams) shows:
- **Without a manager:** everyone nobody can recommend yet. Tick people, choose a manager, and assign them; the
  manager is emailed the names (no scores).
- **Reporting lines:** every manager under the manager they report to, with their own team, how many are further
  down, and any cover. "Team" opens a drawer to move people to another manager, or to none.
- **Cover while a manager is away:** another manager sees and may recommend the team for given dates (at most six
  months, no overlaps). A manager arranges cover for their own team on **My team**; HR can for anyone. It ends by
  itself, or earlier.

**A reporting line can never loop.** Putting a manager's own record under someone who already reports to them is
refused. Every move and cover is in the audit trail (`team_changed`, `cover_arranged`, `cover_ended`) and the
activity log.

**Where people see it.** My growth says who the employee's manager is ("Your manager, … can recommend you") and
whether someone is covering. A skip-level manager sees "Read-only for you" and no recommendation form. My team shows
who each person reports to, with a filter for only the people you can recommend. The review-cycle page warns when
people the model recommends have no manager.

The admin's team editor (Users → Team) still works, for setting up a new manager's account.

## Email: delivery, the notification centre, reminders and digests

Code: `backend/app/core/mailer.py` (sending, the delivery log, retries), `notifications.py` (the bell's history),
`reminders.py`, `digests.py`, `scheduler.py` (the timer), `email_templates.py` (every email's words). Pages: the
bell (`components/NotificationBell.jsx`), the admin's Email page with the **Delivery log**
(`components/admin/DeliveryLog.jsx`), and the email choice on **My profile**. Tests: `tests/test_email_delivery.py`.

**Every email is logged and retried.** Each email gets a row in `email_log`: to whom, the subject, its kind, and
whether it was sent. If the mail server doesn't accept it, it is tried again after 1, 5, 15, 60 and 240 minutes,
then marked "not delivered". The admin's Email page shows the log, what is waiting to be retried, and a **Resend**
button. Once an email is delivered, its content is erased (a welcome email holds a temporary password): only who,
what subject and when are kept. Without a mail server, emails are saved to `instance/outbox/` as before.

**The bell and the email come from the same event.** An email about something the recipient may need to act on
carries a short "notice". Sending it also adds that line to their bell's history, read or unread. The bell has two
parts:
- **Waiting for you:** worked out live, e.g. corrections in HR's queue, or pay rises waiting for Finance.
- **Recent:** that history. Opening an item marks it read; "Mark all read" clears the rest.

**Reminders, each sent once** (`reminders_sent` remembers them). The timer checks every hour; the admin can also
"Run reminders now".

| Who | When | What |
|---|---|---|
| Managers | In the last 3 days before a review cycle's nomination deadline | How many on their own team the model recommends and they haven't nominated (a count, never names; recommending nobody is fine) |
| Finance | A pay rise has waited more than 2 working days | Which pay rises are waiting |
| HR | A cycle's nominations have closed and all are decided | The cycle is ready to close |
| HR | A record correction has waited more than 3 days | How many are waiting |

**Daily digest (optional).** On My profile, anyone can choose "one digest each morning" instead of each email as
it happens. Routine emails are then held and sent together at `DIGEST_HOUR` (default 9:00). The bell still shows
each one at once. **Account emails are never held**: sign-in details, password, username and email address changes
always go out immediately.

**The timer** is one background thread started with the app (`SCHEDULER=0` switches it off; the tests run each
step directly). A problem in one step is logged and never stops the others.

**Email for real use.** Gmail with an app password is fine for a demo. For real staff, use a transactional email
service (Brevo, Postmark, Amazon SES or Mailgun) for better delivery, sender authentication (SPF and DKIM on your
own domain) and bounce reports. It is only a settings change: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_SENDER` and, for port 465, `SMTP_SECURITY=ssl` (see `backend/.env.example`).

## Finance at work

Code: `backend/app/promotion/routes_finance.py`, the page `frontend/src/pages/finance/PaySignOff.jsx`. Tests:
`tests/test_finance_operations.py`.

- **How long each pay rise has waited**, in working days since it last reached Finance, with the longest-waiting
  first. After 2 working days it is highlighted, and Finance gets a reminder.
- **Signing off several at once.** Tick pay rises within the pay policy and sign them off together. Each is signed
  off, logged, audited and announced exactly as if done one by one. A rise outside the policy can't be ticked: it is
  always reviewed on its own, with HR's reason.
- **Review cycles in Finance.** A filter for one cycle's pay rises, the cycle on each row, and how the signed-off
  rises spread across the policy band (a chart, with any outside the policy named).
- **Hand-over to payroll.** Signed-off rises payroll hasn't had yet are listed. Download them as a CSV (employee,
  new role, start date, percentage, cycle), give the file to payroll, then **Mark as sent**. Each is marked once
  (`payroll_sent_at`, and a `payroll_sent` audit event), so nothing is applied twice or forgotten. Still only
  percentages, never salaries.

## Data protection, security and running it for real

### People's rights over their data (`app/privacy/`)

- **A copy of your data** (My profile → Your data, `GET /api/privacy/my-data`): the account, the work record and
  readiness scores, nominations and decisions about you, your ratings and correction requests, notifications and
  activity, as one JSON file.
- **Erasure after someone leaves** (HR, on the employee's page; `POST /api/privacy/employees/{id}/erase`, once no
  nomination or pay rise of theirs is still open): the name becomes "Former employee no. X"; their ratings,
  correction requests with the evidence files, equality-monitoring data and development plan are deleted; the work
  record and the inputs saved with cycle scores and record changes are blanked; a sign-in is unlinked from the
  record; and the person drops out of every list (`Employee.left_at`). Decisions, pay steps and the hash-chained
  audit trail keep their meaning (they never held more than the id).
- **Retention** (`app/privacy/retention.py`): rating comments after 2 years, notifications after 6 months, the
  email log after a year, the activity log after 3 years; applied every morning, shown on the public Privacy page
  (`GET /api/privacy/retention`). Each period is a setting (`RETAIN_*_DAYS`).

### Signing in safely

- **Slowing down guessing** (`app/core/throttle.py`): 20 failed sign-ins from one network address in 15 minutes
  and that address waits, whichever accounts it tried; the per-account lock-out after 5 stays.
- **Two-factor sign-in** (`app/core/totp.py`, My profile): an authenticator app's six-digit code (RFC 6238) after
  the password. `REQUIRE_2FA_ROLES=hr,finance,admin` makes those roles set it up before anything else. Turning it
  off needs the password and a code, and emails the person.
- **Headers**: every API answer says no sniffing, no framing, no caching of personal data (and HTTPS only when
  served over HTTPS); the built website adds a Content-Security-Policy (`vite.config.js`, `deploy/Caddyfile`).
- **Signing out when idle** (`components/IdleSignOut.jsx`): after 30 minutes without use, a 2-minute warning, then
  the session ends on the server too.

### A second person for the riskiest actions (`app/core/approvals.py`)

With `FOUR_EYES=1`, releasing a model version, and confirming a record correction that moves someone across the
threshold, become requests (HTTP 202). Another HR person approves (the action is carried out then, with both names
in the audit trail) or declines with a reason, on the Approvals page. Nobody approves their own request, and one
request per action can be open. Rejecting the correction itself closes its waiting request. Off by default: with
one HR account nothing could ever be approved.

### Fairness in more depth

- **Model card** (`app/promotion/fairness.py`, `evaluation/fairness_detail.py`): each group's true-positive rate,
  false-positive rate and precision next to its selection rate, and the same for gender within each age group
  (groups under 30 test employees left out). The four-fifths rule on the three single characteristics still alone
  decides pass or fail. The proxy analysis's summary (can the inputs predict a characteristic?) is on the card too.
- **Live fairness** adds gender and age band combined, and **pay rises**: the average approved rise per group,
  with the 80% rule on the averages and a Mann-Whitney test before flagging a gap. Groups with fewer than 5 rises
  are never shown.
- **Before a release** (`app/governance/compare.py`, `GET /api/governance/models/{version}/compare`, HR only): the
  candidate and the live model both score today's employees; the model registry shows how many each recommends,
  who would gain or lose a recommendation, and per department. Nothing is saved.

### Development plans (`app/development/`)

Goals an employee works on with their manager, on the readiness page: one click turns a tip into a goal ("Increase
training hours to 35"), or a goal is written freely, with an optional date. The employee, their manager (or cover)
and HR add goals and tick them off; the other side is told on their bell. An admin who may view employees reads
plans. The promotion code never imports this module or names its table (`tests/test_isolation.py`), so a plan can't
change a score.

### Running it on a server

- **Migrations** (`app/core/migrations.py`, `backend/migrations/`): start-up applies every Alembic revision the
  database hasn't had. A database made before migrations existed first gets the old one-off repairs. A table change
  is a new revision (`alembic revision --autogenerate`), written with `migrations/helpers.py` so it works on old and
  new databases alike.
- **Backups** (`app/core/backups.py`, `docs/BACKUPS.md`): nightly at `BACKUP_HOUR` and by hand; the database
  (SQLite's online backup, or `pg_dump`), correction evidence and model registry, with SHA-256 checksums; the newest
  `BACKUP_KEEP` kept; restore checks everything first and keeps today's data aside.
- **Deployment** (`deploy/`, `deploy/README.md`): Docker Compose with PostgreSQL 16, the API (one process: the
  timer runs inside it) and Caddy (the website, HTTPS certificates, security headers). CI builds both images and
  checks the API answers, and runs the backend tests on PostgreSQL.
- **Logs and alerts** (`app/core/logs.py`): one line per request with an id (`X-Request-ID`), never a query string
  or body; `LOG_FORMAT=json` for a log service. An unexpected error, in a request or in the timer, is logged in
  full; the person sees a short message with its reference; admins get an email and a bell notification at most
  once an hour per kind of error, and the admin home page lists the latest.
- **Load** (`evaluation/load_test.py`): with 5,000 employees and 300 decisions, every list makes a fixed number of
  queries (at most 10) and answers in under 0.3 s; opening a cycle scores and saves everyone in about
  0.7 s. `tests/test_query_counts.py` keeps the counts flat.

### Smaller things

- **First-time guide** (`components/FirstTimeGuide.jsx`): a few steps per role on the overview, each linking to
  its page; closing it is kept on the account (`PUT /api/auth/guide`), and My profile brings it back.
- **Printable cycle report** (`/cycles/:id/report`): the cycle, totals, departments, movement and fairness with
  pay, laid out for printing or saving as PDF. HR's copy names the people recommended but not nominated; the
  auditor's has totals only.
- **The user study in the app** (Admin → User study, `app/study/`): see `docs/USER_TEST.md`.

### How it was tested

`test_privacy.py`, `test_security_hardening.py`, `test_approvals.py`, `test_migrations.py`, `test_backups.py`,
`test_logs.py`, `test_query_counts.py`, `test_development.py` and `test_study.py`, plus new cases in
`test_governance.py` (comparison, pay fairness), `test_training.py` (per-group accuracy, combinations) and
`test_isolation.py` (development plans).

## Design system

Every page is built from one small design system, so the whole interface looks and behaves the same. It is a
presentation layer only: no page's behaviour, permissions or API calls depend on it. (Overhauled in October 2026;
before and after screenshots and the page-by-page changes are in `docs/UI_REVIEW.md`.)

Code: `frontend/src/tokens.css` (every colour, size, space, radius and shadow, for light and dark),
`frontend/src/styles.css` (the components, styled once), `frontend/src/components/ui.jsx` (the shared React
components), `components/Overlay.jsx` (modal, drawer, confirm dialog), `components/Toast.jsx` and
`components/charts/BarList.jsx` (charts).

### Fonts

- **Montserrat** (variable), installed locally with `npm install @fontsource-variable/montserrat` and imported once
  in `main.jsx`. Nothing is loaded from Google's servers, so the font works offline and no visitor's address is
  sent to a third party. Fallbacks: `"Montserrat Variable", "Montserrat", system-ui, sans-serif`.
- **Type scale:** 32 / 24 / 20 / 16 / 14 / 12 px. Weights: 700 page titles, 600 section headings, 500 labels and
  buttons, 400 body. Line height 1.55 for text, 1.25 for headings.
- Body text is never smaller than 14px. Only small uppercase labels (table headings, stat labels) use 12px, capitals
  and +0.02em letter-spacing; there are no all-capital sentences.
- Scores, percentages, tables and KPI tiles use **tabular figures** (`font-variant-numeric: tabular-nums`), so
  numbers line up in columns.

### Colours

Defined once in `tokens.css`, with a light and a dark value for each name. The app follows the computer's light or
dark setting until someone uses the toggle; that choice is then remembered in the browser.

| Token | Light | Dark | Used for |
|---|---|---|---|
| `--primary` | `#1E3A5F` (navy) | `#3A73B5` | The one main action on a page; selected options |
| `--sidebar` | `#0F2A44` | `#08131F` | The sidebar, in both themes |
| `--link` | `#1D4F91` | `#8DBBF2` | Links and ghost buttons |
| `--highlight`, `--focus` | `#0B7A6E` (teal) | `#3CC4B2` | The active-menu marker and focus rings only |
| `--bg`, `--surface`, `--surface-sunken` | `#F4F6F9`, `#FFFFFF`, `#EEF1F5` | `#0B121C`, `#131E2B`, `#0F1823` | Page, cards, insets |
| `--border`, `--border-strong` | `#DFE4EA`, `#7B8696` | `#263446`, `#6C7A8C` | Dividers; form fields (3:1) |
| `--text`, `--text-muted` | `#17212E`, `#526072` | `#E6EBF2`, `#9BA9BA` | Text |
| `--success`, `--warning`, `--danger`, `--info` | `#1E7038`, `#8A5300`, `#B42318`, `#1D4F91` | `#6FD08F`, `#F2BD5A`, `#FF8F86`, `#8DBBF2` | Status, each with a tinted background |
| `--up`, `--down` | `#0B7A6E`, `#B8460B` | `#3CC4B2`, `#FF9A5C` | The model's view only: raises, lowers readiness |
| `--chart-1` to `--chart-4` | `#2A78D6`, `#EB6834`, `#1BAF7A`, `#8A95A5` | `#3987E5`, `#D95926`, `#199E70`, `#6C7A8C` | Dashboard charts, in fixed order |

Three rules keep colours meaningful:

1. **Interface, data and status colours never mix.** Teal and orange mean "raises" and "lowers" the score, so they
   are never used for a button or a link. "Not yet recommended" is neutral grey, never red.
2. **Never colour alone.** Every status badge has a word and an icon; factor lists are headed "Raised the score"
   and "Lowered the score"; every chart writes its values beside the marks and has a legend in words.
3. **Contrast.** Every text and background pair meets WCAG AA (4.5:1; 3:1 for large text and for the edges of form
   fields) in both themes. The palette was checked by script, and every page by axe-core in both themes. The chart
   palette was also checked for colour-vision deficiency: adjacent colours stay distinguishable for protanopia,
   deuteranopia and tritanopia.

### Spacing, shape and depth

- A **4px grid**: 4, 8, 12, 16, 24, 32, 48 (`--s-1` to `--s-12`). Cards have 24px padding and 24px between them.
- **Corners:** 8px for cards, inputs and panels; 6px for buttons; badges are pills.
- **One soft shadow** for raised cards, and one stronger one only for things floating above the page (menus,
  modals, drawers, toasts).
- **Motion** is subtle (150 to 200 ms fades and slides) and switched off entirely for people whose computer asks
  for reduced motion.

### Layout

- **App shell:** a navy sidebar with the menu grouped per role (Lucide icons; the current page has a lighter row
  and a teal bar), a top bar with the breadcrumb, the light/dark switch, the notification bell and a profile menu
  (My profile, Sign out), and the page in a column up to 1280px wide.
- **Widths:** from 1024px, the full sidebar (which can be collapsed to icons); from 640 to 1023px, an icon rail
  with page names on hover or focus; under 640px, a drawer opened from the top bar. No page is wider than a 390px
  phone screen; wide tables scroll inside their card.
- **Every page** has a breadcrumb, a title with a one-line description, and at most one primary action.

### Components

All in `components/ui.jsx` unless noted, and used everywhere instead of one-off styles:

| Component | What it is |
|---|---|
| `PageHeader` | Title, one-line description, the page's primary action, and an optional status beside the title |
| `Card` | A panel with a title, description and actions; `flush` for tables; `tone` to highlight (the plain-language summary, the committee note) |
| `StatCard` | A KPI tile: uppercase label, large tabular number, note |
| `Badge` | Status in words with an icon (neutral, success, warning, danger, info, and "up" for the model's view) |
| `Button` | `primary`, `secondary`, `ghost`, `danger`; `sm` and `lg` sizes; a busy state with a spinner. Disabled buttons stay readable |
| Inputs, selects, textareas | One style; a visible 3:1 border; a teal focus ring; hints and problems under the field |
| `Segmented` | Tabs: one row of toggle buttons, one chosen |
| Tables | Sticky header, hover rows, right-aligned numbers (`.num`), `SortHeader` with sort arrows and `aria-sort`, `Pager` |
| `Modal`, `Drawer`, `useConfirm` (`Overlay.jsx`) | Panels over the page: Escape closes them, Tab stays inside, focus returns to the opener. The confirm dialog replaces the browser's own box |
| `useToast` (`Toast.jsx`) | A short confirmation in the corner after an action |
| `Callout` | A message in the page (info, success, warning, error), always with an icon |
| `EmptyState` | An icon, a title and what will appear here |
| `Loading`, `PageLoading` | Skeleton placeholders while something loads, announced once to screen readers |
| `LoadError` | What went wrong in plain words, with a "Try again" button |
| `Gauge`, `Verdict` (`promotion/ScoreBar.jsx`) | The readiness score as a half-circle meter with the threshold marked, and "Recommended" or "Not yet recommended" |
| `BarList`, `Meter`, `StackedBar` (`charts/BarList.jsx`) | Charts in one style: thin rounded bars, values written out, legends in words, no 3D |

### Keyboard and screen readers

- A visible focus ring on everything that can be focused, and a "Skip to the page" link first in the tab order.
- Escape closes the profile menu, the notifications, modals, drawers and the phone menu; focus goes back to the
  button that opened them.
- Every icon-only button has an `aria-label`; decorative icons are hidden from screen readers.
- Loading states are announced once (`role="status"`), errors immediately (`role="alert"`).

## Updates after step 7

### Notifications

A bell at the top right shows what needs attention.

- **HR** is told about record corrections waiting and pay rises Finance sent back.
- **Finance** is told about pay rises waiting for sign-off.
- **Employees** are told when HR decides on a correction they asked for (step 9).

### Welcome emails and account changes

- The admin must give each new account an **email address**. Creating the account sends a **welcome email** with
  the sign-in link, username and temporary password. Without a mail server
  configured, the email is saved to `backend/instance/outbox/` instead, and the admin is told which happened.
  Resetting a password emails the new temporary password the same way. (See "Emails" below for the other emails.)
- The admin can **edit** an account's username, name and email (`PATCH /api/admin/users/{id}`); usernames and
  emails must be unique.
- Everyone can change their own **username** (confirming with their password) and **password** on the
  **My account** page. New accounts are sent there first, to replace the temporary password.
- Note for the thesis: emailing a temporary password is common practice, but email isn't secret. That's why the
  password is temporary and must be changed at first sign-in.

### Emails

Code: `app/core/mailer.py` (sending), `app/core/email_templates.py` (what each email says),
`app/accounts/contacts.py` (who HR is), and the admin page `frontend/src/pages/admin/Email.jsx`.

- **Sending.** The app connects to the mail server with `smtplib` and STARTTLS. With Gmail, that is
  `smtp.gmail.com:587` and an **app password**, which is a separate 16-letter password that can be revoked
  without touching the account password. The settings are read from `backend/.env`, which is kept out of git. The
  admin's Email page shows whether email is set up, but never shows the password.
- **Every email has two versions:** plain text, and a simple branded HTML version. Mail apps show whichever they
  support.
- **Which emails are sent:**

| Email | Trigger | Recipient |
|---|---|---|
| Welcome / password reset | Admin creates an account or resets a password | The person |
| Security alert | Password or username changed (by the person or the admin) | The person; it never contains the password |
| Nomination received | A manager nominates someone | All active HR accounts |
| Decision | HR decides | The manager (with HR's reason), and the employee if approved; rejections aren't emailed to the employee |
| Correction waiting | An employee asks for a record correction | All active HR accounts |
| Correction decided | HR confirms or rejects it | The employee, with HR's reason |

- **Background sending.** Emails are sent after the response has gone back, so a slow mail server never delays
  the page. Welcome and reset emails are the exception: they are sent straight away, so the admin sees whether
  delivery worked.
- **Without a mail server**, every email is saved as an `.eml` file in `backend/instance/outbox/`, and the admin
  can read these on the Email page. The tests use this to check each email's content.

### A tidier menu

The sidebar groups pages under headings (Promotion, Feedback, Administration, Account) that open and close when
clicked; the group holding the current page opens by itself.

### The public website

Visitors who aren't signed in see a small website (`frontend/src/pages/public/`), sharing one menu bar and footer
(`PublicLayout.jsx`). Only the landing page and sign-in are downloaded straight away; the other pages load when
first opened.

| Page | Address | What it shows |
|---|---|---|
| Home | `/` | The promise ("Fair, explainable promotion decisions, with a voice for every employee"), **Sign in** and **How it works**, **How it works** (Predict → Explain → Respond), six features, three promises (a complaint never changes a score; a wrong record can be put right; people make every decision), and the tested results, read live from `results/` through `GET /api/public/summary` |
| Who uses it | `/approach` | The six roles: what each sees and does |
| Promotions | `/promotion` | How a decision is made, from the model's score to Finance's sign-off (with the live threshold) |
| Privacy | `/privacy` | What is stored and what isn't, including that feedback never changes a score |
| Book a demo | `/demo` | A short form (see below) |

The footer shows the project title, and the university, team and supervisors once they are filled in
(`PROJECT` in `frontend/src/brand.js`); nothing is invented.

- **Screenshots** (`frontend/public/landing/*.webp`) are of the real app with made-up demo data, retaken with
  `python scripts/browser_test.py scripts/capture_landing.js`.
- **No stock photos and no testimonials.** A made-up quote would be invented evidence.
- **Every number is measured.** If a result isn't available, the page shows "–", never an example number (a test
  checks the public pages for invented numbers).

## Step 8: The activity log, and all the tests

### The activity log

Code: `backend/app/core/activity.py` (the table and `record()`), `GET /api/admin/activity`, and the admin page
`frontend/src/pages/admin/ActivityLog.jsx`.

Important actions are recorded with **who** did them, **what**, and **on which day**:

| Area | Recorded |
|---|---|
| Signing in | Every sign-in; failed sign-ins on accounts that exist |
| Own account | Password changed, username changed (old → new), profile updated (which details, not their values) |
| Administration | Account created, edited, deactivated or reactivated; password reset; a manager's team set; an admin allowed or no longer allowed to view employee data |
| Employee records | An employee added or edited by HR; employees imported from a file (how many) |
| Promotions | A nomination (by the manager), a decision (by HR, and whether it differed from the model) |
| Feedback | A correction requested, confirmed or rejected; a decision held or resumed |

Only the **admin** can read the log, with a filter by action and a search box.

**What is deliberately not recorded:**

- **Times.** Entries keep only the **date**: an audit needs to know what happened and when, not people's
  working habits.
- **Passwords**, temporary or not (a test checks this too), and sign-in attempts on usernames that don't exist.

**The trade-off to discuss.** Logging every sign-in, even by date only, still shows who was active on a given day.
Two ways to reduce this further: log sign-ins only for the privileged roles (HR and admin), whose access matters
most for security, or keep sign-in records only as daily counts. This project follows the brief (log sign-ins) and
keeps dates only; the alternatives are worth discussing as future work.

### All the tests

Run them with `cd backend` then `.venv\Scripts\python -m pytest`. There are **400 tests**, all passing, in about three
minutes (the tests hash passwords with fewer rounds than the app; a test checks the app's own setting):

| File | Tests | What they prove |
|---|---|---|
| `test_auth_and_roles.py` | 26 | Passwords are hashed with a salt (200,000 rounds in the app); sign-in; wrong password and unknown user look the same; 5 wrong passwords lock an account for 15 minutes; tokens stop working after a password change, reset or sign-out; only the admin manages accounts; deactivation locks people out at once |
| `test_training.py` | 19 | Protected characteristics, pay and department are never model inputs; the 70/10/20 split; the model-choice rule with the common-sense check; the threshold; the four-fifths fairness check; the saved threshold and metrics load |
| `test_explanations.py` | 29 | The contributions add up exactly to the model's output; department never changes a score; improving any input never lowers it; LIME and its fit; the summary ("under 1%" for tiny scores); what-if changes only improvable inputs and saves nothing; tips never suggest making anything worse; batch scoring gives identical scores; who may see whom |
| `test_decisions.py` | 18 | Managers nominate only their team; HR decides; disagreeing with the model needs 20 characters; every decision is logged with the model's view; managers' teams |
| `test_feedback.py` | 28 | Rating explanations (stored with the model version and score; never changes a score; aggregates only, never managers); record corrections (only record values; evidence; HR confirms with a re-score and a log entry, or rejects with a reason; notifications); employees can't edit records; the committee note and hold |
| `test_isolation.py` | 5 | **Isolation**: every prediction answer byte-for-byte identical after ratings, corrections and a held decision; a confirmed correction changes it and is logged; the static check (feedback, equality monitoring and development plans); no SQL on those tables at run time |
| `test_dashboards.py` | 24 | The feedback dashboard's measures, filters, small-group protection, CSV and export script; only HR and the auditor see it; drift and its chance level; the admin's system health |
| `test_auditor.py` | 12 | The compliance auditor reads decisions and the model; never individual feedback, records or changes; demo-account rules |
| `test_finance.py` | 20 | An approval waits for Finance and nobody is told; a rejection never goes to Finance; Finance sees only what a pay decision needs; sign-off makes the promotion final and emails the manager and employee; sending back needs a reason and tells only HR; HR revises and resubmits; every step is kept; only Finance signs off and only HR resubmits; managers see "being finalised" until sign-off |
| `test_accounts_and_notifications.py` | 10 | The first-time guide; welcome emails; editing accounts; changing your username; the public summary reveals no one and shows only measured numbers |
| `test_emails.py` | 12 | Security alerts; nomination and decision emails go to the right people; only the admin uses the Email page; every email has plain and HTML versions |
| `test_employee_records.py` | 24 | HR adds an employee who can be scored at once; values are stored as the model expects; impossible values are refused and unusual ones flagged; no one is added twice; one bad CSV row means nobody is imported; no protected characteristics are accepted; only HR manages records |
| `test_demo_requests.py` | 10 | Anyone can book a demo; it's emailed with Reply-To set to the visitor; the admin lists and ticks off requests; robots and repeats are kept out; visitors' text can't inject HTML; only the admin sees requests |
| `test_profiles_and_permissions.py` | 15 | People update their profile (an email change alerts the old address; only small images as photos); Admin and HR accounts can't be linked to employee records; an admin sees employee data only once allowed, read-only, never feedback; managers are emailed about new team members, and only about new ones |
| `test_evaluation_data.py` | 2 | The usability questionnaire and the perceived-fairness scales (with Cronbach's alpha) are scored correctly |
| `test_recommendations_and_pay.py` | 16 | Managers' recommendations need a rating and example for all four areas, a start date within a year, a rise within HR's policy, and a reason when the model disagrees; HR must set the rise on approval and explain one outside the policy; only HR sets the policy; employees see only their approved promotion; pay is not a model input and changes no prediction |
| `test_accounts_categories.py` | 10 | The admin deletes accounts (never their own, never one in the decision log), a deleted account can't sign in, a deleted manager's team stays in the directory; job titles on new accounts and in the welcome email |
| `test_activity.py` | 9 | Sign-ins and actions are logged by date; passwords never are; only the admin reads the log; a database from the version with reporting is cleaned up |
| `test_calibration.py` | 7 | The calibration measures recognise known cases (perfect, over-confident, too high everywhere); the live model is well calibrated on the test set; the model card shows it |
| `test_cycles.py` | 14 | Opening and closing review cycles, saved scores, re-scoring after a record change, no release while a cycle is open, the CSV export, the auditor's totals only |
| `test_teams.py` | 7 | HR's teams and the queue without a manager; a branch seen read-only, only the own manager nominates; no loops; cover for its dates |
| `test_email_delivery.py` | 10 | Every email logged and on the bell; retries, then resending, content dropped once delivered; daily digests never hold account emails; reminders sent once; working days |
| `test_finance_operations.py` | 6 | Bulk sign-off, the cycle filter, the payroll hand-over |
| `test_governance.py` | 28 | The audit trail's chain; the model registry and human release; blocked models; what a release would change; live fairness at three stages, combinations and pay; the data mapping |
| `test_sessions.py` | 5 | The website gets a cookie, never the token; API clients get a token; the cross-site header; signing out; a password change renews the cookie |
| `test_privacy.py` | 3 | Your data as one file; erasure of someone who has left; retention |
| `test_security_hardening.py` | 5 | Security headers; slowing down guessing per address; two-factor sign-in; a role made to use it; the code standard (RFC 6238) |
| `test_approvals.py` | 5 | The four-eyes rule: off changes nothing; a release and a threshold-crossing correction wait for a second HR person; nobody approves their own; declining needs a reason; rejecting a correction closes its request |
| `test_development.py` | 3 | Development plans: built and ticked off by employee and manager, the other side told, the score unchanged; only the people concerned; part of your data, erased with you |
| `test_migrations.py` | 5 | A new database is built by the migrations; an older one keeps its data and gets new columns; later migrations apply; running twice changes nothing; every table is known |
| `test_backups.py` | 4 | A backup holds the database and a manifest; only the newest are kept; a damaged one is refused; a restore brings data back and keeps today's aside |
| `test_logs.py` | 4 | Every answer has a request id; an unexpected error is reported and alerts admins once; JSON logs; timer failures alert |
| `test_query_counts.py` | 1 | Lists make the same number of queries for 4 rows or 40 |
| `test_study.py` | 4 | The user study inside the app: sessions by code; the link needs consent and stops when finished; answers 1–5; saving writes the files the analysis reads, with its report |

How each requirement in the brief is tested:

| Requirement | Where |
|---|---|
| Roles: each role can only access what it should | `test_auth_and_roles`, plus a "who may see this" test in every other file |
| Model: threshold and metrics load; the fairness check runs | `test_training` |
| Explanations: contributions add up; tips never make a feature worse | `test_explanations` |
| Isolation: prediction code never reads feedback tables; predictions unchanged by feedback | `test_isolation` |
| Feedback channel: ratings, corrections, committee note and hold | `test_feedback` |

Besides the automated tests, `python scripts/browser_test.py` runs 11 checks in headless Chrome against a throwaway
copy of the app (including every menu page for all six roles and the feedback channel end to end), and CI runs
everything on every push (`.github/workflows/ci.yml`).

## Running the prediction, and feedback while the system works

**"Run prediction".** Opening an employee's readiness page no longer runs the model by itself. The page shows who
the employee is and a **Run prediction** button, with which model will run and when it was trained. Clicking it
runs the model in three real steps, each its own request to the server, so what the screen shows is what is
happening:

1. **Scoring the record with the model** and working out each factor's exact contribution
   (`POST /api/promotion/employees/{id}/predict`). The score and explanation appear as soon as this finishes.
2. **Checking with a second method**: LIME (`POST /api/promotion/employees/{id}/lime`).
3. **Finding realistic tips** (`GET /api/promotion/employees/{id}/tips`).

Each step shows as waiting, running (spinning) or done (with how long it took). "Run again" repeats it. Nothing is
saved; the model only advises. Two tests check that the step-by-step result is identical to the all-at-once one
and that the steps follow the same access rules. (Lists and the overview still show scores straight away, as a
summary; the full prediction and its explanation are run from the readiness page.)

**Buttons show that the system is working.** Every button lifts slightly when pointed at and presses in when
clicked. Buttons that wait for the server (signing in, creating accounts, nominating, deciding, sending a correction
request, saving) show a spinning icon and say what is happening ("Signing in…", "Sending…") until the
answer arrives, and can't be clicked twice meanwhile. People whose computer asks for reduced motion get no
animation.

**Light and dark.** Both themes use the same colour names, so every page, including the public website, works in
both; switching fades smoothly instead of flashing.

## Adding real employees (one at a time, or from a CSV file)

The demo directory holds 120 employees from the synthetic dataset. HR can add more on **All employees** with
two buttons. Code: `backend/app/promotion/records.py` (the checks), `routes_records.py` (the API, HR only), and
the pages `EmployeeForm.jsx` and `ImportEmployees.jsx`.

**Where the data comes from.** In a real organisation nobody invents these numbers: they already exist in HR's
systems. Performance scores and ratings come from the annual review; KPIs, projects and tasks from project or KPI
tracking; training, certifications and mentoring from training records; attendance and late days from time and
attendance; years in role and since promotion from the HR record. HR exports them, usually as a spreadsheet.

- **Add employee** is a form grouped as Performance, Development, Reliability and Career. Values are typed the way
  HR's records show them: this year's **and** last year's performance score (the system works out the change the
  model uses), and rates such as attendance as everyday percentages (93, stored as 0.93 like the training data).
- **Import** takes a CSV file (what Excel and HR systems export). HR downloads a template with the right columns,
  fills it in and chooses it; every row is checked and the problems shown per line. Nothing is saved until HR
  clicks Import, and **if any row has a problem, nobody is imported**, so a file is never half-imported.
- **Edit details** on an employee's readiness page updates their record, for example after a new review. Past
  decisions keep the score they were made with (it was saved in the decision log).

**Two kinds of check.** *Errors* are impossible values (a rating of 7 out of 5, negative late days, 2.5
certifications, an unknown department) and stop the save. *Warnings* are possible but outside what the model saw
in training (say 600 training hours): the employee is saved, but HR is told the score is less reliable there,
because the model would be guessing beyond its experience. The same person (same name and department) can't be
added twice, which also stops the same file being imported twice.

**What is never asked for:** gender, age, education, marital status and pay. The model doesn't use them, so the
system doesn't collect them (a test checks they're ignored even if sent).

**A new employee can be scored at once**, because the model only needs their inputs. After saving, HR lands on
their readiness page and clicks Run prediction; and the admin can link them to a login on the Users page.

**Scoring a person is not the same as learning from your organisation.** The model learned what "ready for
promotion" looks like from synthetic employees. For real use, an organisation would export its own history (past
employees' records **and** whether they were promoted), point `train.py` at that file, and use the model only if
the four-fifths fairness check passes on its own people. Adding employees here gives them a score from the current
model; it doesn't retrain it.

## Colours: navy and teal

The palette is now part of the design system: see **Design system → Colours** above.

## Book a demo

Code: `backend/app/demo/` (the table and API), `frontend/src/pages/public/BookDemo.jsx` (the form) and
`frontend/src/pages/admin/DemoRequests.jsx` (the admin's list). Tests: `tests/test_demo_requests.py`.

- **The form** asks for a name, work email, organisation, optional job title, number of employees, what they're
  interested in, and an optional message. No sign-in is needed.
- **What happens:** the request is saved, and emailed to `DEMO_INBOX` in `backend/.env` (if that's empty, the
  Gmail address that sends the platform's emails). The email's **Reply-To** is the visitor, so pressing Reply
  answers them directly. The admin also sees every request under **Administration → Demo requests**, and ticks
  each one off once it's been answered.
- **Keeping robots out, simply:** a hidden "website" box that people never see but form-filling robots fill in
  (such requests are thanked and quietly dropped), at most 3 requests per email address per day, and at most 30
  in total per hour. No IP addresses are stored, in keeping with the rest of the platform.
- Whatever a visitor types is shown as plain text in the email, never as HTML (a test checks this).

## Accounts, profiles and permissions

### Two kinds of account

The admin's **Users** page has two tabs, each with its own list and create form:

| Tab | Roles | Linked to an employee record? |
|---|---|---|
| Administration | Admin, HR | No: the server refuses to link one, because these accounts run the platform rather than being assessed by it |
| Employees | Employee, Manager | Yes (needed for an employee to see their own readiness); managers also get a team |

### Admins who may view employee data

By the brief, admins manage accounts and see no employee data. Sometimes an organisation needs an administrator
to look at the data (for example an IT lead supporting HR). An admin can tick **Allow employee data** on a
specific Admin account. That account then gets an "Employee data" menu with **All employees** and **How the
model works**, read-only: it can open readiness pages and run the prediction, but it can't nominate, decide, edit
records, or see anyone's feedback. The rule is checked on the server (`may_view_all()` in
`app/promotion/routes.py`), every grant and removal is in the activity log, and HR, managers and employees can't be
given it (they already see what their role needs).

### My profile

Everyone has a **My profile** page (`frontend/src/pages/Account.jsx`):

- **Your details:** name, email, phone and job title, plus a photo. The photo is cropped to a square and shrunk to
  256 pixels **in the browser**, so only a few kilobytes are stored (the server accepts only small PNG, JPEG or WebP
  images). Changing your email sends an alert to the **old** address, so someone who took over an account can't
  quietly redirect its emails.
- **Work details** (read-only): role, username, department, employee number, manager, team size for managers,
  and for admins whether they may view employee data.
- **Sign-in and security:** password and username, as before. A brand-new account sees only the password step
  until it has chosen its own password.

### Managers hear about new team members

A manager is emailed whenever people are registered under them: when the admin adds people to their team (only
the people who are new to it), when HR adds an employee with them as manager or moves someone to them, and when a
CSV import puts people on their team (one email per manager, listing everyone). The email contains names only, no
scores or records.

## Recommendations with reasons, and the pay rise

### Who does what

| | Does |
|---|---|
| The model | Gives each employee a readiness score and says whether it recommends promotion. It never nominates or decides. |
| The manager | **Recommends** someone on their team, with stated reasons (below). |
| HR | Reviews the recommendation beside the model's view, **decides**, and sets the final pay rise. |

### The manager's recommendation

On a team member's readiness page, a manager fills in (`NominateBox.jsx`; checked again on the server in
`routes_decisions.py`):

- the **proposed new role** and **start date** (between today and a year from now);
- a **rating from 1 to 5 with a real example** for each of four areas: performance, leadership, skills and
  knowledge, and impact. Every area is required, so a recommendation can't rest on one vague sentence;
- an **overall recommendation**;
- if the model **doesn't** recommend the person, **why the manager disagrees** (at least 20 characters), the
  same rule HR follows when it disagrees;
- a **proposed pay rise** as a percentage, within HR's policy.

HR's review page shows all of it: the facts, the ratings (as dots *and* words, never colour alone), the examples
and both reasons, next to the model's score and explanation.

### The pay rise

Promotions usually come with a pay rise, but pay is sensitive, and the brief keeps it out of the model. So:

- **Only percentages are stored, never salaries.** The rise is a percentage on the nomination (proposed) and on
  the decision (approved). No salary amounts are entered anywhere.
- **HR sets a pay policy**, a range such as 5% to 15% (on the Nominations page). Managers must propose within it.
  HR sets the final figure when approving, and can go outside the range only with a written reason (at least
  20 characters), which is kept in the decision log. Changing the policy is recorded in the activity log.
- **Who sees it:** HR sees every rise; a manager sees the ones on their own recommendations; an employee sees
  their own only once approved (on My growth, and in the approval email, with the new role and start date).
  Pending recommendations are not shown to the employee.
- **The model never sees pay.** Pay isn't one of the model's inputs, and approving a rise changes no prediction;
  two tests check this.

**A limit worth stating:** because the platform deliberately doesn't store gender, age or other protected
characteristics with employee records, it can't check whether pay rises are fair across groups. An organisation
would do that check in its HR system, which holds that data, or by extending the fairness checks with consent.

## Deleting accounts, job titles and outlines

**Deleting accounts.** The admin can delete an account on the Users page (after a confirmation), except:

- **their own** account, so there is always an admin left;
- an account that appears in the **promotion decision log** (it recommended someone or decided on a promotion).
  Deleting it would erase who made those decisions, so the page says to **deactivate** it instead: it can no
  longer sign in, but the record stays.

When an account is deleted, a manager's team members stay in the directory without a manager, and activity-log
entries keep the person's name. The deletion itself is logged.

**Job titles.** The admin enters a job title when creating an account (optional), can change it when editing, and
it appears in the user list and the welcome email ("…created an account for you as Payroll Officer"). People can
also update their own on My profile.

**Outlines.** Panels, tab groups and the sidebar have a thick (2 px), dark slate outline (`--frame` in
`styles.css`), in both themes, so each section stands out clearly.

## Finance: signing off promotion pay rises

Code: `backend/app/promotion/routes_finance.py`, the resubmit endpoint and `tell_about_promotion` in
`routes_decisions.py`, the `pay_reviews` table and `Decision.pay_status` in `models.py`, and the page
`frontend/src/pages/finance/PaySignOff.jsx`.

**A fifth role.** Finance accounts are Administration accounts, like admin and HR: they aren't linked to an
employee record. The admin creates them on the Users page. A demo account `finance` (Fay Finance) is created on a
new, empty database.

**How it works.**

1. HR approves a promotion and sets its pay rise (step 5). The rise is now **with Finance**, and Finance is
   emailed. Nobody else is told yet: the manager's list shows "Being finalised", and the employee sees nothing.
2. Finance reviews it on **Pay sign-off** and either:
   - **signs it off** (an optional note). The promotion is now final: the manager and the employee get their
     emails, and the employee sees the new role and pay rise; or
   - **sends it back to HR** with a reason of at least 20 characters (for example, a budget that is already
     committed). Only HR is told.
3. HR sees "Sent back by Finance" (in the bell, the nominations list and the review page), revises the pay rise
   or keeps it, answers Finance's note, and resubmits. The same policy rule applies: outside the range needs a
   written reason.

A rejection is final at once and never goes to Finance. Promotions approved before Finance sign-off existed are
shown as they were.

**The audit trail.** Every step is a row in `pay_reviews` (sent to Finance, sent back, resubmitted, signed off),
with who, when, the percentage at that step and any note. Rows are never changed or deleted, and the names are
kept even if an account is later renamed or deleted. HR and Finance both see this history as a timeline, and the
activity log records each step.

**What Finance sees, and why.** Only what a pay decision needs: the employee's name and department, the new role
and start date, the pay rise HR approved and the one the manager proposed, the pay policy, and HR's reason if the
rise is outside the policy. Finance does **not** see the model's score, the manager's ratings and examples, or the
reasons for the promotion: whether someone deserves a promotion is HR's decision, and Finance's part is its cost.
Finance can read the pay policy but not change it. As everywhere, only percentages are used, never salaries.

**Finance's page** shows what is waiting, what was sent back, how many rises were signed off this year (and how
many were outside the policy), the average rise, and a breakdown by department.

| Endpoint | Who | What |
|---|---|---|
| `GET /api/finance/pay-reviews` | Finance | Every pay rise with Finance, sent back or signed off, with a summary |
| `POST /api/finance/pay-reviews/{id}/sign-off` | Finance | Sign off (optional note); tells the manager and employee |
| `POST /api/finance/pay-reviews/{id}/return` | Finance | Send back to HR with a reason (20+ characters) |
| `GET /api/finance/pay-policy` | Finance | Read the pay policy |
| `POST /api/promotion/decisions/{id}/resubmit` | HR | Revise a returned pay rise and send it back to Finance |


## Step 9: The employee feedback channel (respond)

Code: `backend/app/feedback/` (`routes.py` for employees, `routes_hr.py` for HR, `corrections.py`, `models.py`),
and `frontend/src/components/feedback/`, `frontend/src/pages/feedback/`.

The platform follows one cycle: **predict → explain → respond**. Steps 2 to 5 cover predicting and explaining;
this step covers responding. **Nothing here changes a score**, except HR confirming a record correction against
evidence, which is logged.

### Two routes on "My growth"

Below the explanation, an employee finds **Respond to this explanation**:

1. **Rate this explanation.** "This explanation was clear" and "This explanation was useful", each 1 to 5 (radio
   buttons labelled Disagree to Agree). Optionally, any factor can be marked "seems wrong" or "seems unfair", with a
   comment. The rating is stored with the model version and the score it explained, both worked out on the server.
   Rating the same model's explanation again replaces the earlier rating. `POST /api/feedback/ratings`.
2. **Correct my record.** The employee picks a value from their own record (the 20 values HR types in; nothing
   protected is even stored), enters the value they believe is right, and gives evidence in words, optionally with
   a PDF, JPEG or PNG (up to 10 MB, recognised by its contents, stored under a random name). One request per value
   at a time. The page lists their requests and HR's decisions. `POST /api/feedback/corrections`.

A confidential route for reporting an unfair assessment was built in an earlier version and removed to keep the
scope focused; it is future work (`docs/future-work/`).

### HR's correction queue

**Record corrections** (`/corrections`) lists waiting requests, oldest first, with the value in the record, the
value asked for, the evidence and any document. HR either:

- **confirms** with the value they verified (which may differ from the one asked for). Only that value changes;
  the employee is re-scored; the record history (step 3) keeps who, the old and new value, the reason, readiness
  before and after, and the model version; the activity log records it; or
- **rejects** with a reason of at least 20 characters, which the employee receives.

Either way the employee gets an email and a notification in the bell.

### The committee note, and holding a decision

While a correction is pending for someone with a nomination, HR's review page shows a **committee note**: the
value in question and that the score may change. HR can **hold the decision** until the correction is resolved;
the decision form is hidden meanwhile. A hold is not a decision, so it never appears in the decision log and never
counts as agreeing or disagreeing with the model. It lifts by itself when the correction is decided, or HR can
take it off hold. Managers never see the note.

### Who sees what

| | Employee | Manager | HR | Auditor |
|---|---|---|---|---|
| Their own ratings and requests | yes | – | – | – |
| Ratings | – | never | totals only | totals only |
| Correction requests and evidence | their own | never | all | totals only |
| Committee note | – | never | yes | – |

### Keeping feedback away from the model

- The feedback code may call the promotion code (a confirmed correction re-scores the employee), but **the
  promotion code never imports, names or queries feedback**. A static check reads every file in
  `app/promotion` and fails if it does.
- At run time, a test records every SQL statement the prediction endpoints run and checks none touches a feedback
  table.
- End to end, `tests/test_isolation.py` records every prediction answer (as HR, the manager and the employee see
  it, the tips, a what-if and everyone's scores), then adds a harsh rating, a pending and a rejected correction,
  and a decision held for the correction.
  Every answer must be **byte-for-byte identical**. Then HR confirms a correction: the explanation must change,
  with the change in the record history and the activity log.
- **No automatic retraining.** Nothing in the app trains a model; only `train.py`, run by a person.

## Step 10: Dashboards and system health

### The feedback dashboard (HR and the auditor)

`/feedback`, computed on the server from the database (`backend/app/feedback/dashboard.py`):

- **Explanations:** ratings; the share rating "clear" 4 or 5; the share rating "useful" 4 or 5; how often each factor
  is contested (marked wrong or unfair), as a sorted bar list.
- **Record corrections:** received, confirmed, rejected, pending; the confirmation rate (of decided requests); the
  mean time from request to decision.
- **The committee:** decisions, how many went against the model, and their written reasons.

Filters: date range, department and model version; **Export CSV** gives the same numbers. Small groups are
protected: rates are withheld below 5 ratings, counts of 1 or 2 show as "<3", and only departments with at least
5 people can be chosen. It never shows a name, a comment or one person's rating.
`python -m evaluation.export_feedback_measures` saves the same measures for the thesis.

### The admin's dashboard

The admin's home (`GET /api/admin/system`): active, locked and new accounts; accounts by role; quick actions
(create a user, reset a password, the audit trail, email); recent activity; and **system health**: the API, the
model (version, training date, a timed test prediction), the fairness gate's last result, email settings, and
**drift**.

**Drift** compares each input in today's directory with the training sample, using the population stability index
(PSI; below 0.1 stable, above 0.25 a large shift). PSI is noisy for small groups, so each input is also compared
with the PSI that chance alone gives a group of that size (from random samples of the training data), and counts
as shifted only above both. With 20 inputs checked at the 95% level, about one may cross that line by chance; the
page says so. The model is never retrained automatically.

### The other home pages

HR sees corrections waiting (with links to the queue and the dashboard); the employee a "Respond to your
explanation" card with their requests; the auditor how many explanations were rated clear; Finance the pay rises
waiting; managers their team and nominations.
