"""
Which columns the promotion model may use, and how the data is prepared and split.

Only performance and development information is used. Protected characteristics and pay are never model inputs;
gender, age and education are kept aside only to check fairness afterwards.
"""
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "employee_promotion_dataset_100000.csv"
TARGET = "promoted"
RANDOM_STATE = 42

# ─── Model inputs ─────────────────────────────────────────────────────────────
NUMERIC_FEATURES = [
    # Performance
    "performance_score",            # this year's score
    "performance_change",           # this year minus last year (see add_performance_change)
    "manager_rating",
    "peer_feedback_score",
    "kpi_achievement_percent",
    "projects_completed",
    "tasks_completed",
    "deadline_adherence_rate",
    "innovation_score",
    "leadership_score",
    "problem_solving_score",
    "skill_assessment_score",
    # Development
    "training_hours_last_year",
    "certifications_count",
    "cross_department_projects",
    "mentoring_sessions",
    # Reliability
    "attendance_rate",
    "late_days",
    # Career stage
    "years_since_last_promotion",
    "years_in_current_role",
]
MODEL_FEATURES = NUMERIC_FEATURES

# Direction in which the model may use each input (monotonic constraints): +1 a higher value can only raise readiness,
# -1 it can only lower it, 0 no constraint. Improving anything a person controls (more training, fewer late days)
# can therefore never lower their score, and a bigger rise in performance never counts against them.
# Time in role and since last promotion stay free: the data decides how they matter.
MONOTONE = {
    "performance_score": +1, "performance_change": +1, "manager_rating": +1, "peer_feedback_score": +1,
    "kpi_achievement_percent": +1, "projects_completed": +1, "tasks_completed": +1, "deadline_adherence_rate": +1,
    "innovation_score": +1, "leadership_score": +1, "problem_solving_score": +1, "skill_assessment_score": +1,
    "training_hours_last_year": +1, "certifications_count": +1, "cross_department_projects": +1,
    "mentoring_sessions": +1, "attendance_rate": +1, "late_days": -1,
    "years_since_last_promotion": 0, "years_in_current_role": 0,
}

# ─── Kept out of the model, and why ───────────────────────────────────────────
FAIRNESS_ONLY = ["gender", "age", "education_level"]          # protected: used only to audit fairness
EXCLUDED = {
    "department": "where someone works says nothing about how well they work; with it, two people with the same "
                  "record could get different scores only because of their department",
    "gender": "protected characteristic",
    "age": "protected characteristic",
    "education_level": "protected characteristic (audited for fairness)",
    "marital_status": "protected characteristic",
    "salary": "pay: reflects past decisions and could carry old pay gaps into promotions",
    "salary_increase_percent": "pay",
    "bonus_last_year": "pay",
    "stock_options": "pay",
    "city_tier": "where someone lives says nothing about their work",
    "employee_engagement_score": "survey of attitudes, not performance",
    "job_satisfaction_score": "survey of attitudes, not performance",
    "internal_mobility_score": "not a measure of performance",
    "avg_monthly_hours": "rewards long hours rather than results, and disadvantages carers",
    "overtime_hours": "rewards long hours rather than results",
    "meeting_hours_per_month": "workload, not performance",
    "remote_work_ratio": "a working arrangement, not performance",
    "team_size": "a property of the team, not the person",
    "employment_type": "contract type, not performance",
    "years_at_company": "tenure; years in role and since last promotion already cover career stage",
    "performance_last_year": "replaced by performance_change",
    "performance_two_years_ago": "replaced by performance_change",
}


def add_performance_change(df: pd.DataFrame) -> pd.DataFrame:
    """
    The dataset has three yearly performance scores that move together very closely (highly correlated).
    Given all three, a linear model splits their effect in confusing ways, e.g. a large positive weight on one
    year and a large negative weight on another, which makes explanations misleading. So the model gets two
    clearer facts instead: this year's score and how much it changed since last year.
    """
    df = df.copy()
    df["performance_change"] = df["performance_score"] - df["performance_last_year"]
    return df


def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    """Read the employee CSV and add the engineered feature."""
    return add_performance_change(pd.read_csv(path))


def split_data(df: pd.DataFrame):
    """
    70% training, 10% validation, 20% test, stratified so each part has the same ~10% promotion rate.
    Validation is for choosing the model and threshold; the test set is used once, at the very end.
    """
    train, rest = train_test_split(df, test_size=0.30, stratify=df[TARGET], random_state=RANDOM_STATE)
    val, test = train_test_split(rest, test_size=2 / 3, stratify=rest[TARGET], random_state=RANDOM_STATE)
    return train, val, test


def build_preprocessor() -> ColumnTransformer:
    """Scale every input to a common range (average 0, spread 1), in the order of NUMERIC_FEATURES."""
    return ColumnTransformer([("numeric", StandardScaler(), NUMERIC_FEATURES)])
