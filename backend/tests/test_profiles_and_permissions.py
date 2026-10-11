"""People update their own profiles; administration and employee accounts are kept apart; an admin can be allowed to
view employee data (read-only); managers are emailed when people join their team."""
import pytest

from tests.conftest import emails_to, login
from tests.test_employee_records import VALUES

PHOTO = "data:image/webp;base64,UklGRhYAAABXRUJQVlA4IAoAAAAwAQCdASoBAAEAAUAmJaQAA3AA/v89WAAAAA=="


# ─── My profile ───────────────────────────────────────────────────────────────
def test_people_see_their_work_details(client):
    profile = client.get("/api/auth/profile", headers=login(client, "employee")).json()
    assert profile["account"]["username"] == "employee"
    assert profile["work"]["department"] and profile["work"]["manager"] == "Mo Manager"
    assert client.get("/api/auth/profile", headers=login(client, "manager")).json()["work"]["team_size"] > 0


def test_people_update_their_name_phone_and_job_title(client):
    headers = login(client, "employee")
    me = client.patch("/api/auth/profile", headers=headers,
                      json={"full_name": "Eli Updated", "phone": "+44 20 7946 0000", "job_title": "Analyst"}).json()
    assert (me["full_name"], me["phone"], me["job_title"]) == ("Eli Updated", "+44 20 7946 0000", "Analyst")
    cleared = client.patch("/api/auth/profile", headers=headers, json={"phone": ""}).json()
    assert cleared["phone"] is None and cleared["job_title"] == "Analyst"  # only what was sent changes


def test_a_new_email_alerts_the_old_address(client):
    client.patch("/api/auth/profile", headers=login(client, "employee"), json={"email": "eli.new@example.org"})
    alert = emails_to("employee@example.org")[-1]
    assert alert["subject"] == "Your email address was changed" and "eli.new@example.org" in alert["text"]
    assert client.get("/api/auth/me", headers=login(client, "employee")).json()["email"] == "eli.new@example.org"


def test_profile_values_are_checked(client):
    headers = login(client, "employee")
    assert client.patch("/api/auth/profile", headers=headers, json={"email": "hr@example.org"}).status_code == 409
    assert client.patch("/api/auth/profile", headers=headers, json={"phone": "call me maybe"}).status_code == 422
    assert client.patch("/api/auth/profile", headers=headers, json={"full_name": "X"}).status_code == 422


def test_a_profile_photo_is_set_and_removed(client):
    headers = login(client, "manager")
    assert client.put("/api/auth/profile/photo", headers=headers, json={"photo": PHOTO}).json()["photo"] == PHOTO
    assert client.put("/api/auth/profile/photo", headers=headers, json={"photo": None}).json()["photo"] is None


def test_only_small_images_are_accepted_as_photos(client):
    headers = login(client, "manager")
    assert client.put("/api/auth/profile/photo", headers=headers, json={"photo": "data:text/html;base64,PGI+"}).status_code == 422
    huge = "data:image/png;base64," + "A" * 400_000
    assert client.put("/api/auth/profile/photo", headers=headers, json={"photo": huge}).status_code == 422


# ─── Administration and employee accounts apart ───────────────────────────────
@pytest.mark.parametrize("role", ["admin", "hr"])
def test_administration_accounts_are_not_linked_to_employee_records(client, role):
    employee_id = client.get("/api/admin/employees", headers=login(client, "admin")).json()[-1]["id"]
    res = client.post("/api/admin/users", headers=login(client, "admin"), json={
        "username": f"new.{role}", "full_name": "New Staff", "email": f"new.{role}@example.org", "role": role,
        "employee_id": employee_id})
    assert res.status_code == 422 and "Administration accounts" in res.json()["detail"]


# ─── Admins who may view employee data ────────────────────────────────────────
def admin_id(client):
    return client.get("/api/auth/me", headers=login(client, "admin")).json()["id"]


def test_admins_see_no_employee_data_until_allowed(client):
    admin = login(client, "admin")
    assert client.get("/api/promotion/employees", headers=admin).status_code == 403
    granted = client.patch(f"/api/admin/users/{admin_id(client)}/permissions", headers=admin, json={"can_view_employees": True})
    assert granted.json()["can_view_employees"] is True
    employees = client.get("/api/promotion/employees", headers=admin).json()["employees"]
    assert len(employees) > 0
    assert client.post(f"/api/promotion/employees/{employees[0]['id']}/predict", headers=admin).status_code == 200


