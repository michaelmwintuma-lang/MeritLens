"""The web API. Start it with:  uvicorn app.main:app --reload  (from the backend folder)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.accounts import routes_admin, routes_auth
from app.accounts.seed import seed_demo_accounts
from app.promotion import routes as promotion_routes
from app.promotion import routes_decisions, routes_finance, routes_records
from app.public import routes as public_routes
from app.promotion.seed import seed_demo_employees
from app.demo import routes as demo_routes
from app.feedback import routes as feedback_routes
from app.feedback import routes_hr as feedback_hr_routes
from app.feedback import dashboard as feedback_dashboard
from app.core.config import APP_NAME
from app.core.database import Base, SessionLocal, add_missing_columns, drop_removed_reporting, engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """On start-up: create any missing tables, then add demo accounts and employees to an empty database."""
    Base.metadata.create_all(engine)
    add_missing_columns()
    drop_removed_reporting()
    with SessionLocal() as db:
        seed_demo_accounts(db)
        seed_demo_employees(db)
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
app.include_router(routes_auth.router)
app.include_router(routes_admin.router)
app.include_router(routes_admin.employees_router)
app.include_router(routes_admin.activity_router)
app.include_router(routes_admin.email_router)
app.include_router(routes_admin.system_router)
app.include_router(promotion_routes.router)
app.include_router(routes_decisions.router)
app.include_router(routes_finance.router)
app.include_router(routes_records.router)
app.include_router(public_routes.router)
app.include_router(feedback_routes.router)
app.include_router(feedback_hr_routes.router)
app.include_router(feedback_hr_routes.ratings_router)
app.include_router(feedback_dashboard.router)
app.include_router(demo_routes.router)
app.include_router(demo_routes.admin_router)


@app.get("/api/health")
def health():
    """Quick check that the API is running."""
    return {"status": "ok"}
