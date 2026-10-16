"""
Before a release: what would change for today's employees if this version replaced the live model?

Both models score everyone in today's directory (a release waits until no review cycle is open). The answer says how
many each recommends, who would move across the threshold (gained or lost a recommendation), how far scores move,
and how the share recommended changes per department. Nothing is saved; it is read by the HR person deciding on
the release, next to the version's model card.
"""
from collections import defaultdict

import joblib
import pandas as pd
from sqlalchemy.orm import Session

from app.governance import registry
from app.promotion.explain import get_model
from app.promotion.features import MODEL_FEATURES
from app.promotion.models import Employee, current_employees

MOST_MOVED = 10  # the people whose score moves most, listed by name for HR


def compare_with_live(db: Session, version: str) -> dict:
    card = registry.card(version)
    if card is None:
        raise LookupError("No such model version.")
    live = get_model()
    candidate = joblib.load(registry.version_dir(version) / "model.joblib")
    employees: list[Employee] = list(db.scalars(current_employees()))
    records = [e.record for e in employees]
    live_scores = live.scores(records)
    new_scores = ([float(s) for s in candidate.predict_proba(pd.DataFrame(records)[MODEL_FEATURES])[:, 1]]
                  if records else [])

    rows, departments = [], defaultdict(lambda: [0, 0, 0])  # department -> [people, live recommends, new recommends]
    for e, old, new in zip(employees, live_scores, new_scores):
        was, now = old >= live.threshold, new >= card["threshold"]
        rows.append({"employee_id": e.id, "full_name": e.full_name, "department": e.department,
                     "live_score": round(old, 4), "new_score": round(new, 4), "change": round(new - old, 4),
                     "live_recommends": was, "new_recommends": now})
        counts = departments[e.department or "–"]
        counts[0] += 1
        counts[1] += was
        counts[2] += now

    changes = [abs(r["change"]) for r in rows]
    return {
        "live_version": live.version, "version": version, "employees": len(rows),
        "live_threshold": live.threshold, "new_threshold": card["threshold"],
        "live_recommends": sum(r["live_recommends"] for r in rows),
        "new_recommends": sum(r["new_recommends"] for r in rows),
        "gained": [r for r in rows if r["new_recommends"] and not r["live_recommends"]],
        "lost": [r for r in rows if r["live_recommends"] and not r["new_recommends"]],
        "average_change": round(sum(changes) / len(changes), 4) if changes else 0.0,
        "most_moved": sorted(rows, key=lambda r: abs(r["change"]), reverse=True)[:MOST_MOVED],
        "by_department": [{"department": d, "employees": c[0], "live_recommends": c[1], "new_recommends": c[2]}
                          for d, c in sorted(departments.items())],
    }
