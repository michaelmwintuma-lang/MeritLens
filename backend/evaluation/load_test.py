"""
Load test: how the main pages' API calls cope with a large organisation.

    python -m evaluation.load_test            5,000 employees (or: python -m evaluation.load_test 20000)

Builds a throwaway database (never instance/app.db) with the demo accounts and N generated employees (records drawn
from the training data, every 25 given to the demo manager, and 300 decided nominations), then times each call several times and counts the
database queries each makes. A count that grows with the number of employees would be an "N+1" problem (one query
per row); the counts should stay flat. Results: results/load_test.json.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
_tmp = tempfile.mkdtemp()
os.environ.update(DATABASE_URL=f"sqlite:///{Path(_tmp, 'load.db').as_posix()}", SCHEDULER="0", SKIP_ENV_FILE="1",
                  WARM_EXPLANATIONS="0", DEMO_PASSWORD="demo1234", OUTBOX_DIR=str(Path(_tmp, "outbox")),
                  PASSWORD_HASH_ITERATIONS="1000")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event, select  # noqa: E402

from app.accounts.models import User  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.promotion.features import MODEL_FEATURES, load_dataset  # noqa: E402
from app.promotion.models import Employee  # noqa: E402

RESULTS = Path(__file__).resolve().parents[2] / "results"
REPEATS = 5
DECISIONS = 300  # decided nominations added with the large organisation
queries = {"count": 0}
event.listen(engine, "before_cursor_execute", lambda *a, **k: queries.__setitem__("count", queries["count"] + 1))


def add_employees(n: int) -> None:
    """N generated employees: real records from the dataset, with made-up names."""
    data = load_dataset().sample(n, random_state=7, replace=n > 100_000)
    with SessionLocal() as db:
        manager = db.scalar(select(User).where(User.username == "manager"))
        start = db.query(Employee).count()
        for i, row in enumerate(data.itertuples(index=False)):
            record = {f: (round(float(getattr(row, f)), 4) if not isinstance(getattr(row, f), str) else getattr(row, f))
                      for f in MODEL_FEATURES}
            db.add(Employee(full_name=f"Load Test {start + i + 1}", department=row.department,
                            record_json=json.dumps(record), manager_user_id=manager.id if i % 25 == 0 else None))
        db.commit()


def add_decided_nominations(n: int) -> None:
    """N nominations by the demo manager, each decided by HR (approved ones signed off by Finance), as after a busy year."""
    from app.promotion.models import Decision, Nomination
    with SessionLocal() as db:
        manager = db.scalar(select(User).where(User.username == "manager"))
        hr = db.scalar(select(User).where(User.username == "hr"))
        people = list(db.scalars(select(Employee.id).limit(n)))
        for i, employee_id in enumerate(people):
            nomination = Nomination(employee_id=employee_id, nominated_by=manager.id, reason="Load test.",
                                    status="approved" if i % 2 else "rejected", proposed_title="Senior", proposed_raise=8.0)
            db.add(nomination)
            db.flush()
            db.add(Decision(nomination_id=nomination.id, employee_id=employee_id, decided_by=hr.id,
                            decision="approve" if i % 2 else "reject", model_score=0.5, model_threshold=0.4,
                            model_recommended=True, agrees_with_model=bool(i % 2), reason="Load test.",
                            approved_raise=8.0 if i % 2 else None, pay_status="signed_off" if i % 2 else None))
        db.commit()


def timed(client, method: str, path: str, headers: dict, **kwargs) -> dict:
    times, counts = [], []
    for _ in range(REPEATS):
        queries["count"] = 0
        started = time.perf_counter()
        res = client.request(method, path, headers=headers, **kwargs)
        times.append((time.perf_counter() - started) * 1000)
        counts.append(queries["count"])
        assert res.status_code < 400, (path, res.status_code, res.text[:200])
    return {"call": f"{method} {path}", "median_ms": round(statistics.median(times), 1),
            "slowest_ms": round(max(times), 1), "queries": max(counts)}


def login(client, username: str) -> dict:
    res = client.post("/api/auth/login", json={"username": username, "password": "demo1234"})
    client.cookies.clear()
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def run(client, label: str) -> list[dict]:
    hr, manager, admin, auditor, finance = (login(client, u) for u in ("hr", "manager", "admin", "auditor", "finance"))
    calls = [
        timed(client, "GET", "/api/promotion/employees", hr),
        timed(client, "GET", "/api/promotion/employees", manager),
        timed(client, "GET", "/api/promotion/nominations", hr),
        timed(client, "GET", "/api/promotion/decisions", hr),
        timed(client, "GET", "/api/finance/pay-reviews", finance),
        timed(client, "GET", "/api/promotion/teams", hr),
        timed(client, "GET", "/api/governance/fairness", auditor),
        timed(client, "GET", "/api/admin/system", admin),
        timed(client, "GET", "/api/admin/employees", admin),
        timed(client, "GET", "/api/feedback/ratings/summary", hr),
    ]
    queries["count"] = 0
    started = time.perf_counter()
    cycle = client.post("/api/promotion/cycles", headers=hr, json={"name": f"Load test cycle {label}"})
    assert cycle.status_code == 201, cycle.text
    calls.append({"call": "POST /api/promotion/cycles (open: score and save everyone)", "queries": queries["count"],
                  "median_ms": round((time.perf_counter() - started) * 1000, 1), "slowest_ms": None})
    cycle_id = cycle.json()["cycle"]["id"] if "cycle" in cycle.json() else cycle.json()["id"]
    calls += [timed(client, "GET", f"/api/promotion/cycles/{cycle_id}", hr),
              timed(client, "GET", "/api/promotion/employees", hr),
              timed(client, "GET", f"/api/governance/fairness?cycle_id={cycle_id}", auditor)]
    calls[-2]["call"] += " (cycle open)"
    return calls


def main():
    sizes = {}
    with TestClient(app) as client:
        sizes["demo (120)"] = run_size(client, 0)
        sizes[f"{N:,}"] = run_size(client, N - 120)
    report = {"employees": N, "repeats": REPEATS, "results": sizes}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "load_test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    small, large = sizes["demo (120)"], sizes[f"{N:,}"]
    print(f"{'call':<52} {'queries 120':>11} {'queries ' + format(N, ','):>14} {'median ms 120':>14} {'median ms ' + format(N, ','):>16}")
    for a, b in zip(small, large):
        flag = "  <- grows with employees" if b["queries"] > a["queries"] + 5 else ""
        print(f"{b['call']:<52} {a['queries']:>11} {b['queries']:>14} {a['median_ms']:>14} {b['median_ms']:>16}{flag}")


def run_size(client, extra: int) -> list[dict]:
    if extra:
        add_employees(extra)
        add_decided_nominations(DECISIONS)
    with SessionLocal() as db:  # a fresh start for the cycle: close any left open by the previous size
        from app.promotion.models import ReviewCycle
        for cycle in db.scalars(select(ReviewCycle).where(ReviewCycle.status == "open")):
            cycle.status = "closed"
        db.commit()
    return run(client, str(extra))


if __name__ == "__main__":
    main()
