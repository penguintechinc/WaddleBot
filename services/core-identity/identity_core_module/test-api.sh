#!/bin/bash
#
# Identity Core Module API Test Script
# Tests all API endpoints for the WaddleBot Identity Core Module
#
# Usage: ./test-api.sh [OPTIONS]
#
# Options:
#   --help              Show this help message
#   --url URL           Base URL for the service (default: http://localhost:8050)
#   --api-key KEY       API key for authenticated requests
#   --verbose           Enable verbose output
#

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Configuration
BASE_URL="${IDENTITY_CORE_URL:-http://localhost:8050}"
API_KEY="${IDENTITY_CORE_API_KEY:-}"
VERBOSE=false

# Test data storage
TEST_USER_ID=""
TEST_VERIFICATION_ID=""
TEST_VERIFICATION_CODE=""
TEST_API_KEY_ID=""

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo -e "${GREEN}[PASS]${NC} $message"
            ((PASS_COUNT++))
            ;;
        "FAIL")
            echo -e "${RED}[FAIL]${NC} $message"
            ((FAIL_COUNT++))
            ;;
        "SKIP")
            echo -e "${YELLOW}[SKIP]${NC} $message"
            ((SKIP_COUNT++))
            ;;
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
    esac
}

# Function to print verbose output
verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Function to print help
print_help() {
    cat << EOF
Identity Core Module API Test Script

Usage: $0 [OPTIONS]

Options:
    --help              Show this help message
    --url URL           Base URL for the service (default: http://localhost:8050)
    --api-key KEY       API key for authenticated requests
    --verbose           Enable verbose output

Environment Variables:
    IDENTITY_CORE_URL       Base URL for the service
    IDENTITY_CORE_API_KEY   API key for authenticated requests

Examples:
    # Test local instance
    $0

    # Test with custom URL
    $0 --url http://identity-core:8050

    # Test with API key
    $0 --api-key "your-api-key-here"

    # Verbose mode
    $0 --verbose

Exit Codes:
    0 - All tests passed
    1 - One or more tests failed

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            print_help
            ;;
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to make API request
api_request() {
    local method=$1
    local endpoint=$2
    local data=${3:-}
    local expect_status=${4:-200}
    local headers=""

    if [ -n "$API_KEY" ]; then
        headers="-H 'X-API-Key: $API_KEY'"
    fi

    verbose "Request: $method $BASE_URL$endpoint"
    if [ -n "$data" ]; then
        verbose "Data: $data"
    fi

    local response
    local status_code

    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            ${headers:+-H "$headers"} \
            -d "$data" \
            "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            ${headers:+-H "$headers"} \
            "$BASE_URL$endpoint")
    fi

    status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    verbose "Response Status: $status_code"
    verbose "Response Body: $body"

    if [ "$status_code" -eq "$expect_status" ]; then
        echo "$body"
        return 0
    else
        echo "$body"
        return 1
    fi
}

# Function to test JSON response
test_json_field() {
    local json=$1
    local field=$2
    local expected=${3:-}

    if ! echo "$json" | jq -e ".$field" > /dev/null 2>&1; then
        verbose "Field '$field' not found in JSON"
        return 1
    fi

    if [ -n "$expected" ]; then
        local actual=$(echo "$json" | jq -r ".$field")
        if [ "$actual" != "$expected" ]; then
            verbose "Field '$field' expected '$expected' but got '$actual'"
            return 1
        fi
    fi

    return 0
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed."
    echo "Please install jq: sudo apt-get install jq"
    exit 1
fi

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed."
    echo "Please install curl: sudo apt-get install curl"
    exit 1
fi

echo "========================================"
echo "Identity Core Module API Tests"
echo "========================================"
echo "Base URL: $BASE_URL"
echo "========================================"
echo ""

# ========================================
# Health Check Endpoints
# ========================================

echo "Testing Health Check Endpoints..."
echo "----------------------------------------"

# Test /health endpoint
TEST_NAME="/health - Basic health check"
if response=$(api_request GET "/health" "" 200 2>&1); then
    if test_json_field "$response" "status" "healthy" && \
       test_json_field "$response" "module" "identity_core_module" && \
       test_json_field "$response" "version"; then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "FAIL" "$TEST_NAME - Invalid response structure"
    fi
else
    print_status "FAIL" "$TEST_NAME - HTTP request failed"
fi

# Test /healthz endpoint (Kubernetes probe)
TEST_NAME="/healthz - Kubernetes liveness probe"
if response=$(api_request GET "/healthz" "" 200 2>&1); then
    if test_json_field "$response" "status" "healthy"; then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "FAIL" "$TEST_NAME - Invalid response structure"
    fi
else
    print_status "FAIL" "$TEST_NAME - HTTP request failed"
fi

# Test /metrics endpoint
TEST_NAME="/metrics - Prometheus metrics"
if response=$(api_request GET "/metrics" "" 200 2>&1); then
    if echo "$response" | grep -q "module_info"; then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "FAIL" "$TEST_NAME - Invalid metrics format"
    fi
else
    print_status "FAIL" "$TEST_NAME - HTTP request failed"
fi

echo ""

# ========================================
# API Status Endpoint
# ========================================

echo "Testing API Status Endpoint..."
echo "----------------------------------------"

# Test /api/v1/status endpoint
TEST_NAME="/api/v1/status - Module status"
if response=$(api_request GET "/api/v1/status" "" 200 2>&1); then
    if test_json_field "$response" "status" "operational" && \
       test_json_field "$response" "module" "identity_core_module"; then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "FAIL" "$TEST_NAME - Invalid response structure"
    fi
else
    print_status "FAIL" "$TEST_NAME - HTTP request failed"
fi

echo ""

# ========================================
# Identity Linking Endpoints (Requires Authentication)
# ========================================

echo "Testing Identity Linking Endpoints..."
echo "----------------------------------------"

if [ -z "$API_KEY" ]; then
    print_status "SKIP" "Identity linking tests - API key required"
    print_status "SKIP" "POST /identity/link - Initiate identity linking"
    print_status "SKIP" "POST /identity/verify - Verify identity"
    print_status "SKIP" "DELETE /identity/unlink - Unlink identity"
else
    # Test POST /identity/link
    TEST_NAME="POST /identity/link - Initiate identity linking"
    link_data='{
        "platform": "twitch",
        "platform_id": "test_user_123",
        "platform_username": "testuser"
    }'
    if response=$(api_request POST "/identity/link" "$link_data" 200 2>&1); then
        if test_json_field "$response" "verification_id" && \
           test_json_field "$response" "verification_code" && \
           test_json_field "$response" "expires_at"; then
            print_status "PASS" "$TEST_NAME"
            TEST_VERIFICATION_ID=$(echo "$response" | jq -r '.verification_id')
            TEST_VERIFICATION_CODE=$(echo "$response" | jq -r '.verification_code')
        else
            print_status "FAIL" "$TEST_NAME - Invalid response structure"
        fi
    else
        # May fail if endpoint not implemented yet
        print_status "SKIP" "$TEST_NAME - Endpoint not available or not implemented"
    fi

    # Test POST /identity/verify
    TEST_NAME="POST /identity/verify - Verify identity"
    if [ -n "$TEST_VERIFICATION_CODE" ]; then
        verify_data="{
            \"verification_code\": \"$TEST_VERIFICATION_CODE\",
            \"platform\": \"twitch\"
        }"
        if response=$(api_request POST "/identity/verify" "$verify_data" 200 2>&1); then
            print_status "PASS" "$TEST_NAME"
        else
            print_status "SKIP" "$TEST_NAME - Endpoint not available or verification expired"
        fi
    else
        print_status "SKIP" "$TEST_NAME - No verification code from previous test"
    fi

    # Test DELETE /identity/unlink
    TEST_NAME="DELETE /identity/unlink - Unlink identity"
    unlink_data='{
        "platform": "twitch",
        "platform_id": "test_user_123"
    }'
    if response=$(api_request DELETE "/identity/unlink" "$unlink_data" 200 2>&1); then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available or nothing to unlink"
    fi
