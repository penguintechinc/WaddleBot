"""Alembic environment configuration for WaddleBot migrations."""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Import models — triggers all model registrations on db.metadata
from libs.flask_core.flask_core.models import db

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use DATABASE_URL environment variable
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Convert postgresql:// to postgresql+psycopg2:// for SQLAlchemy compatibility
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    config.set_main_option('sqlalchemy.url', database_url)

# Set up target_metadata for autogenerate
target_metadata = db.metadata


def include_name(name, type_, parent_names):
    """Filter autogenerate to only tables with SQLAlchemy models.

    Prevents Alembic from generating DROP TABLE for tables managed by
    Node.js hub-api or other systems that lack SQLAlchemy models.
    """
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with advisory locking."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Acquire PostgreSQL advisory lock to prevent concurrent migrations
        connection.execute(text("SELECT pg_advisory_lock(20250001)"))
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_name=include_name,
            )

            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(20250001)"))
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
