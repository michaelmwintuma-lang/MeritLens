# CHAPTER 3: METHODOLOGY

> **Status:** Fully Revised & Corrected Edition (Incorporating Academic City Criteria)  
> **Word Document with Blue Highlights:** [Thesis_Chapter_3_Methodology_Corrected.docx](file:///c:/Projects/HR-simple/docs/Thesis_Chapter_3_Methodology_Corrected.docx) (or root [Thesis_Chapter_3_Methodology_Corrected.docx](file:///c:/Projects/HR-simple/Thesis_Chapter_3_Methodology_Corrected.docx))  
> **Changelog & Audit Guide:** [docs/THESIS_CORRECTIONS_CHANGELOG.md](file:///c:/Projects/HR-simple/docs/THESIS_CORRECTIONS_CHANGELOG.md)

---

### 3.0 Introduction
This chapter details the research methodology, system requirements, architecture, model development, and empirical evaluation strategy for the MeritLens platform. Organized in alignment with the project's specific objectives, the methodology addresses: (1) predictive modeling and fairness auditing (Objective 1); (2) explainability and actionable recourse methods (Objective 2); and (3) employee feedback and contestability channels (Objective 3). The chapter concludes with the human-in-the-loop decision workflow, implementation technologies, and the comprehensive evaluation plan.

---

### 3.1 Research Approach
This study adopts the **Design Science Research (DSR)** methodology (Peffers et al., 2007; Hevner et al., 2004), which is specifically suited for information systems research whose primary contribution is an innovative artifact that solves an identified organizational problem. The research process follows six iterative stages:
1. Problem identification (Chapter 1);
2. Literature-grounded objective definition (Chapter 2);
3. Artifact design and development (Chapter 3);
4. End-to-end multi-role demonstration across simulated organizational personas;
5. Empirical evaluation against technical, fairness, and human factors benchmarks (Chapter 4); and
6. Scientific communication in this dissertation.

The artifact development followed an iterative refinement cycle. For instance, initial algorithmic formulations occasionally suggested reducing certain performance metrics to cross the threshold, leading directly to the implementation of the strict improvement-only (monotonicity) constraint in Section 3.5.4.

---

### 3.2 Requirements Analysis
System requirements were synthesized from the problem statement, the literature design implications in Chapter 2, and the functional needs of each organizational role. Table 3.1 outlines the functional requirements by user role, and Table 3.2 details the non-functional requirements.

#### Table 3.1: Functional Requirements by User Role
*(Note: Restored the missing "Employee" role omitted in the initial draft)*

| User Role | Core Functional Requirements |
|---|---|
| **Employee** *(Restored)* | Inspect personal promotion readiness score and percentile rank; view plain-language explanations of top contributing factors; test interactive "what-if" simulations; view actionable counterfactual improvement tips and convert tips into developmental goals; rate explanation clarity and usefulness (1–5 scale); submit formal factual record dispute tickets accompanied by document evidence. |
| **Manager** | Review team members' readiness metrics and growth histories; set and track developmental goals with team members; submit promotion nominations using a structured 4-criteria rubric (1–5 scale) with mandatory justifications when overriding AI advice; designate managerial cover during absences. |
| **HR Specialist / Committee** | Create and manage review cycles; review manager nominations alongside model readiness scores; hold decisions pending record dispute resolution; confirm or reject employee record correction tickets; enforce compensation policy bands; inspect live fairness dashboards; inspect model cards before releasing model versions; approve/decline requests under the optional four-eyes rule; execute GDPR data erasure requests. |
| **Finance Officer** | Inspect approved promotion nominations to verify and sign off on proposed salary increases against organizational policy bands (default: 5%–15%); return non-compliant compensation proposals to HR with written feedback. |
| **Compliance Auditor** | Read-only access to tamper-evident cryptographic audit logs, model registry, live EEOC fairness metrics, and aggregated feedback trends; blinded from individual employee feedback ratings. |
| **System Administrator** | Provision user accounts and configure organizational reporting lines; monitor system health (model status, fairness gates, data drift via PSI, email delivery); inspect automated database backup status; administer the built-in double-blind user study module. |

#### Table 3.2: Non-Functional Requirements

| Requirement Category | Technical Specification & Architectural Implementation |
|---|---|
| **Feedback Privacy** | Employee explanation ratings are presented exclusively as aggregate metrics (<5 cohort masking); managers are strictly prohibited from viewing team ratings or pending dispute tickets. |
| **Feedback & Scoring Isolation** | Feedback tables and sentiment ratings are architecturally separated from model feature tables and are never read by the prediction engine. |
| **Human Review & Data Integrity** | Employees cannot directly alter model inputs; predictions recalculate only after HR independently validates documentary evidence and commits an audited database change. |
| **Security & Authorization** | Role-Based Access Control (RBAC) enforced on the server for every endpoint; salted PBKDF2-SHA256 password hashing (200,000 rounds); signed, expiring JWT session tokens; rate limiting on failed logins; automatic session timeout. |
| **Explainability** | Every prediction is accompanied by exact additive log-odds feature contributions; models are blocked by an automated EEOC Four-Fifths fairness gate prior to release. |
| **Accountability & Auditability** | All nominations, administrative overrides, pay changes, and model deployments are recorded in an append-only audit log secured by SHA-256 cryptographic hash chains. |
| **Usability & Accessibility** | Clean, high-contrast user interfaces; adherence to WCAG 2.1 A/AA standards (0 axe-core errors); operational status is never conveyed by color alone. |
| **Data Protection (GDPR)** | Self-service personal data export (JSON) under Articles 15 & 20; right to erasure under Article 17; automated data retention purging schedules. |
| **Reliability & Resilience** | Versioned database migrations, automated nightly backups with SHA-256 checksums and verified recovery tests, and structured error logging with administrative notifications. |
| **Scalability** *(Corrected)* | List pages use a fixed number of database queries, however many employees there are, so response times stay steady as the organisation grows. |

---

### 3.3 System Architecture
MeritLens is engineered as a three-tier decoupled web architecture (Figure 3.1): a presentation layer built in React 19, an application services layer powered by Python FastAPI, and an isolated relational persistence layer (SQLite for development, PostgreSQL 16 for production).

#### 3.3.1 Component Architecture
The presentation tier communicates with the backend exclusively via HTTPS/JSON REST APIs. All business logic is encapsulated within independent modular packages:
* **promotion:** predictive inference, exact explanations, counterfactual tips, nomination rubrics;
* **feedback:** explanation ratings, record dispute ticketing, aggregate dashboards;
* **governance:** model registry, SHA-256 audit log, live fairness monitoring;
* **privacy:** GDPR export, erasure, retention; and
* **accounts & shared services:** authentication, token issuance, and user management.

Server-side middleware verifies user roles and session token validity on every incoming request, ensuring that the client interface cannot bypass authorization constraints.

**Figure 3.1: System Architecture of MeritLens with the Isolation Boundary**  
*(Insert Figure 3.1 here)*

#### 3.3.2 Architectural Isolation of the Feedback Channel
Although the feedback and prediction components share the application runtime and audit infrastructure, they are architecturally isolated to eliminate adversarial feedback gaming. The feedback module operates on dedicated database tables that are never referenced, imported, or queried by the prediction engine. This isolation is verified both statically through dependency analysis and dynamically at runtime: calling the prediction API triggers zero SQL queries against feedback tables.

Automated regression suites (`test_isolation.py`) verify that prediction outputs remain byte-for-byte invariant before and after negative feedback or pending disputes are submitted. The only mechanism through which employee feedback can influence a score is via an HR-verified factual correction (Section 3.7). Similarly, developmental goals negotiated between employees and managers are stored in a separate table and do not alter model inputs until corresponding workplace achievements are formally recorded.

---

### 3.4 Promotion Prediction Model

#### 3.4.1 Data and Inputs
The model is trained on the Employee Promotion Prediction Dataset (Kumar, 2026), a synthetic dataset released on Kaggle under the CC0 Public Domain license. It comprises 100,000 simulated employee records across seven departments, encompassing 45 raw columns spanning multi-year performance evaluations, productivity metrics, leadership indicators, training participation, working hours, and compensation, alongside the binary promotion outcome (10.0% positive base rate).

The synthetic dataset was selected over older alternatives (such as the 54,808-record WNS Analytics dataset) because it provides detailed performance and skill-growth attributes (e.g., peer feedback, innovation ratings, attendance reliability) necessary to generate actionable, interpretable explanations. Exactly 20 features were selected as model inputs, with all exclusions documented in Table 3.3.

**Operational Definition of Promotion Readiness:**  
The extent to which an employee's current performance and developmental trajectory resembles that of employees who were historically promoted within the organization. The model computes a continuous readiness score in the range $[0, 1]$; scores equal to or exceeding the decision threshold $t^*$ (Section 3.4.4) indicate a recommendation for promotion. Crucially, the score represents a calibrated ranking against threshold criteria rather than an unconditional guarantee. Because historical outcomes inherently reflect past organizational biases, the model is strictly constrained: protected characteristics and salary proxies are excluded, monotonic growth constraints are enforced, and an automated Four-Fifths fairness gate must be satisfied prior to release.

#### Table 3.3: Model Inputs Used and Attributes Excluded

| Feature Category | Attributes Included / Excluded | Selection Rationale & Status |
|---|---|---|
| **Performance (Used: 12)** | Performance score; annual performance delta (engineered); manager rating; peer feedback; KPI achievement; projects completed; tasks completed; deadline adherence; innovation, leadership, problem-solving, and technical skill scores. | Direct measures of employee output and competency. |
| **Development (Used: 4)** | Training hours completed, professional certifications earned, cross-department projects, mentoring sessions logged. | Actionable indicators of skill development. |
| **Reliability (Used: 2)** | Attendance rate, late arrival days. | Objective measures of work commitment. |
| **Career Stage (Used: 2)** | Years since last promotion, years in current role. | Captures professional tenure and organizational velocity. |
| **Protected Attributes (Excluded)** | Gender, age, education level, marital status. | Excluded to prevent demographic discrimination; retained solely for post-hoc fairness audits. |
| **Department (Excluded)** | Department category (7 departments). | Excluded: historical promotion rates varied from 2.0% (Support) to 33.2% (Engineering), biasing predictions by location. |
| **Compensation (Excluded)** | Base salary, salary increase history, bonus, stock options. | Excluded: prevents carrying historical wage disparities forward into promotion decisions. |
| **Attitudes & Hours (Excluded)** | Engagement survey score, job satisfaction, monthly hours, overtime hours, meeting hours. | Excluded: subjective attitude sentiment and hours spent, rather than actual work delivered. |
| **Circumstances (Excluded)** | Remote-work ratio, contract type, city tier, team size, company tenure, internal mobility. | Excluded: environmental circumstances rather than individual merit. |
| **Earlier Performance (Replaced)** | Performance last year, performance two years ago. | Replaced by engineered performance trend delta (correlation 0.92). |
| **Identifier (Excluded)** | Employee ID. | Unique record key with no predictive value. |

**Dataset Limitations:**  
Diagnostic audits confirm the simulated nature of the data: missing values and duplicate rows are exactly zero, gender is evenly split (50.1% female, 49.9% male), and promotion rates across city tiers and marital status are exactly 10.0%. Furthermore, unobserved drivers such as executive sponsorship or leadership visibility restrict the upper bound of predictive accuracy. In addition, about 2% of extreme outliers on hours and completed projects exist in the raw distribution; consequently, counterfactual tips are bounded between the 5th and 95th percentiles. All empirical results strictly describe the system on this benchmark data.

#### 3.4.2 Feature Engineering and Pre-processing
Diagnostic correlation analysis revealed an exceptionally high correlation ($r \approx 0.92$) between successive annual performance scores, which can cause multicollinearity and opposite sign weights in linear models. Performance was re-engineered into the current performance score and an annual performance trend delta:

$$\text{Performance Trend} = P_t - P_{t-1} \quad (3.1)$$

where $P_t$ denotes the current evaluation score and $P_{t-1}$ denotes the prior year's evaluation. Continuous variables are standardized for linear models using training statistics:

$$z = \frac{x - \mu}{\sigma} \quad (3.2)$$

All pre-processing is encapsulated in a unified scikit-learn pipeline applied consistently to training and serving data.

**Data Partitioning:**  
The 100,000 records were partitioned using stratified sampling (random seed 42) into 70% training (70,000), 10% validation (10,000), and 20% held-out test data (20,000). Pre-processing statistics were fitted strictly on the training partition.

**Figure 3.2: Promotion Model Training and Selection Pipeline**  
*(Insert Figure 3.2 here)*

#### 3.4.3 Model Comparison and Monotonic EBM Formulation
Four candidate architectures were trained and benchmarked: Logistic Regression, Random Forest (Breiman, 2001), XGBoost (Chen & Guestrin, 2016), and the Monotonic Explainable Boosting Machine (EBM) (Lou et al., 2013; Nori et al., 2019).

The Explainable Boosting Machine is a Generalized Additive Model with pairwise interactions ($GA^2M$) that learns one discrete shape function per feature:

$$\text{log-odds}(x) = \beta_0 + \sum_{j=1}^{p} f_j(x_j) \quad (3.3)$$

where $\beta_0$ is the intercept baseline and $f_j$ represents the learned univariate spline shape function for input $x_j$. The promotion readiness probability $p(x)$ is obtained via the standard logistic sigmoid transformation of the log-odds. Crucially, monotonic spline constraints are enforced across actionable inputs, guaranteeing that $f_j$ is strictly non-decreasing.

**Model Selection Protocol (Three Sequential Decision Gates):**
1. **Monotonicity Verification:** The initial screening step applies a common-sense monotonicity check across 2,000 validation candidates. Actionable inputs are increased by +0.5 standard deviations in their improving direction. The violation rate $V$ represents the percentage of instances where an employee's score decreased. Only models achieving $V = 0\%$ are eligible for selection.
2. **Validation PR-AUC Ranking:** Eligible models are compared on validation Precision-Recall AUC.
3. **Parsimony Rule:** When models exhibit comparable accuracy, the most interpretable glass-box model within 0.01 PR-AUC of the top performer is selected (Equation 3.4; Rudin, 2019):

$$\text{PR-AUC}_m \ge \text{PR-AUC}_{\text{best}} - 0.01, \quad \text{with } V_m = 0\% \quad (3.4)$$

#### 3.4.4 Decision Threshold and Evaluation Metrics
Because promotion is an imbalanced outcome (10% positive rate), overall classification accuracy is misleading. The decision threshold $t^*$ is tuned exclusively on the validation set to maximize the F1-score:

$$t^* = \operatorname{argmax}_t F_1(t) \quad (3.5)$$

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}} \quad (3.6) \qquad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}} \quad (3.7)$$

