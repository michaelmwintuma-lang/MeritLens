"""
Database migrations with Alembic (backend/migrations). The app brings its database up to date by itself at start-up:

1. A database made before migrations existed (no alembic_version table) first gets the one-off repairs earlier
   versions ran at every start: optional columns added, removed features' tables dropped, old holds moved.
2. Then every migration it hasn't had yet is applied, in order, and recorded in alembic_version.

So an update never asks anyone to delete their data, on SQLite or PostgreSQL. To change a table: change the model,
then from the backend folder run   .venv/Scripts/python.exe -m alembic revision --autogenerate -m "what changed"
check the new file in migrations/versions (use migrations/helpers.py so it works on old and new databases alike),
and commit it with the change.
"""
import importlib
from pathlib import Path

from sqlalchemy import inspect

from app.core.database import engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
TABLE_MODULES = ("app.accounts.models", "app.core.activity", "app.core.approvals", "app.core.audit", "app.core.holds",
                 "app.core.mailer", "app.core.notifications", "app.core.reminders", "app.demo.models",
                 "app.feedback.models", "app.governance.models", "app.promotion.models", "app.study.models")


def load_all_tables() -> None:
    """Import every module that defines a table, so the metadata knows them all."""
    for name in TABLE_MODULES:
        importlib.import_module(name)


def alembic_config():
    from alembic.config import Config
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def before_migrations_existed() -> bool:
    tables = inspect(engine)
    return not tables.has_table("alembic_version") and tables.has_table("users")


def upgrade() -> None:
    """Bring the database up to date (see above). Running it again changes nothing."""
    from alembic import command
    from app.core.database import Base, add_missing_columns, drop_removed_reporting, move_deferrals_to_holds

    load_all_tables()
    if before_migrations_existed():
        Base.metadata.create_all(engine)  # tables added since (e.g. decision_holds, which the next step fills)
        add_missing_columns()
        drop_removed_reporting()
        move_deferrals_to_holds()
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    add_missing_columns()  # a safety net: an optional column added to a model without its migration


def current_revision() -> str | None:
    from alembic.runtime.migration import MigrationContext
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def head_revision() -> str:
    from alembic.script import ScriptDirectory
    return ScriptDirectory.from_config(alembic_config()).get_current_head()
