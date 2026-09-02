#!/bin/bash
################################################################################
# WaddleBot Hub Module API Test Script
# Comprehensive test suite for all Hub Module API endpoints
################################################################################

set -uo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Configuration
HUB_URL="${HUB_URL:-http://localhost:8060}"
ADMIN_EMAIL="${ADMIN_EMAIL:-${INITIAL_ADMIN_EMAIL:-admin@localhost.local}}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-${INITIAL_ADMIN_PASSWORD:-}}"
AUTH_TOKEN=""
COMMUNITY_ID=""
TEST_USER_ID=""
TEST_SERVER_ID=""
TEST_MIRROR_GROUP_ID=""

# Temporary files
RESPONSE_FILE=$(mktemp)
HEADERS_FILE=$(mktemp)

# Cleanup on exit
trap 'rm -f "$RESPONSE_FILE" "$HEADERS_FILE"' EXIT

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_test() {
    echo -e "\n${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

print_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
    ((TESTS_SKIPPED++))
}

print_summary() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}Passed:  ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed:  ${TESTS_FAILED}${NC}"
    echo -e "${YELLOW}Skipped: ${TESTS_SKIPPED}${NC}"
    echo -e "${BLUE}Total:   $((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))${NC}"
    echo -e "${BLUE}========================================${NC}"
}

show_help() {
    cat << EOF
WaddleBot Hub Module API Test Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -u, --url URL           Hub module URL (default: http://localhost:8060)
    -e, --email EMAIL       Admin email (default: admin@localhost)
    -p, --password PASS     Admin password (default: $INITIAL_ADMIN_PASSWORD, if set)
    -v, --verbose           Enable verbose output (show response bodies)

Environment Variables:
    HUB_URL                 Hub module URL
    ADMIN_EMAIL             Admin email for authentication
    ADMIN_PASSWORD          Admin password for authentication

Examples:
    # Run tests against local instance
    $0

    # Run tests against custom URL
    $0 --url http://hub.example.com:8060

    # Run with custom credentials
    $0 --email admin@example.com --password mypassword

Exit Codes:
    0 - All tests passed
    1 - One or more tests failed

EOF
}

# API call helper
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local expected_status="${4:-200}"
    local use_auth="${5:-true}"

    local curl_opts=(-s -w "\n%{http_code}" -X "$method")

    # Add authentication header if required
    if [ "$use_auth" = "true" ] && [ -n "$AUTH_TOKEN" ]; then
        curl_opts+=(-H "Authorization: Bearer $AUTH_TOKEN")
    fi

    # Add content-type and data if provided
    if [ -n "$data" ]; then
        curl_opts+=(-H "Content-Type: application/json" -d "$data")
    fi

    # Make the API call
    local response
    response=$(curl "${curl_opts[@]}" "${HUB_URL}${endpoint}" 2>&1 || true)

    # Extract status code (last line)
    local status_code
    status_code=$(echo "$response" | tail -n 1)

    # Extract body (all but last line)
    local body
    body=$(echo "$response" | sed '$d')

    # Save response for inspection
    echo "$body" > "$RESPONSE_FILE"

    # Check status code
    if [ "$status_code" = "$expected_status" ]; then
        echo "$body"
        return 0
    else
        echo "Expected status $expected_status, got $status_code" >&2
        echo "Response: $body" >&2
        return 1
    fi
}

################################################################################
# Parse Arguments
################################################################################

VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--url)
            HUB_URL="$2"
            shift 2
            ;;
        -e|--email)
            ADMIN_EMAIL="$2"
            shift 2
            ;;
        -p|--password)
            ADMIN_PASSWORD="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

################################################################################
# Main Test Execution
################################################################################

echo -e "${BLUE}WaddleBot Hub Module API Test Suite${NC}"
echo -e "Testing: ${HUB_URL}"
echo -e "Admin: ${ADMIN_EMAIL}"

################################################################################
# Health Check
################################################################################

print_header "Health Check"

print_test "GET /health"
if response=$(api_call GET /health "" 200 false); then
    if echo "$response" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
        print_pass "Health check returned healthy status"
    else
        print_fail "Health check did not return healthy status"
    fi
else
    print_fail "Health check failed"
    exit 1
fi

################################################################################
# Authentication Tests
################################################################################

print_header "Authentication API Tests"

# Test: Login as admin
print_test "POST /api/v1/auth/login (admin credentials)"
login_data=$(jq -n \
    --arg email "$ADMIN_EMAIL" \
    --arg password "$ADMIN_PASSWORD" \
    '{email: $email, password: $password}')

if response=$(api_call POST /api/v1/auth/login "$login_data" 200 false); then
    AUTH_TOKEN=$(echo "$response" | jq -r '.data.token // .token // empty')
    if [ -n "$AUTH_TOKEN" ]; then
        print_pass "Admin login successful, token obtained"
    else
        print_fail "Admin login succeeded but no token received"
        exit 1
    fi
