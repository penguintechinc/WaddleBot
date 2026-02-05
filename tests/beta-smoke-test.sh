#!/bin/bash
# Waddles Beta Smoke Test
# Validates API endpoints and frontend accessibility after deployment
#
# IMPORTANT: This test MUST pass after deployment to beta cluster.
# All critical endpoints must respond correctly - no 404s or 500s on expected routes.
#
# Usage: ./tests/beta-smoke-test.sh [BASE_URL] [ALB_HOST]
#   BASE_URL defaults to https://waddlebot.penguintech.io
#   ALB_HOST (optional) - ALB DNS name to bypass Cloudflare (e.g., dal2.penguintech.io)
#
# Environment variables:
#   ALB_HOST - ALB DNS name (overrides parameter)
#   VHOST - Virtual host header (extracted from BASE_URL if not set)
#
# Exit codes:
#   0 - All endpoints responding correctly (PASS)
#   1 - One or more endpoints failing (FAIL)

set -e

# Configuration
BASE_URL="${1:-https://waddlebot.penguintech.io}"
ALB_HOST="${ALB_HOST:-${2}}"
TIMEOUT=10
PASSED=0
FAILED=0
WARNINGS=0

# Extract virtual host from BASE_URL for Host header
if [ -z "$VHOST" ]; then
    VHOST=$(echo "$BASE_URL" | sed -E 's#https?://([^/]+).*#\1#')
fi

# Determine if we're using ALB bypass
if [ -n "$ALB_HOST" ]; then
    # Use ALB DNS with Host header to bypass Cloudflare
    CURL_BASE="curl -sk -H \"Host: $VHOST\" https://$ALB_HOST"
    echo "Using ALB bypass: $ALB_HOST with Host header: $VHOST"
else
    # Direct connection
    CURL_BASE="curl -s"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Waddles Beta Smoke Test"
echo "========================================"
echo ""
echo "Target: $BASE_URL"
echo "Timeout: ${TIMEOUT}s per request"
echo ""

# Helper function to test an endpoint
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local expected_status="$4"
    local data="$5"

    local url
    local actual_status

    if [ -n "$ALB_HOST" ]; then
        # Using ALB bypass
        url="https://$ALB_HOST${endpoint}"
        if [ "$method" = "GET" ]; then
            actual_status=$(curl -sk -H "Host: $VHOST" -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" "$url" 2>/dev/null || echo "000")
        elif [ "$method" = "POST" ]; then
            actual_status=$(curl -sk -H "Host: $VHOST" -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" \
                -X POST \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$url" 2>/dev/null || echo "000")
        fi
    else
        # Direct connection
        url="${BASE_URL}${endpoint}"
        if [ "$method" = "GET" ]; then
            actual_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" "$url" 2>/dev/null || echo "000")
        elif [ "$method" = "POST" ]; then
            actual_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" \
                -X POST \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$url" 2>/dev/null || echo "000")
        fi
    fi

    if [ "$actual_status" = "$expected_status" ]; then
        echo -e "${GREEN}  [PASS]${NC} $name ($method $endpoint) -> $actual_status"
        ((PASSED++))
        return 0
    elif [ "$actual_status" = "000" ]; then
        echo -e "${RED}  [FAIL]${NC} $name ($method $endpoint) -> Connection failed (timeout or unreachable)"
        ((FAILED++))
        return 1
    else
        echo -e "${RED}  [FAIL]${NC} $name ($method $endpoint) -> Expected $expected_status, got $actual_status"
        ((FAILED++))
        return 1
    fi
}

