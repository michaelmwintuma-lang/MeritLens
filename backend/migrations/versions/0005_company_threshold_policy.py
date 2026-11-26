"""Company-configurable promotion recommendation threshold.

Revision ID: 0005_company_threshold_policy
Revises: 0004_email_sign_in_codes
Created: 2026-11-26
"""
import sqlalchemy as sa
from alembic import op

from migrations.helpers import create_table_if_missing, has_table

revision = "0005_company_threshold_policy"
down_revision = "0004_email_sign_in_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_if_missing(
        "threshold_policy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("custom_threshold", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by_name", sa.String(120), nullable=True),
    )


def downgrade() -> None:
    if has_table("threshold_policy"):
        op.drop_table("threshold_policy")