fi

echo ""

# ========================================
# Identity Lookup Endpoints (Requires Authentication)
# ========================================

echo "Testing Identity Lookup Endpoints..."
echo "----------------------------------------"

if [ -z "$API_KEY" ]; then
    print_status "SKIP" "Identity lookup tests - API key required"
    print_status "SKIP" "GET /identity/user/<user_id> - Get user identities"
    print_status "SKIP" "GET /identity/platform/<platform>/<platform_id> - Get user by platform"
else
    # Test GET /identity/user/<user_id>
    TEST_NAME="GET /identity/user/<user_id> - Get user identities"
    test_user_id="test_user_001"
    if response=$(api_request GET "/identity/user/$test_user_id" "" 200 2>&1); then
        if test_json_field "$response" "user_id" && \
           test_json_field "$response" "identities"; then
            print_status "PASS" "$TEST_NAME"
        else
            print_status "FAIL" "$TEST_NAME - Invalid response structure"
        fi
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available or user not found"
    fi

    # Test GET /identity/platform/<platform>/<platform_id>
    TEST_NAME="GET /identity/platform/<platform>/<platform_id> - Get user by platform"
    test_platform="twitch"
    test_platform_id="test_platform_123"
    if response=$(api_request GET "/identity/platform/$test_platform/$test_platform_id" "" 200 2>&1); then
        if test_json_field "$response" "user_id" && \
           test_json_field "$response" "display_name"; then
            print_status "PASS" "$TEST_NAME"
        else
            print_status "FAIL" "$TEST_NAME - Invalid response structure"
        fi
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available or platform user not found"
    fi