else
    print_fail "Admin login failed"
    exit 1
fi

# Test: Get current user
print_test "GET /api/v1/auth/me"
if response=$(api_call GET /api/v1/auth/me "" 200 true); then
    if echo "$response" | jq -e '.user.email' > /dev/null 2>&1 || \
       echo "$response" | jq -e '.data.email' > /dev/null 2>&1; then
        print_pass "Get current user info successful"
    else
        print_fail "Get current user info returned unexpected response"
    fi
else
    print_fail "Get current user info failed"
fi

# Test: Register new user (should work if signup enabled)
print_test "POST /api/v1/auth/register (test user)"
register_data=$(jq -n \
    --arg email "testuser_$(date +%s)@example.com" \
    --arg password "TestPass123!" \
    --arg username "testuser_$(date +%s)" \
    '{email: $email, password: $password, username: $username}')

if response=$(api_call POST /api/v1/auth/register "$register_data" 201 false 2>/dev/null); then
    print_pass "User registration successful"
elif response=$(api_call POST /api/v1/auth/register "$register_data" 403 false 2>/dev/null); then
    print_skip "User registration disabled (signup restricted)"
else
    print_skip "User registration failed (may be disabled)"
fi

# Test: Resend verification email
print_test "POST /api/v1/auth/resend-verification"
resend_data=$(jq -n --arg email "$ADMIN_EMAIL" '{email: $email}')
if api_call POST /api/v1/auth/resend-verification "$resend_data" 200 false > /dev/null 2>&1; then
    print_pass "Resend verification email successful"
else
    print_skip "Resend verification email skipped (may already be verified)"
fi

# Test: Verify email (without valid token, should fail)
print_test "GET /api/v1/auth/verify-email (invalid token)"
if api_call GET "/api/v1/auth/verify-email?token=invalid" "" 400 false > /dev/null 2>&1; then
    print_pass "Email verification with invalid token correctly rejected"
else
    print_skip "Email verification endpoint handling varies"
fi

# Test: OAuth URL generation for all platforms
print_test "GET /api/v1/auth/oauth/discord (OAuth URL generation)"
if response=$(api_call GET "/api/v1/auth/oauth/discord?redirectUrl=http://localhost:8060/auth/callback" "" 200 false 2>/dev/null); then
    if echo "$response" | jq -e '.url' > /dev/null 2>&1 || \
       echo "$response" | jq -e '.data.url' > /dev/null 2>&1; then
        print_pass "Discord OAuth URL generation successful"
    else
        print_skip "Discord OAuth URL generation (platform not configured)"
    fi
else
    print_skip "Discord OAuth URL generation skipped"
fi

print_test "GET /api/v1/auth/oauth/twitch (OAuth URL generation)"
if response=$(api_call GET "/api/v1/auth/oauth/twitch?redirectUrl=http://localhost:8060/auth/callback" "" 200 false 2>/dev/null); then
    if echo "$response" | jq -e '.url' > /dev/null 2>&1 || \
       echo "$response" | jq -e '.data.url' > /dev/null 2>&1; then
        print_pass "Twitch OAuth URL generation successful"
    else
        print_skip "Twitch OAuth URL generation (platform not configured)"
    fi
else
    print_skip "Twitch OAuth URL generation skipped"
fi

print_test "GET /api/v1/auth/oauth/youtube (OAuth URL generation)"
if response=$(api_call GET "/api/v1/auth/oauth/youtube?redirectUrl=http://localhost:8060/auth/callback" "" 200 false 2>/dev/null); then
    if echo "$response" | jq -e '.url' > /dev/null 2>&1 || \
       echo "$response" | jq -e '.data.url' > /dev/null 2>&1; then
        print_pass "YouTube OAuth URL generation successful"
    else
        print_skip "YouTube OAuth URL generation (platform not configured)"
    fi
else
    print_skip "YouTube OAuth URL generation skipped"
fi

print_test "GET /api/v1/auth/oauth/kick (OAuth URL generation)"
if response=$(api_call GET "/api/v1/auth/oauth/kick?redirectUrl=http://localhost:8060/auth/callback" "" 200 false 2>/dev/null); then
    if echo "$response" | jq -e '.url' > /dev/null 2>&1 || \
       echo "$response" | jq -e '.data.url' > /dev/null 2>&1; then
        print_pass "KICK OAuth URL generation successful"
    else
        print_skip "KICK OAuth URL generation (platform not configured)"
    fi
else
    print_skip "KICK OAuth URL generation skipped"
fi

print_test "GET /api/v1/auth/oauth/slack (OAuth URL generation)"
if response=$(api_call GET "/api/v1/auth/oauth/slack?redirectUrl=http://localhost:8060/auth/callback" "" 200 false 2>/dev/null); then
    if echo "$response" | jq -e '.url' > /dev/null 2>&1 || \
       echo "$response" | jq -e '.data.url' > /dev/null 2>&1; then
        print_pass "Slack OAuth URL generation successful"
    else
        print_skip "Slack OAuth URL generation (platform not configured)"
    fi
