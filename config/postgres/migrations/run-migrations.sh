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

MIGRATIONS_DIR="$(dirname "$0")"

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

      # Run migration
      if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration_file"; then
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
