"""Book a demo: anyone can ask, the request is emailed and listed for the admin, and robots are kept out."""
import pytest

from app.demo import routes as demo
from tests.conftest import emails_to, login

REQUEST = {"name": "Grace Visitor", "email": "grace@company.example", "organisation": "Acme Ltd", "job_title": "HR Director",
           "size": "250–999", "interest": "Both", "message": "We'd like to see the feedback side."}


@pytest.fixture(autouse=True)
def fresh_limits():
    demo._recent.clear()  # the hourly limit is kept in memory; start each test from zero


def ask(client, **changes):
    return client.post("/api/public/demo-requests", json={**REQUEST, **changes})


def test_anyone_can_book_a_demo_without_signing_in(client):
    res = ask(client)
    assert res.status_code == 201 and res.json()["ok"] is True


def test_the_request_is_emailed_with_reply_to_the_visitor(client):
    ask(client)
    email = emails_to(demo.DEMO_INBOX or "demo-requests")[-1]
    assert email["subject"] == "Demo request: Acme Ltd"
    assert "Grace Visitor" in email["text"] and "HR Director" in email["text"] and "feedback side" in email["text"]
    assert email["reply_to"] == "grace@company.example"


def test_the_admin_sees_requests_and_ticks_them_off(client):
    ask(client)
    admin = login(client, "admin")
    request = client.get("/api/admin/demo-requests", headers=admin).json()[0]
    assert request["organisation"] == "Acme Ltd" and request["handled"] is False
    client.patch(f"/api/admin/demo-requests/{request['id']}", headers=admin, json={"handled": True})
    assert client.get("/api/admin/demo-requests", headers=admin).json()[0]["handled"] is True


def test_robots_filling_the_hidden_box_are_thanked_but_not_saved(client):
    assert ask(client, website="http://spam.example").json()["ok"] is True
    assert client.get("/api/admin/demo-requests", headers=login(client, "admin")).json() == []


def test_bad_details_are_refused(client):
    assert ask(client, email="not-an-email").status_code == 422
    assert ask(client, size="huge").status_code == 422
    assert ask(client, name="").status_code == 422


def test_the_same_email_can_ask_only_three_times_a_day(client):
    for _ in range(3):
        assert ask(client).status_code == 201
    assert ask(client, email="GRACE@company.example").status_code == 429  # same address, different capitals


def test_html_in_a_request_is_shown_as_text_in_the_email(client):
    ask(client, organisation="<script>alert(1)</script> Ltd")
    email = emails_to(demo.DEMO_INBOX or "demo-requests")[-1]
    assert "<script>" not in email["html"] and "&lt;script&gt;" in email["html"]


@pytest.mark.parametrize("username", ["employee", "manager", "hr"])
def test_only_the_admin_sees_demo_requests(client, username):
    headers = login(client, username)
    assert client.get("/api/admin/demo-requests", headers=headers).status_code == 403
    assert client.patch("/api/admin/demo-requests/1", headers=headers, json={"handled": True}).status_code == 403