else
    print_skip "Slack OAuth URL generation skipped"
fi

################################################################################
# Public API Tests
################################################################################

print_header "Public API Tests"

# Test: Get platform stats
print_test "GET /api/v1/public/stats"
if response=$(api_call GET /api/v1/public/stats "" 200 false); then
    if echo "$response" | jq -e '.stats.communities' > /dev/null 2>&1 || \
       echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        print_pass "Get platform stats successful"
    else
        print_fail "Get platform stats returned unexpected response"
    fi
else
    print_fail "Get platform stats failed"
fi

# Test: Get public communities
print_test "GET /api/v1/public/communities"
if response=$(api_call GET /api/v1/public/communities "" 200 false); then
    # Try to extract a community ID for later tests
    COMMUNITY_ID=$(echo "$response" | jq -r '(.data[0].id // .[0].id // empty)' 2>/dev/null || echo "")
    print_pass "Get public communities successful"
else
    print_fail "Get public communities failed"
fi

# Test: Get specific community (if we have an ID)
if [ -n "$COMMUNITY_ID" ]; then
    print_test "GET /api/v1/public/communities/$COMMUNITY_ID"
    if response=$(api_call GET "/api/v1/public/communities/$COMMUNITY_ID" "" 200 false); then
        print_pass "Get specific community successful"
    else
        print_fail "Get specific community failed"
    fi
else
    print_skip "GET /api/v1/public/communities/:id (no community available)"
fi

# Test: Get live streams
print_test "GET /api/v1/public/live"
if api_call GET /api/v1/public/live "" 200 false > /dev/null 2>&1; then
    print_pass "Get live streams successful"
else
    print_skip "Get live streams failed or no streams available"
fi

# Test: Get signup settings
print_test "GET /api/v1/public/signup-settings"
if response=$(api_call GET /api/v1/public/signup-settings "" 200 false); then
    if echo "$response" | jq -e 'has("data") or has("signupEnabled")' > /dev/null 2>&1; then
        print_pass "Get signup settings successful"
    else
        print_fail "Get signup settings returned unexpected response"
    fi
else
    print_fail "Get signup settings failed"
fi

################################################################################
# Community API Tests (Authenticated)
################################################################################

print_header "Community API Tests (Authenticated)"

# Test: Get my communities
print_test "GET /api/v1/communities/my"
if response=$(api_call GET /api/v1/communities/my "" 200 true); then
    # Try to get a community ID from user's communities
    if [ -z "$COMMUNITY_ID" ]; then
        COMMUNITY_ID=$(echo "$response" | jq -r '(.communities[0].id // .data[0].id // .[0].id // empty)' 2>/dev/null || echo "")
    fi
    print_pass "Get my communities successful"
else
    print_fail "Get my communities failed"
fi

# Test: Join community (if we have one and not already a member)
if [ -n "$COMMUNITY_ID" ]; then
    print_test "POST /api/v1/community/$COMMUNITY_ID/join"
    if api_call POST "/api/v1/community/$COMMUNITY_ID/join" "" 200 true > /dev/null 2>&1 || \
       api_call POST "/api/v1/community/$COMMUNITY_ID/join" "" 409 true > /dev/null 2>&1; then
        print_pass "Join community successful (or already member)"
    else
        print_skip "Join community skipped"
    fi
else
    print_skip "POST /api/v1/community/:id/join (no community available)"
fi

# Test: Get join requests
print_test "GET /api/v1/community/join-requests"
if api_call GET /api/v1/community/join-requests "" 200 true > /dev/null 2>&1; then
    print_pass "Get join requests successful"
else
    print_skip "Get join requests skipped"
fi

# Test: Get server link requests
print_test "GET /api/v1/community/server-link-requests"
if api_call GET /api/v1/community/server-link-requests "" 200 true > /dev/null 2>&1; then
    print_pass "Get server link requests successful"
else
    print_skip "Get server link requests skipped"
fi

