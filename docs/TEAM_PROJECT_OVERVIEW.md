# MeritLens: Team Member Quick-Start & Presentation Guide

**"Fair, explainable promotion decisions, with a voice for every employee."**

This guide is designed for project group members to understand the entire MeritLens system in **under 10 minutes** so that everyone is aligned, confident, and presentation-ready.

---

## 1. What is MeritLens in Simple English?

Traditional workplace promotions are often accused of being a "black box"—fraught with favoritism, unwritten rules, and demographic bias. Conversely, standard AI systems that predict promotions can be op aque, can perpetuate historical discrimination, and offer employees zero recourse.

**MeritLens** is an **Explainable AI (XAI) Decision-Support System** designed for employee promotions. It follows a continuous 3-part cycle:

```
    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │  1. PREDICT  │  ────►  │  2. EXPLAIN  │  ────►  │  3. RESPOND  │
    │  Fairness-   │         │  Plain words │         │  Employee    │
    │  checked AI  │         │  & exact math│         │  voice & fix │
    └──────────────┘         └──────────────┘         └──────────────┘
           ▲                                                 │
           └──────────────── HR-Verified Fixes ──────────────┘
```

1. **Predict:** An AI model scores how ready an employee is for promotion based strictly on performance and growth records—**never** on gender, age, education, department, or salary. Any model that fails the legal Four-Fifths fairness rule is blocked.
2. **Explain:** Every score is explained in plain language: what helped the score, what held it back, and realistic "what-if" tips to reach the promotion threshold.
3. **Respond:** Employees have an active voice. They can rate the explanation or ask HR to correct factual errors in their record with evidence.

> **Crucial Rule:** The AI **never** makes the final decision. People decide (Managers recommend, HR approves, Finance signs off). Furthermore, an employee's complaint or feedback **never** changes their AI score directly.

---

## 2. The 6 Roles in the System

| Role | What They Do | Why It Matters |
|---|---|---|
| **Employee** | Views "My Growth", sees their readiness score, reads plain explanations, tests "what-if" simulations, and submits factual record corrections with evidence. | Gives employees transparency and voice (procedural justice). |
| **Manager** | Views team readiness scores, recommends candidates using a 4-criteria rubric (1–5 scale with real examples), and must write a justification if overriding the AI. | Prevents unreasoned favoritism while keeping human judgment. |
| **HR** | Manages review cycles, reviews manager nominations alongside the AI score, approves/rejects promotions, resolves record corrections, and monitors organization-wide fairness. | Ensures cross-company fairness, policy adherence, and final promotion sign-off. |
| **Finance** | Reviews approved promotions solely to approve or dispute the proposed salary increase (e.g., within 5–15% policy). | Separation of duties: Finance checks budget without seeing AI scores or performance notes. |
| **Admin** | Manages user accounts, assigns reporting lines, monitors system health, drift, and backups. | System operations and access control. |
| **Compliance Auditor** | Read-only access to tamper-evident audit trails, fairness metrics, and aggregate feedback. | Guarantees external accountability and regulatory compliance. |

---

## 3. Key Technical & Machine Learning Highlights

If the panel asks technical questions, here are the core facts every member should know:

1. **The Dataset:** 
   - 100,000 synthetic employee records from Kaggle (Kumar, 2026).
   - 10% historical promotion rate (imbalanced data).
   - Split: 70% Training, 10% Validation, 20% Held-out Test (20,000 employees).
2. **The Model:** 
   - **Monotonic Explainable Boosting Machine (EBM)** via InterpretML.
   - **Why EBM over XGBoost / Deep Learning?** EBM is an additive "glass-box" model. We enforced monotonic constraints so that improving a good habit (e.g., taking more training) **never** lowers a score (0% drops in EBM vs 21.9% drops in XGBoost).
3. **The Metrics:**
   - **ROC-AUC: 0.883** | **PR-AUC: 0.474** (against a 0.10 baseline).
   - *Why PR-AUC?* With only 10% positive class, ROC-AUC gives a false sense of security; PR-AUC tests the minority class directly.
4. **The Fairness Gate:**
   - Enforces the US EEOC **Four-Fifths Rule** (Selection Rate Ratio $\ge 0.80$).
   - MeritLens passed: **Gender (0.981)**, **Age Group (0.963)**, **Education (0.887)**.
