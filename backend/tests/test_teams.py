"""
Teams: HR owns reporting lines, with a queue of everyone without a manager; reporting lines chain upwards so a
manager sees their whole branch (read-only beyond their own team) and can never loop; cover while a manager is away.
"""
from datetime import date, timedelta

from app.accounts.models import User
from app.core.database import SessionLocal
from tests.conftest import emails_to, login, recommendation


def overview(client):
    return client.get("/api/promotion/teams", headers=login(client, "hr")).json()


def assign(client, ids, manager_id, expect=200):
    res = client.put("/api/promotion/teams/assign", headers=login(client, "hr"),
                     json={"employee_ids": ids, "manager_user_id": manager_id})
    assert res.status_code == expect, res.text
    return res


def user_id(client, username):
    return client.get("/api/auth/me", headers=login(client, username)).json()["id"]


def second_manager(client, employee_id):
    """A second manager account ("kim"), linked to their own employee record."""
    res = client.post("/api/admin/users", headers=login(client, "admin"), json={
        "username": "kim", "full_name": "Kim Lead", "email": "kim@example.org", "role": "manager",
        "job_title": "Team lead", "employee_id": employee_id})
    assert res.status_code == 201, res.text
    with SessionLocal() as db:  # sign-in with the temporary password works; choose a known one for the test
        from app.core.security import hash_password
        kim = db.get(User, res.json()["user"]["id"])
        kim.password_hash, kim.must_change_password = hash_password("demo1234"), False
        db.commit()
        return kim.id


def test_hr_sees_every_manager_and_everyone_without_one(client):
    data = overview(client)
    [mo] = data["managers"]
    assert mo["full_name"] == "Mo Manager" and mo["direct"] == 12 and mo["reports_to"] is None
    assert len(data["unassigned"]) == data["employees"] - 12
    for username in ("manager", "employee", "admin", "auditor", "finance"):
        assert client.get("/api/promotion/teams", headers=login(client, username)).status_code == 403


def test_hr_assigns_people_and_the_manager_is_told(client):
    mo = user_id(client, "manager")
    people = [p["id"] for p in overview(client)["unassigned"][:3]]
    assert assign(client, people, mo).json()["moved"] == 3
    team = client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]
    assert {p for p in people} <= {e["id"] for e in team}
    assert all(e["relation"] == "direct" for e in team)
    assert any("joined your team" in e["subject"] or "new team members" in e["subject"] for e in emails_to("manager@example.org"))
    events = client.get("/api/governance/audit", headers=login(client, "auditor"), params={"event": "team_changed"}).json()
    assert events["total"] == 3


def test_a_branch_is_seen_read_only_and_only_its_own_manager_nominates(client):
    mo = user_id(client, "manager")
    free = [p["id"] for p in overview(client)["unassigned"]]
    kim_record, kim_team = free[0], free[1:4]
    kim = second_manager(client, kim_record)
    assign(client, [kim_record], mo)           # Kim reports to Mo
    assign(client, kim_team, kim)              # and manages three people

    seen = {e["id"]: e for e in client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]}
    assert seen[kim_record]["relation"] == "direct"
    assert all(seen[p]["relation"] == "branch" and seen[p]["manager"] == "Kim Lead" for p in kim_team)
    assert client.get(f"/api/promotion/employees/{kim_team[0]}", headers=login(client, "manager")).status_code == 200
    refused = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(kim_team[0]))
    assert refused.status_code == 403
    allowed = client.post("/api/promotion/nominations", headers=login(client, "kim"), json=recommendation(kim_team[0]))
    assert allowed.status_code == 201, allowed.text
    # Kim sees only her own team, not Mo's
    kims = {e["id"] for e in client.get("/api/promotion/employees", headers=login(client, "kim")).json()["employees"]}
    assert kims == set(kim_team)
    # The org chart lists Kim under Mo
    rows = {m["full_name"]: m for m in overview(client)["managers"]}
    assert rows["Kim Lead"]["reports_to"] == "Mo Manager" and rows["Mo Manager"]["branch"] == 3


def test_a_reporting_line_never_loops(client):
    mo = user_id(client, "manager")
    free = [p["id"] for p in overview(client)["unassigned"]]
    kim = second_manager(client, free[0])
    assign(client, [free[0]], mo)                       # Kim reports to Mo
    with SessionLocal() as db:                          # Mo's own record
        db.get(User, mo).employee_id = free[1]
        db.commit()
    res = assign(client, [free[1]], kim, expect=409)    # so Mo can't report to Kim
    assert "circle" in res.json()["detail"]
    assign(client, [free[0]], kim, expect=409)          # nor Kim to herself


def test_cover_lets_another_manager_act_for_a_team_for_its_dates(client):
    mo = user_id(client, "manager")
    free = [p["id"] for p in overview(client)["unassigned"]]
    kim = second_manager(client, free[0])
    assign(client, free[1:3], kim)
    today = date.today()

    # Kim arranges cover for herself; she can't arrange it for someone else
    assert client.post("/api/promotion/teams/covers", headers=login(client, "kim"), json={
        "manager_user_id": mo, "cover_user_id": kim, "starts": today.isoformat(), "ends": today.isoformat()}).status_code == 403
    cover = client.post("/api/promotion/teams/covers", headers=login(client, "kim"), json={
        "cover_user_id": mo, "starts": today.isoformat(), "ends": (today + timedelta(days=7)).isoformat(), "note": "Annual leave"})
    assert cover.status_code == 201, cover.text
    assert cover.json()["status"] == "active"
    overlap = client.post("/api/promotion/teams/covers", headers=login(client, "hr"), json={
        "manager_user_id": kim, "cover_user_id": mo, "starts": today.isoformat(), "ends": today.isoformat()})
    assert overlap.status_code == 409

    seen = {e["id"]: e["relation"] for e in client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]}
    assert seen[free[1]] == "cover"
    nominated = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(free[1]))
    assert nominated.status_code == 201, nominated.text
    # Kim sees the nomination made for her team while she was away
    assert any(n["employee"]["id"] == free[1] for n in client.get("/api/promotion/nominations", headers=login(client, "kim")).json())
    profile = client.get(f"/api/promotion/employees/{free[2]}/profile", headers=login(client, "hr")).json()
    assert profile["manager"] == "Kim Lead" and profile["cover"]["name"] == "Mo Manager"

    ended = client.post(f"/api/promotion/teams/covers/{cover.json()['id']}/end", headers=login(client, "kim"))
    assert ended.json()["status"] == "ended"
    assert client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(free[2])).status_code == 403


def test_cover_dates_are_checked(client):
    mo = user_id(client, "manager")
    kim = second_manager(client, overview(client)["unassigned"][0]["id"])
    hr, today = login(client, "hr"), date.today()
    for starts, ends in ((today - timedelta(days=1), today), (today, today + timedelta(days=200)), (today + timedelta(days=3), today)):
        res = client.post("/api/promotion/teams/covers", headers=hr, json={
            "manager_user_id": kim, "cover_user_id": mo, "starts": starts.isoformat(), "ends": ends.isoformat()})
        assert res.status_code == 422
    same = client.post("/api/promotion/teams/covers", headers=hr, json={
        "manager_user_id": mo, "cover_user_id": mo, "starts": today.isoformat(), "ends": today.isoformat()})
    assert same.status_code == 422


def test_an_employee_page_names_their_manager(client):
    own = client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]
    profile = client.get(f"/api/promotion/employees/{own}/profile", headers=login(client, "employee")).json()
    assert profile["manager"] == "Mo Manager" and profile["cover"] is None
