"""Step 3 tests: predictions, exact contributions, LIME, summary, what-if, tips, importance and who may see what."""
import math
from pathlib import Path

import pytest

from app.promotion.explain import get_model, logit
from app.promotion.labels import FEATURE_INFO, IMPROVABLE, UPPER_LIMIT
from app.promotion.seed import TEAM_SIZE
from tests.conftest import login

pytestmark = pytest.mark.skipif(not (Path(__file__).resolve().parents[1] / "models" / "model.joblib").exists(),
                                reason="run train.py first")


def employees(client, username="hr"):
    return client.get("/api/promotion/employees", headers=login(client, username)).json()["employees"]


# ─── Exact contributions ───────────────────────────────────────────────────
def test_contributions_add_up_to_the_models_output(client):
    """base + sum of contributions = the model's log-odds, for every demo employee (checked on unrounded output)."""
    from app.core.database import SessionLocal
    from app.promotion.models import Employee

    model = get_model()
    with SessionLocal() as db:
        records = [e.record for e in db.query(Employee).all()]
    assert len(records) == 120
    for record in records:
        total = model.base_logodds + sum(c["contribution"] for c in model.contributions(record))
        # Each of the 20 contributions is rounded to 4 decimals: allow that rounding (20 x 0.00005) and nothing more
        assert total == pytest.approx(logit(model.score(record)), abs=0.0011)


def test_department_is_not_an_input_and_values_are_in_real_units(client):
    x = client.get(f"/api/promotion/employees/{employees(client)[0]['id']}", headers=login(client, "hr")).json()
    features = [c["feature"] for c in x["contributions"]]
    assert "department" not in features and len(features) == len(set(features)) == 20
    shown = {c["feature"]: c["value_display"] for c in x["contributions"]}
    assert shown["attendance_rate"].endswith("%") and shown["manager_rating"].endswith("/ 5")


def test_average_employee_is_the_reference_point():
    model = get_model()
    assert 0 < 1 / (1 + math.exp(-model.base_logodds)) < 1


# ─── LIME and the summary ─────────────────────────────────────────────────────
def test_lime_gives_rules_a_fit_score_and_a_note_when_the_fit_is_low(client):
    x = client.get(f"/api/promotion/employees/{employees(client)[0]['id']}", headers=login(client, "hr")).json()
    lime = x["lime"]
    assert 1 <= len(lime["rules"]) <= 5 and isinstance(lime["fit_r2"], float)
    assert (lime["note"] is not None) == (lime["fit_r2"] < 0.5)


def test_summary_states_the_score_and_the_threshold(client):
    x = client.get(f"/api/promotion/employees/{employees(client)[0]['id']}", headers=login(client, "hr")).json()
    assert f"{x['score']:.0%}" in x["summary"] and f"{x['threshold']:.0%} threshold" in x["summary"]


# ─── What-if ──────────────────────────────────────────────────────────────────
def test_what_if_changes_the_score_but_saves_nothing(client):
    hr = login(client, "hr")
    # Someone with room to improve their performance score
    for row in employees(client):
        before = client.get(f"/api/promotion/employees/{row['id']}", headers=hr).json()
        score_now = {c["feature"]: c["value"] for c in before["contributions"]}["performance_score"]
        if score_now < 90:
            employee_id = row["id"]
            break
    res = client.post(f"/api/promotion/employees/{employee_id}/what-if", headers=hr,
                      json={"changes": {"performance_score": score_now + 5}})
    assert res.status_code == 200
    assert res.json()["score"] != before["score"] and res.json()["original_score"] == before["score"]
    after = client.get(f"/api/promotion/employees/{employee_id}", headers=hr).json()
    assert after["score"] == before["score"]  # nothing was saved


def test_raising_this_years_performance_also_raises_the_change_since_last_year():
    model = get_model()
    record = {f: model.stats[f]["mean"] for f in model.stats} | {"department": "Finance"}
    changed = model.apply_changes(record, {"performance_score": record["performance_score"] + 4})
    assert changed["performance_change"] == pytest.approx(record["performance_change"] + 4)


@pytest.mark.parametrize("changes", [
    {"years_since_last_promotion": 0},   # not something a person can improve
    {"department": 1},                   # not improvable
    {"performance_change": 10},          # follows from the performance score, not set directly
    {"performance_score": 250},          # outside the realistic range
])
def test_what_if_refuses_inputs_that_cannot_be_changed(client, changes):
    hr = login(client, "hr")
    employee_id = employees(client)[0]["id"]
    assert client.post(f"/api/promotion/employees/{employee_id}/what-if", headers=hr, json={"changes": changes}).status_code == 422


# ─── Tips ─────────────────────────────────────────────────────────────────────
def test_tips_never_suggest_making_anything_worse(client):
    model = get_model()
    hr = login(client, "hr")
    for row in employees(client):
        x = client.get(f"/api/promotion/employees/{row['id']}/tips", headers=hr).json()
        for tip in x["tips"]:
            info = FEATURE_INFO[tip["feature"]]
            assert tip["feature"] in IMPROVABLE
            assert (tip["to"] - tip["from"]) * info["improve"] > 0                  # improving direction only
            assert abs(tip["to"] - tip["from"]) <= model.stats[tip["feature"]]["std"] + 1e-6   # realistic step
            assert tip["to"] <= UPPER_LIMIT.get(info["unit"], math.inf)            # within natural limits
        if x["reaches_threshold"]:
            assert x["projected_score"] >= model.threshold
        assert x["projected_score"] >= x["current_score"]                          # tips never lower the score


