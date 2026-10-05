"""
How each model input is named and shown to people, and which ones a person can work on.

improve: +1 if a higher value is an improvement, -1 if a lower value is (late days), None if it isn't something
a person can change by their own effort (time in role, department). Only improvable inputs appear in the what-if
sliders and in the tips.
"""

FEATURE_INFO = {
    "performance_score":          {"label": "Performance score",              "unit": "points",  "improve": +1, "whole": False},
    "performance_change":         {"label": "Change in performance since last year", "unit": "change", "improve": None, "whole": False},
    "manager_rating":             {"label": "Manager rating",                 "unit": "of5",     "improve": +1, "whole": False},
    "peer_feedback_score":        {"label": "Peer feedback",                  "unit": "of5",     "improve": +1, "whole": False},
    "kpi_achievement_percent":    {"label": "KPI achievement",                "unit": "percent", "improve": +1, "whole": False},
    "projects_completed":         {"label": "Projects completed",             "unit": "count",   "improve": +1, "whole": True},
    "tasks_completed":            {"label": "Tasks completed",                "unit": "count",   "improve": +1, "whole": True},
    "deadline_adherence_rate":    {"label": "Deadlines met",                  "unit": "rate",    "improve": +1, "whole": False},
    "innovation_score":           {"label": "Innovation score",               "unit": "points",  "improve": +1, "whole": False},
    "leadership_score":           {"label": "Leadership score",               "unit": "points",  "improve": +1, "whole": False},
    "problem_solving_score":      {"label": "Problem-solving score",          "unit": "points",  "improve": +1, "whole": False},
    "skill_assessment_score":     {"label": "Skill assessment score",         "unit": "points",  "improve": +1, "whole": False},
    "training_hours_last_year":   {"label": "Training hours last year",       "unit": "hours",   "improve": +1, "whole": False},
    "certifications_count":       {"label": "Certifications",                 "unit": "count",   "improve": +1, "whole": True},
    "cross_department_projects":  {"label": "Cross-department projects",      "unit": "count",   "improve": +1, "whole": True},
    "mentoring_sessions":         {"label": "Mentoring sessions",             "unit": "count",   "improve": +1, "whole": True},
    "attendance_rate":            {"label": "Attendance",                     "unit": "rate",    "improve": +1, "whole": False},
    "late_days":                  {"label": "Late days",                      "unit": "count",   "improve": -1, "whole": True},
    "years_since_last_promotion": {"label": "Years since last promotion",     "unit": "years",   "improve": None, "whole": True},
    "years_in_current_role":      {"label": "Years in current role",          "unit": "years",   "improve": None, "whole": True},
    "department":                 {"label": "Department",                     "unit": "text",    "improve": None, "whole": False},
}

IMPROVABLE = [name for name, info in FEATURE_INFO.items() if info["improve"] is not None]

# Natural limits: scores can't go above 100, ratings above 5, rates above 100%
UPPER_LIMIT = {"points": 100, "percent": 100, "of5": 5, "rate": 1.0}


def label(feature: str) -> str:
    return FEATURE_INFO[feature]["label"]


def format_value(feature: str, value) -> str:
    """A value in its everyday unit: '82', '90.5%', '4.1 / 5', '25 hours', '+3.2 points', 'Finance'."""
    unit = FEATURE_INFO[feature]["unit"]
    if unit == "text":
        return str(value)
    if unit == "rate":
        return f"{value * 100:.1f}%"
    if unit == "percent":
        return f"{value:.1f}%"
    if unit == "of5":
        return f"{value:.1f} / 5"
    if unit == "change":
        return f"{value:+.1f} points"
    if unit == "hours":
        return f"{value:.0f} hours"
    if unit == "years":
        return f"{value:.0f} year{'s' if round(value) != 1 else ''}"
    if unit == "count":
        return f"{value:.0f}"
    return f"{value:.1f}"
