# Running MeritLens on PostgreSQL

SQLite (one file, nothing to install) stays the default and is what `python run.py` uses. PostgreSQL is for a
real deployment: many HR users at once, backups, and **database roles that enforce the isolation rules**:

| Role | Can | Can't |
|---|---|---|
| `meritlens_app` | everything the app does (it owns the tables) | change or delete audit events |
| `meritlens_promotion` | everything the promotion code needs | read or write employees' feedback (`explanation_ratings`, `correction_requests`) or equality-monitoring data (`equality_monitoring`); change or delete audit events |

So "feedback never reaches the model" is enforced three times: by the code's structure, by the isolation tests,
and by the database itself.

## Steps

1. Install PostgreSQL 14 or later, and the driver in the backend's environment:

   ```bash
   pip install -r backend/requirements-postgres.txt
   ```

2. Create the roles and the database (as a superuser, e.g. `postgres`), choosing two passwords:

   ```bash
   psql -U postgres -v app_password="'choose-one'" -v promotion_password="'choose-another'" -f deploy/postgres/setup.sql
   ```

3. In `backend/.env`:

   ```
   DATABASE_URL=postgresql+psycopg://meritlens_app:choose-one@localhost/meritlens
   PROMOTION_DATABASE_URL=postgresql+psycopg://meritlens_promotion:choose-another@localhost/meritlens
   ```

4. Start the app once (`python run.py`): it creates its tables and the demo data.

5. Give the promotion role its (limited) rights:

   ```bash
   psql -U postgres -d meritlens -f deploy/postgres/grants.sql
   ```

   Run it again after an update that adds tables.

## Good to know

- `meritlens_app` owns the tables, so it could in principle grant itself back the rights `grants.sql` removes on
  `audit_events`. For a stronger setup, create the tables with a separate owner role and give `meritlens_app` only
  `SELECT, INSERT, UPDATE, DELETE` on the other tables. Either way, the audit trail's hash chain shows any change
  (Audit trail page: "Check the chain").
- Without `PROMOTION_DATABASE_URL`, the promotion code shares `DATABASE_URL`: it works the same, but the isolation
  then rests on the code and its tests, as with SQLite.
- The test suite runs on SQLite. The CI also runs it on an empty PostgreSQL 16 database (the
  `backend-tests-postgres` job in `.github/workflows/ci.yml`); to do the same on your own PostgreSQL:

  ```bash
  cd backend
  TEST_DATABASE_URL=postgresql+psycopg://postgres:secret@localhost/meritlens_test python -m pytest -q
  ```

  On 2026-10-16 the whole suite ran on PostgreSQL (16-compatible, via the `pgserver` package): 395 passed and 5
  were skipped (they test SQLite-only behaviour, such as copying the database file). That run found and fixed a
  bug SQLite hides, because SQLite doesn't enforce links between tables by default: deleting an account that had
  notifications failed.
- Updates bring the tables up to date by themselves (Alembic migrations, `backend/migrations`). Run `grants.sql`
  again after an update that adds tables.