$$F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}} \quad (3.8)$$

Area Under the Precision-Recall Curve (PR-AUC) serves as the primary evaluation metric (Equation 3.9; Saito & Rehmsmeier, 2015), benchmarked against the 0.10 chance baseline:

$$\text{PR-AUC} = \sum_{n} (R_n - R_{n-1}) P_n \quad (3.9)$$

In addition, ROC-AUC, confusion matrices, and probability calibration via the Brier score (Brier, 1950) are evaluated:

$$\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} (p_i - y_i)^2 \quad (3.10)$$

---

### 3.5 Explanation Methods

#### 3.5.1 Exact Additive Contributions
Because the chosen EBM is an additive model, each prediction decomposes exactly into a linear sum of feature contributions read directly from the model's learned terms. The contribution $\phi_j$ of input $j$ is calculated relative to the average employee over the training distribution:

$$\phi_j = f_j(x_j) - \mathbb{E}[f_j(x_j)] \quad (3.11)$$

$$\text{base} + \sum_{j=1}^{p} \phi_j = \text{log-odds}(x) \quad (3.12)$$

where $\text{base} = \beta_0 + \sum_j \mathbb{E}[f_j(x_j)]$ represents the baseline log-odds of the average employee. For an additive model, these exact contributions mathematically equal the Shapley values (SHAP; Lundberg & Lee, 2017) without requiring sampling approximations.

