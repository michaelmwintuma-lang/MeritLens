"""
Helpers for migrations that must work on every database: a new one made by the baseline (which already has the
newest tables), and an older one made before that change. Each step checks first, so running it twice changes
nothing.
"""
import sqlalchemy as sa
from alembic import op


def has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def has_column(table: str, column: str) -> bool:
    return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))


def add_column_if_missing(table: str, column: sa.Column) -> None:
    if has_table(table) and not has_column(table, column.name):
        with op.batch_alter_table(table) as batch:  # SQLite can't change a table in place: batch copies it
            batch.add_column(column)


def create_table_if_missing(name: str, *columns, **kwargs) -> None:
    if not has_table(name):
        op.create_table(name, *columns, **kwargs)
