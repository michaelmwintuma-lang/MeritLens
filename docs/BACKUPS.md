# Backups and restoring

MeritLens keeps its own backups. Each one is a single zip file holding everything that can't be made again:

| In the backup | Why |
|---|---|
| The database (`app.db`, or `database.dump` on PostgreSQL) | accounts, employees, decisions, pay, feedback, the audit trail |
| `correction_evidence/` | the files employees attached to record-correction requests |
| `model_registry/` | trained model versions waiting for release, or released before |
| `manifest.json` | when it was made, which database migration it is at, and a SHA-256 checksum of every file |

Not in the backup, on purpose: `backend/.env` and `backend/instance/secret.key` (secrets: keep a copy somewhere
safe yourself; without the old `secret.key`, everyone simply signs in again), and the live model and results (they
are in git).

## When backups are made

- **Every night** at `BACKUP_HOUR` (2 a.m. by default) while the app runs. `BACKUPS=0` switches this off.
- **By hand**, from the `backend` folder:

  ```bash
  .venv/Scripts/python.exe -m app.core.backups create     # Windows
  .venv/bin/python -m app.core.backups create             # Linux / macOS
  .venv/Scripts/python.exe -m app.core.backups list
  ```

The newest `BACKUP_KEEP` backups (14 by default) are kept in `BACKUP_DIR` (`backend/instance/backups` by default);
older ones are removed. The admin's home page shows when the last one was made, and warns when it is more than a
day and a half old.

**Copy backups to another disk or machine** (a USB drive, a network share, cloud storage): a backup on the same disk
as the data is lost with it. On a server, point `BACKUP_DIR` at a mounted backup volume.

The SQLite copy is made with SQLite's online backup, so it is consistent even while people are using the app.

## Restoring

1. **Stop the app.**
2. From the `backend` folder:

   ```bash
   .venv/Scripts/python.exe -m app.core.backups restore instance/backups/meritlens-20261016-020000.zip
   ```

   Every file is checked against the manifest's checksum, and the database against SQLite's integrity check,
   before anything is changed; a damaged backup is refused. Today's database and evidence folder are kept next to
   them (`app.db.before-restore-<time>`), so a restore can itself be undone.
3. Start the app. If the backup is from an older version, start-up brings its tables up to date (migrations).

**Practise a restore** now and then, on a copy of the app: a backup only counts once it has been restored.

## PostgreSQL

Backups call `pg_dump` (PostgreSQL's client tools must be on the PATH) and store `database.dump` in the zip. To
restore: unzip it, then, with the app stopped,

```bash
pg_restore --clean --if-exists -d "postgresql://meritlens_app:...@localhost/meritlens" database.dump
```

and copy `correction_evidence/` back to `FEEDBACK_FILES_DIR`. Run `deploy/postgres/grants.sql` again afterwards.
Your database host's own backups (e.g. point-in-time recovery) are better still; use them too.
