"""Repair scoped DB users + seed default hub admin on partially migrated DBs.

031_scoped_database_users.sql used to abort entirely (savepoint rollback,
see 0001_baseline_from_sql_migrations.py) on every fresh-DB bootstrap
because one of its GRANT statements referenced a `module_configs` table
that no CREATE TABLE migration ever defines. That's fixed in the file
itself now, but 0001's baseline only ever applies each legacy .sql file
ONCE, on a database with an empty schema_migrations table -- a database
that already went through baseline before this fix (e.g. an existing beta
DB) has 031_scoped_database_users.sql permanently marked "skipped" and
will never pick up the fix on its own. Same story for
081_seed_default_hub_admin.sql, which is new. This re-applies both,
following the 0003/0004 repair-migration pattern already established here.

Revision ID: 0005_repair_scoped_users
Revises: 0004_repair_credential_acl
"""

import os
import re

import sqlalchemy as sa

from alembic import op

revision = "0005_repair_scoped_users"
down_revision = "0004_repair_credential_acl"
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


def _prepare_sql(sql_content: str) -> str:
    lines = [
        line for line in sql_content.split("\n") if not line.strip().startswith("\\")
    ]
    content = "\n".join(lines)
    content = re.sub(r"(?m)^\s*BEGIN\s*;\s*$", "", content)
    content = re.sub(r"(?m)^\s*COMMIT\s*;\s*$", "", content)
    return content.strip()


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

    # Always re-apply, unconditionally -- grant_privs_if_exists() makes this
    # file fully idempotent, and a role existing already does NOT mean its
    # grants are complete: `modules` (046_add_remaining_admin_tables.sql,
    # which sorts after this file) doesn't exist yet on the baseline's first
    # pass, so those specific grants only land on this second pass, by which
    # point 046 has already run as part of the 000-081 baseline.
    print("[schema-repair] repairing scoped DB users via 031_scoped_database_users.sql")
    _apply_sql_file(conn, "031_scoped_database_users.sql")
    role_now_exists = conn.execute(
        sa.text("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'mod_core_identity'")
    ).fetchone()
    if not role_now_exists:
        raise RuntimeError(
            "mod_core_identity role is still missing after re-applying "
            "031_scoped_database_users.sql"
        )

    admin_exists = conn.execute(
        sa.text("SELECT 1 FROM hub_users WHERE email = 'admin@localhost.local'")
    ).fetchone()
    if admin_exists:
        print(
            "[schema-repair] default hub admin already present, skipping 081 re-apply"
        )
    else:
        print(
            "[schema-repair] seeding default hub admin via 081_seed_default_hub_admin.sql"
        )
        _apply_sql_file(conn, "081_seed_default_hub_admin.sql")


def downgrade() -> None:
    raise RuntimeError("Scoped-user/admin-seed repairs cannot be safely downgraded.")
