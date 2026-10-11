"""SQLite database connection, shared by every part of the backend."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import DATABASE_URL

# check_same_thread=False lets FastAPI use the connection from its worker threads
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Parent class of every database table."""


def get_db():
    """Give a request its own database session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns() -> None:
    """
    SQLite can't update an existing table by itself. When a new optional column is added to a table in the code,
    this adds it to an existing database too, so nobody has to delete their data after an update.
    """
    from sqlalchemy import inspect

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
    from sqlalchemy import inspect

    tables = inspect(engine)
    with engine.begin() as connection:
        for name in REMOVED_TABLES:
            if tables.has_table(name):
                connection.exec_driver_sql(f'DROP TABLE "{name}"')
        if tables.has_table("activity_log"):
            marks = ", ".join("?" for _ in REMOVED_ACTIONS)
            connection.exec_driver_sql(f"DELETE FROM activity_log WHERE action IN ({marks})", REMOVED_ACTIONS)
    if engine.url.database:
        shutil.rmtree(Path(engine.url.database).parent / "evidence", ignore_errors=True)
