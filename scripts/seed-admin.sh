#!/bin/bash
# =============================================================================
# Waddles Admin Seeding Script
# Creates the default admin user in the PostgreSQL database
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-waddlebot}"
DB_USER="${POSTGRES_USER:-waddlebot}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"

# SECURITY (CWE-798): no default admin credential. Both must be supplied
# explicitly via flags or ADMIN_EMAIL/ADMIN_PASSWORD env vars.
ADMIN_EMAIL="${ADMIN_EMAIL:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILE="${SCRIPT_DIR}/../config/postgres/seed_admin.sql"

show_help() {
    cat << EOF
Waddles Admin Seeding Script

Usage: $0 --email EMAIL --password PASSWORD [OPTIONS]

Creates or resets the admin user with the credentials you supply.
No default credential is ever used -- --email/--password (or the
ADMIN_EMAIL/ADMIN_PASSWORD env vars) are required.

Options:
    -h, --help              Show this help message
    -e, --email EMAIL       Admin email (required, or set ADMIN_EMAIL)
    -w, --password PASS     Admin password (required, or set ADMIN_PASSWORD)
    -H, --host HOST         PostgreSQL host (default: localhost)
    -p, --port PORT         PostgreSQL port (default: 5432)
    -d, --database DB       Database name (default: waddlebot)
    -U, --user USER         Database user (default: waddlebot)
    -W, --db-password PASS  Database password (or set POSTGRES_PASSWORD env var)
    --docker                Use docker exec to run against containerized postgres

Environment Variables:
    ADMIN_EMAIL              Admin email to create/reset
    ADMIN_PASSWORD           Admin password to create/reset
    POSTGRES_HOST             Database host
    POSTGRES_PORT             Database port
    POSTGRES_DB               Database name
    POSTGRES_USER             Database user
    POSTGRES_PASSWORD         Database password

Examples:
    # Run against local PostgreSQL
    $0 --email admin@example.com --password 'S0me-Strong-Passw0rd!' -W mypassword

    # Run against docker container
    ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='S0me-Strong-Passw0rd!' $0 --docker

EOF
}

USE_DOCKER=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -e|--email)
            ADMIN_EMAIL="$2"
            shift 2
            ;;
        -w|--password)
            ADMIN_PASSWORD="$2"
            shift 2
            ;;
        -H|--host)
            DB_HOST="$2"
            shift 2
            ;;
        -p|--port)
            DB_PORT="$2"
            shift 2
            ;;
        -d|--database)
            DB_NAME="$2"
            shift 2
            ;;
        -U|--user)
            DB_USER="$2"
            shift 2
            ;;
        -W|--db-password)
            DB_PASSWORD="$2"
            shift 2
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Check seed file exists
if [ ! -f "$SEED_FILE" ]; then
    echo -e "${RED}Error: Seed file not found: $SEED_FILE${NC}"
    exit 1
fi

# SECURITY: fail closed -- never fall back to a default admin credential.
if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}Error: --email/--password (or ADMIN_EMAIL/ADMIN_PASSWORD) are required.${NC}"
    show_help
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Waddles Admin Seeding Script${NC}"
echo -e "${BLUE}========================================${NC}"

# seed_admin.sql reads the admin credential from these env vars via
# psql's \getenv -- never from a CLI arg, so it never lands in shell
# history or `ps`.
export ADMIN_EMAIL
export ADMIN_PASSWORD

if [ "$USE_DOCKER" = true ]; then
    echo -e "${YELLOW}Running against Docker container...${NC}"

    # Find the postgres container
    POSTGRES_CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -n1)

    if [ -z "$POSTGRES_CONTAINER" ]; then
        # Try alternative names
        POSTGRES_CONTAINER=$(docker ps --filter "name=db" --format "{{.Names}}" | head -n1)
    fi

    if [ -z "$POSTGRES_CONTAINER" ]; then
        echo -e "${RED}Error: No PostgreSQL container found${NC}"
        echo "Running containers:"
        docker ps --format "table {{.Names}}\t{{.Image}}"
        exit 1
    fi

    echo -e "Using container: ${GREEN}$POSTGRES_CONTAINER${NC}"

    # Copy seed file to container and run
    docker cp "$SEED_FILE" "$POSTGRES_CONTAINER:/tmp/seed_admin.sql"
    docker exec -i -e ADMIN_EMAIL="$ADMIN_EMAIL" -e ADMIN_PASSWORD="$ADMIN_PASSWORD" \
        "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/seed_admin.sql

else
    echo -e "${YELLOW}Running against PostgreSQL at ${DB_HOST}:${DB_PORT}${NC}"

    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}Error: Database password required. Use -W or set POSTGRES_PASSWORD${NC}"
        exit 1
    fi

    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SEED_FILE"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Admin user seeded successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Email: ${BLUE}${ADMIN_EMAIL}${NC}"
echo -e "Password: (as supplied -- not echoed)"
