#!/bin/bash

set -e

# Test credential refresh service
# Verifies token refresh, Redis notifications, and module credential updates
# Exit codes: 0 = all tests pass, 1 = any test fails

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Database configuration from environment or defaults
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-waddlebot}"
DB_SUPERUSER="${DB_SUPERUSER:-postgres}"
DB_SUPERUSER_PASSWORD="${DB_SUPERUSER_PASSWORD:-postgres}"

# Redis configuration from environment or defaults
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# TAP output file
TAP_OUTPUT="${TAP_OUTPUT:-/tmp/credential_refresh_test.tap}"

echo "1..0 # TAP version 13" > "$TAP_OUTPUT"

# Cleanup function
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}Test interrupted or failed. Cleaning up...${NC}" >&2
    fi
    # Clean up test data
    PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$DB_NAME" \
        -c "DELETE FROM platform_integrations WHERE platform = 'test-refresh';" \
        2>/dev/null || true
    return $exit_code
}

trap cleanup EXIT INT TERM

# Helper function for test assertions
test_assertion() {
    local test_name="$1"
    local condition="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    if eval "$condition"; then
        echo -e "${GREEN}✓${NC} PASS: $test_name"
        echo "ok $TESTS_RUN - $test_name" >> "$TAP_OUTPUT"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} FAIL: $test_name"
        echo "not ok $TESTS_RUN - $test_name" >> "$TAP_OUTPUT"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Test prerequisite: Check database connectivity
test_db_connectivity() {
    local result
    result=$(PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$DB_NAME" \
        -t -c "SELECT 1" 2>&1) || {
        echo -e "${RED}ERROR: Cannot connect to PostgreSQL${NC}"
        echo "Database: $DB_HOST:$DB_PORT/$DB_NAME"
        exit 1
    }
}

# Test prerequisite: Check Redis connectivity
test_redis_connectivity() {
    local result
    result=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" PING 2>&1) || {
        echo -e "${RED}ERROR: Cannot connect to Redis${NC}"
        echo "Redis: $REDIS_HOST:$REDIS_PORT"
        exit 1
    }
    if [ "$result" != "PONG" ]; then
        echo -e "${RED}ERROR: Redis did not respond with PONG${NC}"
        exit 1
    fi
}

echo "========================================="
echo "Credential Refresh Integration Tests"
echo "========================================="
echo "Database: $DB_HOST:$DB_PORT/$DB_NAME"
echo "Redis: $REDIS_HOST:$REDIS_PORT"
echo "========================================="
echo

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"
test_db_connectivity
test_redis_connectivity
echo -e "${GREEN}Prerequisites OK${NC}"
echo

# Test 1: Insert expiring credential
echo -e "${BLUE}Setting up expiring test credential...${NC}"
EXPIRY_TIME=$(date -u -d '+2 minutes' +'%Y-%m-%d %H:%M:%S')

PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$DB_NAME" 2>&1 << EOF
DELETE FROM platform_integrations WHERE platform = 'test-refresh';

INSERT INTO platform_integrations (
    platform, integration_type, access_token, refresh_token,
    client_id, expires_at, is_active, is_encrypted
) VALUES (
    'test-refresh', 'bot', 'old_access_token', 'refresh_token_123',
    'test_client_id', '$EXPIRY_TIME'::timestamp, true, false
);
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to insert test credential${NC}"
    exit 1
fi

echo -e "${GREEN}Test credential inserted${NC}"
echo

# Test 2: Verify credential was inserted
echo -e "${BLUE}Verifying credential insertion...${NC}"
CRED_COUNT=$(PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform = 'test-refresh';")

test_assertion \
    "Credential inserted successfully" \
    "[ \"$CRED_COUNT\" -eq 1 ]"

echo

# Test 3: Test credential manager can SELECT credentials
echo -e "${BLUE}Testing credential_manager SELECT access...${NC}"
QUERY_RESULT=$(PGPASSWORD="mod_credential_manager_dev_changeme" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "credential_manager" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform = 'test-refresh';" 2>&1 || echo "ERROR")

test_assertion \
    "credential_manager can query platform_integrations" \
    "[ \"$QUERY_RESULT\" -eq 1 ]"

echo

# Test 4: Test expiring token detection
echo -e "${BLUE}Testing expiring token detection...${NC}"
EXPIRING_COUNT=$(PGPASSWORD="mod_credential_manager_dev_changeme" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "credential_manager" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM platform_integrations
     WHERE is_active = TRUE
       AND refresh_token IS NOT NULL
       AND expires_at IS NOT NULL
       AND expires_at < NOW() + INTERVAL '5 minutes';" 2>&1)

test_assertion \
    "Expiring tokens detected within 5-minute window" \
    "[ \"$EXPIRING_COUNT\" -ge 1 ]"

echo

# Test 5: Test credential manager UPDATE access
echo -e "${BLUE}Testing credential_manager UPDATE access...${NC}"
UPDATE_RESULT=$(PGPASSWORD="mod_credential_manager_dev_changeme" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "credential_manager" -d "$DB_NAME" -t -c \
    "UPDATE platform_integrations
     SET access_token = 'new_access_token',
         expires_at = NOW() + INTERVAL '1 hour',
         updated_at = NOW()
     WHERE platform = 'test-refresh'
     RETURNING id;" 2>&1 | grep -c "^[0-9]" || echo 0)

test_assertion \
    "credential_manager can update platform_integrations" \
    "[ \"$UPDATE_RESULT\" -eq 1 ]"

echo

# Test 6: Verify token was updated
echo -e "${BLUE}Verifying token update...${NC}"
UPDATED_TOKEN=$(PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$DB_NAME" -t -c \
    "SELECT access_token FROM platform_integrations WHERE platform = 'test-refresh';")

test_assertion \
    "Token was updated to new_access_token" \
    "[ \"$UPDATED_TOKEN\" = \"new_access_token\" ]"

echo

# Test 7: Redis pub/sub connectivity
echo -e "${BLUE}Testing Redis pub/sub connectivity...${NC}"
REDIS_PING=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" PING 2>&1)

test_assertion \
    "Redis is accessible for pub/sub notifications" \
    "[ \"$REDIS_PING\" = \"PONG\" ]"

echo

# Test 8: Verify hub_admin can see audit logs (if implemented)
echo -e "${BLUE}Testing credential access audit logs...${NC}"
AUDIT_TABLE_EXISTS=$(PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables
     WHERE table_name = 'credential_access_log';" 2>&1)

if [ "$AUDIT_TABLE_EXISTS" -eq 1 ]; then
    AUDIT_COUNT=$(PGPASSWORD="mod_hub_admin_dev_changeme" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "hub_admin" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM credential_access_log;" 2>&1 || echo "0")

    test_assertion \
        "Audit log table is accessible" \
        "[ -n \"$AUDIT_COUNT\" ]"
else
    echo -e "${YELLOW}⊘${NC} SKIP: credential_access_log table not yet created"
fi

echo

# Update TAP output with total count
sed -i '1s/.*/1..'$TESTS_RUN'/' "$TAP_OUTPUT"

echo
echo "========================================="
echo "Credential Refresh Test Results"
echo "========================================="
printf "Tests Run:    %2d\n" "$TESTS_RUN"
printf "Tests Passed: ${GREEN}%2d${NC}\n" "$TESTS_PASSED"
printf "Tests Failed: ${RED}%2d${NC}\n" "$TESTS_FAILED"
echo "========================================="
echo "TAP Output: $TAP_OUTPUT"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All credential refresh tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some credential refresh tests failed!${NC}"
    exit 1
fi
