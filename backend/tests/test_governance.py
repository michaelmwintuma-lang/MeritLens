"""
The redesign's governance features: enforced holds, the tamper-evident audit trail, the model registry with its
human release step, live fairness monitoring, and the data mapping used to retrain on other organisations' data.
"""
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select

from app.core import audit
from app.core.config import MODEL_REGISTRY_DIR, MODELS_DIR, RESULTS_DIR
from app.core.database import SessionLocal
from app.governance import registry
from app.promotion.features import MODEL_FEATURES, TARGET
from app.promotion.mapping import MappingError, apply_mapping, load_mapping
from tests.conftest import login, recommendation


def hr_name(client) -> str:
    return client.get("/api/auth/me", headers=login(client, "hr")).json()["full_name"]


def team_member(client) -> int:
    team = client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]
    return team[1]["id"]


def nominate(client, person: int) -> int:
    res = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(person))
    assert res.status_code == 201, res.text
    return res.json()["id"]


def ask_correction(client, person: int) -> dict:
    """The nominee asks HR to correct their record (as HR's own staff would see it: a pending request)."""
    from app.feedback.models import CorrectionRequest
    with SessionLocal() as db:
        request = CorrectionRequest(employee_id=person, requested_by=None, field="manager_rating", current_value=3,
                                    requested_value=4, note="Entered wrongly in the review system.")
        db.add(request)
        db.commit()
        return {"id": request.id}


# ─── Holds are enforced ────────────────────────────────────────────────────────
def test_a_decision_on_hold_is_refused_until_the_hold_lifts(client):
    hr = login(client, "hr")
    person = team_member(client)
    nomination = nominate(client, person)
    request = ask_correction(client, person)
    assert client.post(f"/api/hr/feedback/nominations/{nomination}/defer", headers=hr).json()["deferred"]

    decide = lambda: client.post(f"/api/promotion/nominations/{nomination}/decision", headers=hr,  # noqa: E731
                                 json={"decision": "reject", "reason": "Not enough evidence of leadership yet."})
    refused = decide()
    assert refused.status_code == 409 and "on hold" in refused.json()["detail"]

    # Rejecting the correction resolves it: the hold lifts by itself and the decision can be made
    client.post(f"/api/hr/feedback/corrections/{request['id']}/reject", headers=hr,
                json={"reason": "The review system shows the original rating of 3."})
    assert not client.get(f"/api/hr/feedback/nominations/{nomination}/note", headers=hr).json()["deferred"]
    assert decide().status_code == 201


def test_hr_can_take_a_decision_off_hold_and_then_decide(client):
    hr = login(client, "hr")
    person = team_member(client)
    nomination = nominate(client, person)
    ask_correction(client, person)
    client.post(f"/api/hr/feedback/nominations/{nomination}/defer", headers=hr)
    client.post(f"/api/hr/feedback/nominations/{nomination}/resume", headers=hr)
    res = client.post(f"/api/promotion/nominations/{nomination}/decision", headers=hr,
                      json={"decision": "reject", "reason": "Not enough evidence of leadership yet."})
    assert res.status_code == 201


# ─── The audit trail ───────────────────────────────────────────────────────────
def audit_events(client, **params) -> list[dict]:
    return client.get("/api/governance/audit", headers=login(client, "auditor"), params=params).json()["events"]


def test_a_decision_is_audited_with_what_the_model_said(client):
    hr = login(client, "hr")
    nomination = nominate(client, team_member(client))
    decision = client.post(f"/api/promotion/nominations/{nomination}/decision", headers=hr,
                           json={"decision": "approve", "reason": "Strong leadership the data doesn't capture yet.",
                                 "approved_raise": 8}).json()
    [made] = audit_events(client, event="decision_made")
    assert made["subject_id"] == str(decision["id"]) and made["actor"] == hr_name(client)
    assert made["payload"]["score"] == decision["model_score"] and made["model_version"] == decision["model_version"]
    assert len(made["payload"]["top_factors"]) == 5
    assert [e["event"] for e in audit_events(client)][:3] == ["pay_submitted", "decision_made", "nomination_made"]


def test_the_audit_chain_is_intact_and_detects_tampering(client):
    hr = login(client, "hr")
    nominate(client, team_member(client))
    auditor = login(client, "auditor")
    verified = client.get("/api/governance/audit/verify", headers=auditor).json()
    assert verified["intact"] and verified["events"] >= 1

    # Someone edits the database directly: the chain shows exactly where
    with SessionLocal() as db:
        db.connection().exec_driver_sql("UPDATE audit_events SET payload_json = '{}' WHERE id = 1")
        db.commit()
    broken = client.get("/api/governance/audit/verify", headers=auditor).json()
    assert not broken["intact"] and broken["first_broken_id"] == 1 and broken["problem"] == "content was changed"
    assert hr  # HR made the event; only the auditor and admins read the trail