#### 3.5.2 LIME as an Independent Second Opinion
LIME provides an independent audit by fitting a sparse local linear surrogate model $g$ around perturbed copies of the employee record (Equation 3.13; Ribeiro et al., 2016):

$$\xi(x) = \operatorname{argmin}_{g \in G} \sum_{z \in Z} \pi_x(z) [f(z) - g(z)]^2 + \Omega(g) \quad (3.13)$$

To ensure transparency regarding local surrogate fidelity, the weighted goodness-of-fit $R^2$ is computed and displayed (Equation 3.14):

$$R^2 = 1 - \frac{\sum_z \pi_x(z) [f(z) - g(z)]^2}{\sum_z \pi_x(z) [f(z) - \bar{f}]^2} \quad (3.14)$$

If $R^2$ falls below 0.50, the interface displays an explicit warning. Exact additive contributions serve as the primary explanation, with LIME functioning strictly as a comparative check.

#### 3.5.3 Plain-Language Summaries and Role-Based Presentation
To ensure non-technical comprehension, predictions are summarized into natural language identifying the employee's readiness score, the two factors that contributed most positively, and the two factors that held the score back. On the employee's 'My Growth' portal, complex log-odds mathematics are hidden behind an optional "Show technical details" toggle, presenting a clean, empowering interface.