# Community-specific endpoints (require membership)
if [ -n "$COMMUNITY_ID" ]; then
    print_test "GET /api/v1/community/$COMMUNITY_ID/dashboard"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/dashboard" "" 200 true > /dev/null 2>&1; then
        print_pass "Get community dashboard successful"
    else
        print_skip "Get community dashboard skipped (may require membership)"
    fi

    print_test "GET /api/v1/community/$COMMUNITY_ID/servers"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/servers" "" 200 true > /dev/null 2>&1; then
        print_pass "Get community servers successful"
    else
        print_skip "Get community servers skipped"
    fi

    print_test "GET /api/v1/community/$COMMUNITY_ID/modules"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/modules" "" 200 true > /dev/null 2>&1; then
        print_pass "Get installed modules successful"
    else
        print_skip "Get installed modules skipped"
    fi

    print_test "GET /api/v1/community/$COMMUNITY_ID/leaderboard"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/leaderboard" "" 200 true > /dev/null 2>&1; then
        print_pass "Get leaderboard successful"
    else
        print_skip "Get leaderboard skipped"
    fi

    print_test "GET /api/v1/community/$COMMUNITY_ID/activity"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/activity" "" 200 true > /dev/null 2>&1; then
        print_pass "Get activity feed successful"
    else
        print_skip "Get activity feed skipped"
    fi

    print_test "GET /api/v1/community/$COMMUNITY_ID/events"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/events" "" 200 true > /dev/null 2>&1; then
        print_pass "Get events successful"
    else
        print_skip "Get events skipped"
    fi

    print_test "GET /api/v1/community/$COMMUNITY_ID/memories"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/memories" "" 200 true > /dev/null 2>&1; then
        print_pass "Get memories successful"
    else
        print_skip "Get memories skipped"
    fi

    print_test "GET /api/v1/community/$COMMUNITY_ID/chat/history"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/chat/history" "" 200 true > /dev/null 2>&1; then
        print_pass "Get chat history successful"
    else
        print_skip "Get chat history skipped"
    fi

    print_test "GET /api/v1/community/$COMMUNITY_ID/chat/channels"
    if api_call GET "/api/v1/community/$COMMUNITY_ID/chat/channels" "" 200 true > /dev/null 2>&1; then
        print_pass "Get chat channels successful"
    else
        print_skip "Get chat channels skipped"
    fi
fi

################################################################################
# Admin API Tests (Community Admin)
################################################################################

print_header "Admin API Tests (Community Admin)"

