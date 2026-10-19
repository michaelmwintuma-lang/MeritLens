"""
Database migrations (app/core/migrations.py): a new database is built by them, a database made before they existed
is repaired and brought under them without losing data, and running them again changes nothing.
"""
from sqlalchemy import inspect, text

from app.core import migrations
from app.core.database import Base, engine
from tests.conftest import login


def test_a_new_database_is_built_by_the_migrations_and_marked_up_to_date(client):
    assert migrations.current_revision() == migrations.head_revision() == "0004_email_sign_in_codes"
    tables = set(inspect(engine).get_table_names())
    assert {"users", "employees", "audit_events", "approvals", "alembic_version"} <= tables


def test_a_database_from_before_migrations_keeps_its_data_and_gets_new_columns(client):
    hr = login(client, "hr")
    before = client.get("/api/promotion/employees", headers=hr).json()["employees"]
    # As an older version left it: no record of migrations, and a column added since missing
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE alembic_version")
        connection.exec_driver_sql('ALTER TABLE users DROP COLUMN "totp_secret"')
    assert migrations.before_migrations_existed()

    migrations.upgrade()
    assert migrations.current_revision() == migrations.head_revision()
    assert "totp_secret" in {c["name"] for c in inspect(engine).get_columns("users")}
    assert client.get("/api/promotion/employees", headers=login(client, "hr")).json()["employees"] == before


def test_a_database_at_the_baseline_gets_the_later_migrations(client):
    with engine.begin() as connection:
        connection.exec_driver_sql('ALTER TABLE users DROP COLUMN "guide_done"')
        connection.exec_driver_sql("UPDATE alembic_version SET version_num = '0001_baseline'")
    migrations.upgrade()
    assert migrations.current_revision() == migrations.head_revision()
    assert "guide_done" in {c["name"] for c in inspect(engine).get_columns("users")}


def test_running_the_migrations_again_changes_nothing(client):
    with engine.connect() as connection:
        users = connection.execute(text("SELECT COUNT(*) FROM users")).scalar()
    migrations.upgrade()
    migrations.upgrade()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar() == users
        assert connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar() == 1


def test_the_migrations_know_every_table_the_code_defines():
    """A table defined in a module missing from TABLE_MODULES would never be created by the baseline."""
    from pathlib import Path
    import app
    defined = {str(p.relative_to(Path(app.__file__).parent.parent).with_suffix("")).replace("\\", ".").replace("/", ".")
               for p in Path(app.__file__).parent.rglob("*.py") if "__tablename__" in p.read_text(encoding="utf-8")}
    assert defined == set(migrations.TABLE_MODULES)
    migrations.load_all_tables()
    assert "approvals" in Base.metadata.tables
