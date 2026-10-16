"""
How Alembic reaches the database: through the app's own engine (DATABASE_URL), with every table the app defines, so
`alembic revision --autogenerate` compares the code with the database.
"""
import logging.config

from alembic import context

from app.core.database import Base, engine
from app.core.migrations import load_all_tables

config = context.config
if config.config_file_name is not None and not config.attributes.get("connection"):
    logging.config.fileConfig(config.config_file_name, disable_existing_loggers=False)

load_all_tables()
target_metadata = Base.metadata


def run() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:  # the app's start-up passes its own connection
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


run()
