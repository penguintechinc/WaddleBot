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

python3 - <<'PY'
import os
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
print(
    "Database: "
    f"driver={url.drivername} host={url.host or '<local>'} "
    f"port={url.port or '<default>'} database={url.database or '<default>'}"
)
PY

# ── Wait for PostgreSQL ──────────────────────────────────────────────────────
echo "Waiting for database..."
i=0
while ! python3 -c "
import os, sqlalchemy, sys
try:
    url = os.environ['DATABASE_URL'].replace('postgresql://', 'postgresql+psycopg2://', 1)
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

# Missing tables are expected on a fresh or partially migrated database. Report
# them before migration so persisted-volume repairs are visible in the logs.
python3 - <<'PY'
import os
import sqlalchemy

required = {"commands", "platform_integrations"}
url = os.environ["DATABASE_URL"].replace(
    "postgresql://", "postgresql+psycopg2://", 1
)
engine = sqlalchemy.create_engine(url)
with engine.connect() as connection:
    present = set(connection.execute(sqlalchemy.text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name IN "
        "('commands', 'platform_integrations')"
    )).scalars())
missing = sorted(required - present)
print("Pre-migration schema: " + (
    f"missing {', '.join(missing)}" if missing else "required tables present"
))
PY

# ── Run Alembic ──────────────────────────────────────────────────────────────
echo "Running Alembic upgrade head..."
cd /app
alembic upgrade head

# A zero exit from Alembic is insufficient if the minimum schema is incomplete.
python3 - <<'PY'
import os
import sqlalchemy

required = {"commands", "platform_integrations"}
url = os.environ["DATABASE_URL"].replace(
    "postgresql://", "postgresql+psycopg2://", 1
)
engine = sqlalchemy.create_engine(url)
with engine.connect() as connection:
    present = set(connection.execute(sqlalchemy.text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name IN "
        "('commands', 'platform_integrations')"
    )).scalars())
missing = sorted(required - present)
if missing:
    raise SystemExit(
        "ERROR: migration completed with required tables missing: "
        + ", ".join(missing)
    )
print("Post-migration schema: required tables present")
PY

echo "=== All migrations complete ==="