def test_audit_events_cant_be_changed_or_deleted_through_the_app(client):
    nominate(client, team_member(client))
    with SessionLocal() as db:
        event = db.scalar(select(audit.AuditEvent))
        event.actor_name = "someone else"
        with pytest.raises(PermissionError):
            db.flush()
        db.rollback()
        with pytest.raises(PermissionError):
            db.delete(db.scalar(select(audit.AuditEvent)))
            db.flush()


def test_only_the_auditor_and_admins_read_the_audit_trail(client):
    for username in ("auditor", "admin"):
        assert client.get("/api/governance/audit", headers=login(client, username)).status_code == 200
    for username in ("hr", "manager", "employee", "finance"):
        assert client.get("/api/governance/audit", headers=login(client, username)).status_code == 403


def test_the_audit_trail_never_copies_what_an_employee_wrote(client):
    employee = login(client, "employee")
    note = "My manager entered the wrong rating; see the attached review."
    res = client.post("/api/feedback/corrections", headers=employee,
                      json={"field": "manager_rating", "requested_value": 5, "note": note})
    assert res.status_code == 201, res.text
    [requested] = audit_events(client, event="correction_requested")
    assert note not in json.dumps(requested)


# ─── The model registry ────────────────────────────────────────────────────────
def make_candidate(passes: bool = True) -> str:
    """A second registered version: the live model's own files under a new version name (as train.py would)."""
    live = registry.live_version()
    version = "v29990101000000" if passes else "v29990102000000"
    folder = MODEL_REGISTRY_DIR / version
    shutil.copytree(MODEL_REGISTRY_DIR / live, folder)
    info = json.loads((folder / "model_info.json").read_text())
    info.update(version=version, trained_at="2999-01-01T00:00:00+00:00")
    (folder / "model_info.json").write_text(json.dumps(info))
    card = json.loads((folder / "card.json").read_text())
    card.update(version=version, trained_at=info["trained_at"], fairness_passes=passes)
    (folder / "card.json").write_text(json.dumps(card))
    return version


def test_the_live_model_is_registered_with_its_card(client):
    rows = client.get("/api/governance/models", headers=login(client, "auditor")).json()
    [live] = [r for r in rows if r["status"] == "live"]
    assert live["version"] == registry.live_version() and live["fairness_passes"]
    card = client.get(f"/api/governance/models/{live['version']}", headers=login(client, "hr")).json()["card"]
    assert card["test_results"]["roc_auc"] > 0.5 and card["fairness"]["passes"] and card["intended_use"]
    assert card["limitations"] and card["inputs"] == MODEL_FEATURES


def test_a_candidate_goes_live_only_when_hr_releases_it_with_a_note(client):
    old, new = registry.live_version(), make_candidate()
    hr = login(client, "hr")
    statuses = {r["version"]: r["status"] for r in client.get("/api/governance/models", headers=hr).json()}
    assert statuses == {old: "live", new: "candidate"}

    for username in ("admin", "auditor", "manager"):  # only HR releases
        assert client.post(f"/api/governance/models/{new}/release", headers=login(client, username),
                           json={"note": "Retrained on this year's reviews."}).status_code == 403
    short = client.post(f"/api/governance/models/{new}/release", headers=hr, json={"note": "ok"})
    assert short.status_code == 422

    res = client.post(f"/api/governance/models/{new}/release", headers=hr,
                      json={"note": "Retrained on this year's reviews; card checked by HR."})
    assert res.status_code == 200 and res.json()["status"] == "live"
    assert registry.live_version() == new
    # The app switched without a restart, and the release is in the audit trail
    assert client.get("/api/promotion/employees", headers=hr).json()["model_version"] == new
    [released] = audit_events(client, event="model_released")
    assert released["payload"]["previous_version"] == old and released["actor"] == hr_name(client)

    # Rolling back is releasing the older version again
    back = client.post(f"/api/governance/models/{old}/release", headers=hr,
                       json={"note": "Rolled back while we check the new version."})
    assert back.status_code == 200 and registry.live_version() == old
    statuses = {r["version"]: r["status"] for r in client.get("/api/governance/models", headers=hr).json()}
    assert statuses == {old: "live", new: "retired"}


