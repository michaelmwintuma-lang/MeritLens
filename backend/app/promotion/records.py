"""
Adding and editing employees' work records: what HR types in (one at a time, or as a CSV file), and how it's checked.

HR enters values the way they appear in HR's own systems, and they're turned into the model's inputs:
- this year's AND last year's performance score; the model's "change since last year" is worked out from them
- rates (attendance, deadlines met) as everyday percentages, e.g. 93, stored as 0.93 like in the training data

Two kinds of check:
- errors: impossible values (a rating of 7 out of 5, negative late days, 2.5 certifications). Nothing is saved.
- warnings: possible, but outside what the model saw in training (e.g. 300 training hours). Saved, but the score
  is less reliable there, because the model is guessing beyond its experience.

Gender, age, education and pay are deliberately not asked for: the model doesn't use them.
"""
import csv
import io

from app.promotion.labels import FEATURE_INFO

# What HR enters, grouped as on the form. limits = what is possible at all; scale = how it's stored.
ENTRY_FIELDS = [
    # name,                       group,          limits,       whole, scale
    ("performance_score",         "Performance",  (0, 100),     False, 1),
    ("performance_last_year",     "Performance",  (0, 100),     False, 1),
    ("manager_rating",            "Performance",  (1, 5),       False, 1),
    ("peer_feedback_score",       "Performance",  (1, 5),       False, 1),
    ("kpi_achievement_percent",   "Performance",  (0, 200),     False, 1),
    ("projects_completed",        "Performance",  (0, 500),     True,  1),
    ("tasks_completed",           "Performance",  (0, 2000),    True,  1),
    ("deadline_adherence_rate",   "Performance",  (0, 100),     False, 100),
    ("innovation_score",          "Performance",  (0, 100),     False, 1),
    ("leadership_score",          "Performance",  (0, 100),     False, 1),
    ("problem_solving_score",     "Performance",  (0, 100),     False, 1),
    ("skill_assessment_score",    "Performance",  (0, 100),     False, 1),
    ("training_hours_last_year",  "Development",  (0, 2000),    False, 1),
    ("certifications_count",      "Development",  (0, 100),     True,  1),
    ("cross_department_projects", "Development",  (0, 100),     True,  1),
    ("mentoring_sessions",        "Development",  (0, 500),     True,  1),
    ("attendance_rate",           "Reliability",  (0, 100),     False, 100),
    ("late_days",                 "Reliability",  (0, 366),     True,  1),
    ("years_since_last_promotion", "Career",      (0, 60),      True,  1),
    ("years_in_current_role",     "Career",       (0, 60),      True,  1),
]
GROUPS = ["Performance", "Development", "Reliability", "Career"]
LABELS = {name: FEATURE_INFO[name]["label"] for name, *_ in ENTRY_FIELDS if name in FEATURE_INFO}
LABELS["performance_last_year"] = "Performance score last year"
LABELS["performance_score"] = "Performance score this year"
SCALE = {name: scale for name, _, _, _, scale in ENTRY_FIELDS}

CSV_COLUMNS = ["full_name", "department", "manager_username", *[name for name, *_ in ENTRY_FIELDS]]
MAX_CSV_ROWS = 5000


def field_list(stats: dict) -> list[dict]:
    """The form's fields, each with its possible range and the range the model saw in training (in entry units)."""
    fields = []
    for name, group, (low, high), whole, scale in ENTRY_FIELDS:
        trained = stats.get("performance_score" if name == "performance_last_year" else name)
        fields.append({
            "name": name, "label": LABELS[name], "group": group, "min": low, "max": high, "whole": whole,
            "percent": scale == 100,
            "typical": [round(trained["min"] * scale, 1), round(trained["max"] * scale, 1)] if trained else None,
            "example": round(trained["mean"] * scale, 0 if whole else 1) if trained else low,
        })
    return fields


def to_record(values: dict, stats: dict) -> tuple[dict, dict, dict]:
    """
    Check what HR entered and turn it into the model's inputs.
    Returns (record, errors, warnings); errors and warnings are {field name: message}.
    """
    errors, warnings, entered = {}, {}, {}
    for name, _, (low, high), whole, scale in ENTRY_FIELDS:
        raw = values.get(name)
        if raw is None or str(raw).strip() == "":
            errors[name] = f"{LABELS[name]} is missing."
            continue
        try:
            number = float(str(raw).strip().rstrip("%"))
        except ValueError:
            errors[name] = f"{LABELS[name]} must be a number (got '{raw}')."
            continue
        if not low <= number <= high:
            errors[name] = f"{LABELS[name]} must be between {low} and {high}{'%' if scale == 100 else ''}."
        elif whole and number != int(number):
            errors[name] = f"{LABELS[name]} must be a whole number."
        else:
            entered[name] = number
    if errors:
        return {}, errors, warnings

    # The model's inputs: change since last year instead of last year's score; rates as 0-1
    record = {name: entered[name] / SCALE[name] for name in entered if name != "performance_last_year"}
    record["performance_change"] = entered["performance_score"] - entered["performance_last_year"]

    for name, value in record.items():
        trained = stats.get(name)
        if trained and not trained["min"] <= value <= trained["max"]:
            label = FEATURE_INFO[name]["label"]
            scale = SCALE.get(name, 1)
            warnings[name] = (f"{label} is outside what the model saw in training "
                              f"({round(trained['min'] * scale, 1):g} to {round(trained['max'] * scale, 1):g}), "
                              "so the score is less reliable.")
    return record, errors, warnings


def to_entry(record: dict) -> dict:
    """The other way round, for the edit form: a stored record in the units HR types in."""
    values = {name: record[name] * SCALE[name] for name, *_ in ENTRY_FIELDS if name in record}
    values["performance_last_year"] = record["performance_score"] - record["performance_change"]
    return {name: round(value, 2) for name, value in values.items()}


def read_csv(text: str) -> list[dict]:
    """The CSV file's rows as dictionaries. Raises ValueError for a file that can't be used at all."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))  # ﻿: the marker Excel puts at the start
    if not reader.fieldnames:
        raise ValueError("The file is empty.")
    headers = [h.strip() for h in reader.fieldnames]
    if missing := [c for c in CSV_COLUMNS if c not in headers and c != "manager_username"]:
        raise ValueError(f"The file is missing these columns: {', '.join(missing)}. Download the template to see them all.")
    rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]
    rows = [row for row in rows if any(row.values())]  # skip blank lines
    if not rows:
        raise ValueError("The file has a header but no employees.")
    if len(rows) > MAX_CSV_ROWS:
        raise ValueError(f"Please import at most {MAX_CSV_ROWS} employees at a time.")
    return rows
