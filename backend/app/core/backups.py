"""
Backups: one zip file holding everything that can't be made again.

- the database (SQLite: copied with SQLite's online backup, so it is consistent even while the app is running;
  PostgreSQL: a pg_dump, when pg_dump is installed),
- the evidence employees attached to record corrections (FEEDBACK_FILES_DIR), and
- the model registry (trained versions waiting for release, or released before), with
- a manifest: when, which migration the database is at, and a SHA-256 checksum of every file, checked on restore.

Not included: backend/.env and instance/secret.key (secrets: keep them somewhere safe separately; without the old
secret.key everyone simply signs in again), and the live model and results (they are in git).

Made every night by the timer (core/scheduler.py, BACKUPS=0 switches it off), and by hand, from the backend folder:

    .venv/Scripts/python.exe -m app.core.backups create
    .venv/Scripts/python.exe -m app.core.backups list
    .venv/Scripts/python.exe -m app.core.backups restore instance/backups/meritlens-20261016-020000.zip

The newest BACKUP_KEEP backups are kept (14 by default) in BACKUP_DIR (instance/backups by default). Keep copies on
another disk or machine too: a backup on the same disk is lost with it.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import DATABASE_URL, FEEDBACK_FILES_DIR, INSTANCE_DIR, MODEL_REGISTRY_DIR

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(INSTANCE_DIR / "backups")))
BACKUP_KEEP = int(os.getenv("BACKUP_KEEP", "14"))
BACKUPS_ON = os.getenv("BACKUPS", "1") != "0"
FOLDERS = {"correction_evidence": FEEDBACK_FILES_DIR, "model_registry": MODEL_REGISTRY_DIR}


def sqlite_path() -> Path | None:
    return Path(DATABASE_URL.removeprefix("sqlite:///")) if DATABASE_URL.startswith("sqlite:///") else None


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_database(target_dir: Path) -> str:
    """Copy the database into target_dir; returns the file's name."""
    source = sqlite_path()
    if source is not None:
        with closing(sqlite3.connect(source)) as live, closing(sqlite3.connect(target_dir / "app.db")) as copy:
            live.backup(copy)  # consistent even while the app writes
        return "app.db"
    if shutil.which("pg_dump") is None:
        raise RuntimeError("PostgreSQL backups need pg_dump (part of PostgreSQL's client tools) on the PATH.")
    url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    subprocess.run(["pg_dump", "--format=custom", f"--file={target_dir / 'database.dump'}", url], check=True)
    return "database.dump"


def create() -> Path:
    """Make a backup now and remove the oldest beyond BACKUP_KEEP. Returns the backup's path."""
    from app.core.migrations import current_revision
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = BACKUP_DIR / f"meritlens-{stamp}.zip"
    with tempfile.TemporaryDirectory() as staging:
        staging = Path(staging)
        files = [dump_database(staging)]
        for name, folder in FOLDERS.items():
            if folder.exists():
                shutil.copytree(folder, staging / name)
                files += [p.relative_to(staging).as_posix() for p in (staging / name).rglob("*") if p.is_file()]
        manifest = {"made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "database": "sqlite" if sqlite_path() else "postgresql", "migration": current_revision(),
                    "files": {f: checksum(staging / f) for f in files}}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2))
        partial = target.with_suffix(".partial")
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
            for f in [*files, "manifest.json"]:
                archive.write(staging / f, f)
        os.replace(partial, target)  # never a half-written backup under a backup's name
    rotate()
    return target


def existing() -> list[Path]:
    return sorted(BACKUP_DIR.glob("meritlens-*.zip"), reverse=True) if BACKUP_DIR.exists() else []


def rotate() -> None:
    for old in existing()[BACKUP_KEEP:]:
        old.unlink()


def latest() -> dict | None:
    """The newest backup, for the admin's System page."""
    backups = existing()
    if not backups:
        return None
    newest = backups[0]
    return {"file": newest.name, "made_at": datetime.fromtimestamp(newest.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "size_kb": round(newest.stat().st_size / 1024), "count": len(backups), "folder": str(BACKUP_DIR)}


def verify(archive_path: Path, into: Path) -> dict:
    """Unpack a backup into `into` and check every file against the manifest. Returns the manifest."""
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():  # nothing may land outside the folder
            if name.startswith(("/", "\\")) or ".." in Path(name).parts:
                raise ValueError(f"Unsafe path in the backup: {name}")
        archive.extractall(into)
    manifest = json.loads((into / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if checksum(into / name) != expected:
            raise ValueError(f"{name} doesn't match its checksum: the backup is damaged.")
    if (into / "app.db").exists():
        with closing(sqlite3.connect(into / "app.db")) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("The database in the backup failed SQLite's integrity check.")
    return manifest


def restore(archive_path: Path) -> list[str]:
    """
    Put a backup back (SQLite). Stop the app first. What is there now is kept next to it (".before-restore-<time>"),
    so a restore can itself be undone. Returns what was done, in words.
    """
    source = sqlite_path()
    if source is None:
        raise RuntimeError("On PostgreSQL, restore database.dump from the backup with pg_restore (docs/BACKUPS.md).")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    done = []
    with tempfile.TemporaryDirectory() as unpacked:
        unpacked = Path(unpacked)
        manifest = verify(archive_path, unpacked)
        if source.exists():
            kept = source.with_name(f"{source.name}.before-restore-{stamp}")
            shutil.copy2(source, kept)
            done.append(f"kept the current database as {kept.name}")
        shutil.copy2(unpacked / "app.db", source)
        for suffix in ("-wal", "-shm"):  # a write-ahead log from the old database must not be replayed onto this one
            Path(f"{source}{suffix}").unlink(missing_ok=True)
        done.append(f"restored the database from {manifest['made_at']}")
        for name, folder in FOLDERS.items():
            if not (unpacked / name).exists():
                continue
            if folder.exists():
                folder.rename(folder.with_name(f"{folder.name}.before-restore-{stamp}"))
            shutil.copytree(unpacked / name, folder)
            done.append(f"restored {name.replace('_', ' ')}")
    return done


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("create", "list", "restore"):
        print(__doc__)
        return 2
    if argv[0] == "create":
        print(f"Backup made: {create()}")
    elif argv[0] == "list":
        for path in existing():
            print(f"{path.name}  {path.stat().st_size // 1024} KB")
    else:
        if len(argv) < 2:
            print("Which backup? e.g. restore instance/backups/meritlens-20261016-020000.zip")
            return 2
        answer = input("Is the app stopped? Restoring replaces today's data with the backup's (it is kept aside). [y/N] ")
        if answer.strip().lower() != "y":
            print("Nothing was changed.")
            return 1
        for step in restore(Path(argv[1])):
            print("-", step)
        print("Done. Start the app again; it brings the database up to date if the backup is older.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
