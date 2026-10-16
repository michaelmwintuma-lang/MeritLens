"""Baseline: every table as of October 2026.

A new database gets all of them here. A database made before migrations existed already has them (the start-up's
one-off repairs have brought it up to date first: app/core/migrations.py); creating checks first, so nothing
changes for it. Every later change to the tables is a new revision after this one.

Revision ID: 0001_baseline
Revises:
Created: 2026-10-16
"""
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.core.database import Base
    from app.core.migrations import load_all_tables
    load_all_tables()
    Base.metadata.create_all(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    raise NotImplementedError("The baseline can't be undone: restore a backup instead (scripts/restore.py).")