def test_the_permission_is_read_only_and_never_includes_feedback(client):
    admin = login(client, "admin")
    client.patch(f"/api/admin/users/{admin_id(client)}/permissions", headers=admin, json={"can_view_employees": True})
    assert client.get("/api/promotion/nominations", headers=admin).status_code == 403
    assert client.get("/api/promotion/decisions", headers=admin).status_code == 403
    assert client.post("/api/promotion/records", headers=admin, json={"full_name": "X Y", "department": "Sales", "values": VALUES}).status_code == 403
    assert client.get("/api/hr/feedback/corrections", headers=admin).status_code == 403


def test_the_permission_can_be_taken_away_and_is_logged(client):
    admin = login(client, "admin")
    me = admin_id(client)
    client.patch(f"/api/admin/users/{me}/permissions", headers=admin, json={"can_view_employees": True})
    client.patch(f"/api/admin/users/{me}/permissions", headers=admin, json={"can_view_employees": False})
    assert client.get("/api/promotion/employees", headers=admin).status_code == 403
    actions = [e["action"] for e in client.get("/api/admin/activity", headers=admin).json()["entries"]]
    assert actions.count("permission_changed") == 2


def test_only_admin_accounts_can_be_given_the_permission(client):
    hr_id = client.get("/api/auth/me", headers=login(client, "hr")).json()["id"]
    res = client.patch(f"/api/admin/users/{hr_id}/permissions", headers=login(client, "admin"), json={"can_view_employees": True})
    assert res.status_code == 400
    me = admin_id(client)
    assert client.patch(f"/api/admin/users/{me}/permissions", headers=login(client, "hr"), json={"can_view_employees": True}).status_code == 403


# ─── Managers hear about new team members ─────────────────────────────────────
MANAGER_EMAIL = "manager@example.org"


def manager_id(client):
    return client.get("/api/auth/me", headers=login(client, "manager")).json()["id"]


def test_a_manager_is_emailed_when_hr_adds_someone_to_their_team(client):
    client.post("/api/promotion/records", headers=login(client, "hr"), json={
        "full_name": "Nia Joiner", "department": "Sales", "manager_user_id": manager_id(client), "values": VALUES})
    email = emails_to(MANAGER_EMAIL)[-1]
    assert email["subject"] == "Nia Joiner has joined your team"
    assert "%" not in email["text"]  # names only: no scores


def test_an_import_sends_each_manager_one_email(client):
    from tests.test_employee_records import csv_text
    before = len(emails_to(MANAGER_EMAIL))
    text = csv_text(("Ola One", "Sales", "manager", {}), ("Pat Two", "HR", "manager", {}), ("Quin Three", "HR", "", {}))
    client.post("/api/promotion/records/import", headers=login(client, "hr"), json={"csv": text, "save": True})
    emails = emails_to(MANAGER_EMAIL)
    assert len(emails) == before + 1 and emails[-1]["subject"] == "2 new team members"
    assert "Ola One" in emails[-1]["text"] and "Pat Two" in emails[-1]["text"] and "Quin Three" not in emails[-1]["text"]


def test_setting_a_team_emails_only_about_new_members(client):
    admin = login(client, "admin")
    mid = manager_id(client)
    directory = client.get("/api/admin/employees", headers=admin).json()
    current = [e["id"] for e in directory if e["manager_user_id"] == mid]
    newcomer = next(e for e in directory if e["manager_user_id"] is None)
    before = len(emails_to(MANAGER_EMAIL))
    client.put(f"/api/admin/users/{mid}/team", headers=admin, json={"employee_ids": current})  # nobody new
    assert len(emails_to(MANAGER_EMAIL)) == before
    client.put(f"/api/admin/users/{mid}/team", headers=admin, json={"employee_ids": current + [newcomer["id"]]})
    assert emails_to(MANAGER_EMAIL)[-1]["subject"] == f"{newcomer['full_name']} has joined your team"
