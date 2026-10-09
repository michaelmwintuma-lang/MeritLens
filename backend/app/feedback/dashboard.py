"""
The feedback dashboard, for HR and the compliance auditor: how employees respond to their explanations, how
record corrections are handled, what is reported, and where committees went against the model.

Every number is worked out here from the database, with the filters applied (date range, department, model
version). Small groups are protected:
- clarity, usefulness and contest shares are withheld below MIN_GROUP ratings;
- counts of 1 or 2 (reports per category, factor marks) are shown as "<3";
- only departments with at least MIN_GROUP employees can be chosen, so a filter can't single anyone out.
Never a name, a comment, a report's text or one person's rating.
"""
import csv
import io
import json
from collections import Counter
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.database import get_db
from app.core.roles import AUDITOR, HR
from app.core.security import require_roles
from app.feedback.models import CorrectionRequest, ExplanationRating
from app.promotion.features import MODEL_FEATURES
from app.promotion.labels import label
from app.promotion.models import Decision, Employee
from app.promotion.routes import model
from app.reporting.models import Report
from app.reporting.routes import CATEGORY_GROUPS

router = APIRouter(prefix="/api/feedback/dashboard", tags=["feedback dashboard"])
viewers = require_roles(HR, AUDITOR)
MIN_GROUP = 5
SMALL = 3  # counts below this (but above 0) are shown as "<3"


def small(count: int) -> int | str:
    return f"<{SMALL}" if 0 < count < SMALL else count


def rate(part: int, whole: int, minimum: int = MIN_GROUP) -> float | None:
    return round(part / whole, 4) if whole >= minimum else None


def department_options(db: Session) -> list[str]:
    """Departments large enough to filter by."""
    counts = db.execute(select(Employee.department, func.count()).group_by(Employee.department)).all()
    return sorted(d for d, n in counts if n >= MIN_GROUP)


def parse_day(text: str | None) -> date | None:
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Dates must look like 2026-10-09.")


def measures(db: Session, start: str | None, end: str | None, department: str | None, model_version: str | None) -> dict:
    first, last = parse_day(start), parse_day(end)
    if department and department not in department_options(db):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Departments with fewer than {MIN_GROUP} people can't be chosen, so no one can be singled out.")
    since = datetime.combine(first, time.min) if first else None
    until = datetime.combine(last, time.max) if last else None
    in_department = select(Employee.id).where(Employee.department == department)

    def when(column, query):
        if since:
            query = query.where(column >= since)
        if until:
            query = query.where(column <= until)
        return query

    # ─── Ratings ──────────────────────────────────────────────────────────────
    query = when(ExplanationRating.created_at, select(ExplanationRating))
    if department:
        query = query.where(ExplanationRating.employee_id.in_(in_department))
    if model_version:
        query = query.where(ExplanationRating.model_version == model_version)
    ratings = list(db.scalars(query))
    n = len(ratings)
    marks = Counter()
    for r in ratings:
        for flag in json.loads(r.flagged_json):
            marks[(flag["feature"], flag["kind"])] += 1
    contested = sorted(
        ({"feature": f, "label": label(f), "wrong": small(marks[(f, "wrong")]), "unfair": small(marks[(f, "unfair")]),
          "share": rate(marks[(f, "wrong")] + marks[(f, "unfair")], n), "_total": marks[(f, "wrong")] + marks[(f, "unfair")]}
         for f in MODEL_FEATURES if marks[(f, "wrong")] or marks[(f, "unfair")]),
        key=lambda c: -c["_total"])
    for c in contested:
        del c["_total"]

    # ─── Record corrections (not tied to a model version) ─────────────────────
    query = when(CorrectionRequest.created_at, select(CorrectionRequest))
    if department:
        query = query.where(CorrectionRequest.employee_id.in_(in_department))
    requests = list(db.scalars(query))
    by_status = Counter(r.status for r in requests)
    decided = [r for r in requests if r.status != "pending"]
    hours = [(r.decided_at - r.created_at).total_seconds() / 3600 for r in decided]

    # ─── Anonymous reports: counts per category, by date only ─────────────────
    query = select(Report.category, func.count()).group_by(Report.category)
    if first:
        query = query.where(Report.created_on >= first)
    if last:
        query = query.where(Report.created_on <= last)
    counts = dict(db.execute(query).all())
    categories = [{"category": key, "label": name, "count": small(counts.get(key, 0))}
                  for _, items in CATEGORY_GROUPS for key, name in items]
    earlier = sum(n for key, n in counts.items() if key not in {c["category"] for c in categories})

    # ─── Committee decisions and overrides ────────────────────────────────────
    query = when(Decision.decided_at, select(Decision))
    if department:
        query = query.where(Decision.employee_id.in_(in_department))
    if model_version:
        query = query.where(Decision.model_version == model_version)
    decisions = list(db.scalars(query.order_by(Decision.decided_at.desc())))
    overrides = [d for d in decisions if not d.agrees_with_model]

    return {
        "filters": {"start": start, "end": end, "department": department, "model_version": model_version},
        "ratings": {"count": n, "min_group": MIN_GROUP,
                    "clarity_rate": rate(sum(r.clarity >= 4 for r in ratings), n),
                    "usefulness_rate": rate(sum(r.usefulness >= 4 for r in ratings), n),
                    "contested": contested},
        "corrections": {"received": len(requests), "confirmed": by_status["confirmed"], "rejected": by_status["rejected"],
                        "pending": by_status["pending"],
                        "confirmation_rate": rate(by_status["confirmed"], len(decided), minimum=1),
                        "mean_resolution_hours": round(sum(hours) / len(hours), 1) if hours else None},
        "reports": {"by_category": categories, "earlier_categories": small(earlier),
                    "note": "Reports are counted by date only: they hold no department, person or model version."},
        "committee": {"decisions": len(decisions), "overrides": len(overrides),
                      "override_rate": rate(len(overrides), len(decisions), minimum=1),
                      "reasons": [{"decided_on": d.decided_at.date().isoformat(), "decision": d.decision,
                                   "model_recommended": d.model_recommended, "reason": d.reason} for d in overrides]},
    }


