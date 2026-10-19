"""Sign-in codes sent by email: the current code's hash, expiry, when it was sent and its wrong tries (users.email_code_*).

Revision ID: 0004_email_sign_in_codes
Revises: 0003_development_plans
Created: 2026-10-17
"""
import sqlalchemy as sa
from alembic import op

from migrations.helpers import add_column_if_missing

revision = "0004_email_sign_in_codes"
down_revision = "0003_development_plans"
branch_labels = None
depends_on = None

COLUMNS = [
    sa.Column("email_code_hash", sa.String(64), nullable=True),
    sa.Column("email_code_expires", sa.DateTime(), nullable=True),
    sa.Column("email_code_sent_at", sa.DateTime(), nullable=True),
    sa.Column("email_code_attempts", sa.Integer(), nullable=True),
]


def upgrade() -> None:
    for column in COLUMNS:
        add_column_if_missing("users", column)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        for column in COLUMNS:
            batch.drop_column(column.name)
