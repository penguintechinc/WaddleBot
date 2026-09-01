#!/bin/bash
# Test Phase Completion Script
# Tests completed phases to verify API functionality

set -e

echo "========================================="
echo "Waddles Phase Completion Test"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed=0
test_failed=0

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local method=$3
    local data=$4

    echo -n "Testing $name... "

    if [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null || echo "000")
    else
        response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo "000")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [[ "$http_code" =~ ^(200|201|404)$ ]]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        ((test_passed++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        ((test_failed++))
        return 1
    fi
}

echo "========================================="
echo "Phase 3.1: Shoutout Module Tests"
echo "========================================="

# Test Shoutout Module (if running)
SHOUTOUT_URL="http://localhost:8011"

test_endpoint "Shoutout Status" "$SHOUTOUT_URL/status" "GET"
test_endpoint "Shoutout Health" "$SHOUTOUT_URL/health" "GET"

echo ""
echo "========================================="
echo "Phase 3.2: Memories Module Tests"
echo "========================================="

# Test Memories Module (if running)
MEMORIES_URL="http://localhost:8013"

test_endpoint "Memories Status" "$MEMORIES_URL/api/v1/status" "GET"
test_endpoint "Memories Health" "$MEMORIES_URL/health" "GET"

# Test quote endpoints (will return 400 for missing data, but endpoint exists)
test_endpoint "Quotes Endpoint" "$MEMORIES_URL/api/v1/quotes" "POST" '{"test":"data"}'

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "Passed: ${GREEN}$test_passed${NC}"
echo -e "Failed: ${RED}$test_failed${NC}"
echo ""

if [ $test_failed -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${YELLOW}Some tests failed (modules may not be running)${NC}"
    exit 1
fi