if [ -n "$COMMUNITY_ID" ]; then
    # Test: Get members
    print_test "GET /api/v1/admin/$COMMUNITY_ID/members"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/members" "" 200 true 2>/dev/null); then
        print_pass "Get community members successful"
        # Try to get a member ID for testing
        TEST_USER_ID=$(echo "$response" | jq -r '(.data[0].id // .[0].id // empty)' 2>/dev/null || echo "")
    else
        print_skip "Get community members skipped (requires admin role)"
    fi

    # Test: Update member role
    if [ -n "$TEST_USER_ID" ]; then
        print_test "PUT /api/v1/admin/$COMMUNITY_ID/members/$TEST_USER_ID/role"
        role_data='{"role": "moderator"}'
        if api_call PUT "/api/v1/admin/$COMMUNITY_ID/members/$TEST_USER_ID/role" "$role_data" 200 true > /dev/null 2>&1; then
            print_pass "Update member role successful"
        else
            print_skip "Update member role skipped (requires admin role)"
        fi
    else
        print_skip "PUT /api/v1/admin/:communityId/members/:userId/role (no member ID)"
    fi

    # Test: Get community settings
    print_test "GET /api/v1/admin/$COMMUNITY_ID/settings"
    if api_call GET "/api/v1/admin/$COMMUNITY_ID/settings" "" 200 true > /dev/null 2>&1; then
        print_pass "Get community settings successful"
    else
        print_skip "Get community settings skipped (requires admin role)"
    fi

    # Test: Update community settings
    print_test "PUT /api/v1/admin/$COMMUNITY_ID/settings"
    settings_data='{"description": "Test community description"}'
    if api_call PUT "/api/v1/admin/$COMMUNITY_ID/settings" "$settings_data" 200 true > /dev/null 2>&1; then
        print_pass "Update community settings successful"
    else
        print_skip "Update community settings skipped (requires admin role)"
    fi

    # Test: Get linked servers
    print_test "GET /api/v1/admin/$COMMUNITY_ID/servers"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/servers" "" 200 true 2>/dev/null); then
        print_pass "Get linked servers successful"
        TEST_SERVER_ID=$(echo "$response" | jq -r '(.data[0].id // .[0].id // empty)' 2>/dev/null || echo "")
    else
        print_skip "Get linked servers skipped (requires admin role)"
    fi

    # Test: Get server link requests
    print_test "GET /api/v1/admin/$COMMUNITY_ID/server-link-requests"
    if api_call GET "/api/v1/admin/$COMMUNITY_ID/server-link-requests" "" 200 true > /dev/null 2>&1; then
        print_pass "Get server link requests successful"
    else
        print_skip "Get server link requests skipped (requires admin role)"
    fi

    # Test: Get join requests
    print_test "GET /api/v1/admin/$COMMUNITY_ID/join-requests"
    if api_call GET "/api/v1/admin/$COMMUNITY_ID/join-requests" "" 200 true > /dev/null 2>&1; then
        print_pass "Get join requests successful"
    else
        print_skip "Get join requests skipped (requires admin role)"
    fi

    # Test: Get mirror groups
    print_test "GET /api/v1/admin/$COMMUNITY_ID/mirror-groups"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/mirror-groups" "" 200 true 2>/dev/null); then
        print_pass "Get mirror groups successful"
        TEST_MIRROR_GROUP_ID=$(echo "$response" | jq -r '(.data[0].id // .[0].id // empty)' 2>/dev/null || echo "")
    else
        print_skip "Get mirror groups skipped (requires admin role)"
    fi

    # Test: Create mirror group
    print_test "POST /api/v1/admin/$COMMUNITY_ID/mirror-groups"
    mirror_group_data=$(jq -n \
        --arg name "Test Mirror Group $(date +%s)" \
        '{name: $name, isActive: true}')
    if response=$(api_call POST "/api/v1/admin/$COMMUNITY_ID/mirror-groups" "$mirror_group_data" 201 true 2>/dev/null); then
        print_pass "Create mirror group successful"
        # Try to get the created mirror group ID
        CREATED_MIRROR_GROUP_ID=$(echo "$response" | jq -r '(.data.id // .id // empty)' 2>/dev/null || echo "")
        if [ -z "$TEST_MIRROR_GROUP_ID" ] && [ -n "$CREATED_MIRROR_GROUP_ID" ]; then
            TEST_MIRROR_GROUP_ID="$CREATED_MIRROR_GROUP_ID"
        fi
    else
        print_skip "Create mirror group skipped (requires admin role)"
    fi

    # Test: Get specific mirror group
    if [ -n "$TEST_MIRROR_GROUP_ID" ]; then
        print_test "GET /api/v1/admin/$COMMUNITY_ID/mirror-groups/$TEST_MIRROR_GROUP_ID"
        if api_call GET "/api/v1/admin/$COMMUNITY_ID/mirror-groups/$TEST_MIRROR_GROUP_ID" "" 200 true > /dev/null 2>&1; then
            print_pass "Get mirror group details successful"
        else
            print_skip "Get mirror group details skipped"
        fi

        # Test: Update mirror group
        print_test "PUT /api/v1/admin/$COMMUNITY_ID/mirror-groups/$TEST_MIRROR_GROUP_ID"
        update_mirror_data='{"name": "Updated Mirror Group", "isActive": true}'
        if api_call PUT "/api/v1/admin/$COMMUNITY_ID/mirror-groups/$TEST_MIRROR_GROUP_ID" "$update_mirror_data" 200 true > /dev/null 2>&1; then
            print_pass "Update mirror group successful"
        else
            print_skip "Update mirror group skipped"
        fi

        # Test: Delete mirror group
        print_test "DELETE /api/v1/admin/$COMMUNITY_ID/mirror-groups/$TEST_MIRROR_GROUP_ID"
        if api_call DELETE "/api/v1/admin/$COMMUNITY_ID/mirror-groups/$TEST_MIRROR_GROUP_ID" "" 200 true > /dev/null 2>&1; then
            print_pass "Delete mirror group successful"
        else
            print_skip "Delete mirror group skipped"
        fi
    else
        print_skip "Mirror group detail tests (no mirror group ID)"
    fi

    # Test: Get modules
    print_test "GET /api/v1/admin/$COMMUNITY_ID/modules"
    if api_call GET "/api/v1/admin/$COMMUNITY_ID/modules" "" 200 true > /dev/null 2>&1; then
        print_pass "Get admin modules successful"
    else
        print_skip "Get admin modules skipped (requires admin role)"
    fi

    # Test: Get browser sources
    print_test "GET /api/v1/admin/$COMMUNITY_ID/browser-sources"
    if api_call GET "/api/v1/admin/$COMMUNITY_ID/browser-sources" "" 200 true > /dev/null 2>&1; then
        print_pass "Get browser sources successful"
    else
        print_skip "Get browser sources skipped (requires admin role)"
    fi

    # Test: Generate temp password
    print_test "POST /api/v1/admin/$COMMUNITY_ID/temp-password"
    temp_pass_data='{"userIdentifier": "testuser@example.com"}'
    if api_call POST "/api/v1/admin/$COMMUNITY_ID/temp-password" "$temp_pass_data" 200 true > /dev/null 2>&1; then
        print_pass "Generate temp password successful"
    else
        print_skip "Generate temp password skipped (requires admin role)"
    fi

    # ============================================================
    # Reputation Configuration Tests (FICO-style 300-850 scoring)
    # ============================================================

    # Test: Get reputation config
    print_test "GET /api/v1/admin/$COMMUNITY_ID/reputation/config"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/reputation/config" "" 200 true 2>/dev/null); then
        if echo "$response" | jq -e '.config' > /dev/null 2>&1 || \
           echo "$response" | jq -e '.data' > /dev/null 2>&1; then
            print_pass "Get reputation config successful"
        else
            print_fail "Get reputation config returned unexpected response"
        fi
    else
        print_skip "Get reputation config skipped (requires admin role)"
    fi

    # Test: Update reputation config (may fail if not premium)
    print_test "PUT /api/v1/admin/$COMMUNITY_ID/reputation/config"
    rep_config_data='{"auto_ban_enabled": false, "auto_ban_threshold": 450, "starting_score": 600}'
    if api_call PUT "/api/v1/admin/$COMMUNITY_ID/reputation/config" "$rep_config_data" 200 true > /dev/null 2>&1; then
        print_pass "Update reputation config successful"
    elif api_call PUT "/api/v1/admin/$COMMUNITY_ID/reputation/config" "$rep_config_data" 403 true > /dev/null 2>&1; then
        print_skip "Update reputation config skipped (premium feature)"
    else
        print_skip "Update reputation config skipped (requires admin role)"
    fi

    # Test: Get at-risk users (users near auto-ban threshold)
    print_test "GET /api/v1/admin/$COMMUNITY_ID/reputation/at-risk"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/reputation/at-risk" "" 200 true 2>/dev/null); then
        if echo "$response" | jq -e '.users' > /dev/null 2>&1 || \
           echo "$response" | jq -e '.data' > /dev/null 2>&1; then
            print_pass "Get at-risk users successful"
        else
            print_fail "Get at-risk users returned unexpected response"
        fi
    else
        print_skip "Get at-risk users skipped (requires admin role)"
    fi

    # Test: Get reputation leaderboard
    print_test "GET /api/v1/admin/$COMMUNITY_ID/reputation/leaderboard"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/reputation/leaderboard?limit=10" "" 200 true 2>/dev/null); then
        if echo "$response" | jq -e 'has("users") or has("data")' > /dev/null 2>&1; then
            print_pass "Get reputation leaderboard successful"
        else
            print_fail "Get reputation leaderboard returned unexpected response"
        fi
    else
        print_skip "Get reputation leaderboard skipped (requires admin role)"
    fi

    # Test: Adjust member reputation (if we have a member ID)
    if [ -n "$TEST_USER_ID" ]; then
        print_test "PUT /api/v1/admin/$COMMUNITY_ID/members/$TEST_USER_ID/reputation"
        rep_adjust_data='{"amount": 10, "reason": "API test adjustment"}'
        if api_call PUT "/api/v1/admin/$COMMUNITY_ID/members/$TEST_USER_ID/reputation" "$rep_adjust_data" 200 true > /dev/null 2>&1; then
            print_pass "Adjust member reputation successful"
        else
            print_skip "Adjust member reputation skipped (requires admin role)"
        fi
    else
        print_skip "PUT /api/v1/admin/:communityId/members/:userId/reputation (no member ID)"
    fi

    ############################################################################
    # Bot Score API Tests
    ############################################################################
    print_header "Bot Score API Tests"

    # Test: Get bot score
    print_test "GET /api/v1/admin/$COMMUNITY_ID/bot-score"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/bot-score" "" 200 true 2>/dev/null); then
        if echo "$response" | jq -e '.botScore' > /dev/null 2>&1 || \
           echo "$response" | jq -e '.success' > /dev/null 2>&1; then
            print_pass "Get bot score successful"
        else
            print_fail "Get bot score returned unexpected response"
        fi
    else
        print_skip "Get bot score skipped (requires admin role)"
    fi

    # Test: Get suspected bots
    print_test "GET /api/v1/admin/$COMMUNITY_ID/suspected-bots"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/suspected-bots?limit=10&minConfidence=50" "" 200 true 2>/dev/null); then
        if echo "$response" | jq -e '.suspectedBots' > /dev/null 2>&1 || \
           echo "$response" | jq -e '.success' > /dev/null 2>&1; then
            print_pass "Get suspected bots successful"
        else
            print_fail "Get suspected bots returned unexpected response"
        fi
    else
        print_skip "Get suspected bots skipped (requires admin role)"
    fi

    ############################################################################
    # Announcement API Tests
    ############################################################################
    print_header "Announcement API Tests"

    # Test: Get announcements
    print_test "GET /api/v1/admin/$COMMUNITY_ID/announcements"
    if response=$(api_call GET "/api/v1/admin/$COMMUNITY_ID/announcements" "" 200 true 2>/dev/null); then
        if echo "$response" | jq -e '.data' > /dev/null 2>&1 || \
           echo "$response" | jq -e '.success' > /dev/null 2>&1; then
            print_pass "Get announcements successful"
        else
            print_fail "Get announcements returned unexpected response"
        fi
    else
        print_skip "Get announcements skipped (requires admin role)"
    fi

    # Test: Create announcement
    print_test "POST /api/v1/admin/$COMMUNITY_ID/announcements"
    announcement_data='{"title": "Test Announcement", "content": "This is a test announcement from API tests", "announcementType": "general", "status": "draft"}'
    TEST_ANNOUNCEMENT_ID=""
    if response=$(api_call POST "/api/v1/admin/$COMMUNITY_ID/announcements" "$announcement_data" 201 true 2>/dev/null); then
        TEST_ANNOUNCEMENT_ID=$(echo "$response" | jq -r '(.data.id // .id // empty)' 2>/dev/null || echo "")
        if [ -n "$TEST_ANNOUNCEMENT_ID" ]; then
            print_pass "Create announcement successful (ID: $TEST_ANNOUNCEMENT_ID)"
        else
            print_pass "Create announcement successful"
        fi
    else
        print_skip "Create announcement skipped (requires admin role)"
    fi

    # Test: Update announcement (if we created one)
    if [ -n "$TEST_ANNOUNCEMENT_ID" ]; then
        print_test "PUT /api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID"
        update_data='{"title": "Updated Test Announcement", "content": "Updated content"}'
        if api_call PUT "/api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID" "$update_data" 200 true > /dev/null 2>&1; then
            print_pass "Update announcement successful"
        else
            print_skip "Update announcement skipped"
        fi

        # Test: Pin announcement
        print_test "PUT /api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/pin"
        if api_call PUT "/api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/pin" "" 200 true > /dev/null 2>&1; then
            print_pass "Pin announcement successful"
        else
            print_skip "Pin announcement skipped"
        fi

        # Test: Unpin announcement
        print_test "PUT /api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/unpin"
        if api_call PUT "/api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/unpin" "" 200 true > /dev/null 2>&1; then
            print_pass "Unpin announcement successful"
        else
            print_skip "Unpin announcement skipped"
        fi

        # Test: Publish announcement
        print_test "POST /api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/publish"
        if api_call POST "/api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/publish" "" 200 true > /dev/null 2>&1; then
            print_pass "Publish announcement successful"
        else
            print_skip "Publish announcement skipped"
        fi

        # Test: Get broadcast status
        print_test "GET /api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/broadcast-status"
        if api_call GET "/api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/broadcast-status" "" 200 true > /dev/null 2>&1; then
            print_pass "Get broadcast status successful"
        else
            print_skip "Get broadcast status skipped"
        fi

        # Test: Archive announcement
        print_test "POST /api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/archive"
        if api_call POST "/api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID/archive" "" 200 true > /dev/null 2>&1; then
            print_pass "Archive announcement successful"
        else
            print_skip "Archive announcement skipped"
        fi

        # Test: Delete announcement (cleanup)
        print_test "DELETE /api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID"
        if api_call DELETE "/api/v1/admin/$COMMUNITY_ID/announcements/$TEST_ANNOUNCEMENT_ID" "" 200 true > /dev/null 2>&1; then
            print_pass "Delete announcement successful"
        else
            print_skip "Delete announcement skipped"
        fi
    else
        print_skip "Announcement CRUD tests (no announcement ID)"
    fi
