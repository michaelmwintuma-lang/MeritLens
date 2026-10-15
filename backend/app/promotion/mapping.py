"""
Data mapping: turn an organisation's own HR export into the model's inputs, so the same training pipeline can be
retrained on a different organisation's history (train.py --mapping my_mapping.json).

A mapping is a small JSON file (backend/data/mappings/*.json) that says, for each of the model's 20 inputs, which
column of the export holds it and how to convert it:

    {"column": "kpi_pct"}                                      the value as it is
    {"column": "appraisal", "from_range": [1, 4], "to_range": [1, 5]}   a rating on another scale, mapped linearly
    {"column": "attendance", "scale": 100}                     multiplied (e.g. 0.93 -> 93), then "offset" added
    {"difference": ["score_this_year", "score_last_year"]}     one column minus another

and which columns hold the outcome (promoted or not), the department (kept to organise who sees whom, never a
model input) and the characteristics used only for the fairness check. Every mapping is stored in the model card
of each model trained with it, so it is always known what data a model learned from.
"""
import json
from pathlib import Path

import pandas as pd

from app.promotion.features import FAIRNESS_ONLY, MODEL_FEATURES, TARGET

MAPPINGS_DIR = Path(__file__).resolve().parents[2] / "data" / "mappings"
DATA_DIR = MAPPINGS_DIR.parent
DEFAULT_MAPPING = MAPPINGS_DIR / "kaggle_employee_promotion.json"


class MappingError(ValueError):
    """The mapping or the export doesn't fit: the message says exactly what to fix."""


def load_mapping(path: Path = DEFAULT_MAPPING) -> dict:
    mapping = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [f for f in MODEL_FEATURES if f not in mapping.get("inputs", {})]
    if missing:
        raise MappingError(f"The mapping doesn't say where to find: {', '.join(missing)}.")
    for key in ("source", "target", "department"):
        if key not in mapping:
            raise MappingError(f"The mapping has no '{key}' section.")
    return mapping


def _column(frame: pd.DataFrame, name: str, purpose: str) -> pd.Series:
    if name not in frame.columns:
        raise MappingError(f"The export has no column '{name}' (needed for {purpose}).")
    values = pd.to_numeric(frame[name], errors="coerce") if purpose != "department" else frame[name]
    if purpose != "department" and values.isna().any():
        rows = list(values[values.isna()].index[:5] + 2)  # +2: a header row, and rows counted from 1
        raise MappingError(f"Column '{name}' (for {purpose}) has empty or non-numeric values, e.g. on rows {rows}.")
    return values


def convert(frame: pd.DataFrame, rule: dict, purpose: str) -> pd.Series:
    """Apply one input's rule to the export."""
    if "difference" in rule:
        first, second = rule["difference"]
        values = _column(frame, first, purpose) - _column(frame, second, purpose)
    else:
        values = _column(frame, rule["column"], purpose).astype(float)
    if "from_range" in rule:
        (a, b), (c, d) = rule["from_range"], rule.get("to_range", rule["from_range"])
        values = c + (values - a) * (d - c) / (b - a)
    return values * rule.get("scale", 1) + rule.get("offset", 0)


def apply_mapping(frame: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """The export in the model's terms: the 20 inputs, the outcome, department and the fairness-only columns."""
    out = pd.DataFrame(index=frame.index)
    id_column = mapping.get("id_column")  # optional: without one, rows are numbered
    if id_column and id_column not in frame.columns:
        raise MappingError(f"The export has no column '{id_column}' (named as the employee ID).")
    out["employee_id"] = frame[id_column] if id_column else range(1, len(frame) + 1)
    for feature in MODEL_FEATURES:
        out[feature] = convert(frame, mapping["inputs"][feature], feature)
    target = mapping["target"]
    raw = frame[target["column"]] if target["column"] in frame.columns else None
    if raw is None:
        raise MappingError(f"The export has no column '{target['column']}' (needed for the outcome).")
    out[TARGET] = raw.isin(target.get("positive", [1])).astype(int)
    if out[TARGET].nunique() < 2:
        raise MappingError("Every row has the same outcome, so there is nothing to learn from.")
    out["department"] = _column(frame, mapping["department"]["column"], "department").astype(str)
    for characteristic in FAIRNESS_ONLY:
        rule = mapping.get("fairness", {}).get(characteristic)
        if rule is None:
            raise MappingError(f"The mapping doesn't say where to find '{characteristic}', which the fairness check needs.")
        out[characteristic] = frame[rule["column"]] if characteristic != "age" else _column(frame, rule["column"], "age")
    return out


def load_mapped(mapping: dict, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Read the export a mapping names and convert it."""
    source = Path(mapping["source"])
    return apply_mapping(pd.read_csv(source if source.is_absolute() else data_dir / source), mapping)
