"""The web API. Start it with:  uvicorn app.main:app --reload  (from the backend folder)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.accounts import routes_admin, routes_auth
from app.accounts.seed import seed_demo_accounts
from app.promotion import routes as promotion_routes
from app.promotion import routes_cycles, routes_decisions, routes_finance, routes_records, routes_teams
from app.public import routes as public_routes
from app.promotion.seed import round_whole_numbers, seed_demo_employees
from app.demo import routes as demo_routes
from app.feedback import routes as feedback_routes
from app.feedback import routes_hr as feedback_hr_routes
from app.feedback import dashboard as feedback_dashboard
from app.governance import routes as governance_routes
from app.study import routes as study_routes
from app.privacy import routes as privacy_routes
from app.governance.monitoring import seed_demo_monitoring
from app.governance.registry import ensure_live_registered
from app.core import approvals, notifications, reminders, scheduler  # noqa: F401 (reminders: its table)
from app.core.config import APP_NAME, APP_URL
from app.core import logs, migrations
from app.core.database import SessionLocal


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    On start-up: bring the database up to date (migrations: app/core/migrations.py), add demo accounts and
    employees to an empty database, and make sure the live model is in the model registry.
    """
    migrations.upgrade()
    with SessionLocal() as db:
        seed_demo_accounts(db)
        seed_demo_employees(db)
        round_whole_numbers(db)
        seed_demo_monitoring(db)
    ensure_live_registered()
    scheduler.start()  # email retries, reminders and daily digests (not in tests)
    yield
    scheduler.stop()


logs.configure()
app = FastAPI(title=APP_NAME, lifespan=lifespan)


@app.middleware("http")
async def security_headers(request, call_next):
    """
    Headers that close common holes: no sniffing content types, no showing the API inside another site's frame, no
    leaking addresses to other sites, no caching of personal data, and (over HTTPS) HTTPS only. The website's own
    headers, including its Content-Security-Policy, are set where it is served (vite.config.js, deploy/Caddyfile).
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if APP_URL.startswith("https://"):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.middleware("http")
async def log_requests(request, call_next):
    """
    Log every request with an id (core/logs.py). An unexpected error is logged in full, the person gets a short
    message quoting the id, and the admins are alerted once the answer has gone.
    """
    import re
    import time

    from fastapi.responses import JSONResponse
    from starlette.background import BackgroundTask

    given = request.headers.get("X-Request-ID", "")
    request_id = given if re.fullmatch(r"[A-Za-z0-9-]{1,64}", given) else logs.new_request_id()
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as error:  # noqa: BLE001 - anything not already turned into an answer
        route = request.scope.get("route")
        where = f"{request.method} {getattr(route, 'path', request.url.path)}"
        reference, alert = logs.report(where, error, request_id, alert_now=False)
        response = JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. If it happens "
                                f"again, please tell your administrator and quote reference {reference}."})
        if alert:
            response.background = BackgroundTask(logs.alert_admins, where, f"{type(error).__name__}: {str(error)[:300]}",
                                                 reference)
    response.headers["X-Request-ID"] = request_id
    logs.request_log.info("%s %s %s", request.method, request.url.path, response.status_code,
                          extra={"request_id": request_id, "method": request.method, "path": request.url.path,
                                 "status": response.status_code, "ms": round((time.perf_counter() - started) * 1000, 1)})
    return response
app.include_router(routes_auth.router)
app.include_router(notifications.router)
app.include_router(routes_admin.router)
app.include_router(routes_admin.employees_router)
app.include_router(routes_admin.activity_router)
app.include_router(routes_admin.email_router)
app.include_router(routes_admin.system_router)
app.include_router(promotion_routes.router)
app.include_router(routes_decisions.router)
app.include_router(routes_finance.router)
app.include_router(routes_records.router)
app.include_router(routes_cycles.router)
app.include_router(routes_teams.router)
app.include_router(public_routes.router)
app.include_router(feedback_routes.router)
app.include_router(feedback_hr_routes.router)
app.include_router(feedback_hr_routes.ratings_router)
app.include_router(feedback_dashboard.router)
app.include_router(governance_routes.router)
app.include_router(study_routes.router)
app.include_router(privacy_routes.router)
app.include_router(approvals.router)
app.include_router(demo_routes.router)
app.include_router(demo_routes.admin_router)


@app.get("/api/health")
def health():
    """Quick check that the API is running."""
    return {"status": "ok"}