def test_hr_sees_what_a_release_would_change_for_today_s_employees(client):
    new = make_candidate()  # the live model's own files: nothing should move
    res = client.get(f"/api/governance/models/{new}/compare", headers=login(client, "hr"))
    assert res.status_code == 200
    diff = res.json()
    assert diff["employees"] == 120 and diff["version"] == new
    assert diff["live_recommends"] == diff["new_recommends"] and diff["gained"] == diff["lost"] == []
    assert diff["average_change"] == 0 and sum(d["employees"] for d in diff["by_department"]) == 120
    assert client.get(f"/api/governance/models/{new}/compare", headers=login(client, "auditor")).status_code == 403
    assert client.get("/api/governance/models/v1/compare", headers=login(client, "hr")).status_code == 404


def test_a_model_that_failed_the_fairness_check_can_never_be_released(client):
    blocked = make_candidate(passes=False)
    hr = login(client, "hr")
    statuses = {r["version"]: r["status"] for r in client.get("/api/governance/models", headers=hr).json()}
    assert statuses[blocked] == "blocked"
    res = client.post(f"/api/governance/models/{blocked}/release", headers=hr,
                      json={"note": "Please release this one anyway, it looks fine."})
    assert res.status_code == 409 and "fairness" in res.json()["detail"]
    assert registry.live_version() != blocked


def test_releasing_publishes_the_versions_results(client):
    new = make_candidate()
    metrics = json.loads((MODEL_REGISTRY_DIR / new / "results" / "metrics.json").read_text())
    metrics["roc_auc"] = 0.9123
    (MODEL_REGISTRY_DIR / new / "results" / "metrics.json").write_text(json.dumps(metrics))
    client.post(f"/api/governance/models/{new}/release", headers=login(client, "hr"),
                json={"note": "Retrained on this year's reviews; card checked by HR."})
    assert json.loads((RESULTS_DIR / "metrics.json").read_text())["roc_auc"] == 0.9123
    assert client.get("/api/public/summary").json()["roc_auc"] == 0.9123
    assert (MODELS_DIR / "model_info.json").exists()


# ─── Live fairness ─────────────────────────────────────────────────────────────
def test_live_fairness_checks_three_stages_per_characteristic(client):
    report = client.get("/api/governance/fairness", headers=login(client, "auditor")).json()
    assert report["with_monitoring_data"] == report["employees"] == 120
    assert [c["characteristic"] for c in report["checks"]] == ["gender", "age_band", "education_level", "gender_age_band"]
    combined = {g["group"] for s in report["checks"][3]["stages"][:1] for g in s["groups"]}
    assert "Female, 40+" in combined or "Male, under 40" in combined
    gender = report["checks"][0]
    assert [s["stage"] for s in gender["stages"]] == ["Model recommends", "Managers nominate", "HR approves (of decided)"]
    model_stage = gender["stages"][0]
    assert model_stage["status"] in ("passes", "below four-fifths", "within chance") and model_stage["ratio"] is not None
    # Nobody has been decided yet: no rate is guessed
    assert gender["stages"][2]["status"] == "not enough data"


@pytest.mark.parametrize("counts, status", [
    ({"F": (8, 62), "M": (4, 59)}, "within chance"),       # ratio 0.53, but small groups: chance does this often
    ({"F": (40, 100), "M": (10, 100)}, "below four-fifths"),  # ratio 0.25 on 100 each: very unlikely by chance
    ({"F": (50, 100), "M": (45, 100)}, "passes"),
    ({"F": (2, 4), "M": (5, 50)}, "not enough data"),        # one group under 5: never shown, nothing to compare
    ({"BSc": (0, 81), "MSc": (3, 36)}, "not enough data"),   # 3 selected in all: too few to judge
])
def test_a_gap_is_flagged_only_when_it_is_unlikely_to_be_chance(counts, status):
    from app.governance.monitoring import stage
    result = stage(counts, "Model recommends")
    assert result["status"] == status
    if sum(selected for selected, _ in counts.values()) < 5:  # so few that a rate could point to one person
        assert all(g["rate"] is None for g in result["groups"])
    if status in ("within chance", "below four-fifths"):
        assert (result["p_value"] < 0.05) == (status == "below four-fifths")


def test_pay_rises_are_compared_per_group_and_small_groups_are_never_shown():
    from app.governance.monitoring import pay_check
    groups = {i: ("F" if i < 20 else "M") for i in range(40)} | {40: "X", 41: "X"}
    alike = {i: 5.0 + (i % 3) for i in range(42)}
    result = pay_check("gender", "Gender", groups, alike)
    assert result["status"] == "passes" and result["ratio"] > 0.8
    [x] = [g for g in result["groups"] if g["group"] == "X"]
    assert not x["shown"] and x["average"] is None and x["count"] is None  # 2 rises: could point to a person
    unequal = {i: (3.0 + (i % 2) * 0.1 if i < 20 else 8.0 + (i % 2) * 0.1) for i in range(40)}
    flagged = pay_check("gender", "Gender", groups, unequal)
    assert flagged["status"] == "below four-fifths" and flagged["p_value"] < 0.05
    assert pay_check("gender", "Gender", groups, {})["status"] == "not enough data"


