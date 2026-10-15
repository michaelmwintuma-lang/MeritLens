"""
Sign-in through an httpOnly session cookie (the website), alongside "Authorization: Bearer" (API clients).

The website never sees the login token: it lives in a cookie page scripts can't read. A state-changing request that
relies on the cookie must carry X-Requested-With, which another site's form can't add.
"""
from app.core.config import SESSION_COOKIE

WEBSITE = {"X-Requested-With": "MeritLens"}


def sign_in_as_website(client, username="hr"):
    res = client.post("/api/auth/login", json={"username": username, "password": "demo1234"}, headers=WEBSITE)
    assert res.status_code == 200, res.text
    return res


def test_the_website_gets_a_cookie_and_never_the_token(client):
    res = sign_in_as_website(client)
    assert res.json()["access_token"] is None and res.json()["user"]["username"] == "hr"
    cookie = res.headers["set-cookie"].lower()
    assert SESSION_COOKIE in cookie and "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
    assert client.get("/api/auth/me").json()["username"] == "hr"  # the cookie alone signs the browser in


def test_api_clients_still_get_a_token(client):
    res = client.post("/api/auth/login", json={"username": "hr", "password": "demo1234"})
    assert res.json()["access_token"]


def test_a_state_changing_request_with_only_the_cookie_needs_the_website_header(client):
    sign_in_as_website(client)
    body = {"full_name": "Hana Updated"}
    refused = client.patch("/api/auth/profile", json=body)  # as if another site submitted a form
    assert refused.status_code == 403
    assert client.patch("/api/auth/profile", json=body, headers=WEBSITE).status_code == 200
    assert client.get("/api/auth/me").status_code == 200  # reading needs no header


def test_signing_out_removes_the_cookie_and_withdraws_the_session(client):
    sign_in_as_website(client)
    stolen = client.cookies.get(SESSION_COOKIE, path="/api") or next(iter(client.cookies.values()))
    res = client.post("/api/auth/logout", headers=WEBSITE)
    assert res.status_code == 200 and SESSION_COOKIE in res.headers["set-cookie"]
    assert client.get("/api/auth/me").status_code == 401
    # Even a copy of the old cookie no longer works
    client.cookies.set(SESSION_COOKIE, stolen, path="/api")
    assert client.get("/api/auth/me").status_code == 401


def test_changing_the_password_renews_the_cookie(client):
    sign_in_as_website(client, "employee")
    res = client.post("/api/auth/change-password", headers=WEBSITE,
                      json={"current_password": "demo1234", "new_password": "a-much-longer-password-1"})
    assert res.status_code == 200, res.text
    assert res.json()["access_token"] is None and SESSION_COOKIE in res.headers["set-cookie"]
    assert client.get("/api/auth/me").json()["username"] == "employee"
