"""The first-time guide on the overview: whether each person has closed it (users.guide_done).

Revision ID: 0002_first_time_guide
Revises: 0001_baseline
Created: 2026-10-16
"""
import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing

revision = "0002_first_time_guide"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column_if_missing("users", sa.Column("guide_done", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("guide_done")
