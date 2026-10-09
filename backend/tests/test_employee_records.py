"""HR adds employees (one at a time or from a CSV file), edits records, and the new people can be scored at once."""
import pytest

from app.promotion.records import CSV_COLUMNS
from tests.conftest import login

# A plausible employee, entered the way HR would type it (percentages for rates, last year's score)
VALUES = {
    "performance_score": 88, "performance_last_year": 80, "manager_rating": 4.2, "peer_feedback_score": 4.0,
    "kpi_achievement_percent": 85, "projects_completed": 6, "tasks_completed": 40, "deadline_adherence_rate": 92,
    "innovation_score": 75, "leadership_score": 80, "problem_solving_score": 70, "skill_assessment_score": 78,
    "training_hours_last_year": 40, "certifications_count": 3, "cross_department_projects": 2, "mentoring_sessions": 4,
    "attendance_rate": 96, "late_days": 1, "years_since_last_promotion": 3, "years_in_current_role": 3,
}


def add(client, name="Ada Newcomer", department="Engineering", **changes):
    return client.post("/api/promotion/records", headers=login(client, "hr"),
                       json={"full_name": name, "department": department, "values": {**VALUES, **changes}})


def csv_text(*rows):
    lines = [",".join(CSV_COLUMNS)]
    for name, department, manager, changes in rows:
        values = {**VALUES, **changes}
        lines.append(",".join([name, department, manager, *[str(values[c]) for c in CSV_COLUMNS[3:]]]))
    return "\n".join(lines)


# ─── Adding one employee ──────────────────────────────────────────────────────
def test_hr_adds_an_employee_who_can_be_scored_straight_away(client):
    res = add(client)
    assert res.status_code == 201 and res.json()["warnings"] == {}
    employee_id = res.json()["id"]
    hr = login(client, "hr")
    scored = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=hr).json()
    assert scored["full_name"] == "Ada Newcomer" and 0 <= scored["score"] <= 1
    # The admin can now link a login to them
    directory = client.get("/api/admin/employees", headers=login(client, "admin")).json()
    assert any(e["id"] == employee_id and e["login"] is None for e in directory)


def test_values_are_stored_as_the_model_expects_them(client):
    employee_id = add(client).json()["id"]
    stored = client.get(f"/api/promotion/records/{employee_id}", headers=login(client, "hr")).json()["values"]
    # What HR typed comes back the same, so the edit form shows familiar numbers...
    assert stored["performance_last_year"] == 80 and stored["attendance_rate"] == 96
    # ...and the model gets the change since last year and rates as 0-1, like in training
    explained = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=login(client, "hr")).json()
    values = {c["feature"]: c["value"] for c in explained["contributions"]}
    assert values["performance_change"] == pytest.approx(8) and values["attendance_rate"] == pytest.approx(0.96)


def test_impossible_values_are_refused_with_every_problem_listed(client):
    res = add(client, manager_rating=7, late_days=-1, certifications_count=2.5, leadership_score="lots")
    assert res.status_code == 422
    fields = res.json()["detail"]["fields"]
    assert set(fields) == {"manager_rating", "late_days", "certifications_count", "leadership_score"}


def test_missing_values_and_unknown_departments_are_refused(client):
    values = {k: v for k, v in VALUES.items() if k != "attendance_rate"}
    res = client.post("/api/promotion/records", headers=login(client, "hr"),
                      json={"full_name": "No Attendance", "department": "Astronomy", "values": values})
    assert set(res.json()["detail"]["fields"]) == {"attendance_rate", "department"}


def test_unusual_but_possible_values_are_saved_with_a_warning(client):
    res = add(client, training_hours_last_year=600)
    assert res.status_code == 201 and "training_hours_last_year" in res.json()["warnings"]


def test_the_same_person_cannot_be_added_twice(client):
    add(client)
    assert add(client).status_code == 422
    assert add(client, department="Finance").status_code == 201  # same name, another department: someone else


def test_no_protected_characteristics_or_pay_are_accepted(client):
    employee_id = add(client, gender="Female", age=50, salary=90000).json()["id"]
    stored = client.get(f"/api/promotion/records/{employee_id}", headers=login(client, "hr")).json()["values"]
    assert not {"gender", "age", "salary"} & set(stored)


# ─── Editing ──────────────────────────────────────────────────────────────────
def test_hr_edits_a_record_and_the_score_follows(client):
    employee_id = add(client).json()["id"]
    hr = login(client, "hr")
    before = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=hr).json()["score"]
    record = client.get(f"/api/promotion/records/{employee_id}", headers=hr).json()
    record["values"]["leadership_score"] = 30
    assert client.put(f"/api/promotion/records/{employee_id}", headers=hr, json=record).status_code == 200
    after = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=hr).json()["score"]
    assert after < before