def test_tips_for_someone_already_recommended_are_empty(client):
    recommended = [r for r in employees(client) if r["recommended"]]
    if recommended:
        x = client.get(f"/api/promotion/employees/{recommended[0]['id']}/tips", headers=login(client, "hr")).json()
        assert x["already_recommended"] and x["tips"] == []


# ─── Overall importance ───────────────────────────────────────────────────────
def test_importance_covers_every_input_and_sums_to_one(client):
    rows = client.get("/api/promotion/importance", headers=login(client, "employee")).json()["features"]
    assert len(rows) == 20 and sum(r["share"] for r in rows) == pytest.approx(1, abs=0.001)


# ─── Who may see what ─────────────────────────────────────────────────────────
def test_hr_sees_everyone(client):
    assert len(employees(client, "hr")) == 120


def test_manager_sees_only_their_team(client):
    manager = login(client, "manager")
    team = employees(client, "manager")
    assert len(team) == TEAM_SIZE
    team_ids = {r["id"] for r in team}
    outsider = next(r["id"] for r in employees(client, "hr") if r["id"] not in team_ids)
    assert client.get(f"/api/promotion/employees/{next(iter(team_ids))}", headers=manager).status_code == 200
    assert client.get(f"/api/promotion/employees/{outsider}", headers=manager).status_code == 403
    assert client.get(f"/api/promotion/employees/{outsider}/tips", headers=manager).status_code == 403
    assert client.post(f"/api/promotion/employees/{outsider}/what-if", headers=manager, json={"changes": {}}).status_code == 403


def test_employee_sees_only_themselves(client):
    employee = login(client, "employee")
    own = employees(client, "employee")
    assert len(own) == 1
    me = client.get("/api/auth/me", headers=employee).json()
    assert own[0]["id"] == me["employee_id"]
    colleague = next(r["id"] for r in employees(client, "hr") if r["id"] != me["employee_id"])
    assert client.get(f"/api/promotion/employees/{colleague}", headers=employee).status_code == 403


def test_admin_has_no_access_to_promotion_data(client):
    admin = login(client, "admin")
    some_id = employees(client)[0]["id"]
    for path in ["/api/promotion/employees", f"/api/promotion/employees/{some_id}", "/api/promotion/importance"]:
        assert client.get(path, headers=admin).status_code == 403


# ─── Running the model step by step ("Run prediction") ────────────────────────
def test_running_a_prediction_in_steps_gives_the_same_answer(client):
    hr = login(client, "hr")
    employee_id = employees(client)[0]["id"]
    profile = client.get(f"/api/promotion/employees/{employee_id}/profile", headers=hr).json()
    assert "score" not in profile and profile["model"]  # opening the page doesn't run the model
    run = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=hr).json()
    full = client.get(f"/api/promotion/employees/{employee_id}", headers=hr).json()
    assert run["score"] == full["score"] and run["contributions"] == full["contributions"]
    assert run["lime"] is None and run["duration_ms"] >= 0
    second = client.post(f"/api/promotion/employees/{employee_id}/lime", headers=hr).json()
    assert second["rules"] == full["lime"]["rules"]


def test_the_steps_follow_the_same_access_rules(client):
    team_ids = {e["id"] for e in employees(client, "manager")}
    outsider = next(e["id"] for e in employees(client) if e["id"] not in team_ids)
    manager = login(client, "manager")
    for path in ["profile"]:
        assert client.get(f"/api/promotion/employees/{outsider}/{path}", headers=manager).status_code == 403
    for path in ["predict", "lime"]:
        assert client.post(f"/api/promotion/employees/{outsider}/{path}", headers=manager).status_code == 403


def test_two_people_with_the_same_record_get_the_same_score_whatever_their_department():
    model = get_model()
    record = {f: model.stats[f]["mean"] for f in model.stats}
    scores = {model.score(record | {"department": d}) for d in model.info["departments"]}
    assert len(scores) == 1


def test_improving_any_input_never_lowers_the_score():
    """The monotonic model's promise, checked on the live model for a spread of records."""
    model = get_model()
    for record in model.background.sample(50, random_state=1).to_dict("records"):
        before = model.score(record)
        for feature in IMPROVABLE:
            step = FEATURE_INFO[feature]["improve"] * model.stats[feature]["std"]
            better = record | {feature: record[feature] + step}
            if feature == "performance_score":  # this year's score also moves the change since last year
                better["performance_change"] += step
            assert model.score(better) >= before - 1e-9, feature


def test_importance_directions_follow_the_constraints():
    from app.promotion.features import MONOTONE
    rows = {r["feature"]: r for r in get_model().importance}
    assert abs(sum(r["share"] for r in rows.values()) - 1) < 0.001
    for feature, direction in MONOTONE.items():
        if direction > 0:
            assert rows[feature]["direction"] in ("higher raises readiness", "no effect")
        elif direction < 0:
            assert rows[feature]["direction"] in ("higher lowers readiness", "no effect")


def test_the_model_page_lists_everything_the_model_never_uses(client):
    """Review B6: the page left department and other excluded information out, and hard-coded the sample size."""
    from app.promotion.features import EXCLUDED
    data = client.get("/api/promotion/importance", headers=login(client, "employee")).json()
    names = {n["name"] for n in data["never_used"]}
    assert {"department", "gender", "age", "salary"} <= names and len(names) == len(EXCLUDED)
    assert data["sample_size"] == len(get_model().background)