5. **No Proxies:**
   - When we trained machine learning classifiers to predict gender or age using all 20 performance inputs, the accuracy was **ROC-AUC 0.50** (pure guessing).

---

## 4. How the "Respond" Channel Works (Zero Gaming)

One of the most impressive features of MeritLens is how it handles employee pushback:

- **Can an employee game the system?** **No.**
- Rating an explanation ("seems unfair") or submitting feedback is strictly isolated from the prediction pipeline (`test_isolation.py`).
- A score changes **only if**:
  1. The employee spots a factual error (e.g., "My 40 training hours were recorded as 4").
  2. The employee submits documentation/evidence.
  3. An HR administrator reviews and verifies the evidence.
  4. Once HR updates the record, the model re-scores the employee automatically, and the change is recorded in the audit log.

---

## 5. Security & Legal Governance (EU AI Act & GDPR)

- **EU AI Act Ready:** Employment AI is categorized as "High-Risk". MeritLens satisfies Article 14 (Human-in-the-loop oversight) and Article 12 (Traceability and auditability).
- **Tamper-Evident Audit Trail:** Every nomination, decision, pay rise, and model release is stored in an append-only log linked with **SHA-256 cryptographic hash chains**. Any alteration immediately breaks the chain.
- **Privacy by Design:** Protected demographic data is kept in an isolated table and is only used in aggregate for live fairness reporting. Groups under 5 people are masked (`<3` or hidden) to prevent de-anonymization.

---

## 6. Suggested Presentation Role Division

If your team is presenting together, here is a clean way to divide the speaking parts:

### Speaker 1: Introduction, Problem & System Overview
- **Topics:** The problem with traditional promotions (bias, opacity) and standard AI (black-box). The solution: MeritLens and the 3-step cycle (Predict, Explain, Respond).
- **Key Demo:** Show the **Employee Portal ("My Growth")** and the plain-language explanation with tips.

### Speaker 2: Machine Learning, Explainability & Fairness
- **Topics:** The dataset, why EBM was chosen over XGBoost (monotonicity), PR-AUC vs ROC-AUC, exact contributions vs LIME, and the Four-Fifths fairness gate.
- **Key Demo:** Show the **Model Card**, feature importances, and the **Live Fairness Dashboard**.

### Speaker 3: Human-in-the-Loop Workflow & Feedback Channel
- **Topics:** Manager nominations (4 structured criteria), HR decision dashboard, Finance sign-off (separation of duties), and how employees request record corrections without gaming the model.
- **Key Demo:** Show a **Manager nomination**, an **HR approval with hold**, and a **Finance sign-off**.

### Speaker 4: Architecture, Security, Limitations & Conclusion
- **Topics:** FastAPI + React architecture, PostgreSQL isolation, hash-chained audit logs, GDPR privacy rights (data export/erasure), synthetic data limitations, and future work.
- **Key Demo:** Show the **Audit Trail ("Check the chain")** and system health.

---

## 7. Existing Documents in This Repository (Where to Read More)

Depending on how deeply you or your teammates want to read, share these specific files:

| File Path | What It Contains | Who Should Read It | Reading Time |
|---|---|---|---|
| **`README.md`** | Complete system documentation, setup commands, and role guides. | Everyone | 10 mins |
| **`docs/THESIS_GUIDE.md`** | Thesis outline, research questions (RQ1–RQ4), academic citations, and direct answers to supervisor questions. | Main presenters / Report writers | 15 mins |
| **`docs/EVALUATION_RESULTS.md`** | All benchmark tables, exact scores, confusion matrices, and calibration metrics. | ML / Technical Speaker | 5 mins |
| **`docs/LIMITATIONS.md`** | Critical analysis of synthetic data, department task differences, and future extensions (essential for Q&A defense). | Everyone for defense prep | 5 mins |
| **`docs/HOW_IT_WORKS.md`** | Deep technical dive into every API endpoint, database schema, and test suite. | Developers / Backend specialists | 20 mins |
| **`docs/USER_TEST.md`** | The 11 usability tasks, System Usability Scale (SUS), and Colquitt organizational justice survey. | Usability / HCI presenter | 5 mins |