# ─── Importing a CSV file ─────────────────────────────────────────────────────
def test_a_csv_is_checked_first_and_saved_only_when_asked(client):
    hr = login(client, "hr")
    text = csv_text(("Bea One", "Sales", "manager", {}), ("Cal Two", "Finance", "", {"late_days": 4}))
    check = client.post("/api/promotion/records/import", headers=hr, json={"csv": text}).json()
    assert check["total"] == 2 and check["failed"] == 0 and check["saved"] == 0
    saved = client.post("/api/promotion/records/import", headers=hr, json={"csv": text, "save": True}).json()
    assert saved["saved"] == 2
    team = client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]
    assert any(e["full_name"] == "Bea One" for e in team)  # the manager column put her on the team


def test_one_bad_row_means_nobody_is_imported(client):
    hr = login(client, "hr")
    text = csv_text(("Dee Good", "Sales", "", {}), ("Eve Bad", "Sales", "nobody", {"manager_rating": 9}))
    res = client.post("/api/promotion/records/import", headers=hr, json={"csv": text, "save": True}).json()
    assert res["failed"] == 1 and res["saved"] == 0
    bad = res["rows"][1]
    assert bad["line"] == 3 and len(bad["errors"]) == 2  # the rating and the unknown manager
    names = [e["full_name"] for e in client.get("/api/promotion/employees", headers=hr).json()["employees"]]
    assert "Dee Good" not in names


def test_importing_the_same_file_twice_is_refused(client):
    hr = login(client, "hr")
    text = csv_text(("Fay Twice", "Support", "", {}))
    client.post("/api/promotion/records/import", headers=hr, json={"csv": text, "save": True})
    again = client.post("/api/promotion/records/import", headers=hr, json={"csv": text, "save": True}).json()
    assert again["saved"] == 0 and "already in the directory" in again["rows"][0]["errors"][0]


def test_a_file_without_the_right_columns_is_explained(client):
    res = client.post("/api/promotion/records/import", headers=login(client, "hr"), json={"csv": "name,score\nA,1"})
    assert res.status_code == 422 and "missing these columns" in res.json()["detail"]


# ─── Who may do this ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("username", ["employee", "manager", "admin"])
def test_only_hr_manages_employee_records(client, username):
    headers = login(client, username)
    assert client.get("/api/promotion/records/fields", headers=headers).status_code == 403
    assert client.post("/api/promotion/records", headers=headers,
                       json={"full_name": "X Y", "department": "Sales", "values": VALUES}).status_code == 403
    assert client.post("/api/promotion/records/import", headers=headers, json={"csv": "a"}).status_code == 403


def test_adding_and_importing_are_in_the_activity_log(client):
    add(client)
    client.post("/api/promotion/records/import", headers=login(client, "hr"),
                json={"csv": csv_text(("Gus Log", "HR", "", {})), "save": True})
    actions = [e["action"] for e in client.get("/api/admin/activity", headers=login(client, "admin")).json()["entries"]]
    assert "employee_added" in actions and "employees_imported" in actions


# ─── Record history (review B7) ───────────────────────────────────────────────
def test_an_edit_keeps_old_and_new_values_the_scores_and_the_model_version(client):
    employee_id = add(client).json()["id"]
    hr = login(client, "hr")
    record = client.get(f"/api/promotion/records/{employee_id}", headers=hr).json()
    before = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=hr).json()
    record["values"]["projects_completed"] = 9
    record["reason"] = "Two projects were missing from the review form."
    client.put(f"/api/promotion/records/{employee_id}", headers=hr, json=record)
    after = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=hr).json()

    [entry] = client.get(f"/api/promotion/records/{employee_id}/history", headers=hr).json()
    assert entry["changes"] == [{"field": "projects_completed", "old": 6, "new": 9, "label": "Projects completed",
                                 "old_display": "6", "new_display": "9"}]
    assert entry["changed_by"] == "Hana Reviewer" and entry["source"] == "hr_edit"
    assert entry["reason"] == "Two projects were missing from the review form."
    assert entry["score_before"] == before["score"] and entry["score_after"] == after["score"]
    assert entry["model_version"] == before["model_version"]


def test_an_edit_that_changes_no_input_adds_nothing_to_the_history(client):
    employee_id = add(client).json()["id"]
    hr = login(client, "hr")
    record = client.get(f"/api/promotion/records/{employee_id}", headers=hr).json()
    client.put(f"/api/promotion/records/{employee_id}", headers=hr, json=record | {"full_name": "Ada Renamed"})
    assert client.get(f"/api/promotion/records/{employee_id}/history", headers=hr).json() == []


@pytest.mark.parametrize("username, allowed", [("hr", True), ("auditor", True), ("manager", False), ("employee", False)])
def test_who_may_read_a_records_history(client, username, allowed):
    employee_id = add(client).json()["id"]
    res = client.get(f"/api/promotion/records/{employee_id}/history", headers=login(client, username))
    assert (res.status_code == 200) == allowed


def test_the_history_cannot_be_changed_or_deleted(client):
    employee_id = add(client).json()["id"]
    hr = login(client, "hr")
    for method in ("PUT", "PATCH", "DELETE"):
        assert client.request(method, f"/api/promotion/records/{employee_id}/history", headers=hr).status_code == 405