#### 3.5.4 Interactive What-If Tool and Actionable Counterfactual Tips
The What-If tool enables employees to simulate potential growth by adjusting only actionable inputs within realistic bounds without modifying stored database records. Counterfactual improvement tips compute the minimum realistic growth necessary to reach the promotion threshold $t^*$, constrained strictly to actionable factors in their improving direction (Equation 3.15; Wachter et al., 2018; Ustun et al., 2019):

$$\min_{\Delta} \sum_{j \in \text{actionable}} \frac{|\Delta_j|}{\sigma_j} \quad \text{subject to} \quad p(x + \Delta) \ge t^*, \quad 0 \le d_j \Delta_j \le \sigma_j, \quad x_j + \Delta_j \in [q_{j,0.05}, q_{j,0.95}] \quad (3.15)$$

where $\Delta_j$ is the required growth for actionable input $j$, $\sigma_j$ is the standard deviation, $d_j$ is the direction of improvement (+1 for training, -1 for late days), and bounds are restricted to the 5th and 95th percentiles. Employees can convert any tip into a formal developmental goal with a single click.

#### 3.5.5 Evaluating Explanation Quality
Explanation quality is evaluated across four empirical dimensions: (1) Mathematical exactness (gap in Equation 3.12); (2) Common-sense monotonicity (zero score reductions under positive growth); (3) LIME local fidelity (Equation 3.14); and (4) Agreement between LIME's top feature and the top five exact additive contributions (Equation 3.16):

