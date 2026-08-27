"""Repair required tables on partially migrated databases.

Revision ID: 0003_repair_required
Revises: 0002_channel_creation
Create Date: 2026-07-25
"""

import os
import re

import sqlalchemy as sa
from alembic import op

revision = "0003_repair_required"
down_revision = "0002_channel_creation"
branch_labels = None
depends_on = None

LEGACY_SQL_DIR = os.environ.get(
    "LEGACY_SQL_DIR",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "config",
        "postgres",
        "migrations",
    ),
)

REQUIRED_MIGRATIONS = {
    "commands": "002_add_commands_table.sql",
    "platform_integrations": "030_platform_integrations.sql",
}


def _prepare_sql(sql_content: str) -> str:
    lines = [
        line for line in sql_content.split("\n")
        if not line.strip().startswith("\\")
    ]
    content = "\n".join(lines)
    content = re.sub(r"(?m)^\s*BEGIN\s*;\s*$", "", content)
    content = re.sub(r"(?m)^\s*COMMIT\s*;\s*$", "", content)
    return content.strip()


def _table_exists(conn, table_name: str) -> bool:
    return bool(conn.execute(
        sa.text("SELECT to_regclass(:table_name) IS NOT NULL"),
        {"table_name": f"public.{table_name}"},
    ).scalar())


def _apply_sql_file(conn, filename: str) -> None:
    path = os.path.join(os.path.abspath(LEGACY_SQL_DIR), filename)
    if not os.path.isfile(path):
        raise RuntimeError(f"Required migration file not found: {path}")
    with open(path, encoding="utf-8") as migration:
        prepared = _prepare_sql(migration.read())
    if prepared:
        raw_connection = conn.connection.dbapi_connection
        with raw_connection.cursor() as cursor:
            cursor.execute(prepared)


def upgrade() -> None:
    conn = op.get_bind()
    for table_name, filename in REQUIRED_MIGRATIONS.items():
        if _table_exists(conn, table_name):
            print(f"[schema-repair] {table_name} already present")
            continue
        print(f"[schema-repair] repairing {table_name} via {filename}")
        _apply_sql_file(conn, filename)
        if not _table_exists(conn, table_name):
            raise RuntimeError(
                f"Required table {table_name} is still missing after {filename}"
            )


def downgrade() -> None:
    raise RuntimeError("Required schema repairs cannot be safely downgraded.")
