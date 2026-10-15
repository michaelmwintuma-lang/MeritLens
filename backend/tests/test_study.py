"""
The user study inside the app: sessions with a code, never a name; a facilitator's link that needs no sign-in and
works only for its own session until it is finished; and the export in exactly the format evaluation/user_test.py
reads, with its report.
"""
import csv

import pytest

from app.study import routes as study
from app.study.protocol import ITEMS, TASKS
from evaluation import user_test
from tests.conftest import login


@pytest.fixture
def evaluation_folder(tmp_path, monkeypatch):
    """The analysis writes to a temporary folder, never to backend/evaluation or results/."""
    monkeypatch.setattr(study, "EVALUATION", tmp_path)
    monkeypatch.setattr(user_test, "SUS_FILE", tmp_path / "user_test_sus.csv")
    monkeypatch.setattr(user_test, "TASKS_FILE", tmp_path / "user_test_tasks.csv")
    monkeypatch.setattr(user_test, "RESULTS", tmp_path / "results")
    return tmp_path


def new_session(client):
    res = client.post("/api/study/sessions", headers=login(client, "admin"))
    assert res.status_code == 201, res.text
    return res.json()


def run_through(client, link, answer=4):
    token = link.rsplit("/", 1)[1]
    assert client.post(f"/api/study/run/{token}/consent").json()["consented"]
    for i, (task, *_ ) in enumerate(TASKS):
        res = client.post(f"/api/study/run/{token}/tasks", json={"task": task, "completed": "yes" if i % 3 else "help", "seconds": 60 + i})
        assert res.status_code == 200, res.text
    res = client.post(f"/api/study/run/{token}/finish", json={"answers": {k: answer for k in ITEMS},
                                                             "roles_played": "employee, manager and hr", "comments": "The menu was clear."})
    assert res.status_code == 200, res.text
    return token


def test_only_the_admin_starts_sessions_and_each_gets_the_next_code(client):
    for username in ("hr", "manager", "employee"):
        assert client.post("/api/study/sessions", headers=login(client, username)).status_code == 403
    first, second = new_session(client), new_session(client)
    assert (first["code"], second["code"]) == ("P1", "P2")
    assert first["link"].startswith("/study/") and first["link"] != second["link"]


def test_the_link_needs_consent_first_and_stops_working_when_finished(client):
    token = new_session(client)["link"].rsplit("/", 1)[1]
    protocol = client.get(f"/api/study/run/{token}").json()
    assert protocol["code"] == "P1" and len(protocol["tasks"]) == 11 and "anonymous" in protocol["consent"]
    assert client.post(f"/api/study/run/{token}/tasks", json={"task": "T1", "completed": "yes", "seconds": 30}).status_code == 409
    assert client.get("/api/study/run/not-a-real-link").status_code == 404
    run_through(client, f"/study/{token}")
    assert client.post(f"/api/study/run/{token}/tasks", json={"task": "T1", "completed": "no", "seconds": 1}).status_code == 409


def test_every_statement_needs_an_answer_from_1_to_5(client):
    token = new_session(client)["link"].rsplit("/", 1)[1]
    client.post(f"/api/study/run/{token}/consent")
    partial = {k: 3 for k in ITEMS[:-1]}
    assert client.post(f"/api/study/run/{token}/finish", json={"answers": partial, "roles_played": "employee"}).status_code == 422
    wrong = {k: 6 for k in ITEMS}
    assert client.post(f"/api/study/run/{token}/finish", json={"answers": wrong, "roles_played": "employee"}).status_code == 422


def test_saving_writes_the_files_the_analysis_reads_and_returns_its_report(client, evaluation_folder):
    admin = login(client, "admin")
    assert client.post("/api/study/analyse", headers=admin).status_code == 409  # nothing finished yet
    run_through(client, new_session(client)["link"], answer=4)
    run_through(client, new_session(client)["link"], answer=3)
    new_session(client)  # not finished: left out
    res = client.post("/api/study/analyse", headers=admin)
    assert res.status_code == 200, res.text
    assert res.json()["participants"] == 2 and "SUS" in res.json()["report"]
    with open(evaluation_folder / "user_test_sus.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["participant"] for r in rows] == ["P1", "P2"] and rows[0]["q1"] == "4"
    with open(evaluation_folder / "user_test_tasks.csv", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 22
    listed = client.get("/api/study/sessions", headers=admin).json()
    assert [s["finished"] for s in listed] == [False, True, True]