$$\text{Agreement} = \frac{\text{Employees with top LIME factor in top-5 exact contributions}}{\text{Total employees evaluated}} \quad (3.16)$$

---

### 3.6 Fairness Audit and Automated Build Gate
The platform enforces the US EEOC Four-Fifths (80%) Rule across gender, age groups, and education levels on the test set. The selection rate $\text{SR}_g$ for group $g$ is the proportion recommended:

$$\text{SR}_g = \frac{1}{n_g} \sum_{i \in g} \mathbb{I}[p_i \ge t^*] \quad (3.17)$$

The adverse impact ratio must satisfy Equation 3.18 (EEOC, 1978; Feldman et al., 2015):

$$\text{Disparate Impact Ratio} = \frac{\min_g \text{SR}_g}{\max_g \text{SR}_g} \ge 0.80 \quad (3.18)$$

Any candidate model producing an adverse impact ratio below 0.80 is automatically blocked from deployment by the build pipeline. Equal opportunity (true-positive rate ratios) and intersectional cohorts (e.g., gender within age bands) are also evaluated and reported on the model card.

**Proxy Variable Detection:**  
To ensure excluded demographic variables are not secretly reconstructed through correlated performance inputs (Barocas & Selbst, 2016), three statistical tests are conducted:
1. Effect size screening using Cohen's $d$ ($<0.20$), Pearson $r$ ($<0.10$), and $\eta^2$ ($<0.01$);
2. Adversarial classifiers (linear and gradient-boosted) trained to predict demographic traits from the 20 merit inputs, where an ROC-AUC near 0.50 mathematically proves zero proxy leakage; and
3. Department confounding analysis.

