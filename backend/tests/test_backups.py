"""
Backups (app/core/backups.py): a consistent copy of the database with the correction evidence and a checksummed
manifest; the oldest beyond BACKUP_KEEP removed; a damaged backup refused; a restore that keeps today's data aside.
"""
import sqlite3
import zipfile
from contextlib import closing

import pytest

from app.core import backups, migrations
from app.core.database import is_sqlite
from tests.conftest import login

# These copy and restore an SQLite file; on PostgreSQL a backup is a pg_dump (docs/BACKUPS.md)
pytestmark = pytest.mark.skipif(not is_sqlite(), reason="SQLite backups; PostgreSQL uses pg_dump")


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(backups, "BACKUP_DIR", tmp_path / "backups")
    return tmp_path / "backups"


def test_a_backup_holds_the_database_and_a_manifest(client, backup_dir):
    path = backups.create()
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert {"app.db", "manifest.json"} <= names
        manifest = __import__("json").loads(archive.read("manifest.json"))
    assert manifest["migration"] == migrations.head_revision() and "app.db" in manifest["files"]
    copy = backup_dir / "copy.db"
    copy.write_bytes(zipfile.ZipFile(path).read("app.db"))
    with closing(sqlite3.connect(copy)) as db, db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] >= 6
    status = client.get("/api/admin/system", headers=login(client, "admin")).json()["backup"]
    assert status["file"] == path.name and status["count"] == 1


def test_only_the_newest_backups_are_kept(client, backup_dir, monkeypatch):
    monkeypatch.setattr(backups, "BACKUP_KEEP", 2)
    backup_dir.mkdir()
    for stamp in ("20200101-000000", "20200102-000000", "20200103-000000"):
        (backup_dir / f"meritlens-{stamp}.zip").write_bytes(b"old")
    newest = backups.create()
    assert [p.name for p in backups.existing()] == [newest.name, "meritlens-20200103-000000.zip"]


def test_a_damaged_backup_is_refused(client, backup_dir, tmp_path):
    path = backups.create()
    damaged = tmp_path / "damaged.zip"
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(damaged, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            target.writestr(name, data + b"x" if name == "app.db" else data)
    with pytest.raises(ValueError, match="checksum"):
        backups.restore(damaged)


def test_a_restore_brings_back_the_data_and_keeps_today_s_aside(client, backup_dir, tmp_path, monkeypatch):
    database = tmp_path / "restore-target.db"
    monkeypatch.setattr(backups, "DATABASE_URL", f"sqlite:///{database.as_posix()}")
    monkeypatch.setattr(backups, "FOLDERS", {"correction_evidence": tmp_path / "evidence"})
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("CREATE TABLE notes (text TEXT)")
        db.execute("INSERT INTO notes VALUES ('before')")
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "payslip.pdf").write_bytes(b"%PDF evidence")
    path = backups.create()

    with closing(sqlite3.connect(database)) as db, db:
        db.execute("UPDATE notes SET text = 'after'")
    (tmp_path / "evidence" / "payslip.pdf").unlink()

    steps = backups.restore(path)
    assert any("kept the current database" in s for s in steps)
    with closing(sqlite3.connect(database)) as db, db:
        assert db.execute("SELECT text FROM notes").fetchone()[0] == "before"
    assert (tmp_path / "evidence" / "payslip.pdf").read_bytes() == b"%PDF evidence"
    [kept] = tmp_path.glob("restore-target.db.before-restore-*")
    with closing(sqlite3.connect(kept)) as db, db:
        assert db.execute("SELECT text FROM notes").fetchone()[0] == "after"
