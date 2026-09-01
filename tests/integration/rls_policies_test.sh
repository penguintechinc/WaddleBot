#!/bin/bash

set -e

# Test RLS policies on platform_integrations table
# Verifies each module user can only access their platform credentials
# Exit codes: 0 = all tests pass, 1 = any test fails

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Database configuration from environment or defaults
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-waddlebot}"
DB_SUPERUSER="${DB_SUPERUSER:-postgres}"
DB_SUPERUSER_PASSWORD="${DB_SUPERUSER_PASSWORD:-postgres}"

# TAP output file
TAP_OUTPUT="${TAP_OUTPUT:-/tmp/rls_policies_test.tap}"

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
        -c "DELETE FROM platform_integrations WHERE platform IN ('test-twitch', 'test-discord', 'test-slack');" \
        2>/dev/null || true
    return $exit_code
}

trap cleanup EXIT INT TERM

# Helper function for database queries with error handling
query_as_user() {
    local username="$1"
    local password="$2"
    local query="$3"

    PGPASSWORD="$password" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "$username" -d "$DB_NAME" \
        -t -c "$query" 2>&1
}

# Helper function for test assertions
test_query() {
    local test_name="$1"
    local username="$2"
    local password="$3"
    local query="$4"
    local expected_rows="$5"

    TESTS_RUN=$((TESTS_RUN + 1))

    # Execute query as specific database user
    local result
    result=$(query_as_user "$username" "$password" "$query" 2>&1) || true

    # Count non-empty lines (excluding blank lines and headers)
    local row_count
    row_count=$(echo "$result" | grep -c "^[^[:space:]]*" || echo 0)

    if [ "$row_count" -eq "$expected_rows" ]; then
        echo -e "${GREEN}✓${NC} PASS: $test_name"
        echo "ok $TESTS_RUN - $test_name" >> "$TAP_OUTPUT"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} FAIL: $test_name (expected $expected_rows rows, got $row_count)"
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
        echo "User: $DB_SUPERUSER"
        exit 1
    }
}

echo "========================================="
echo "RLS Policy Enforcement Tests"
echo "========================================="
echo "Database: $DB_HOST:$DB_PORT/$DB_NAME"
echo "Superuser: $DB_SUPERUSER"
echo "========================================="
echo

# Check database connectivity
test_db_connectivity

# Test 1: Insert test data as superuser
echo -e "${BLUE}Setting up test data...${NC}"
PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$DB_NAME" 2>&1 << 'EOF'
DELETE FROM platform_integrations WHERE platform IN ('test-twitch', 'test-discord', 'test-slack');

INSERT INTO platform_integrations (platform, integration_type, access_token, is_active)
VALUES
  ('test-twitch', 'bot', 'twitch_token_123', true),
  ('test-discord', 'bot', 'discord_token_456', true),
  ('test-slack', 'bot', 'slack_token_789', true);
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to insert test data${NC}"
    exit 1
fi

echo -e "${GREEN}Test data inserted successfully${NC}"
echo

# Test 2: Test RLS for twitch_action user
echo -e "${BLUE}Testing twitch_action user permissions...${NC}"
test_query \
    "twitch_action can SELECT twitch platform" \
    "twitch_action" "mod_twitch_action_dev_changeme" \
    "SELECT platform FROM platform_integrations WHERE platform = 'test-twitch' AND is_active = TRUE;" \
    "1"

test_query \
    "twitch_action cannot SELECT discord platform (RLS blocks)" \
    "twitch_action" "mod_twitch_action_dev_changeme" \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform = 'test-discord';" \
    "0"

test_query \
    "twitch_action cannot SELECT slack platform (RLS blocks)" \
    "twitch_action" "mod_twitch_action_dev_changeme" \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform = 'test-slack';" \
    "0"

echo

# Test 3: Test RLS for discord_action user
echo -e "${BLUE}Testing discord_action user permissions...${NC}"
test_query \
    "discord_action can SELECT discord platform" \
    "discord_action" "mod_discord_action_dev_changeme" \
    "SELECT platform FROM platform_integrations WHERE platform = 'test-discord' AND is_active = TRUE;" \
    "1"

test_query \
    "discord_action cannot SELECT twitch platform (RLS blocks)" \
    "discord_action" "mod_discord_action_dev_changeme" \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform = 'test-twitch';" \
    "0"

test_query \
    "discord_action cannot SELECT slack platform (RLS blocks)" \
    "discord_action" "mod_discord_action_dev_changeme" \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform = 'test-slack';" \
    "0"

echo

# Test 4: Test RLS for slack_action user
echo -e "${BLUE}Testing slack_action user permissions...${NC}"
test_query \
    "slack_action can SELECT slack platform" \
    "slack_action" "mod_slack_action_dev_changeme" \
    "SELECT platform FROM platform_integrations WHERE platform = 'test-slack' AND is_active = TRUE;" \
    "1"

test_query \
    "slack_action cannot SELECT twitch platform (RLS blocks)" \
    "slack_action" "mod_slack_action_dev_changeme" \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform = 'test-twitch';" \
    "0"

echo

# Test 5: Test hub_admin has full access (no RLS restrictions)
echo -e "${BLUE}Testing hub_admin full access...${NC}"
test_query \
    "hub_admin can SELECT all platforms" \
    "hub_admin" "mod_hub_admin_dev_changeme" \
    "SELECT COUNT(DISTINCT platform) FROM platform_integrations WHERE platform IN ('test-twitch', 'test-discord', 'test-slack');" \
    "3"

test_query \
    "hub_admin can SELECT all test platforms with data" \
    "hub_admin" "mod_hub_admin_dev_changeme" \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform IN ('test-twitch', 'test-discord', 'test-slack');" \
    "3"

echo

# Test 6: Test analytics user has read-only access to platform_integrations
echo -e "${BLUE}Testing analytics user permissions...${NC}"
test_query \
    "analytics can SELECT all platforms (read-only)" \
    "analytics" "mod_analytics_dev_changeme" \
    "SELECT COUNT(*) FROM platform_integrations WHERE platform IN ('test-twitch', 'test-discord', 'test-slack');" \
    "3"

echo

# Update TAP output with total count
sed -i '1s/.*/1..'$TESTS_RUN'/' "$TAP_OUTPUT"

echo
echo "========================================="
echo "RLS Policy Test Results"
echo "========================================="
printf "Tests Run:    %2d\n" "$TESTS_RUN"
printf "Tests Passed: ${GREEN}%2d${NC}\n" "$TESTS_PASSED"
printf "Tests Failed: ${RED}%2d${NC}\n" "$TESTS_FAILED"
echo "========================================="
echo "TAP Output: $TAP_OUTPUT"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All RLS policy tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some RLS policy tests failed!${NC}"
    exit 1
fi