#### 3.6.1 Model Release Governance and Live Monitoring
A newly trained model is registered as a candidate in the model registry. It can be promoted to production only after an authorized HR specialist inspects the comprehensive model card, reviews department-level projection deltas, and signs off with a written release justification. In production, live fairness monitoring recalculates the Four-Fifths ratio across nominations and approvals, while Population Stability Index (PSI) tracks demographic and feature drift.

---

### 3.7 Employee Feedback Channel
The employee feedback channel operationalizes Objective 3 through a "Respond to this explanation" interface on the "My Growth" portal, providing two distinct pathways (Figure 3.3):

**Figure 3.3: Employee Feedback Channel Architecture (Two Distinct Routes)**  
*(Insert Figure 3.3 here)*

* **Pathway 1 (Explanation Ratings):** Employees can rate explanation clarity ("This explanation was clear") and usefulness ("This explanation was useful") on a 1–5 scale, flag individual factors perceived as unfair, and provide written commentary. Ratings are stored alongside model metadata and displayed exclusively in aggregate to HR specialists and compliance auditors. Managers are blinded to feedback ratings to prevent retaliation.
* **Pathway 2 (Factual Record Corrections):** If an employee identifies a factual discrepancy in their personnel records (e.g., unrecorded training hours or project completions), they submit a correction ticket specifying the proposed value and attaching documentary evidence (e.g., PDF review forms or certificates). The ticket is routed to HR specialists for verification. An employee cannot edit their record directly; a prediction recalculates only after HR formally validates the evidence, updates the underlying database, and records an audited change delta.
* **Feedback Safeguards:** An HR feedback dashboard displays the clarity rate, usefulness rate, and most contested factors. To preserve employee anonymity, cohort masking suppresses any demographic group with fewer than 5 ratings, displaying counts of 1 to 2 as "<3". Models are never automatically retrained on user feedback, preventing feedback loops and adversarial manipulation.

---

### 3.8 Human-in-the-Loop Decision Process
In accordance with EU AI Act Article 14 mandates, MeritLens maintains strict human-in-the-loop oversight throughout the promotion lifecycle (Figure 3.4). The AI operates strictly as an advisory decision-support tool; humans retain all decision-making authority:
* **Manager Nomination:** Managers nominate team members by completing a structured 4-criteria rubric (Job Mastery, Collaboration, Problem Solving, Continuous Growth; rated 1–5 with concrete behavioral examples). If a manager nominates an employee below the AI threshold or passes over a top candidate, a mandatory written justification is required.
* **HR Deliberation:** HR committees review nominations alongside AI readiness scores, explanations, and any open employee dispute tickets. If a record dispute is pending, HR can place the nomination on "Hold" until the factual record is verified. Approved nominations pass to Finance.
* **Finance Compensation Sign-Off:** Finance officers review approved nominations solely to certify that proposed salary increases conform to organizational policy bands (default: 5%–15%). Finance is blinded to AI scores, performance ratings, and demographic data (strict separation of duties).
* **Four-Eyes Governance:** Under an optional four-eyes rule, high-impact administrative actions (releasing a model or confirming a dispute ticket that shifts an employee across the threshold) require a second HR specialist's confirmation.

**Figure 3.4: Human-in-the-Loop Promotion Decision Process**  
*(Insert Figure 3.4 here)*

---

### 3.9 Implementation, Testing and Monitoring
MeritLens is implemented as a modern full-stack web platform utilizing React 19 (Vite, React Router 7, Tailwind CSS) for the presentation tier and Python 3.11 FastAPI for the backend API. Relational persistence is managed via SQLite in development and PostgreSQL 16 in containerized production deployments. Authentication utilizes signed, expiring JSON Web Tokens (JWT) stored in HTTP-only, SameSite cookies with salted PBKDF2-SHA256 password hashing (200,000 rounds) and optional TOTP two-factor authentication.

