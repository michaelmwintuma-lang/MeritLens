"""
The database connection, shared by every part of the backend.

SQLite is the default: one file (instance/app.db), nothing to install. PostgreSQL works too: set DATABASE_URL to
postgresql+psycopg://user:password@host/meritlens (see deploy/postgres/README.md). With PostgreSQL, the promotion
code can also connect as its own database role (PROMOTION_DATABASE_URL) that has no access to the feedback and
equality-monitoring tables, so the database itself, not only the code, keeps feedback away from the model.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import DATABASE_URL, PROMOTION_DATABASE_URL


def make_engine(url: str):
    """An engine with the right options for its kind of database."""
    if url.startswith("sqlite"):
        # check_same_thread=False lets FastAPI use the connection from its worker threads
        return create_engine(url, connect_args={"check_same_thread": False})
    # A server database: check a pooled connection still works before using it (servers close idle ones)
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# The promotion code's own connection: a restricted database role when PROMOTION_DATABASE_URL is set, otherwise
# the same connection as everything else (SQLite has no roles; the code checks in tests/test_isolation.py apply).
promotion_engine = make_engine(PROMOTION_DATABASE_URL) if PROMOTION_DATABASE_URL else engine
PromotionSessionLocal = sessionmaker(bind=promotion_engine, autoflush=False)


class Base(DeclarativeBase):
    """Parent class of every database table."""


def is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"


def get_db():
    """Give a request its own database session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_promotion_db():
    """The same, for the promotion code: through its restricted role when one is configured."""
    db = PromotionSessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns() -> None:
    """
    SQLite can't update an existing table by itself. When a new optional column is added to a table in the code,
    this adds it to an existing database too, so nobody has to delete their data after an update.
    """
    existing_tables = inspect(engine)
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if not existing_tables.has_table(table.name):
                continue
            have = {column["name"] for column in existing_tables.get_columns(table.name)}
            for column in table.columns:
                if column.name not in have and column.nullable:
                    connection.exec_driver_sql(
                        f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column.type.compile(engine.dialect)}')


# Anonymous reporting was removed from this version (see git tag with-anonymous-reporting). A database made by an
# earlier version still holds its tables, its activity-log entries and its evidence files; they are removed once.
REMOVED_TABLES = ("report_evidence", "report_messages", "reports")
REMOVED_ACTIONS = ("report_replied", "report_updated", "reappraisal_started")


def drop_removed_reporting() -> None:
    """
    Remove anonymous reporting's tables, activity-log entries and evidence folder, if an older version left them.
    The evidence folder was kept next to the database file (backend/instance/evidence).
    """
    import shutil
    from pathlib import Path

    tables = inspect(engine)
    with engine.begin() as connection:
        for name in REMOVED_TABLES:
            if tables.has_table(name):
                connection.exec_driver_sql(f'DROP TABLE "{name}"')
        if tables.has_table("activity_log"):
            for action in REMOVED_ACTIONS:  # bound parameters: the same SQL works on SQLite and PostgreSQL
                connection.execute(text("DELETE FROM activity_log WHERE action = :action"), {"action": action})
    if is_sqlite() and engine.url.database:
        shutil.rmtree(Path(engine.url.database).parent / "evidence", ignore_errors=True)


def move_deferrals_to_holds() -> None:
    """
    Earlier versions kept "decision on hold" in the feedback part's nomination_deferrals table, which the promotion
    code may not read, so a hold could only be advisory. Holds now live in the neutral decision_holds table
    (app/core/holds.py) that the decision code checks. Move any old ones across once, then drop the old table.
    """
    if not inspect(engine).has_table("nomination_deferrals"):
        return
    with engine.begin() as connection:
        rows = connection.execute(text(
            "SELECT nomination_id, deferred_by_name, deferred_at, lifted_at, lifted_because FROM nomination_deferrals")).all()
        for row in rows:
            connection.execute(text(
                "INSERT INTO decision_holds (nomination_id, reason, placed_by_name, placed_at, lifted_at, lifted_because) "
                "VALUES (:n, 'correction_pending', :by, :at, :lifted, :because)"),
                {"n": row[0], "by": row[1], "at": row[2], "lifted": row[3], "because": row[4]})
        connection.exec_driver_sql('DROP TABLE "nomination_deferrals"')
