"""Development plans: goals an employee works on with their manager (development_goals).

Revision ID: 0003_development_plans
Revises: 0002_first_time_guide
Created: 2026-10-16
"""
import sqlalchemy as sa
from alembic import op

from migrations.helpers import create_table_if_missing

revision = "0003_development_plans"
down_revision = "0002_first_time_guide"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_if_missing(
        "development_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("feature", sa.String(60), nullable=True),
        sa.Column("target", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("due", sa.Date(), nullable=True),
        sa.Column("added_by_name", sa.String(120), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.Column("done_by_name", sa.String(120), nullable=True),
        sa.Column("done_at", sa.DateTime(), nullable=True),
    )
    if not any(i["name"] == "ix_development_goals_employee_id" for i in sa.inspect(op.get_bind()).get_indexes("development_goals")):
        op.create_index("ix_development_goals_employee_id", "development_goals", ["employee_id"])


def downgrade() -> None:
    op.drop_table("development_goals")
