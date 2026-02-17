#!/bin/sh
# WaddleBot Database Migration Runner (Alembic)
# Waits for DB readiness, then runs Alembic upgrade head.
set -e

echo "=== WaddleBot DB Migrations (Alembic) ==="

# ── Resolve DATABASE_URL ─────────────────────────────────────────────────────
if [ -z "${DATABASE_URL:-}" ]; then
    DB_HOST="${DB_HOST:-${DATABASE_HOST:-infra-postgres}}"
    DB_PORT="${DB_PORT:-${DATABASE_PORT:-5432}}"
    DB_NAME="${DB_NAME:-${DATABASE_NAME:-waddlebot}}"
    DB_USER="${DB_USER:-${DATABASE_USER:-waddlebot}}"
    DB_PASS="${DB_PASS:-${DATABASE_PASSWORD:-${POSTGRES_PASSWORD:-changeme}}}"
    DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    export DATABASE_URL
fi

echo "Database: ${DATABASE_URL%%@*}@***"

# ── Wait for PostgreSQL ──────────────────────────────────────────────────────
echo "Waiting for database..."
i=0
while ! python3 -c "
import sqlalchemy, sys
try:
    url = '${DATABASE_URL}'.replace('postgresql://', 'postgresql+psycopg2://', 1)
    e = sqlalchemy.create_engine(url)
    with e.connect() as c:
        c.execute(sqlalchemy.text('SELECT 1'))
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    i=$((i+1))
    if [ "$i" -ge 30 ]; then
        echo "ERROR: Database not ready after 60s"
        exit 1
    fi
    echo "  Not ready, retrying in 2s (attempt ${i}/30)..."
    sleep 2
done
echo "Database ready."

# ── Run Alembic ──────────────────────────────────────────────────────────────
echo "Running Alembic upgrade head..."
cd /app
alembic upgrade head

echo "=== All migrations complete ==="
