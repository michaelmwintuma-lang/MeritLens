# MeritLens: Project Documentation Index & System Reference Guide

**"Fair, explainable promotion decisions, with a voice for every employee."**

This master document serves as the primary technical specification, testing audit report, and team presentation guide for the **MeritLens** platform. It consolidates all system architecture, machine learning evaluations, governance protocols, and validation benchmarks into a unified reference for team members, supervisors, and external auditors.

---

## Document Metadata

| Attribute | Specification Details |
|---|---|
| **System Name** | MeritLens (Explainable AI Decision-Support Platform) |
| **Repository Location** | `c:\Projects\HR-simple` |
| **Word Document** | [Project Documentation Index.docx](file:///c:/Projects/HR-simple/docs/Project%20Documentation%20Index.docx) (also in root: [Project Documentation Index.docx](file:///c:/Projects/HR-simple/Project%20Documentation%20Index.docx)) |
| **Core Framework** | FastAPI (Python 3.11+), React 18, Tailwind CSS, InterpretML (EBM), SQLite / PostgreSQL |
| **Target Domain** | Human Resource Promotion Decision-Support & Algorithmic Fairness |
| **Primary Ethical Standards** | EU AI Act (High-Risk Employment AI), US EEOC 4/5ths Disparate Impact Rule, Colquitt Organizational Justice Theory |
| **Verification Status** | 400 Automated Backend Tests Passing; 100% Monotonic Explanations; Zero Proxy Leakage |

---

## Table of Contents

1. [Executive Summary & Core Philosophy](#1-executive-summary--core-philosophy)
2. [The Six System Roles & Separation of Duties](#2-the-six-system-roles--separation-of-duties)
3. [The Promotion Round Lifecycle (End-to-End Workflow)](#3-the-promotion-round-lifecycle-end-to-end-workflow)
4. [Machine Learning & Explainability Pipeline](#4-machine-learning--explainability-pipeline)
5. [Comprehensive Testing & Validation Methodology](#5-comprehensive-testing--validation-methodology)
   - [5.1 Predictive Performance on Held-out Test Set](#51-predictive-performance-on-held-out-test-set-20000-employees)
   - [5.2 Probability Calibration & Decile Analysis](#52-probability-calibration--decile-analysis)
   - [5.3 Algorithmic Fairness: The EEOC Four-Fifths Build Gate](#53-algorithmic-fairness-the-eeoc-four-fifths-build-gate)
   - [5.4 Subgroup Accuracy & Intersectional Parity](#54-subgroup-accuracy--intersectional-parity)
   - [5.5 Elimination of Proxies & Department Confounding](#55-elimination-of-proxies--department-confounding)
   - [5.6 Explainability Faithfulness & Monotonicity Checks](#56-explainability-faithfulness--monotonicity-checks)
   - [5.7 Feedback Channel Isolation Regression Tests (Zero Gaming)](#57-feedback-channel-isolation-regression-tests-zero-gaming)
   - [5.8 Backend Software Quality & Test Suite Coverage (400 Tests)](#58-backend-software-quality--test-suite-coverage)
   - [5.9 UI, Viewport & Accessibility Validation (WCAG 2.1 A/AA)](#59-ui-viewport--accessibility-validation)
   - [5.10 Database Performance & N+1 Query Elimination](#510-database-performance--n1-query-elimination)
   - [5.11 Human Usability & Organizational Justice Protocol](#511-human-usability--organizational-justice-protocol)
6. [Security, Cryptographic Audit Chains & Regulatory Compliance](#6-security-cryptographic-audit-chains--regulatory-compliance)
7. [Supervisory Defense & Q&A Strategy](#7-supervisory-defense--qa-strategy)
8. [Master Performance & Calibration Metrics Cheat Sheet](#8-master-performance--calibration-metrics-cheat-sheet)
9. [Project Documentation Index & Navigation Map](#9-project-documentation-index--navigation-map)

---

## 1. Executive Summary & Core Philosophy

Workplace promotion processes are frequently criticized for being opaque "black boxes" vulnerable to managerial favoritism, unspoken rules, and unconscious bias. Conversely, standard AI systems that predict promotions often automate and entrench historical discrimination, provide unintelligible scores, and offer employees zero procedural recourse.

**MeritLens** is an Explainable AI (XAI) Decision-Support Platform engineered to resolve this fundamental organizational dilemma. It establishes a closed-loop decision support cycle:

```
    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │  1. PREDICT  │  ────►  │  2. EXPLAIN  │  ────►  │  3. RESPOND  │
    │  Fairness-   │         │  Plain words │         │  Employee    │
    │  checked AI  │         │  & exact math│         │  voice & fix │
    └──────────────┘         └──────────────┘         └──────────────┘
           ▲                                                 │
           └──────────────── HR-Verified Fixes ──────────────┘
```

1. **Predict:** An additive machine learning model scores candidate promotion readiness based strictly on objective performance and skill-growth data. Demographic variables and department labels are fully excluded, and a strict EEOC Four-Fifths fairness check blocks discriminatory models.
2. **Explain:** Every readiness score is decomposed into exact feature contributions and translated into natural-language statements. For employees below the promotion threshold, the system computes actionable, realistic counterfactual tips ("What-If" scenarios).
3. **Respond:** Employees are provided an active voice. They can rate explanation clarity, contest perceived unfairness, and submit formal factual record correction requests accompanied by documentary evidence.
4. **Human-in-the-Loop Governance:** Managers nominate candidates using structured behavioral rubrics; HR committees evaluate holistic dossiers and resolve disputes; Finance certifies compensation bounds. Every action is sealed in a cryptographic SHA-256 audit log.

> [!IMPORTANT]
> **Core Governance Principle:** The AI never makes the promotion decision. Humans decide. Furthermore, employee ratings or contestations never modify their AI score directly. A score updates only if HR verifies factual documentary evidence and amends the underlying performance database.

---

## 2. The Six System Roles & Separation of Duties

MeritLens enforces rigorous Role-Based Access Control (RBAC) across six organizational personas to maintain procedural justice and organizational separation of duties:

| Role Persona | Primary System Capabilities | Access Boundaries & Blindspots |
|---|---|---|
| **Employee** | Views "My Growth" portal; inspects readiness score, exact additive contributions, and actionable tips; runs interactive "what-if" simulators; submits factual dispute tickets with evidence. | Can only see their own file. Cannot access manager nomination notes, peer scores, or HR deliberation logs. |
| **Manager** | Inspects team member readiness metrics; reviews historical trends; nominates candidates for review cycles using a 4-criteria behavioral rubric; writes mandatory justifications when overriding the AI. | Can only see direct/indirect department reports. Completely blinded to employee explanation ratings and pending correction tickets (anti-retaliation). |
| **HR Specialist / Committee** | Creates and manages company promotion cycles; evaluates manager nominations alongside AI explanations; resolves employee record corrections; grants approvals, holds, or rejections; tracks organization-wide fairness. | Has organizational visibility over performance and nominations. Strictly blinded from approving salary compensation adjustments (separation of financial powers). |
| **Finance Officer** | Inspects approved promotions solely to verify and approve proposed salary increases within company policy bands (e.g., 5% to 15% limits); manages payroll transitions. | Blinded to AI readiness scores, performance notes, manager commentary, and employee demographic data. Focus is strictly budgetary. |
| **Compliance Auditor** | Conducts compliance reviews; inspects cryptographic SHA-256 tamper-evident audit trails; audits EEOC fairness metrics and aggregated feedback trends. | Global read-only access. Strictly prohibited from creating, updating, or deleting operational records. |
| **System Administrator** | User account provisioning; reporting tree configuration; database backups; monitoring model drift (Population Stability Index). | Administrative systems access. Cannot nominate candidates or approve promotions. |

---

## 3. The Promotion Round Lifecycle (End-to-End Workflow)

A standard promotion cycle flows through five tightly coordinated phases:

```
[HR Opens Review Cycle]
       │
       ▼
[Batch Prediction Engine Scores All Active Employees]
       │
       ▼
[Managers Review Team Dashboard] ──► [Manager Submits Nomination via 4-Part Rubric]
                                              │ (Mandatory text justification if overriding AI)
                                              ▼
                                     [HR Committee Deliberation]
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
               [HR Approves]                                    [HR Holds / Rejects]
                      │                                               │
                      ▼                                               ▼
          [Finance Salary Sign-off]                             [Cycle Concluded]
                      │
                      ▼
          [Promotion Finalized] ──► [Cryptographic SHA-256 Audit Log Appended]
                                ──► [Automated In-App Notification Sent]
```

- **Phase 1: Activation & Snapshot:** HR initializes an official promotion round with defined start and end dates. The system triggers batch scoring, generating immutable snapshot predictions and baseline fairness metrics for all eligible staff.
- **Phase 2: Manager Nominations:** Department managers review their team dashboards. Nominations require completing an anchored 4-part rubric (Job Mastery, Team Collaboration, Problem Solving, Continuous Growth; rated 1–5). If a manager nominates an employee below the 0.2283 AI threshold, or passes over a top candidate, the system enforces a mandatory written rationale.
- **Phase 3: HR Review & Dispute Resolution:** HR reviews the nomination dossiers. If an employee has an active factual dispute ticket regarding their performance records, the decision is placed on "Hold" until resolved. HR formally Approves, Holds, or Rejects.
- **Phase 4: Finance Compensation Sign-Off:** Approved candidates are routed to the Finance dashboard. Finance validates that proposed compensation increases conform to organizational policy bands, preventing unbudgeted or inequitable pay awards.
- **Phase 5: Audit Sealing & Notification:** Upon Finance approval, the promotion is finalized. An entry is appended to the SHA-256 cryptographic audit chain, and an automated notification is dispatched to the employee.

---

## 4. Machine Learning & Explainability Pipeline

The predictive engine is built on 100,000 synthetic employee records (Kumar, 2026, Kaggle, CC0) partitioned into 70,000 training, 10,000 validation, and 20,000 test records using stratified random sampling.

### Feature Auditing & Exclusion Policy

To satisfy legal and ethical guidelines, candidate features were scrutinized under strict exclusion criteria:
- **Protected Attributes:** Gender, age, education level, and marital status were excluded from all model inputs and reserved strictly for post-hoc fairness audits.
- **Systemic Biases:** Department was removed because historical promotion rates varied wildly from 2.0% in Support to 33.2% in Engineering. Including department rewarded employees based on office politics and organizational silos rather than individual merit.
- **Contaminated Proxies:** Base salary, overtime/working hours, subjective attitude surveys, and office location tiers were eliminated to prevent contaminated proxy leakage.
- **Retained Merit Inputs:** 20 objective, development-oriented metrics were retained, including annual performance improvement (+51.5% total model weight), completed projects (10.7%), tasks completed on schedule (6.9%), leadership rating (4.5%), and verified training hours.

### Model Selection & The Common-Sense Monotonicity Test

Four candidate architectures were trained and subjected to an automated common-sense monotonicity test on 2,000 validation employees. Actionable growth inputs were nudged upward by +0.5 standard deviations. Any reduction in an employee's score was recorded as a common-sense violation:

| Candidate Architecture | Validation PR-AUC | Validation ROC-AUC | Common-Sense Violations | Eligibility Status |
|---|---|---|---|---|
| **Monotonic EBM (Chosen)** | **0.4671** | **0.8806** | **0.0%** | **PASSED & SELECTED** |
| XGBoost Ensemble | 0.4699 | 0.8777 | 21.9% | REJECTED (Severe Violations) |
| Logistic Regression | 0.4618 | 0.8793 | 16.7% | REJECTED (Multicollinearity Drops) |
| Random Forest | 0.4528 | 0.8769 | 30.1% | REJECTED (High Violation Rate) |

> [!NOTE]
> **Why Explainable Boosting Machines (EBM)?** EBM belongs to the Generalized Additive Model family with pairwise interactions ($g(E[y]) = \beta_0 + \sum f_i(x_i) + \sum f_{ij}(x_i, x_j)$). By enforcing monotonic spline constraints, MeritLens mathematically guarantees that an employee who takes more training or finishes more projects will **never** see their readiness score decrease. Standard gradient boosting (XGBoost) failed this basic test in over 21% of instances.

---

## 5. Comprehensive Testing & Validation Methodology

The testing and validation of MeritLens was conducted across ten rigorous, independent technical and human-centered dimensions. Every empirical claim in this system is backed by an automated script and reproducible test fixture.

### 5.1 Predictive Performance on Held-out Test Set (20,000 Employees)

The final monotonic EBM model was evaluated on 20,000 unseen test employees at the validation-optimized decision threshold of **0.2283**:

| Metric Name | Empirical Value | Baseline / Target | Technical Interpretation |
|---|---|---|---|
| **ROC-AUC** | **0.8833** | 0.5000 (Random) | Excellent discrimination across varying decision thresholds. |
| **PR-AUC** | **0.4736** | 0.1000 (Base Rate) | Primary metric for imbalanced data (10% positive class). Represents a **4.7x lift** over random guessing. |
| **Precision** | **41.02%** | - | 41% of recommended candidates were historically promoted. |
| **Recall** | **59.50%** | - | Captures 60% of all historically promoted employees. |
| **F1-Score** | **0.4856** | - | Harmonic mean optimized at threshold 0.2283. |
| **Overall Accuracy** | **87.40%** | - | High true-negative recognition on imbalanced data. |
| **Selection Share** | **14.50%** | 10.00% (Historical) | Identifies an expanded pool of high-readiness candidates. |

**Confusion Matrix:** 1,190 True Positives, 1,711 False Positives, 810 False Negatives, 16,289 True Negatives.

### 5.2 Probability Calibration & Decile Analysis

A model used for human decision-support must produce well-calibrated probabilities, not arbitrary relative rankings. Evaluated using Brier score and Expected Calibration Error (ECE):
- **Brier Score:** 0.0677 (compared to 0.0900 for a naive model guessing the 10% base rate).
- **Brier Skill Score:** 0.248 (24.8% improvement over standard baseline).
- **Expected Calibration Error (ECE across 10 deciles):** **0.0056** (under 0.6% deviation).
- **Reliability Curve Fit:** Slope = 0.998, Intercept = -0.013. Scores near the 0.23 threshold map to an observed empirical promotion rate of 23.7%.

### 5.3 Algorithmic Fairness: The EEOC Four-Fifths Build Gate

Under US Equal Employment Opportunity Commission (EEOC) guidelines, an adverse impact is detected if a protected demographic's selection rate is less than 80% (0.80) of the highest group's rate. MeritLens embeds this check as an automated CI/CD gate—any model failing this test cannot be deployed:

| Demographic Characteristic | Group Selection Rates | Adverse Impact Ratio | EEOC Gate Outcome |
|---|---|---|---|
| **Gender** | Female: 14.6%, Male: 14.4% | **0.982** (Well above 0.80) | **PASSED** (No Disparate Impact) |
| **Age Group** | Under 40: 14.8%, 40+: 14.2% | **0.963** (Well above 0.80) | **PASSED** (No Disparate Impact) |
| **Education Level** | Bachelor: 14.3%, Master: 14.7%, PhD: 16.1% | **0.887** (Lowest-to-highest) | **PASSED** (No Disparate Impact) |

### 5.4 Subgroup Accuracy & Intersectional Parity

In addition to selection rates, the system was validated across intersectional demographic slices to prevent hidden harms:
- **Gender True-Positive Rate (TPR) Ratio:** 0.952 (Female TPR 61.0% vs Male TPR 58.1%).
- **Age True-Positive Rate Ratio:** 0.899 (Under 40 TPR 63.0% vs Age 40+ TPR 56.6%).
- **Intersectional Selection Ratio:** Female Under 40 (15.0%) vs Male 40+ (14.1%) yielded a ratio of **0.945**.
- **False-Positive Rate Parity:** False-positive rates across all seven demographic and intersectional cohorts remained tightly bounded between 9.1% and 10.4% (maximum disparity of only 1.3 percentage points).

### 5.5 Elimination of Proxies & Department Confounding

To verify that the 20 merit inputs did not secretly encode demographic proxies, adversarial classifiers were trained to predict gender, age, and education exclusively from performance data:
- **Gender Classifier:** ROC-AUC = 0.500 (Pure random guessing; zero demographic signal in performance inputs).
- **Age Group Classifier:** ROC-AUC = 0.500 (Cohen's $d < 0.016$, statistically negligible).
- **Education Classifier:** ROC-AUC = 0.500 (No degree proxy leakage).
- **Department Analysis:** Excluding department was a deliberate ethical choice. While including department increased PR-AUC to 0.6325, it severely penalized low-promotion departments. Without department, the model recommends 24.7% of Engineering vs 7.9% of Support (compared to historical rates of 33.2% vs 2.0%), significantly leveling the playing field.

### 5.6 Explainability Faithfulness & Monotonicity Checks

Explanations were validated on the 120-employee validation sample using automated scripts (`evaluate_explanations.py`):
- **Mathematical Exactness:** The maximum gap between the baseline log-odds plus the sum of all individual feature contributions and the model's direct output was **0.000347**, proving exact mathematical faithfulness.
- **Explanatory Monotonicity:** 2,040 individual perturbation checks (17 continuous features $\times$ 120 employees) confirmed that improving a performance metric **never** lowered a score or produced a negative contribution delta.
- **Actionable Tips Validity:** For 90.7% (98 of 108) of employees currently below threshold, the counterfactual tips generated a viable path to cross the 0.2283 promotion threshold within reasonable growth parameters.
- **LIME Sanity Audit:** LIME local linear models exhibited poor fit (median $R^2 = 0.135$) due to flat decision boundaries far from the threshold, proving why intrinsic EBM glass-box models are vastly superior to post-hoc explainers.

### 5.7 Feedback Channel Isolation Regression Tests (Zero Gaming)

A central vulnerability in algorithmic governance is feedback gaming. The isolation test suite (`test_isolation.py`) verified total architectural separation:
- **Baseline Recording:** The prediction API responses for target employees were recorded as cryptographic byte baselines.
- **Adversarial Injection:** Aggressive negative user ratings (e.g., rating = 1, "Extremely unfair") and pending/rejected factual dispute tickets were submitted.
- **Invariance Verification:** Subsequent prediction calls returned **byte-for-byte identical** scores, confirming that user sentiment cannot contaminate the scoring model.
- **Controlled Update Pipeline:** A score updates **only** when an HR specialist verifies physical documentation, updates the record in the database, and triggers an audited recalculation.

### 5.8 Backend Software Quality & Test Suite Coverage

The backend is covered by **400 automated pytest cases** across 37 dedicated test suites executing in under five minutes:

| Test Module | Test Focus & Security Boundary | Status |
|---|---|---|
| `test_auth_and_roles.py` | JWT token signing, role-based endpoint permissions, deactivation lockout | PASSED |
| `test_isolation.py` | Proves employee feedback and ratings never modify AI predictions | PASSED |
| `test_governance.py` | SHA-256 cryptographic audit hash chaining and tamper detection | PASSED |
| `test_cycles.py` | Promotion review round state transitions, batch scoring, deadline controls | PASSED |
| `test_approvals.py` | Manager nominations, 4-part rubrics, override justifications | PASSED |
| `test_finance_operations.py` | Finance salary sign-offs, policy threshold enforcement (5-15%) | PASSED |
| `test_email_delivery.py` | In-app notifications, digest generation, delivery tracking | PASSED |
| `test_privacy.py` | GDPR Article 15/20 data portability, demographic masking (<5 rule) | PASSED |
| `test_query_counts.py` | Regression fixture ensuring database queries never grow with row counts | PASSED |
| `test_backups.py` | Automated database backups, restore verification, schema integrity | PASSED |

### 5.9 UI, Viewport & Accessibility Validation

The front-end was evaluated using automated browser automation scripts (`scripts/browser_test.py`):
- **E2E Journeys:** 10 complex multi-role workflows were executed end-to-end without errors.
- **axe-core WCAG Audit:** Evaluated with axe-core across 45 unique screens in both light and dark themes. Achieved **0 WCAG 2.1 A/AA violations**.
- **Mobile Viewport:** Verified on emulated 390px mobile viewports; zero horizontal overflow detected.

### 5.10 Database Performance & N+1 Query Elimination

A load test on a 5,000-employee database (`results/load_test.json`) confirmed that query optimization eliminated all N+1 query loops:

| Endpoint / Operation | Queries Before Fix | Queries After Fix | Median Latency (5k Employees) |
|---|---|---|---|
| **Batch Scoring 5,000 Staff** | 5,000+ roundtrips | Vectorized Batch | **13 milliseconds** |
| **Opening Review Cycle** | 5,022 queries | 23 queries | **0.69 seconds** |
| **HR Nominations Dashboard** | 1,204 queries | 6 queries | **0.05 seconds** |
| **Finance Salary Reviews** | 604 queries | 8 queries | **0.02 seconds** |
| **Decision Log Inspection** | 903 queries | 6 queries | **0.03 seconds** |

### 5.11 Human Usability & Organizational Justice Protocol

MeritLens embeds an automated User Study Module ([USER_TEST.md](file:///c:/Projects/HR-simple/docs/USER_TEST.md)) directly into the Admin portal to measure human factors:
- **Standardized Tasks:** 11 Structured Task Scenarios across Employee (T1-T5), Manager (T6-T7), HR (T8-T10), and Verification (T11) roles.
- **SUS Benchmark:** 10-item standardized System Usability Scale instrument measuring operational friction.
- **Justice Perception:** Colquitt Organizational Justice Survey measuring informational justice (clarity and reasonableness) and procedural justice (voice, consistency, and ability to request factual correction).
- **Double-Blind Lab Tool:** Administration portal enables researchers to assign anonymous subject IDs (P1, P2), guide sessions with timed tasks, and export structured analysis reports with Cronbach's alpha.

---

## 6. Security, Cryptographic Audit Chains & Regulatory Compliance

### 6.1 EU AI Act High-Risk Compliance
Employment decision-support systems are classified as High-Risk under Annex III of the EU AI Act. MeritLens was built to comply with these stringent regulations:
- **Article 14 (Human Oversight):** MeritLens enforces human-in-the-loop governance. The AI cannot execute promotions autonomously; it advises managers and HR committees.
- **Article 12 (Traceability & Record-Keeping):** All predictions, human overrides, and managerial justifications are persistently logged in immutable storage.
- **Article 10 (Data Governance & Bias Monitoring):** Four-Fifths fairness gates block biased deployments, and the Population Stability Index (PSI) monitors live data drift.

### 6.2 SHA-256 Cryptographic Audit Hash Chains
To prevent retroactive manipulation by rogue administrators or compromised accounts, the audit trail operates as a tamper-evident blockchain-style hash chain:

$$\text{Block Hash}_n = \text{SHA-256}\Big(\text{Block Hash}_{n-1} \,\|\, \text{Timestamp} \,\|\, \text{Actor ID} \,\|\, \text{Action} \,\|\, \text{Payload}\Big)$$

Any modification to a past nomination, score, or manager justification breaks all downstream hashes. Auditors can click "Verify Chain" in the UI to mathematically validate the entire organizational history in seconds.

### 6.3 Privacy by Design & GDPR Alignment
- **GDPR Articles 15 & 20:** One-click personal data export allows employees to download their full dossier, predictions, and dispute history in structured JSON.
- **GDPR Article 17:** Right to Erasure support with anonymization safeguards for historic aggregate fairness audits.
- **Demographic Cohort Masking:** Aggregate fairness reports mask any demographic cohort containing fewer than 5 employees (`<5`) to eliminate re-identification risks.

---

## 7. Supervisory Defense & Q&A Strategy

### Team Presentation Distribution

| Team Member Role | Assigned Topic Focus | Primary Live System Demo |
|---|---|---|
| **Speaker 1: Product & Ethics** | Problem statement, systemic bias, 3-step cycle (Predict, Explain, Respond), procedural justice. | Employee Portal ("My Growth"), Natural-Language Explanations, Interactive "What-If" Sliders |
| **Speaker 2: Machine Learning** | Dataset properties, why Monotonic EBM beat XGBoost, PR-AUC vs ROC-AUC, EEOC Four-Fifths gate. | Model Card, Feature Importance Chart, Live Organizational Fairness Dashboard |
| **Speaker 3: Governance & Workflow** | Manager 4-part rubric, override justifications, HR review, Finance separation of duties, dispute tickets. | Submit Manager Nomination, HR Approval with Hold, Finance Compensation Sign-Off |
| **Speaker 4: Architecture & Security** | FastAPI/React architecture, N+1 query elimination, SHA-256 audit chain, EU AI Act compliance. | Click "Verify Chain" in Audit Log, 400 Backend Pytest Summary, User Study Portal |

### Top 4 Defense Questions & Model Answers

**Q1: "Why did you select EBM over XGBoost if XGBoost had a slightly higher validation PR-AUC?"**  
> *"XGBoost achieved a PR-AUC of 0.4699 compared to EBM's 0.4671—a negligible difference of 0.0028. However, XGBoost produced common-sense monotonicity violations in 21.9% of tests, meaning employees improving their skills could see their scores drop. EBM achieved 0.0% violations while delivering exact additive explanations without relying on post-hoc linear approximations like LIME."*

**Q2: "Why did you eliminate the Department feature if it was highly predictive?"**  
> *"Including department increased PR-AUC to 0.6325, but it learned historical organizational inequality: Engineering had a 33% promotion rate while Support had 2%. Using department would institutionalize past unequal opportunity. Eliminating department leveled the playing field, ensuring candidates are judged on individual growth rather than team placement."*

**Q3: "How do you guarantee employees cannot game the AI with dispute tickets?"**  
> *"The feedback channel is architecturally quarantined (verified in `test_isolation.py`). User ratings and submitted correction tickets have zero programmatic connection to feature matrices. A score recalculates ONLY if HR independently validates supporting evidence and amends the underlying database record."*

**Q4: "What happens when a manager overrides the AI recommendation?"**  
> *"MeritLens is a decision-support system, not an autonomous decider. Managers can nominate candidates below the threshold or pass over high-scoring candidates, but the interface forces them to complete a structured 4-part behavioral rubric and provide a written justification. This creates a transparent audit trail for HR committee scrutiny."*

---

## 8. Master Performance & Calibration Metrics Cheat Sheet

| Benchmark Metric Category | Verified Quantitative Result | Significance & Context |
|---|---|---|
| **Dataset Scale** | 100,000 synthetic rows (Kumar, 2026) | Stratified split: 70k train, 10k val, 20k test |
| **Base Promotion Rate** | 10.0% positive class | Realistic imbalanced organizational distribution |
| **EBM Test ROC-AUC** | **0.8833** | Strong global ranking and discrimination capacity |
| **EBM Test PR-AUC** | **0.4736** | 4.7x lift over 0.10 chance baseline |
| **Decision Threshold** | **0.2283** | Optimized for maximum F1 on validation set |
| **EBM Test Precision / Recall** | 41.02% / 59.50% | F1-Score = 0.4856 at 0.2283 threshold |
| **Monotonicity Violations** | **0.0% (EBM)** vs 21.9% (XGBoost) | Proves that positive growth never lowers score |
| **Brier Score / Brier Skill** | 0.0677 / 0.248 | High probability calibration accuracy |
| **Expected Calibration Error** | **0.0056** (10 deciles) | Scores near 0.23 reflect 23.7% actual promotions |
| **Gender Four-Fifths Ratio** | **0.982** (Female 14.6%, Male 14.4%) | Passed EEOC adverse impact threshold (>0.80) |
| **Age Four-Fifths Ratio** | **0.963** (Under 40: 14.8%, 40+: 14.2%) | Passed EEOC adverse impact threshold (>0.80) |
| **Education Four-Fifths Ratio** | **0.887** (Bachelor 14.3%, PhD 16.1%) | Passed EEOC adverse impact threshold (>0.80) |
| **Demographic Proxy Signal** | **ROC-AUC = 0.500** (Zero Signal) | Performance inputs do not encode protected traits |
| **Explanation Exactness Gap** | **0.000347** (Log-odds diff) | Mathematically exact additive decomposition |
| **Counterfactual Tip Reach** | **90.7%** (98 of 108 candidates) | Achievable milestone roadmap to promotion threshold |
| **Feedback Isolation Check** | Byte-for-byte invariant | Proves sentiment feedback cannot game the AI |
| **Automated Test Suites** | **400 backend pytest cases** | 100% pass across 37 test modules |
| **Accessibility Audit** | **0 WCAG 2.1 A/AA violations** | 45 screens audited with axe-core in light/dark |
| **Batch Scoring Latency** | **13 ms** for 5,000 employees | Vectorized inference eliminates runtime bottlenecks |

---

## 9. Project Documentation Index & Navigation Map

| Document Filename | Document Scope & Summary | Target Audience | Read Time |
|---|---|---|---|
| [README.md](file:///c:/Projects/HR-simple/README.md) | Complete system overview, local installation guide, role quickstarts, and execution commands. | All Team Members & Evaluators | 10 min |
| [TEAM_PROJECT_OVERVIEW.md](file:///c:/Projects/HR-simple/docs/TEAM_PROJECT_OVERVIEW.md) | High-level summary, presentation role division, 10-minute crash course on system philosophy. | Team Members & Presenters | 8 min |
| [HOW_IT_WORKS.md](file:///c:/Projects/HR-simple/docs/HOW_IT_WORKS.md) | Exhaustive technical deep-dive into every database table, API endpoint, auth token, and review step. | Backend Developers & Architects | 25 min |
| [EVALUATION_RESULTS.md](file:///c:/Projects/HR-simple/docs/EVALUATION_RESULTS.md) | Byte-for-byte empirical evaluation log; all benchmark tables, calibration deciles, and fairness checks. | ML Specialists & Evaluators | 10 min |
| [USER_TEST.md](file:///c:/Projects/HR-simple/docs/USER_TEST.md) | Complete user study protocol: 11 tasks, SUS questionnaire, Colquitt justice survey, lab procedure. | HCI & Usability Researchers | 10 min |
| [THESIS_GUIDE.md](file:///c:/Projects/HR-simple/docs/THESIS_GUIDE.md) | Academic framing: Research questions (RQ1-RQ4), methodology justification, literature citations. | Report Authors & Dissertation Leads | 20 min |
| [LIMITATIONS.md](file:///c:/Projects/HR-simple/docs/LIMITATIONS.md) | Critical evaluation of synthetic data constraints, department disparities, and future improvements. | Defense Prep & Examiners | 8 min |
| [DATA_MODEL.md](file:///c:/Projects/HR-simple/docs/DATA_MODEL.md) | Entity relationship descriptions, database tables, audit chain schemas, and foreign keys. | Database & Backend Engineers | 10 min |
| [BACKUPS.md](file:///c:/Projects/HR-simple/docs/BACKUPS.md) | Automated database backup routines, point-in-time recovery, and operational integrity. | System Administrators | 5 min |
