"""
Development plans (app/development): the employee and their manager (and HR) add goals, often from the tips, and
tick them off; the other side is told. Others can't see a plan, admins only read it, and a plan never changes a
score (tests/test_isolation.py keeps the promotion code away from it).
"""
from tests.conftest import login


def team_member(client) -> int:
    """The demo employee: in the demo manager's team, with a sign-in of their own."""
    return client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]


def test_a_manager_and_the_employee_build_the_plan_and_tick_goals_off(client):
    person, manager, employee = team_member(client), login(client, "manager"), login(client, "employee")
    tip = client.get(f"/api/promotion/employees/{person}/tips", headers=manager).json()
    score_before = client.get(f"/api/promotion/employees/{person}", headers=manager).json()["score"]

    goal = client.post(f"/api/development/{person}/goals", headers=manager,
                       json={"title": "Do 35 hours of training", "feature": "training_hours_last_year", "target": 35,
                             "due": "2027-03-31"})
    assert goal.status_code == 201, goal.text
    assert client.post(f"/api/development/{person}/goals", headers=employee,
                       json={"title": "Do 35 hours of training"}).status_code == 409  # already in the plan
    bell = client.get("/api/notifications", headers=employee).json()
    assert any("new goal" in n["text"] for n in (bell["items"] if isinstance(bell, dict) else bell))

    done = client.patch(f"/api/development/goals/{goal.json()['id']}", headers=employee, json={"done": True}).json()
    assert done["done"] and done["done_by"]
    plan = client.get(f"/api/development/{person}", headers=manager).json()
    assert plan["can_change"] and [g["done"] for g in plan["goals"]] == [True]
    # Writing goals down changes nothing about the score
    assert client.get(f"/api/promotion/employees/{person}", headers=manager).json()["score"] == score_before
    assert tip is not None


def test_only_the_people_concerned_see_or_change_a_plan(client):
    person = team_member(client)
    hr = login(client, "hr")
    goal = client.post(f"/api/development/{person}/goals", headers=hr, json={"title": "Lead one project"}).json()
    for username in ("finance", "auditor"):
        assert client.get(f"/api/development/{person}", headers=login(client, username)).status_code == 403
    other = next(e["id"] for e in client.get("/api/promotion/employees", headers=hr).json()["employees"] if e["id"] != person)
    assert client.get(f"/api/development/{other}", headers=login(client, "employee")).status_code == 403
    assert client.delete(f"/api/development/goals/{goal['id']}", headers=login(client, "employee")).status_code == 204
    assert client.get(f"/api/development/{person}", headers=hr).json()["goals"] == []
