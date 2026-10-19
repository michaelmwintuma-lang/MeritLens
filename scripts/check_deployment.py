"""
Check that a running MeritLens works end to end through the website's own address, the way a browser uses it:
    python scripts/check_deployment.py https://your-app.vercel.app
    python scripts/check_deployment.py http://127.0.0.1:5173            (the app on this PC: python run.py)

It asks for the demo accounts' password (DEMO_PASSWORD on the server) without showing it, or reads it from the
DEMO_PASSWORD environment variable. Then, for each role, it
signs in, checks the session cookie is safe, reads the account back, and signs out. It needs only Python, and it
changes nothing except signing the checked accounts out (signing out ends their sessions everywhere).

Other roles or accounts:   --users admin,hr
"""
import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request

WEBSITE = {"X-Requested-With": "MeritLens"}  # what the website sends (frontend/src/api.ts)
ROLES = ["admin", "hr", "manager", "employee", "finance", "auditor"]
problems = 0


def call(base, path, method="GET", body=None, cookie=None, website=True):
    """One request through the site's address. Returns (status, headers, parsed body or text)."""
    headers = dict(WEBSITE) if website else {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            status, head, raw = res.status, res.headers, res.read()
    except urllib.error.HTTPError as err:
        status, head, raw = err.code, err.headers, err.read()
    try:
        return status, head, json.loads(raw)
    except ValueError:
        return status, head, raw.decode("utf-8", "replace")


def check(ok, what, hint=""):
    global problems
    print(f"  {'pass' if ok else 'FAIL'}  {what}" + (f"\n        -> {hint}" if not ok and hint else ""))
    problems += not ok
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("site", help="the website's address, e.g. https://your-app.vercel.app")
    parser.add_argument("--users", default=",".join(ROLES), help="usernames to sign in as (default: the six demo roles)")
    args = parser.parse_args()
    base = args.site.rstrip("/")
    secure = base.startswith("https://")

    print(f"\nThe website ({base})")
    status, head, page = call(base, "/", website=False)
    check(status == 200 and isinstance(page, str) and "<title>MeritLens</title>" in page, "the website loads",
          "is this the right address, and did the Vercel build succeed (Root Directory: frontend)?")
    if secure:
        check("Content-Security-Policy" in head, "security headers are sent", "frontend/vercel.json wasn't applied")

    print("\nWebsite -> backend")
    status, _, health = call(base, "/api/health", website=False)
    if not check(status == 200 and isinstance(health, dict) and health.get("status") == "ok",
                 "/api/health reaches the backend through the website's address",
                 f"got {status}. In frontend/vercel.json, replace YOUR-BACKEND-ADDRESS with the backend's address, push, "
                 "and check https://<backend>/api/health answers {\"status\":\"ok\"}."):
        return finish()

    password = os.getenv("DEMO_PASSWORD") or getpass.getpass("\nThe demo accounts' password (not shown): ")
    for username in [u.strip() for u in args.users.split(",") if u.strip()]:
        print(f"\nSigning in as {username}")
        status, head, body = call(base, "/api/auth/login", "POST", {"username": username, "password": password})
        detail = body.get("detail") if isinstance(body, dict) else None
        if status == 401 and isinstance(detail, dict) and detail.get("code_required"):
            where = "their email" if detail.get("method") == "email" else "an authenticator app"
            print(f"  skip  this account needs a code from {where} at sign-in; check it in the browser")
            continue
        if not check(status == 200, "the password is accepted",
                     f"got {status}: {detail or body}. Is DEMO_PASSWORD on the backend the password you typed?"):
            continue
        check(body.get("access_token") is None, "the website gets no token it could leak (the cookie carries it)")
        set_cookie = head.get("Set-Cookie", "")
        flags = set_cookie.lower()
        check("httponly" in flags, "the session cookie is httpOnly (page scripts can't read it)")
        check("samesite=strict" in flags, "the session cookie is SameSite=Strict")
        if secure:
            check("secure" in flags, "the session cookie is Secure (sent over HTTPS only)",
                  "set APP_URL on the backend to the https:// website address")
        cookie = set_cookie.split(";", 1)[0]

        status, _, me = call(base, "/api/auth/me", cookie=cookie)
        check(status == 200 and me.get("username") == username, f"the backend knows who is signed in ({me.get('role') if isinstance(me, dict) else '?'})",
              "the cookie didn't come back: the website and the API must share one address (the /api rewrite)")
        status, _, _ = call(base, "/api/auth/logout", "POST", cookie=cookie, website=False)
        check(status == 403, "a change without the website's header is refused (cross-site request forgery guard)")
        status, _, _ = call(base, "/api/auth/logout", "POST", cookie=cookie)
        check(status == 200, "signing out works")
        status, _, _ = call(base, "/api/auth/me", cookie=cookie)
        check(status == 401, "after signing out, the old cookie no longer works")
    return finish()


def finish():
    print("\nAll checks passed." if not problems else f"\n{problems} check(s) failed: see the hints above.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