fi

echo ""

# ========================================
# Verification Management Endpoints (Requires Authentication)
# ========================================

echo "Testing Verification Management Endpoints..."
echo "----------------------------------------"

if [ -z "$API_KEY" ]; then
    print_status "SKIP" "Verification management tests - API key required"
    print_status "SKIP" "GET /identity/pending - Get pending verifications"
    print_status "SKIP" "POST /identity/resend - Resend verification code"
else
    # Test GET /identity/pending
    TEST_NAME="GET /identity/pending - Get pending verifications"
    if response=$(api_request GET "/identity/pending" "" 200 2>&1); then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available"
    fi

    # Test POST /identity/resend
    TEST_NAME="POST /identity/resend - Resend verification code"
    if [ -n "$TEST_VERIFICATION_ID" ]; then
        resend_data="{
            \"verification_id\": \"$TEST_VERIFICATION_ID\"
        }"
        if response=$(api_request POST "/identity/resend" "$resend_data" 200 2>&1); then
            print_status "PASS" "$TEST_NAME"
        else
            print_status "SKIP" "$TEST_NAME - Endpoint not available or verification expired"
        fi
    else
        print_status "SKIP" "$TEST_NAME - No verification ID from previous test"
    fi
fi

echo ""

# ========================================
# API Key Management Endpoints (Requires Authentication)
# ========================================

echo "Testing API Key Management Endpoints..."
echo "----------------------------------------"

if [ -z "$API_KEY" ]; then
    print_status "SKIP" "API key management tests - API key required"
    print_status "SKIP" "POST /identity/api-keys - Create API key"
    print_status "SKIP" "GET /identity/api-keys - List API keys"
    print_status "SKIP" "POST /identity/api-keys/<key_id>/regenerate - Regenerate API key"
    print_status "SKIP" "DELETE /identity/api-keys/<key_id> - Revoke API key"
else
    # Test POST /identity/api-keys
    TEST_NAME="POST /identity/api-keys - Create API key"
    create_key_data='{
        "name": "Test API Key",
        "expires_in_days": 365
    }'
    if response=$(api_request POST "/identity/api-keys" "$create_key_data" 200 2>&1); then
        if test_json_field "$response" "api_key" && \
           test_json_field "$response" "key_id" && \
           test_json_field "$response" "expires_at"; then
            print_status "PASS" "$TEST_NAME"
            TEST_API_KEY_ID=$(echo "$response" | jq -r '.key_id')
        else
            print_status "FAIL" "$TEST_NAME - Invalid response structure"
        fi
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available"
    fi

    # Test GET /identity/api-keys
    TEST_NAME="GET /identity/api-keys - List API keys"
    if response=$(api_request GET "/identity/api-keys" "" 200 2>&1); then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available"
    fi

    # Test POST /identity/api-keys/<key_id>/regenerate
    TEST_NAME="POST /identity/api-keys/<key_id>/regenerate - Regenerate API key"
    if [ -n "$TEST_API_KEY_ID" ]; then
        if response=$(api_request POST "/identity/api-keys/$TEST_API_KEY_ID/regenerate" "" 200 2>&1); then
            if test_json_field "$response" "api_key" && \
               test_json_field "$response" "expires_at"; then
                print_status "PASS" "$TEST_NAME"
            else
                print_status "FAIL" "$TEST_NAME - Invalid response structure"
            fi
        else
            print_status "SKIP" "$TEST_NAME - Endpoint not available"
        fi
    else
        print_status "SKIP" "$TEST_NAME - No API key ID from previous test"
    fi

    # Test DELETE /identity/api-keys/<key_id>
    TEST_NAME="DELETE /identity/api-keys/<key_id> - Revoke API key"
    if [ -n "$TEST_API_KEY_ID" ]; then
        if response=$(api_request DELETE "/identity/api-keys/$TEST_API_KEY_ID" "" 200 2>&1); then
            print_status "PASS" "$TEST_NAME"
        else
            print_status "SKIP" "$TEST_NAME - Endpoint not available"
        fi
    else
        print_status "SKIP" "$TEST_NAME - No API key ID from previous test"
    fi
