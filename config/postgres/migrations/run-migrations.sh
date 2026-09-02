#!/bin/bash
# Waddles Database Migration Runner
# Runs all SQL migrations in order

set -e

# Database connection from environment or defaults
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-waddlebot}"
DB_USER="${POSTGRES_USER:-waddlebot}"
DB_PASSWORD="${POSTGRES_PASSWORD:-password}"

# SECURITY (CWE-798): no default admin credential is ever set here. These
# are forwarded, if present, into the waddlebot.initial_admin_email /
# waddlebot.initial_admin_password session GUCs that migration 081 reads
# via current_setting() to bootstrap the first super-admin. Unset ->
# migration 081 skips admin creation entirely (fail closed).
INITIAL_ADMIN_EMAIL="${INITIAL_ADMIN_EMAIL:-}"
INITIAL_ADMIN_PASSWORD="${INITIAL_ADMIN_PASSWORD:-}"

MIGRATIONS_DIR="$(dirname "$0")"

# Preamble file bridging INITIAL_ADMIN_EMAIL/PASSWORD into session GUCs via
# psql's :'var' substitution (only -f/stdin-sourced SQL is substituted --
# -c command strings are not). Regenerated fresh each run; cleaned up on exit.
ADMIN_GUC_PREAMBLE="$(mktemp)"
trap 'rm -f "$ADMIN_GUC_PREAMBLE"' EXIT
cat > "$ADMIN_GUC_PREAMBLE" << 'PREAMBLE_SQL'
-- \o suppresses these two SELECT results so the plaintext admin password
-- is never echoed to stdout/CI logs.
\o /dev/null
SELECT set_config('waddlebot.initial_admin_email', :'admin_email', false);
SELECT set_config('waddlebot.initial_admin_password', :'admin_password', false);
\o
PREAMBLE_SQL

echo "=== Waddles Database Migrations ==="
echo "Host: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Check if PostgreSQL is reachable
echo "Checking database connection..."
export PGPASSWORD="$DB_PASSWORD"
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
  echo "ERROR: Cannot connect to database"
  exit 1
fi
echo "✓ Database connection OK"
echo ""

# Create migrations tracking table if not exists
echo "Creating migrations tracking table..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'SQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
  id SERIAL PRIMARY KEY,
  migration_file VARCHAR(255) UNIQUE NOT NULL,
  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  checksum VARCHAR(64)
);
SQL
echo "✓ Migrations table ready"
echo ""

# Run migrations
for migration_file in "$MIGRATIONS_DIR"/*.sql; do
  if [ -f "$migration_file" ]; then
    filename=$(basename "$migration_file")

    # Skip the run-migrations script itself
    if [ "$filename" = "run-migrations.sh" ]; then
      continue
    fi

    # Check if migration already applied
    applied=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
      "SELECT COUNT(*) FROM schema_migrations WHERE migration_file = '$filename'")

    if [ "$applied" -eq 0 ]; then
      echo "Running migration: $filename"

      # Calculate checksum
      checksum=$(sha256sum "$migration_file" | awk '{print $1}')

      # Run migration. The preamble bridges INITIAL_ADMIN_EMAIL/PASSWORD into
      # session GUCs (harmless no-op for every file except 081, which
      # reads them via current_setting() to bootstrap the first admin).
      if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -v admin_email="$INITIAL_ADMIN_EMAIL" \
        -v admin_password="$INITIAL_ADMIN_PASSWORD" \
        -f "$ADMIN_GUC_PREAMBLE" \
        -f "$migration_file"; then
        # Record migration
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
          "INSERT INTO schema_migrations (migration_file, checksum) VALUES ('$filename', '$checksum')"
        echo "✓ Migration $filename completed"
      else
        echo "✗ Migration $filename FAILED"
        exit 1
      fi
    else
      echo "⊘ Migration $filename already applied (skipping)"
    fi
    echo ""
  fi
done

echo "=== All migrations completed ==="
