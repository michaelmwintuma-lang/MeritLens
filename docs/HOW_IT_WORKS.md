# How It Works

A plain-English explanation of every part of the system and why it was built that way. One section is added per
build step.

## Step 1: Accounts, signing in and roles

### What it does

Every person who uses the platform (except anonymous reporters) has an account with a username, a password and
exactly one **role**: Employee, Manager, HR or Admin. The role decides what they can see and do.

| Role | Can do |
|---|---|
| Employee | See their own readiness score, explanation and tips; submit an anonymous report |
| Manager | See their team's scores; nominate team members |
| HR | See all employees; decide on nominations; handle anonymous reports |
| Admin | Create accounts; view the activity log |

Only an **admin** can create accounts, for any of the four roles. Nobody can sign themselves up. A new account
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
backend/app/reporting/  (step 6 onwards) anonymous reports
```

Promotion and reporting will be **separate packages with separate tables**. The promotion code will never
import anything from the reporting package, and a test will prove that report data can't reach the model.

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

The model only sees **performance and development** information (21 inputs, listed in
`app/promotion/features.py`):

| Group | Inputs |
|---|---|
| Performance | performance score, change in performance since last year, manager rating, peer feedback, KPI achievement, projects completed, tasks completed, deadline adherence, innovation, leadership, problem solving, skill assessment |
| Development | training hours, certifications, cross-department projects, mentoring sessions |
| Reliability | attendance rate, late days |
| Career stage | years since last promotion, years in current role |
| Where they work | department |

Every other column is left out **with a written reason** (the `EXCLUDED` list in `features.py`, checked by a
test so no column is forgotten):

- **Protected characteristics** (gender, age, education, marital status) are never model inputs. Gender, age and
  education are kept aside only to check fairness afterwards.
- **Pay** (salary, raises, bonus, stock) records how someone has already been valued, and could carry old pay
  gaps into promotion decisions.
- **Attitude surveys** (engagement, job satisfaction) measure how someone feels, not how they perform.
- **Working hours** (monthly hours, overtime, meetings, remote ratio) would reward long hours rather than
  results, and disadvantage people with caring duties.
- Where someone lives (city tier), team size, contract type and tenure at the company are not about the work.

**Why "change since last year" instead of three yearly scores.** The dataset has performance scores for this
year, last year and two years ago. They move together very closely, so a linear model given all three splits
their effect in confusing ways (for example a large positive weight on one year and a large negative weight on
another), which would make the explanations misleading. Two clearer facts replace them: this year's score, and
how much it changed since last year.

### The three parts of the data

| Part | Size | Used for |
|---|---|---|
| Training | 70,000 | Fitting the models |
| Validation | 10,000 | Choosing the model and the decision threshold |
| Test | 20,000 | Measuring the final model, **once**, at the very end |

The split is **stratified** (each part has the same 10% promotion rate) and fixed with `random_state=42`, so
it's the same every run. Keeping the test set untouched until the end means the reported results are an honest
estimate of how the model does on employees it has never seen.

### Three models, one chosen

| Model | Validation PR-AUC | Validation ROC-AUC |
|---|---|---|
| **Logistic Regression** (chosen) | **0.6323** | **0.9261** |
| XGBoost | 0.6259 | 0.9220 |
| Random Forest | 0.6134 | 0.9220 |

- **Logistic Regression** gives each input one weight, so its predictions are easy to explain.
- **Random Forest** and **XGBoost** combine hundreds of decision trees; they are often more accurate but
  harder to explain.

Because only 10% were promoted, each model gives the rare "promoted" cases more weight (**class weights**)
rather than copying them (oversampling), which would show the model the same people many times.

**How the model is chosen.** The models are compared by **PR-AUC** (area under the precision-recall curve) on the
validation set. PR-AUC is used because it focuses on how well the model finds the rare promoted employees;
accuracy would look good even for a model that never recommends anyone (90% correct). The rule: if Logistic
Regression is within 0.01 of the best model, choose it because it is the easiest to explain. Here it was
simply the best of the three, so it was chosen outright.

### The decision threshold

The model gives each employee a score between 0 and 1. The **threshold** is the cut-off above which the model
recommends promotion. It is chosen on the validation set as the value with the best **F1 score** (a balance
between precision and recall): **0.7887**.

Why so high? Class weights make the model treat promoted employees as more important, which pushes all scores
upwards. So the score is a **ranking of readiness, not a probability**: a score of 0.79 doesn't mean a 79%
chance of promotion. What matters is whether a score is above or below the threshold, and by how much.

### Results on the test set (measured once)

| Measure | Result | Meaning |
|---|---|---|
| ROC-AUC | 0.9295 | How often a promoted employee is ranked above a non-promoted one (0.5 = coin flip) |
| PR-AUC | 0.6325 | How well promoted employees are found (random guessing: 0.10) |
| Accuracy | 0.9101 | Share of all employees classified correctly |
| Precision | 0.5418 | Of those the model recommends, the share actually promoted |
| Recall | 0.6550 | Of those actually promoted, the share the model recommends |
| F1 | 0.5930 | Balance of precision and recall |
| Share recommended | 12.1% | Close to the real 10% promotion rate |

Confusion matrix (20,000 test employees): 1,310 correctly recommended, 1,108 recommended but not promoted, 690
promoted but not recommended, 16,892 correctly not recommended.

Curves: `results/roc_curve.png` and `results/pr_curve.png`.

### Fairness check (four-fifths rule)

For each group the script measures the **selection rate**: the share of the group the model recommends. The
**four-fifths rule**, a common test for unfair impact, requires every group's rate to be at least 80% of the
highest group's rate. If any check fails, the script prints a warning and does **not** save the model as the
live model.

| Attribute | Selection rates | Ratio (lowest / highest) | Result |
|---|---|---|---|
| Gender | Female 12.3%, Male 11.9% | 0.969 | Pass |
| Age group | Under 40: 12.2%, 40+: 12.0% | 0.982 | Pass |
| Education | Bachelor 12.0%, Master 12.2%, PhD 12.9% | 0.926 | Pass |

The model passed, so it was saved as the live model (`backend/models/model.joblib`, with its threshold and
inputs in `model_info.json`). `results/fairness.json` also records each group's real promotion rate for
comparison.

### How it was tested

`backend/tests/test_training.py` (12 tests) checks that:

- protected characteristics and pay are never model inputs, and every column is either used or excluded with a
  reason;
- the performance-change feature is calculated correctly and replaces the yearly scores;
- the split is 70/10/20, stratified, without overlap, and the same every run;
- the model-choice rule prefers Logistic Regression when within 0.01, and otherwise picks the clearly better model;
- the threshold search finds the right cut-off on simple data;
- the four-fifths rule passes at exactly 80% and fails below it, and age groups are assigned correctly;
- after training, the saved threshold and metrics load and agree, the curve images exist, and the live model
  passed the fairness check and produces scores between 0 and 1.

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
| Admin | None of it: admins manage accounts, not promotions |

### What the API returns for one employee

**Readiness score.** The model's score, shown as a percentage, and whether it is above the threshold (79%).
As explained in step 2, it ranks readiness; it is not a probability.

**Exact contributions (SHAP).** Logistic regression adds up one term per input:

```
log-odds = base + sum of  weight × (value − average value)
```

Each term is that input's **contribution**: how much it pushes this employee's score up or down compared with
an average employee. For a linear model this is exactly what SHAP calculates, so no approximation is needed.
"base" is the log-odds of an imaginary employee with average values on everything (their score: 15.3%).
Because the terms add up exactly to the model's output, the explanation is complete: there's nothing the
model used that isn't shown. A test checks this for all 120 demo employees.

Department is one input but becomes seven yes/no columns inside the model (one per department); their seven
terms are added together and shown as one item, "Department". Every value is shown in its normal unit
("90.5%", "4.1 / 5", "13 years").

**LIME, a second opinion.** LIME works differently: it creates 2,000 slightly altered copies of the employee's
record, asks the model to score them, fits a small simple model to those answers, and reads rules from it (for
example "Leadership score > 65.52 raises readiness"). Its **fit (R²)** says how well that simple model copies
the real one around this employee. Below 0.5, a note says to treat the rules as a rough guide.

In practice, LIME's fit is low for most employees here (median 0.21 over 40 employees; 35 of 40 below 0.5).
That's expected: most employees are far from the threshold, where the model's curve is flat and a simple
local model has little to fit. This is why the exact contributions are the main explanation, and LIME is shown
only as a second opinion, with its fit.

**Plain-language summary.** Built from the score, the threshold and the two biggest contributions each way:

> Readiness is 13%, below the 79% threshold, so the model does not yet recommend promotion. Compared with an
> average employee, it is raised mainly by leadership score (72.2) and performance score (82.2), and lowered
> mainly by years since last promotion (13 years) and attendance (86.8%).

**What-if.** The user changes some inputs and gets the new score and explanation. Only **improvable** inputs
(things a person can work on, such as training hours or late days) can be changed, within the range real
employees had. Department, years in role, years since promotion and the protected characteristics can't be.
Nothing is saved. Raising this year's performance score also raises "change since last year" by the same
amount, because that is how the change is calculated.

**Tips to improve.** The smallest realistic improvements that would reach the threshold:

1. Only improvable inputs, and only in the improving direction (more training, fewer late days).
2. Only inputs where improving actually raises the score. If the model happened to give an improvement a
   negative weight, it is never suggested.
3. Each input by at most one standard deviation, and not past what the top 5% of employees achieve
   (and never past natural limits such as 100%).
4. The inputs with the biggest possible effect first, stopping as soon as the threshold is reached.

For the 107 demo employees not yet recommended, the tips reach the threshold for 82. For the other 25, the tips
show the most realistic progress, and the projected score says how far it gets.

**Overall importance.** Across 2,000 training employees: the average size of each input's contribution, as a
share of the total.

| Input | Share of the model's effect | Direction |
|---|---|---|
| Change in performance since last year | 39.5% | higher raises readiness |
| Department | 26.3% | depends on the department |
| Leadership score | 5.6% | higher raises readiness |
| Years since last promotion | 4.8% | higher lowers readiness |
| Performance score | 4.7% | higher raises readiness |
| KPI achievement | 3.9% | higher raises readiness |

### Points to discuss in the thesis

- **One input dominates.** Change in performance since last year accounts for about 40% of the model's
  effect, so for most people one tip (raise this year's performance) is enough.
- **Department matters a lot (26%)** but is not something a person controls. Department is a fair input
  only if promotion opportunities really differ by department; otherwise it carries forward differences in how
  departments promoted in the past. The fairness check in step 2 covers gender, age and education, not
  department.
- **Years since last promotion lowers readiness.** In this data, people who have waited a long time are less
  likely to be promoted. The model reproduces that pattern; it doesn't judge whether it's fair.

### API endpoints

| Method and path | Who | Returns |
|---|---|---|
| `GET /api/promotion/employees` | HR, manager, employee | The employees they may see, with scores |
| `GET /api/promotion/employees/{id}` | Same, for their visible employees | Score, contributions, LIME, summary, what-if options |
| `POST /api/promotion/employees/{id}/what-if` | Same | Score and contributions with the changes applied |
| `GET /api/promotion/employees/{id}/tips` | Same | Tips and the projected score |
| `GET /api/promotion/importance` | HR, manager, employee | Overall importance |

### How it was tested

`backend/tests/test_explanations.py` (18 tests) checks that:

- the contributions add up exactly to the model's output, for all 120 demo employees;
- department is shown as one item and values are in their real units;
- LIME returns rules and a fit score, with a note exactly when the fit is below 0.5;
- the summary states the score and the threshold;
- a what-if changes the score but saves nothing; changing this year's performance also changes the change
  since last year; non-improvable inputs and impossible values are refused;
- across all 120 employees, tips only use improvable inputs, only in the improving direction, by at most one
  standard deviation, within natural limits, and never lower the score;
- overall importance covers all 21 inputs and adds up to 100%;
- HR sees all 120 employees, a manager only their 12, an employee only themselves, and the admin nothing.

## Step 4: The promotion pages

Code: `frontend/src/pages/promotion/` (pages) and `frontend/src/components/promotion/` (the parts of an
explanation, one file each).

### Which pages each role gets

| Role | Menu | What it shows |
|---|---|---|
| Employee | My readiness · How the model works | Their own score, explanation, what-if and tips |
| Manager | My team · How the model works | Their team with scores; click a name for the full explanation |
| HR | All employees · How the model works | Everyone, with search, department filter and "recommended only"; click a name for the full explanation |
| Admin | Users | No promotion pages: admins manage accounts, not promotions |

The website hides pages a role can't use, but the real protection is the backend (step 3): even if someone
typed a page address or called the API directly, they would only get data their role allows.

### The readiness page

One page, used both for "My readiness" and when HR or a manager opens an employee. Top to bottom, it answers
the questions a person naturally asks:

1. **Where do I stand?** The score as a percentage on a 0–100% bar, with the threshold marked, and
   "Recommended" or "Not yet recommended" in words. Below it, the plain-language summary, plus a note that the
   score ranks readiness (it isn't a probability) and that HR makes the decision.
2. **Why?** Two short lists: what raised the score and what lowered it, compared with an average employee, each
   with the person's real value and a bar for the size of the effect. "Show all 21 factors" opens a table
   with the exact numbers, which add up to the score.
3. **Second opinion.** LIME's rules, marked where they name the same factors as the main explanation, with its
   fit score and the warning when the fit is low.
4. **What if?** A slider for each improvable factor, set to the person's current value and limited to the
   range real employees had. "See the new score" asks the backend; nothing is saved. "Reset" puts everything
   back.
5. **Tips to improve.** Numbered steps ("Increase leadership score from 46.3 to 58.6"), followed by a sentence
   on where they lead: above the threshold, or how much closer.

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

## Step 6: Anonymous reporting

Code: `backend/app/reporting/` (its own package and table, separate from the promotion part), and the pages
`frontend/src/pages/reporting/Report.jsx` and `CheckReport.jsx`.

### Who can report, and what "anonymous" means here

Reports come from **members of the organisation**: a person must be signed in, which keeps outsiders and spam
out. Every account can report (employees, managers, HR and admins are all staff).

But **the report is never linked to the account**. The reporting endpoints check that someone is signed in and
then use nothing else about them: the account is not passed on, not saved, and not logged. The only link between
a report and its author is the **secret key**, which only the reporter has.

### Reporting, step by step

1. **Write.** Choose a category (harassment, discrimination, bullying, health and safety, ethics or fraud,
   something else) and describe what happened.
2. **Check what will be sent.** The text goes to the anonymiser and comes back cleaned. Nothing is saved at
   this point. The reporter sees:
   - the cleaned text, with every replacement highlighted (`[PERSON 1]`, `[DATE 1]`, ...);
   - a list of what was removed ("Ben Quinn" → [PERSON 1]), shown only to them and never sent or saved;
   - warnings about phrases that could identify them, with the reason;
   - an editable copy of the cleaned text. After an edit, it must be checked again before sending.

   The reporter ticks "I've read this and it doesn't contain anything that identifies me", then sends.
3. **Save your key.** The reporter gets a **case ID** (e.g. `R-6YS9-WDFP`) and a **secret key** (four groups of
   four characters). The page says clearly that the key is shown once and can't be recovered, even by an
   administrator, because it isn't linked to any account.

Later, **Check my report** opens the case with the case ID and key.

### The anonymiser

`app/reporting/anonymiser.py` uses simple, readable rules:

| What | Becomes | How it's found |
|---|---|---|
| Names of people in the organisation | `[PERSON 1]`, `[PERSON 2]`, ... | The full names of everyone in the employee directory and every account holder |
| A first or last name on its own | The same person's tag if they were named in full; otherwise a new tag | Only when capitalised, because many surnames are also ordinary words ("Brooks", "Manager") |
| Email addresses | `[EMAIL 1]` | Pattern `something@domain.tld` |
| Phone numbers | `[PHONE 1]` | 7 or more digits, with spaces, dashes or a leading + |
| Dates | `[DATE 1]` | "12/03/2025", "2025-03-12", "12 March", "March 12th 2025" |

The same person keeps the same tag throughout a report, and tags are numbered in the order they appear.
Ordinary text such as "we hit our targets" is left alone.

**Identifying phrases** are flagged but not removed, because the reporter may need them to explain what
happened: "I'm the only woman in the team", "I've worked here for 12 years", "since I joined", "I'm the new
intern", "my desk", personal circumstances. The reporter decides whether to reword them.

**When sending**, the backend runs the anonymiser again on the final text. If a name, email, phone number or
date has crept back in through editing, the report is refused with a request to check again. The original text
is never saved.

### What is stored, and what is deliberately not

| Stored | Not stored |
|---|---|
| A random case ID | Who sent it: no user, account or employee column at all |
| The category | The original, un-anonymised text |
| The approved, anonymised text | The time: only the **date** is kept |
| The date | IP addresses or browser details |
| A **hash** of the key (like passwords: PBKDF2 with a salt) | The key itself |
| Status (open), and wrong-attempt counters | Any request log (the server's request log is switched off in `run.py`) |

Two less obvious protections:

- **Case IDs are random**, not numbered in order, so a case ID says nothing about when the report was made.
- **The table keeps no hidden row order.** SQLite normally numbers rows in the order they are added; the
  reports table is created `WITHOUT ROWID`, so the order of reports can't be lined up against who was signed
  in at the time.

### Opening a case: protection against guessing

- **The same answer for every failure.** A wrong case ID, a wrong key and a locked case all get exactly the same
  message, so nobody can find out which case IDs exist. An unknown case ID even takes the same time to check as
  a real one.
- **Lockout.** After **five wrong keys**, the case is locked for **15 minutes**; during that time even the
  right key is refused.

### Report data never reaches the promotion model

The reporting code lives in its own package with its own table. The promotion code (and `train.py`) never
imports anything from it; a test reads every promotion file to prove it. A second test scores all employees,
adds reports, and scores them again: the predictions are identical.

### What remains (to discuss honestly in the thesis)

- **At the moment of sending, the server knows who is signed in.** That is the price of keeping reporting to
  members of the organisation (the design choice made for this project). The code never stores or logs it,
  but someone able to change the server's code could capture it. A version that needs no sign-in would avoid
  this, at the cost of letting anyone with the page link report.
- **Request logs elsewhere.** This app's request log is off. In a real deployment, any proxy or hosting service
  in front of it must not log requests either.
- **The anonymiser only knows what its rules describe.** Nicknames, misspelled names, people outside the
  directory, or a distinctive writing style can still identify someone. That is why the reporter always
  reviews and approves the text.
- **Dates and the activity log.** Reports keep the date. If the activity log (step 8) recorded exact sign-in
  times and very few people signed in on a given day, the date alone could narrow down the reporter. Step 8
  must take this into account.

### How it was tested

`backend/tests/test_reporting.py` (20 tests) checks that:

- the anonymiser replaces directory names (full, and first names alone, with one tag per person), emails,
  phone numbers and dates; leaves ordinary text alone; only replaces a lone surname when it's capitalised; and
  flags identifying phrases once each;
- reporting needs a signed-in account; the preview stores nothing;
- a report gets a random case ID and key; only a salted hash of the key is stored; the date is stored without a
  time;
- the reports table has no column that could hold the reporter's identity, and the stored report contains none
  of the reporter's details; the table has no hidden row order;
- text that still contains a name or phone number, or an unknown category, is refused;
- every role can report;
- the key opens the case; a wrong case ID and a wrong key get exactly the same answer; five wrong keys lock the
  case, even against the right key, until 15 minutes have passed;
- the promotion code never imports the reporting code, and predictions are identical before and after reports
  are added.

A browser walkthrough confirmed the whole flow as an employee: names, date and phone were replaced, "I'm the
only woman in the team" was flagged, the report was sent, a wrong key was refused with the standard message,
and the right key opened the case.

## The interface design

The website follows one consistent, calm style (`frontend/src/styles.css`, `frontend/src/components/ui.jsx`):

- **Layout:** a white sidebar with the platform's name, a menu with an icon for every page (the active page is a
  dark pill), and the signed-in person at the bottom with their role, a light/dark switch and a sign-out button.
- **Pages** start with a large title and icon, a one-line explanation of what the page is for, and a divider.
- **Overview pages** show four "stat cards" (a small label, a big number, a short note), then the main list in a
  white card. Lists use a switch such as **Waiting | Decided | All**, and a friendly message when empty.
- **Light and dark mode** use the same colour names (defined once, at the top of the stylesheet), so every page
  works in both. The choice is remembered in the browser.
- **Accessibility:** status is always written in words (and arrows such as ▲ / ▼), never shown by colour alone;
  icons are decorative, the text next to them carries the meaning.
- Icons come from the open-source **Lucide** icon set; the font is **Plus Jakarta Sans**.

## Step 7: The conversation, triage and HR's report inbox

Code: `backend/app/reporting/triage.py`, `routes.py` (reporter side), `routes_hr.py` (HR side), the
`report_messages` table in `models.py`, and the pages `ReportInbox.jsx`, `ReportCase.jsx` and `CheckReport.jsx`.

### Triage: how urgent is a report?

A simple, readable keyword list (`triage.py`) suggests a priority when a report arrives:

1. **Harmless phrases are removed first**, so they can't trigger anything: "hit our targets", "the deadline is
   killing me", "we killed it", "hit the ground running"...
2. **High** if the text contains a word suggesting danger: "threatened", "unsafe", "hit me", "assaulted",
   "weapon", "stalking"... **Medium** if it contains a word suggesting mistreatment: "harassed", "bullied",
   "shouted", "humiliated", "racist", "retaliation"... Otherwise **low**.
3. **Category minimums**: safety reports are always at least high; harassment and discrimination at least medium.
4. **HR sees why**: the words that triggered the priority are marked in the report (red for high-priority words,
   amber for medium), with the reasons in plain words. HR can change the priority at any time; the original
   suggestion is kept alongside it.

Keyword rules are deliberately simple: anyone can read the list and see exactly why a report got its priority.
They also miss things a person would catch (sarcasm, unusual wording), which is why HR always reviews and can
override.

### The conversation

Reporter and HR can write to each other inside the case:

- The reporter opens the case with the **case ID and key** ("Check my report"), reads the replies, and writes
  back. Every request needs the key again; nothing links the reporter's account to the case.
- **Nobody is named.** The reporter sees HR only as **Investigator**; HR sees the reporter only as **Reporter**.
  The messages table stores the sender as just "reporter" or "investigator", with the **date only**; the order
  comes from a running number within the case. HR is reminded not to sign with their name or ask who the
  reporter is.
- **The reporter's messages go through the same anonymiser** as the report: the page shows exactly what the
  investigator will see (names, emails, phone numbers and dates replaced, identifying phrases flagged) before
  sending, and the backend refuses a message that still contains any of them.
- HR's first reply moves the case from "open" to "investigating".
- The reporter sees the case's status, and its outcome once closed, but not its priority or HR's internal view.

### HR's report inbox and case page

- **Inbox:** stat cards (open cases, high priority, awaiting a reply, closed), then every report with its
  category, priority, status, date and whether the reporter is waiting for a reply. Open, high-priority cases
  come first. A switch filters Open | Investigating | Closed | All.
- **Case page:** the report with its warning words marked; "Why this priority"; the conversation with a reply
  box; and "Manage the case" to set the priority, status and outcome.
- **Closing a case needs an outcome**: concern upheld, concern not upheld, not enough evidence either way, or
  resolved informally. The outcome stays in the reporting part: it is never used by the promotion model.

### API endpoints

| Method and path | Who | Does |
|---|---|---|
| `POST /api/reports/access` | Anyone signed in, with the case ID and key | The case, its status and outcome, and the conversation |
| `POST /api/reports/messages` | Same | The reporter replies (must already be anonymised) |
| `GET /api/hr/reports` | HR | The inbox |
| `GET /api/hr/reports/{case}` | HR | One case: text, triage, conversation, options |
| `POST /api/hr/reports/{case}/messages` | HR | Reply as the investigator |
| `PATCH /api/hr/reports/{case}` | HR | Change priority, status or outcome |

### How it was tested

`backend/tests/test_conversation.py` (19 tests) checks that:

- threatening and danger words give high priority, mistreatment words medium, others low; harmless phrases are
  ignored; the category minimums apply; the trigger words and reasons are returned; a new report starts at the
  suggested priority;
- investigator and reporter can talk; both see only "investigator" and "reporter", and no name or username
  appears anywhere in the conversation;
- a reporter message that still contains a name or phone number is refused; replying needs the right key;
- the reporter never sees the priority; HR's first reply marks the case "investigating";
- HR can change the priority; closing needs an outcome; impossible values are refused;
- the reporter sees the outcome and can't write to a closed case;
- the inbox lists open, high-priority cases first and shows when the reporter wrote last;
- only HR can see the inbox, open a case or reply as the investigator.

The tests from step 6 were extended: the messages table may only have the columns case, number, sender, text
and date.

A browser walkthrough confirmed the whole conversation: a report about being threatened arrived as high
priority with "threatened" and "unsafe" marked; HR replied; the reporter, who saw only "Investigator", replied
naming a colleague and a date, which arrived at HR as "[PERSON 1] ... [DATE 1]"; HR closed the case as
"concern upheld", and the reporter saw that outcome.

### Keeping the case ID and key

The key is the only link between a report and its author, so losing it means losing the conversation. But it
must **never be stored on the server** (for example "remember my keys" in the user's account, or emailing it to
them): that would link the report to the reporter's account, which is exactly what anonymity rules out. So
every way of keeping the key happens on the reporter's side, and the server never learns about it
(`frontend/src/keyStore.js`):

| Option | Where the key goes | Good for |
|---|---|---|
| Save on this device | This browser's storage | A personal phone or laptop. A warning appears first: anyone using the same browser could read it |
| Download a receipt | A small text file | Keeping it with other private files |
| Password manager | The browser's password manager (Chrome, Edge) | The safest choice: encrypted and synced to the person's own devices |
| Copy | The clipboard | Pasting into a notes app |

**My report keys** (`pages/reporting/ReportKeys.jsx`) lists the keys saved on this device, with **Open** (goes
straight into the case without typing), **Copy**, **Download** and **Forget**, plus a form to add a key that was
written down and four tips on keeping keys safe. When a case is opened from this page, the key is passed inside
the app, never in the web address, which would be kept in the browser's history.

"Check my report" marks its two fields as a username and password, so password managers recognise them and can
fill them in.

**The trade-off to discuss:** convenience against risk on shared devices. Saving on the device is opt-in with a
warning, never automatic; and a lost key still can't be recovered, by design. The reporter can always make a new
report.

## Updates after step 7

### Reporting is for employees and managers

Anonymous reporting (making a report, checking it, and saved keys) is for **employees and managers**: the people
likely to need it. **HR** handles reports in the report inbox instead, and **admins** manage accounts, so neither
sees the reporting pages. This is enforced by the backend (`REPORTER_ROLES` in `app/core/roles.py`), not just
hidden in the menu; a test checks that HR and admins get "403" from every reporting endpoint.

Saved keys are kept **separately for each account** on a device (`frontend/src/keyStore.js`), so if someone else
signs in on the same computer (a colleague, or HR) they don't see them in the app.

### Notifications

A bell at the top right shows what needs attention.

- **HR** is told about new reports nobody has answered yet and reporters waiting for a reply
  (`GET /api/hr/reports/notifications`). These are worked out from the cases themselves, so nothing extra is
  stored, in particular no time at which the reporter wrote.
- **Reporters** are told when the investigator replies, or their case is closed. This can't be stored on the
  server: a record saying "this account follows that case" would link the report to the reporter. So the
  reporter's **own browser** checks the cases saved on that device (`POST /api/reports/updates`) and compares them
  with what the reporter has already seen. Opening the case clears the notification. Only saved cases are
  checked, which the bell explains.

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
| New report alert | A report is submitted | All active HR accounts |

- **Report alerts reveal nothing.** They contain only the case ID, the category and the triage priority. They
  never include the report text or anything about the reporter, and **reporters are never emailed**, because an
  email would link their account to the report. Tests check both.
- **Background sending.** Alerts are sent after the response has gone back, so a slow mail server never delays
  the page. Welcome and reset emails are the exception: they are sent straight away, so the admin sees whether
  delivery worked.
- **Without a mail server**, every email is saved as an `.eml` file in `backend/instance/outbox/`, and the admin
  can read these on the Email page. The tests use this to check each email's content.
- **Limitation to discuss.** A report alert reaches HR moments after the report is sent. Someone who watches
  their inbox and also knows who was at a computer at that moment could narrow down the reporter. The alert
  carries no time beyond the email's own, but the email itself is a timestamp. Future work could send alerts in
  a daily digest instead.

### A tidier menu

The sidebar groups pages under headings (Promotion, Reporting, Administration, Account) that open and close when
clicked; the group holding the current page opens by itself.

### The public website

Visitors who aren't signed in see a small website (`frontend/src/pages/public/`), one page per menu item, all
sharing one menu bar and footer (`PublicLayout.jsx`); the menu highlights the page you're on:

| Page | Address | What it shows |
|---|---|---|
| Home | `/` | The headline, the model's tested results (read live from `results/` through the public `GET /api/public/summary`, which contains nothing about any person), three cards that open the other pages, the design principle |
| Approach | `/approach` | The three pillars (explain every score, check fairness first, protect every voice) and the four roles |
| Promotion | `/promotion` | What an employee sees, and the four steps of a promotion decision |
| Reporting | `/reporting` | What the reporter sees, the four steps from concern to conversation, and HR's side |
| Privacy | `/privacy` | The six privacy promises, and a note that the demo uses synthetic data |
| Book a demo | `/demo` | A short form (see below) |

Every page ends with a navy band offering **Book a demo** or **Sign in**. The sign-in page links back to the website.

Its look takes inspiration from people-first HR sites: large photos of real people working together, sections
that alternate text and pictures, and a dark footer with columns.

- **Photos of people** (`frontend/public/landing/people/`) are from **Pexels**, whose licence allows free use
  without asking permission; the photographers are credited in the footer anyway. The footer also says that the
  people pictured are not users of the system.
- **Screenshots** (`frontend/public/landing/*.webp`) are of the real app with made-up demo data, shown in small
  frames over the photos.
- **No testimonials.** Many company sites quote a happy customer; a made-up quote would be invented evidence, so
  the site states the design principle instead: "The model advises. People decide."

Any image can be replaced with your own (same file names).

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
| Reports | HR's replies and HR's changes to priority, status and outcome (with the case ID) |

Only the **admin** can read the log, with a filter by action and a search box.

**What is deliberately not recorded:**

- **Anything a reporter does**: sending a report, checking text, opening a case with the key, replying, or
  checking for news. A test performs all of these and checks that the log doesn't grow by a single entry.
- **Times.** Like reports, entries keep only the **date**. A sign-in time could otherwise be lined up with a
  report to narrow down who wrote it.
- **Passwords**, temporary or not (a test checks this too), and sign-in attempts on usernames that don't exist.

**The trade-off to discuss.** Logging every sign-in, even by date only, still shows who was active on a given day.
If a report arrived on a day when only one person signed in, the date alone could point at them. Two ways to
reduce this further: log sign-ins only for the privileged roles (HR and admin), whose access matters most for
security, or keep sign-in records only as daily counts. This project follows the brief (log sign-ins) and keeps
dates only; the alternatives are worth discussing as future work.

### All the tests

Run them with `cd backend` then `.venv\Scripts\python -m pytest`. There are **189 tests**, all passing:

| File | Tests | What they prove |
|---|---|---|
| `test_auth_and_roles.py` | 19 | Passwords are hashed with a salt; sign-in; wrong password and unknown user look the same; only the admin manages accounts; deactivation locks people out at once |
| `test_training.py` | 12 | Protected characteristics and pay are never model inputs; the 70/10/20 split; the model-choice rule; the threshold; the four-fifths fairness check; the saved threshold and metrics load |
| `test_explanations.py` | 20 | The contributions (SHAP) add up exactly to the model's output; LIME and its fit; the summary; what-if changes only improvable inputs and saves nothing; tips never suggest making anything worse; who may see whom |
| `test_decisions.py` | 17 | Managers nominate only their team; HR decides; disagreeing with the model needs 20 characters; every decision is logged with the model's view; managers' teams |
| `test_reporting.py` | 20 | The anonymiser removes names, emails, phones and dates; the key is hashed; dates without times; nothing about the reporter is stored; wrong attempts lock the case; **isolation**: the prediction code never touches report data, and predictions are identical before and after reports |
| `test_conversation.py` | 19 | Triage; the conversation shows no names; reporter messages are anonymised; HR's inbox and case updates |
| `test_accounts_and_notifications.py` | 13 | Welcome emails; editing accounts; changing your username; notifications for HR and reporters; the public summary reveals no one |
| `test_emails.py` | 14 | Security alerts; nomination and decision emails go to the right people; report alerts hold no text and nothing about the reporter; reporters get no email; only the admin uses the Email page; every email has plain and HTML versions |
| `test_employee_records.py` | 16 | HR adds an employee who can be scored at once; values are stored as the model expects; impossible values are refused and unusual ones flagged; no one is added twice; one bad CSV row means nobody is imported; no protected characteristics are accepted; only HR manages records |
| `test_demo_requests.py` | 10 | Anyone can book a demo; it's emailed with Reply-To set to the visitor; the admin lists and ticks off requests; robots and repeats are kept out; visitors' text can't inject HTML; only the admin sees requests |
| `test_profiles_and_permissions.py` | 15 | People update their profile (an email change alerts the old address; only small images as photos); Admin and HR accounts can't be linked to employee records; an admin sees employee data only once allowed, read-only, never reports; managers are emailed about new team members, and only about new ones |
| `test_evaluation_data.py` | 4 | The labelled evaluation reports are well formed (every label copied exactly from its report); the evaluation counts every report; the usability questionnaire is scored by the standard formula |
| `test_activity.py` | 10 | Sign-ins and actions are logged by date; nothing a reporter does is logged; passwords never are; only the admin reads the log |

How each requirement in the brief is tested:

| Requirement | Where |
|---|---|
| Roles: each role can only access what it should | `test_auth_and_roles`, plus a "who may see this" test in every other file |
| Model: threshold and metrics load; the fairness check runs | `test_training` |
| Explanations: SHAP adds up; tips never make a feature worse | `test_explanations` |
| Reporting: anonymiser, hashed key, lockout, dates without times | `test_reporting` |
| Isolation: prediction code never reads report tables; predictions unchanged by reports | `test_reporting` (last two tests) |

Besides the automated tests, every step was also checked by walking through it in a real browser, as each role.

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
clicked. Buttons that wait for the server (signing in, creating accounts, nominating, deciding, sending a report or
a reply, saving) show a spinning icon and say what is happening ("Signing in…", "Sending securely…") until the
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
their readiness page and clicks Run prediction; the admin can link them to a login on the Users page; and their
name joins the directory the report anonymiser uses.

**Scoring a person is not the same as learning from your organisation.** The model learned what "ready for
promotion" looks like from synthetic employees. For real use, an organisation would export its own history (past
employees' records **and** whether they were promoted), point `train.py` at that file, and use the model only if
the four-fifths fairness check passes on its own people. Adding employees here gives them a score from the current
model; it doesn't retrain it.

## Colours: navy and teal

The whole product (public website, app and emails) uses one palette, defined once as colour names in
`frontend/src/styles.css`, with a light and a dark version:

| Role | Light | Dark | Used for |
|---|---|---|---|
| Navy | `#0F2A44` | `#E6EDF5` (inverted) | Headings' weight, primary buttons, the active menu item, dark bands |
| Teal | `#0B7A6E` | `#2DD4BF` | Links, highlights, "Book a demo" buttons, factors that raise a score |
| Orange | `#B14F0C` | `#F4A261` | Factors that lower a score (teal and orange stay distinct for colour-blind readers) |
| Background | `#F5F8FA` | `#0B1622` | Page background |

Why navy and teal: navy reads as trustworthy and serious, which matters for promotions and misconduct reports;
teal is calm and positive without the alarm of red or the sameness of plain blue. Every text colour was checked
against the WCAG AA contrast minimum (4.5:1) on the background it's used on. Status is still never shown by
colour alone: there's always a word or an icon too.

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
records, or see anything from the reporting part. The rule is checked on the server (`may_view_all()` in
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

### Report keys: copy and paste without losing anything

- **My report keys** has separate **Copy case ID**, **Copy key** and **Copy both** buttons, each briefly showing
  "Copied".
- On **Check my report**, pasting text that contains both (from Copy both, or the downloaded receipt) into
  either box fills **both** boxes.
- If you paste the case ID, go to My report keys for the key, and come back, the case ID is still there. It's
  kept in the page's memory only: never written to storage, gone when the tab closes, and never shown to another
  account signing in on the same tab.