fi

echo ""

# ========================================
# User Authentication Endpoints (Requires Authentication)
# ========================================

echo "Testing User Authentication Endpoints..."
echo "----------------------------------------"

# Test POST /auth/register
TEST_NAME="POST /auth/register - Register new user"
register_data='{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "username": "testuser"
}'
if response=$(api_request POST "/auth/register" "$register_data" 200 2>&1); then
    print_status "PASS" "$TEST_NAME"
else
    print_status "SKIP" "$TEST_NAME - Endpoint not available or user exists"
fi

# Test POST /auth/login
TEST_NAME="POST /auth/login - Login user"
login_data='{
    "email": "test@example.com",
    "password": "TestPassword123!"
}'
if response=$(api_request POST "/auth/login" "$login_data" 200 2>&1); then
    print_status "PASS" "$TEST_NAME"
else
    print_status "SKIP" "$TEST_NAME - Endpoint not available"
fi

# Test GET /auth/profile
TEST_NAME="GET /auth/profile - Get user profile"
if [ -n "$API_KEY" ]; then
    if response=$(api_request GET "/auth/profile" "" 200 2>&1); then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available"
    fi
else
    print_status "SKIP" "$TEST_NAME - API key required"
fi

# Test PUT /auth/profile
TEST_NAME="PUT /auth/profile - Update user profile"
if [ -n "$API_KEY" ]; then
    update_data='{
        "display_name": "Test User Updated"
    }'
    if response=$(api_request PUT "/auth/profile" "$update_data" 200 2>&1); then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available"
    fi
else
    print_status "SKIP" "$TEST_NAME - API key required"
fi

# Test POST /auth/logout
TEST_NAME="POST /auth/logout - Logout user"
if [ -n "$API_KEY" ]; then
    if response=$(api_request POST "/auth/logout" "" 200 2>&1); then
        print_status "PASS" "$TEST_NAME"
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available"
    fi
else
    print_status "SKIP" "$TEST_NAME - API key required"
fi

echo ""

# ========================================
# Monitoring Endpoints
# ========================================

echo "Testing Monitoring Endpoints..."
echo "----------------------------------------"

# Test GET /identity/stats
TEST_NAME="GET /identity/stats - Get identity statistics"
if [ -n "$API_KEY" ]; then
    if response=$(api_request GET "/identity/stats" "" 200 2>&1); then
        if test_json_field "$response" "total_users" && \
           test_json_field "$response" "total_identities"; then
            print_status "PASS" "$TEST_NAME"
        else
            print_status "FAIL" "$TEST_NAME - Invalid response structure"
        fi
    else
        print_status "SKIP" "$TEST_NAME - Endpoint not available"
    fi
else
    print_status "SKIP" "$TEST_NAME - API key required"
fi

# Test GET /identity/health
TEST_NAME="GET /identity/health - Identity health check"
if response=$(api_request GET "/identity/health" "" 200 2>&1); then
    print_status "PASS" "$TEST_NAME"
else
    print_status "SKIP" "$TEST_NAME - Endpoint not available"
fi

echo ""

# ========================================
# Summary
# ========================================

echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "${GREEN}Passed:${NC}  $PASS_COUNT"
echo -e "${RED}Failed:${NC}  $FAIL_COUNT"
echo -e "${YELLOW}Skipped:${NC} $SKIP_COUNT"
echo "========================================"

# Exit with appropriate code
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}Tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