@router.get("")
def dashboard(start: str | None = None, end: str | None = None, department: str | None = None,
              model_version: str | None = None, db: Session = Depends(get_db), _: User = Depends(viewers)):
    """The dashboard's numbers for these filters, and the filter options."""
    versions = {v for (v,) in db.execute(select(ExplanationRating.model_version).distinct())}
    versions |= {v for (v,) in db.execute(select(Decision.model_version).distinct()) if v}
    versions.add(model().version)
    return {**measures(db, start, end, department, model_version),
            "options": {"departments": department_options(db), "model_versions": sorted(versions, reverse=True),
                        "current_model_version": model().version},
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


@router.get("/export.csv")
def export(start: str | None = None, end: str | None = None, department: str | None = None,
           model_version: str | None = None, db: Session = Depends(get_db), _: User = Depends(viewers)):
    """The same numbers as a CSV file (section, measure, value), with the same small-group protection."""
    data = measures(db, start, end, department, model_version)
    out = io.StringIO()

    class Writer:
        """A CSV writer that says why a value is missing instead of leaving it blank."""
        def __init__(self):
            self.csv = csv.writer(out)

        def writerow(self, row):
            self.csv.writerow(["withheld (too few to show)" if v is None else v for v in row])

        def writerows(self, rows):
            for row in rows:
                self.writerow(row)
    writer = Writer()
    writer.writerow(["section", "measure", "value"])
    for key, value in data["filters"].items():
        writer.writerow(["filter", key, value or "all"])
    r = data["ratings"]
    writer.writerows([["ratings", "ratings", r["count"]], ["ratings", "clarity rate (4 or 5)", r["clarity_rate"]],
                      ["ratings", "usefulness rate (4 or 5)", r["usefulness_rate"]]])
    for c in r["contested"]:
        writer.writerows([["contested factor", f"{c['label']}: marked wrong", c["wrong"]],
                          ["contested factor", f"{c['label']}: marked unfair", c["unfair"]],
                          ["contested factor", f"{c['label']}: share of ratings", c["share"]]])
    for key, value in data["corrections"].items():
        writer.writerow(["corrections", key.replace("_", " "), value])
    for c in data["reports"]["by_category"]:
        writer.writerow(["anonymous reports", c["label"], c["count"]])
    writer.writerow(["anonymous reports", "earlier categories", data["reports"]["earlier_categories"]])
    m = data["committee"]
    writer.writerows([["committee", "decisions", m["decisions"]], ["committee", "overrides", m["overrides"]],
                      ["committee", "override rate", m["override_rate"]]])
    for reason in m["reasons"]:
        writer.writerow(["override reason", reason["decided_on"], reason["reason"]])
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="feedback-dashboard.csv"'})