def test_live_fairness_includes_pay(client):
    report = client.get("/api/governance/fairness", headers=login(client, "hr")).json()
    assert [p["characteristic"] for p in report["pay"]][:1] == ["gender"]
    assert report["pay"][0]["status"] == "not enough data"  # no promotions approved with a rise yet


def test_live_fairness_never_shows_a_group_under_five(client):
    report = client.get("/api/governance/fairness", headers=login(client, "hr")).json()
    for check in report["checks"]:
        for stage in check["stages"]:
            for group in stage["groups"]:
                if not group["shown"]:
                    assert group["rate"] is None and group["count"] is None


def test_live_fairness_is_for_hr_admins_and_the_auditor(client):
    for username in ("manager", "employee", "finance"):
        assert client.get("/api/governance/fairness", headers=login(client, username)).status_code == 403


# ─── Data mapping ──────────────────────────────────────────────────────────────
def other_organisation(rows: int = 40) -> tuple[pd.DataFrame, dict]:
    """An export with its own column names and scales, and the mapping that reads it."""
    mapping = load_mapping()
    frame = pd.DataFrame({f"col_{f}": [float(i % 7 + 1) for i in range(rows)] for f in MODEL_FEATURES})
    frame["appraisal_1_to_4"] = [1 + i % 4 for i in range(rows)]
    frame["score_now"], frame["score_before"] = [70.0 + i % 5 for i in range(rows)], [68.0] * rows
    frame["got_promoted"] = ["yes" if i % 5 == 0 else "no" for i in range(rows)]
    frame["dept"], frame["sex"], frame["age_years"], frame["degree"] = "Ops", "F", 35, "Master"
    inputs = {f: {"column": f"col_{f}"} for f in MODEL_FEATURES}
    inputs["manager_rating"] = {"column": "appraisal_1_to_4", "from_range": [1, 4], "to_range": [1, 5]}
    inputs["performance_change"] = {"difference": ["score_now", "score_before"]}
    inputs["attendance_rate"] = {"column": "col_attendance_rate", "scale": 0.01}
    mapping.update(id_column=None, inputs=inputs, target={"column": "got_promoted", "positive": ["yes"]},
                   department={"column": "dept"},
                   fairness={"gender": {"column": "sex"}, "age": {"column": "age_years"},
                             "education_level": {"column": "degree"}})
    return frame, mapping


def test_a_mapping_turns_another_organisations_export_into_the_models_inputs():
    frame, mapping = other_organisation()
    out = apply_mapping(frame, mapping)
    assert set(MODEL_FEATURES) <= set(out.columns) and out[TARGET].sum() == 8
    assert out["manager_rating"].min() == 1 and out["manager_rating"].max() == 5   # 1-4 stretched to 1-5
    assert out["performance_change"].iloc[3] == pytest.approx(5.0)                  # 73 - 68
    assert out["attendance_rate"].iloc[0] == pytest.approx(0.01)


def test_the_default_mapping_reproduces_the_dataset_exactly():
    from app.promotion.features import load_dataset
    from app.promotion.mapping import load_mapped
    mapped, raw = load_mapped(load_mapping()), load_dataset()
    pd.testing.assert_frame_equal(mapped[MODEL_FEATURES], raw[MODEL_FEATURES], check_dtype=False)
    assert (mapped[TARGET] == raw[TARGET]).all()


@pytest.mark.parametrize("break_it, message", [
    (lambda f, m: f.drop(columns=["col_late_days"]), "no column 'col_late_days'"),
    (lambda f, m: f.assign(col_late_days=["x"] * len(f)), "non-numeric"),
    (lambda f, m: f.assign(got_promoted="no"), "same outcome"),
])
def test_a_mapping_that_doesnt_fit_says_exactly_what_to_fix(break_it, message):
    frame, mapping = other_organisation()
    with pytest.raises(MappingError, match=message):
        apply_mapping(break_it(frame, mapping), mapping)


def test_a_mapping_must_cover_every_input(tmp_path: Path):
    mapping = load_mapping()
    del mapping["inputs"]["late_days"]
    (tmp_path / "m.json").write_text(json.dumps(mapping))
    with pytest.raises(MappingError, match="late_days"):
        load_mapping(tmp_path / "m.json")