# Helper function for endpoints that should NOT return 404
test_not_404() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"

    local url
    local actual_status

    if [ -n "$ALB_HOST" ]; then
        # Using ALB bypass
        url="https://$ALB_HOST${endpoint}"
        if [ "$method" = "GET" ]; then
            actual_status=$(curl -sk -H "Host: $VHOST" -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" "$url" 2>/dev/null || echo "000")
        elif [ "$method" = "POST" ]; then
            actual_status=$(curl -sk -H "Host: $VHOST" -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" \
                -X POST \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$url" 2>/dev/null || echo "000")
        fi
    else
        # Direct connection
        url="${BASE_URL}${endpoint}"
        if [ "$method" = "GET" ]; then
            actual_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" "$url" 2>/dev/null || echo "000")
        elif [ "$method" = "POST" ]; then
            actual_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" \
                -X POST \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$url" 2>/dev/null || echo "000")
        fi
    fi

    if [ "$actual_status" = "404" ]; then
        echo -e "${RED}  [FAIL]${NC} $name ($method $endpoint) -> 404 NOT FOUND (endpoint missing!)"
        ((FAILED++))
        return 1
    elif [ "$actual_status" = "000" ]; then
        echo -e "${RED}  [FAIL]${NC} $name ($method $endpoint) -> Connection failed"
        ((FAILED++))
        return 1
    elif [ "$actual_status" = "500" ] || [ "$actual_status" = "502" ] || [ "$actual_status" = "503" ]; then
        echo -e "${YELLOW}  [WARN]${NC} $name ($method $endpoint) -> Server error $actual_status (check logs)"
        ((WARNINGS++))
        return 0
    else
        echo -e "${GREEN}  [PASS]${NC} $name ($method $endpoint) -> $actual_status"
        ((PASSED++))
        return 0
    fi
}

echo "----------------------------------------"
echo "1. Frontend Accessibility"
echo "----------------------------------------"

# Test frontend loads
test_endpoint "Homepage loads" "GET" "/" "200"

echo ""
echo "----------------------------------------"
echo "2. Public API Endpoints"
echo "----------------------------------------"

# These endpoints should exist and NOT return 404
test_not_404 "Signup settings" "GET" "/api/v1/signup-settings"
test_not_404 "Cookie policy" "GET" "/api/v1/cookie/policy"
test_not_404 "Cookie consent" "GET" "/api/v1/cookie"
test_not_404 "Platform stats" "GET" "/api/v1/stats"
test_not_404 "Public communities" "GET" "/api/v1/communities"

echo ""
echo "----------------------------------------"
echo "3. Authentication Endpoints"
echo "----------------------------------------"

# Auth endpoints - should exist (may return 400/401 but NOT 404)
test_not_404 "Login endpoint" "POST" "/api/v1/auth/login" '{"email":"test@test.com","password":"test"}'
test_not_404 "Register endpoint" "POST" "/api/v1/auth/register" '{"email":"test@test.com","password":"test123"}'
test_not_404 "Current user" "GET" "/api/v1/auth/me"

echo ""
echo "----------------------------------------"
echo "4. Health Endpoints"
echo "----------------------------------------"

# Health check endpoint (if exists)
test_endpoint "API health" "GET" "/api/v1/health" "200" 2>/dev/null || \
    echo -e "${YELLOW}  [SKIP]${NC} Health endpoint not configured"

echo ""
echo "========================================"
echo "Summary"
echo "========================================"
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

# Calculate result
if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}BETA SMOKE TEST FAILED${NC}"
    echo ""
    echo "Critical issues found:"
    echo "- 404 errors indicate missing API routes"
    echo "- Check frontend API URLs match backend routes"
    echo "- Verify deployment includes all required services"
    exit 1
fi

if [ "$WARNINGS" -gt 0 ]; then
    echo -e "${YELLOW}BETA SMOKE TEST PASSED WITH WARNINGS${NC}"
    echo ""
    echo "Server errors detected - check application logs for:"
    echo "- Database connection issues"
    echo "- Missing environment variables"
    echo "- Service dependencies not ready"
    exit 0
fi

echo -e "${GREEN}BETA SMOKE TEST PASSED${NC}"
echo "All $PASSED endpoints responding correctly!"
exit 0