**Automated Software Testing Suite:**  
Software quality is enforced through 400 backend pytest cases across 37 test modules, verifying role permissions, EEOC fairness gates, explanation exactness, Finance sign-offs, feedback channel isolation, GDPR compliance, and database query count scaling (`test_query_counts.py`). End-to-end browser journeys are verified with Playwright, and web accessibility is audited with axe-core against WCAG 2.1 A/AA standards (0 violations across 45 screens in light and dark themes).

---

### 3.10 Evaluation Plan
Table 3.4 summarizes the empirical evaluation matrix, linking each system dimension to its methodological instrument and corresponding research question.

#### Table 3.4: System Evaluation Matrix Mapped to Research Questions

| Evaluation Dimension | Methodological Instrument & Metrics | Target Research Question |
|---|---|---|
| **Predictive Validity & Calibration** | PR-AUC (Eq 3.9), ROC-AUC, Brier score (Eq 3.10), Expected Calibration Error (ECE), Confusion Matrix. | **RQ1** |
| **Algorithmic Fairness Gate** | EEOC Four-Fifths Disparate Impact Ratio (Eq 3.18), Equal Opportunity ratios, Proxy Variable detection ($d$, $r$, $\eta^2$, adversarial classifiers). | **RQ1** |
| **Explanation Exactness & Faithfulness** | Additive log-odds exactness gap (Eq 3.12), common-sense monotonicity checks ($V = 0\%$), LIME $R^2$ fidelity (Eq 3.14), LIME agreement (Eq 3.16), counterfactual tip feasibility. | **RQ2** |
| **Feedback Channel & Isolation** | Clarity rate (Eq 3.19), contest share (Eq 3.20), correction confirmation rate (Eq 3.21); byte-for-byte static and runtime SQL isolation tests. | **RQ3** |
| **Human Usability & Perceived Justice** | 11-task standardized user test protocol, System Usability Scale (SUS; Eq 3.22; Brooke, 1996), and 8 perceived justice items adapted from Colquitt (2001) measuring informational and procedural fairness. | **RQ4** |
| **Software Quality & Scalability** | 400 backend pytests, 10 browser journeys, WCAG 2.1 A/AA accessibility audit, 5,000-employee load test with query count regression verification. | **All RQs** |

**Feedback Channel Formulas:**
* Clarity Rate:

$$\text{Clarity Rate} = \frac{\text{Explanations rated 4 or 5 for clarity}}{\text{Total rated explanations}} \quad (3.19)$$

* Contest Share:

$$\text{Contest Share}_j = \frac{n_j}{\sum_k n_k} \quad (3.20)$$

* Correction Confirmation Rate:

$$\text{Confirmation Rate} = \frac{\text{Confirmed corrections}}{\text{Total resolved dispute requests}} \quad (3.21)$$

**Human Usability and Perceived Fairness Protocol:**  
The human-centered usability study employs 5 to 8 participants across 11 realistic workplace tasks (Nielsen & Landauer, 1993). Usability is benchmarked via the 10-item System Usability Scale (SUS; Brooke, 1996; Equation 3.22):

$$\text{SUS} = 2.5 \times \left[ \sum_{i \in \text{odd}} (s_i - 1) + \sum_{i \in \text{even}} (5 - s_i) \right] \quad (3.22)$$

interpreted against Sauro (2011) industry baselines. Perceived fairness is evaluated using eight Likert items adapted from Colquitt (2001) (four measuring informational justice regarding explanation clarity and reasonableness, and four measuring procedural justice regarding voice and error correction).

---

### 3.11 Chapter Summary
This chapter detailed the Design Science Research methodology, user requirements, and multi-tier system architecture of MeritLens. To achieve Objective 1, four candidate algorithms were evaluated on 100,000 synthetic records, prioritizing an interpretable Monotonic EBM that satisfies common-sense checks and the EEOC Four-Fifths fairness gate. For Objective 2, predictions are explained via exact additive contributions, LIME second opinions, plain-language summaries, and actionable counterfactual tips. For Objective 3, an architecturally isolated feedback channel empowers employees to rate explanations and request factual record corrections without compromising model scoring integrity. These mechanisms are reinforced by robust software testing, role separation, and a comprehensive evaluation plan. The empirical findings are presented in Chapter 4.
