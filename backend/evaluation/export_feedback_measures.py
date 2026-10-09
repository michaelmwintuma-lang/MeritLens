"""
Export the feedback dashboard's measures for the thesis (Chapter Four):   python -m evaluation.export_feedback_measures

From the backend folder. It reads the app's database (backend/instance/app.db, or DATABASE_URL) and changes nothing.
The numbers are worked out by the same code as the feedback dashboard (app/feedback/dashboard.py), with the same
protection of small groups, and saved to results/feedback_measures.json:

- clarity rate and usefulness rate: the share of rated explanations scored 4 or 5 (withheld below 5 ratings);
- contest share per factor: how often each factor was marked "seems wrong" or "seems unfair";
- record corrections: received, confirmed, rejected, pending, the confirmation rate and the mean time to decide;
- anonymous reports per promotion category, and the committee's override rate.

Optional:  --start 2026-01-01 --end 2026-12-31  --department Finance  --model-version v20261008215310
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.database import SessionLocal
from app.feedback.dashboard import MIN_GROUP, measures

RESULTS = Path(__file__).resolve().parents[2] / "results"


def export(db, start=None, end=None, department=None, model_version=None) -> dict:
    """The measures for these filters, with what they mean, ready to save."""
    data = measures(db, start, end, department, model_version)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "the app's database, via app/feedback/dashboard.py (the feedback dashboard's own code)",
        "small_groups": f"rates withheld (null) below {MIN_GROUP} ratings; counts of 1 or 2 shown as \"<3\"",
        "filters": data["filters"],
        "explanations": {
            "ratings": data["ratings"]["count"],
            "clarity_rate": data["ratings"]["clarity_rate"],
            "usefulness_rate": data["ratings"]["usefulness_rate"],
            "contest_share_per_factor": data["ratings"]["contested"],
        },
        "record_corrections": data["corrections"],
        "anonymous_reports_by_category": data["reports"]["by_category"],
        "committee": {key: data["committee"][key] for key in ("decisions", "overrides", "override_rate")},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--start"), parser.add_argument("--end"), parser.add_argument("--department")
    parser.add_argument("--model-version")
    args = parser.parse_args()
    with SessionLocal() as db:
        result = export(db, args.start, args.end, args.department, args.model_version)
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / "feedback_measures.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    e, c = result["explanations"], result["record_corrections"]
    print(f"{e['ratings']} ratings (clarity rate {e['clarity_rate']}), {c['received']} correction requests "
          f"(confirmation rate {c['confirmation_rate']}, mean {c['mean_resolution_hours']} h to decide). Saved {path}")


if __name__ == "__main__":
    main()