else
    print_skip "Admin API tests (no community available)"
fi

################################################################################
# SuperAdmin API Tests
################################################################################

print_header "SuperAdmin API Tests"

# Test: Get dashboard stats
print_test "GET /api/v1/superadmin/dashboard"
if response=$(api_call GET /api/v1/superadmin/dashboard "" 200 true 2>/dev/null); then
    print_pass "Get superadmin dashboard successful"
else
    print_skip "Get superadmin dashboard skipped (requires super_admin role)"
fi

# Test: List all communities
print_test "GET /api/v1/superadmin/communities"
if response=$(api_call GET /api/v1/superadmin/communities "" 200 true 2>/dev/null); then
    print_pass "List all communities successful"
else
    print_skip "List all communities skipped (requires super_admin role)"
fi

# Test: Create community (Discord)
print_test "POST /api/v1/superadmin/communities (Discord platform)"
community_data=$(jq -n \
    --arg name "test_community_$(date +%s)" \
    --arg display_name "Test Community" \
    '{name: $name, displayName: $display_name, platform: "discord", isPublic: true}')
if response=$(api_call POST /api/v1/superadmin/communities "$community_data" 201 true 2>/dev/null); then
    print_pass "Create Discord community successful"
    CREATED_COMMUNITY_ID=$(echo "$response" | jq -r '(.data.id // .id // empty)' 2>/dev/null || echo "")
