"""Baseline migration from legacy SQL files.

Handles two scenarios:
1. Existing DB (beta): schema_migrations table exists with entries → no-op
2. Fresh DB: Executes all legacy SQL migration files in order

Revision ID: 0001_baseline
Revises: None
Create Date: 2026-02-16
"""
import os
import glob
from alembic import op
import sqlalchemy as sa

revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None

# Path where legacy SQL files are mounted in the migration container
LEGACY_SQL_DIR = os.environ.get(
    'LEGACY_SQL_DIR',
    os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'postgres', 'migrations')
)


def upgrade() -> None:
    conn = op.get_bind()

    # Check if this DB was already migrated by the legacy psql runner
    result = conn.execute(sa.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_schema = 'public' AND table_name = 'schema_migrations'"
        ")"
    ))
    has_schema_migrations = result.scalar()

    if has_schema_migrations:
        count = conn.execute(sa.text(
            "SELECT COUNT(*) FROM schema_migrations"
        )).scalar()
        if count > 0:
            print(f"[baseline] Legacy schema_migrations has {count} entries — DB already migrated, skipping.")
            return

    # Fresh DB: run all legacy SQL migration files in sorted order
    sql_dir = os.path.abspath(LEGACY_SQL_DIR)
    sql_files = sorted(glob.glob(os.path.join(sql_dir, '*.sql')))

    if not sql_files:
        print(f"[baseline] WARNING: No SQL files found in {sql_dir}")
        print("[baseline] If this is a fresh deployment, tables will be created by autogenerate migrations.")
        return

    print(f"[baseline] Fresh DB detected. Applying {len(sql_files)} legacy SQL migrations...")

    # Create schema_migrations table for tracking
    conn.execute(sa.text(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "  version VARCHAR(255) PRIMARY KEY,"
        "  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        "  description TEXT"
        ")"
    ))

    for sql_file in sql_files:
        fname = os.path.basename(sql_file)
        version = fname.replace('.sql', '')

        # Check if already applied (defensive)
        already = conn.execute(sa.text(
            "SELECT 1 FROM schema_migrations WHERE version = :v"
        ), {"v": version}).fetchone()

        if already:
            print(f"  Skipping (already applied): {fname}")
            continue

        print(f"  Applying: {fname}")
        with open(sql_file, 'r') as f:
            sql_content = f.read()

        # Execute the migration (split on semicolons for multi-statement files)
        # Filter out empty statements and psql meta-commands
        for statement in sql_content.split(';'):
            stmt = statement.strip()
            if not stmt or stmt.startswith('\\') or stmt.startswith('--'):
                continue
            # Skip ANALYZE commands that fail on empty tables
            try:
                conn.execute(sa.text(stmt))
            except Exception as e:
                # ANALYZE on non-existent tables is non-fatal
                if 'ANALYZE' in stmt.upper():
                    print(f"    ANALYZE warning (non-fatal): {e}")
                else:
                    raise

        conn.execute(sa.text(
            "INSERT INTO schema_migrations (version) VALUES (:v) ON CONFLICT DO NOTHING"
        ), {"v": version})

    print("[baseline] All legacy SQL migrations applied.")


def downgrade() -> None:
    # Downgrade is intentionally not supported for the baseline.
    # Dropping all tables would destroy the database.
    raise RuntimeError(
        "Cannot downgrade baseline migration. "
        "To reset, drop the database and re-run migrations."
    )