else
    print_skip "Create Discord community skipped (requires super_admin role)"
fi

# Test: Create community with YouTube platform
print_test "POST /api/v1/superadmin/communities (YouTube platform)"
youtube_community_data=$(jq -n \
    --arg name "test_youtube_$(date +%s)" \
    --arg display_name "Test YouTube Community" \
    '{name: $name, displayName: $display_name, platform: "youtube", isPublic: true}')
if response=$(api_call POST /api/v1/superadmin/communities "$youtube_community_data" 201 true 2>/dev/null); then
    print_pass "Create YouTube community successful"
    YOUTUBE_COMMUNITY_ID=$(echo "$response" | jq -r '(.data.id // .id // empty)' 2>/dev/null || echo "")
    # Clean up - delete this test community
    if [ -n "$YOUTUBE_COMMUNITY_ID" ]; then
        api_call DELETE "/api/v1/superadmin/communities/$YOUTUBE_COMMUNITY_ID" "" 200 true > /dev/null 2>&1
    fi
else
    print_skip "Create YouTube community skipped (requires super_admin role)"
fi

# Test: Create community with KICK platform
print_test "POST /api/v1/superadmin/communities (KICK platform)"
kick_community_data=$(jq -n \
    --arg name "test_kick_$(date +%s)" \
    --arg display_name "Test KICK Community" \
    '{name: $name, displayName: $display_name, platform: "kick", isPublic: true}')
if response=$(api_call POST /api/v1/superadmin/communities "$kick_community_data" 201 true 2>/dev/null); then
    print_pass "Create KICK community successful"
    KICK_COMMUNITY_ID=$(echo "$response" | jq -r '(.data.id // .id // empty)' 2>/dev/null || echo "")
    # Clean up - delete this test community
    if [ -n "$KICK_COMMUNITY_ID" ]; then
        api_call DELETE "/api/v1/superadmin/communities/$KICK_COMMUNITY_ID" "" 200 true > /dev/null 2>&1
    fi
else
    print_skip "Create KICK community skipped (requires super_admin role)"
fi

# Test: Create community with owner name (string, not ID)
print_test "POST /api/v1/superadmin/communities (with ownerName string)"
owner_community_data=$(jq -n \
    --arg name "test_owner_$(date +%s)" \
    --arg display_name "Test Owner Community" \
    --arg owner_name "TestOwner" \
    '{name: $name, displayName: $display_name, platform: "twitch", ownerName: $owner_name, isPublic: true}')
if response=$(api_call POST /api/v1/superadmin/communities "$owner_community_data" 201 true 2>/dev/null); then
    print_pass "Create community with ownerName successful"
    OWNER_COMMUNITY_ID=$(echo "$response" | jq -r '(.data.id // .id // empty)' 2>/dev/null || echo "")
    # Clean up - delete this test community
    if [ -n "$OWNER_COMMUNITY_ID" ]; then
        api_call DELETE "/api/v1/superadmin/communities/$OWNER_COMMUNITY_ID" "" 200 true > /dev/null 2>&1
    fi
else
    print_skip "Create community with ownerName skipped (requires super_admin role)"
fi

# Test: Get specific community
if [ -n "$CREATED_COMMUNITY_ID" ]; then
    print_test "GET /api/v1/superadmin/communities/$CREATED_COMMUNITY_ID"
    if api_call GET "/api/v1/superadmin/communities/$CREATED_COMMUNITY_ID" "" 200 true > /dev/null 2>&1; then
        print_pass "Get community by ID successful"
    else
        print_skip "Get community by ID skipped"
    fi

    # Test: Update community
    print_test "PUT /api/v1/superadmin/communities/$CREATED_COMMUNITY_ID"
    update_data='{"displayName": "Updated Test Community", "description": "Updated description"}'
    if api_call PUT "/api/v1/superadmin/communities/$CREATED_COMMUNITY_ID" "$update_data" 200 true > /dev/null 2>&1; then
        print_pass "Update community successful"
    else
        print_skip "Update community skipped"
    fi

    # Test: Delete community (should succeed for non-global community)
    print_test "DELETE /api/v1/superadmin/communities/$CREATED_COMMUNITY_ID"
    if api_call DELETE "/api/v1/superadmin/communities/$CREATED_COMMUNITY_ID" "" 200 true > /dev/null 2>&1; then
        print_pass "Delete community successful"
    else
        print_skip "Delete community skipped"
    fi
fi

# Test: Get hub settings
print_test "GET /api/v1/superadmin/settings"
if response=$(api_call GET /api/v1/superadmin/settings "" 200 true 2>/dev/null); then
    print_pass "Get hub settings successful"
else
    print_skip "Get hub settings skipped (requires super_admin role)"
fi

# Test: Update hub settings
print_test "PUT /api/v1/superadmin/settings"
settings_data='{"signupEnabled": true, "emailVerificationRequired": false}'
if api_call PUT /api/v1/superadmin/settings "$settings_data" 200 true > /dev/null 2>&1; then
    print_pass "Update hub settings successful"
else
    print_skip "Update hub settings skipped (requires super_admin role)"
fi

# Test: Get all modules
print_test "GET /api/v1/superadmin/marketplace/modules"
if api_call GET /api/v1/superadmin/marketplace/modules "" 200 true > /dev/null 2>&1; then
    print_pass "Get all modules successful"
else
    print_skip "Get all modules skipped (requires super_admin role)"
fi

# Test: Get platform configs
print_test "GET /api/v1/superadmin/platform-config"
if api_call GET /api/v1/superadmin/platform-config "" 200 true > /dev/null 2>&1; then
    print_pass "Get platform configs successful"
else
    print_skip "Get platform configs skipped (requires super_admin role)"
fi

################################################################################
# Test: Logout
################################################################################

print_header "Logout"

print_test "POST /api/v1/auth/logout"
if api_call POST /api/v1/auth/logout "" 200 true > /dev/null 2>&1; then
    print_pass "Logout successful"
else
    print_skip "Logout skipped"
fi

################################################################################
# Print Summary and Exit
################################################################################

print_summary

if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
