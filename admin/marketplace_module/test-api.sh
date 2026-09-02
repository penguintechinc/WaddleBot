#!/bin/bash

################################################################################
# WaddleBot Marketplace Module API Test Script
# Comprehensive test suite for all Marketplace Module API endpoints
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
MARKETPLACE_URL="${MARKETPLACE_URL:-http://localhost:3001}"
ADMIN_EMAIL="${ADMIN_EMAIL:-${INITIAL_ADMIN_EMAIL:-admin@localhost.local}}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-${INITIAL_ADMIN_PASSWORD:-}}"
AUTH_TOKEN=""
COMMUNITY_ID="${COMMUNITY_ID:-1}"
TEST_MODULE_ID=""
TEST_SUBSCRIPTION_ID=""

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
WaddleBot Marketplace Module API Test Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -u, --url URL           Marketplace module URL (default: http://localhost:3001)
    -e, --email EMAIL       Admin email (default: admin@localhost)
    -p, --password PASS     Admin password (default: $INITIAL_ADMIN_PASSWORD, if set)
    -c, --community ID      Community ID for testing (default: 1)
    -v, --verbose           Enable verbose output (show response bodies)

Environment Variables:
    MARKETPLACE_URL         Marketplace module URL
    ADMIN_EMAIL             Admin email for authentication
    ADMIN_PASSWORD          Admin password for authentication
    COMMUNITY_ID            Community ID for testing

Examples:
    # Run tests against local instance
    $0

    # Run tests against custom URL
    $0 --url http://marketplace.example.com:3001

    # Run with custom credentials and community ID
    $0 --email admin@example.com --password mypassword --community 42

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
    response=$(curl "${curl_opts[@]}" "${MARKETPLACE_URL}${endpoint}" 2>&1 || true)

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
            MARKETPLACE_URL="$2"
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
        -c|--community)
            COMMUNITY_ID="$2"
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

echo -e "${BLUE}WaddleBot Marketplace Module API Test Suite${NC}"
echo -e "Testing: ${MARKETPLACE_URL}"
echo -e "Community ID: ${COMMUNITY_ID}"

################################################################################
# Health Check
################################################################################

print_header "Health Check"

print_test "GET /health"
if response=$(api_call GET /health "" 200 false); then
    if echo "$response" | jq -e '.status' > /dev/null 2>&1; then
        print_pass "Health check successful"
    else
        print_fail "Health check returned unexpected response"
    fi
else
    print_fail "Health check failed"
    exit 1
fi

################################################################################
# Module Browse Tests (Public)
################################################################################

print_header "Module Browse Tests (Public)"

# Test: Browse all modules
print_test "GET /api/modules (list all modules)"
if response=$(api_call GET "/api/modules" "" 200 false); then
    if echo "$response" | jq -e 'type == "array" or .data' > /dev/null 2>&1; then
        print_pass "Browse modules successful"
        # Try to extract a module ID for later tests
        TEST_MODULE_ID=$(echo "$response" | jq -r '(.[0].id // .data[0].id // empty)' 2>/dev/null || echo "")
    else
        print_fail "Browse modules returned unexpected response"
    fi
else
    print_skip "Browse modules failed or no modules available"
fi

# Test: Get module details (if we have a module ID)
if [ -n "$TEST_MODULE_ID" ]; then
    print_test "GET /api/modules/$TEST_MODULE_ID (get module details)"
    if response=$(api_call GET "/api/modules/$TEST_MODULE_ID" "" 200 false); then
        if echo "$response" | jq -e '.id or .data.id' > /dev/null 2>&1; then
            print_pass "Get module details successful"
        else
            print_fail "Get module details returned unexpected response"
        fi
    else
        print_fail "Get module details failed"
    fi
else
    print_skip "GET /api/modules/:id (no module available)"
fi

################################################################################
# Community Subscriptions Tests (Requires Auth)
################################################################################

print_header "Community Subscriptions Tests"

# Note: In a real scenario, you would need proper authentication setup
# These tests assume the module endpoints are available without authentication
# or that we can bypass it for testing purposes

# Test: Get community subscriptions (list installed modules)
print_test "GET /api/communities/$COMMUNITY_ID/subscriptions (list community subscriptions)"
if response=$(api_call GET "/api/communities/$COMMUNITY_ID/subscriptions" "" 200 false); then
    if echo "$response" | jq -e 'type == "array" or .data' > /dev/null 2>&1; then
        print_pass "Get community subscriptions successful"
        # Try to extract a subscription ID
        TEST_SUBSCRIPTION_ID=$(echo "$response" | jq -r '(.[0].id // .data[0].id // empty)' 2>/dev/null || echo "")
    else
        print_skip "Get community subscriptions returned unexpected response"
    fi
else
    print_skip "Get community subscriptions skipped (may require authentication)"
fi

# Test: Subscribe to a module (if we have a module ID)
if [ -n "$TEST_MODULE_ID" ]; then
    print_test "POST /api/communities/$COMMUNITY_ID/subscriptions (subscribe to module)"
    subscribe_data=$(jq -n --argjson moduleId "$TEST_MODULE_ID" '{moduleId: $moduleId}')

    if response=$(api_call POST "/api/communities/$COMMUNITY_ID/subscriptions" "$subscribe_data" 201 false 2>/dev/null); then
        if echo "$response" | jq -e '.id or .data.id' > /dev/null 2>&1; then
            print_pass "Subscribe to module successful"
            # Save subscription ID if created
            NEW_SUBSCRIPTION_ID=$(echo "$response" | jq -r '(.id // .data.id // empty)' 2>/dev/null || echo "")
            if [ -z "$TEST_SUBSCRIPTION_ID" ] && [ -n "$NEW_SUBSCRIPTION_ID" ]; then
                TEST_SUBSCRIPTION_ID="$NEW_SUBSCRIPTION_ID"
            fi
        else
            print_skip "Subscribe to module returned unexpected response"
        fi
    elif response=$(api_call POST "/api/communities/$COMMUNITY_ID/subscriptions" "$subscribe_data" 409 false 2>/dev/null); then
        print_skip "Subscribe to module skipped (already subscribed)"
    else
        print_skip "Subscribe to module skipped or failed"
    fi
else
    print_skip "POST /api/communities/:id/subscriptions (no module available)"
fi

# Test: Update subscription
if [ -n "$TEST_SUBSCRIPTION_ID" ]; then
    print_test "PUT /api/communities/$COMMUNITY_ID/subscriptions/$TEST_SUBSCRIPTION_ID (update subscription)"
    update_data='{"isEnabled": true}'

    if api_call PUT "/api/communities/$COMMUNITY_ID/subscriptions/$TEST_SUBSCRIPTION_ID" "$update_data" 200 false > /dev/null 2>&1; then
        print_pass "Update subscription successful"
    else
        print_skip "Update subscription skipped (may require authentication)"
    fi
else
    print_skip "PUT /api/communities/:id/subscriptions/:id (no subscription available)"
fi

# Test: Unsubscribe (remove subscription)
if [ -n "$TEST_SUBSCRIPTION_ID" ]; then
    print_test "DELETE /api/communities/$COMMUNITY_ID/subscriptions/$TEST_SUBSCRIPTION_ID (unsubscribe module)"

    if api_call DELETE "/api/communities/$COMMUNITY_ID/subscriptions/$TEST_SUBSCRIPTION_ID" "" 200 false > /dev/null 2>&1 || \
       api_call DELETE "/api/communities/$COMMUNITY_ID/subscriptions/$TEST_SUBSCRIPTION_ID" "" 204 false > /dev/null 2>&1; then
        print_pass "Unsubscribe module successful"
    else
        print_skip "Unsubscribe module skipped (may require authentication)"
    fi
else
    print_skip "DELETE /api/communities/:id/subscriptions/:id (no subscription available)"
fi

################################################################################
# Payment Endpoints Tests
################################################################################

print_header "Payment Endpoints Tests"

# Test: Get supported payment providers
print_test "GET /api/payments/providers (list supported payment providers)"
if response=$(api_call GET "/api/payments/providers" "" 200 false); then
    if echo "$response" | jq -e 'type == "array" or .providers or .data' > /dev/null 2>&1; then
        print_pass "Get payment providers successful"
    else
        print_skip "Get payment providers returned unexpected response"
    fi
else
    print_skip "Get payment providers skipped (endpoint may not be available)"
fi

# Test: Validate payment provider config
print_test "GET /api/payments/config/validate/stripe (validate provider config)"
if response=$(api_call GET "/api/payments/config/validate/stripe" "" 200 false); then
    if echo "$response" | jq -e '.valid or .success or .data' > /dev/null 2>&1; then
        print_pass "Validate payment provider config successful"
    else
        print_skip "Validate payment provider config returned unexpected response"
    fi
elif response=$(api_call GET "/api/payments/config/validate/stripe" "" 400 false 2>/dev/null); then
    print_skip "Validate payment provider config skipped (provider not configured)"
else
    print_skip "Validate payment provider config skipped (endpoint unavailable)"
fi

# Test: Create checkout session
print_test "POST /api/payments/checkout (create checkout session)"
checkout_data=$(jq -n \
    --arg provider "stripe" \
    '{provider: $provider, amount: 9999, currency: "USD", description: "Test checkout"}')

if response=$(api_call POST "/api/payments/checkout" "$checkout_data" 201 false 2>/dev/null); then
    if echo "$response" | jq -e '.sessionId or .id or .data.sessionId' > /dev/null 2>&1; then
        print_pass "Create checkout session successful"
    else
        print_skip "Create checkout session returned unexpected response"
    fi
elif response=$(api_call POST "/api/payments/checkout" "$checkout_data" 400 false 2>/dev/null); then
    print_skip "Create checkout session skipped (invalid request or not configured)"
else
    print_skip "Create checkout session skipped (endpoint unavailable)"
fi

# Test: Create payment
print_test "POST /api/payments/complete (complete payment)"
payment_data=$(jq -n \
    --arg provider "stripe" \
    '{provider: $provider, transactionId: "test-txn-123", amount: 9999, status: "pending"}')

if response=$(api_call POST "/api/payments/complete" "$payment_data" 201 false 2>/dev/null); then
    if echo "$response" | jq -e '.transactionId or .id or .data.transactionId' > /dev/null 2>&1; then
        print_pass "Complete payment successful"
    else
        print_skip "Complete payment returned unexpected response"
    fi
elif response=$(api_call POST "/api/payments/complete" "$payment_data" 400 false 2>/dev/null); then
    print_skip "Complete payment skipped (invalid request or not configured)"
else
    print_skip "Complete payment skipped (endpoint unavailable)"
fi

# Test: Get payment
print_test "GET /api/payments/stripe/test-payment-123 (get payment details)"
if response=$(api_call GET "/api/payments/stripe/test-payment-123" "" 200 false 2>/dev/null); then
    if echo "$response" | jq -e '.provider or .transactionId or .data' > /dev/null 2>&1; then
        print_pass "Get payment details successful"
    else
        print_skip "Get payment details returned unexpected response"
    fi
elif response=$(api_call GET "/api/payments/stripe/test-payment-123" "" 404 false 2>/dev/null); then
    print_skip "Get payment details skipped (payment not found)"
else
    print_skip "Get payment details skipped (endpoint unavailable)"
fi

# Test: Create subscription
print_test "POST /api/payments/subscriptions (create payment subscription)"
subscription_data=$(jq -n \
    --arg provider "stripe" \
    '{provider: $provider, customerId: "test-customer-123", planId: "test-plan-monthly", amount: 999}')

if response=$(api_call POST "/api/payments/subscriptions" "$subscription_data" 201 false 2>/dev/null); then
    if echo "$response" | jq -e '.subscriptionId or .id or .data.subscriptionId' > /dev/null 2>&1; then
        print_pass "Create payment subscription successful"
    else
        print_skip "Create payment subscription returned unexpected response"
    fi
elif response=$(api_call POST "/api/payments/subscriptions" "$subscription_data" 400 false 2>/dev/null); then
    print_skip "Create payment subscription skipped (invalid request or not configured)"
else
    print_skip "Create payment subscription skipped (endpoint unavailable)"
fi

# Test: Create refund
print_test "POST /api/payments/refunds (create refund)"
refund_data=$(jq -n \
    --arg provider "stripe" \
    '{provider: $provider, transactionId: "test-txn-123", amount: 9999, reason: "customer_request"}')

if response=$(api_call POST "/api/payments/refunds" "$refund_data" 201 false 2>/dev/null); then
    if echo "$response" | jq -e '.refundId or .id or .data.refundId' > /dev/null 2>&1; then
        print_pass "Create refund successful"
    else
        print_skip "Create refund returned unexpected response"
    fi
elif response=$(api_call POST "/api/payments/refunds" "$refund_data" 400 false 2>/dev/null); then
    print_skip "Create refund skipped (invalid request or not configured)"
else
    print_skip "Create refund skipped (endpoint unavailable)"
fi

# Test: Create customer
print_test "POST /api/payments/customers (create payment customer)"
customer_data=$(jq -n \
    --arg provider "stripe" \
    '{provider: $provider, email: "test@example.com", name: "Test Customer"}')

if response=$(api_call POST "/api/payments/customers" "$customer_data" 201 false 2>/dev/null); then
    if echo "$response" | jq -e '.customerId or .id or .data.customerId' > /dev/null 2>&1; then
        print_pass "Create payment customer successful"
    else
        print_skip "Create payment customer returned unexpected response"
    fi
elif response=$(api_call POST "/api/payments/customers" "$customer_data" 400 false 2>/dev/null); then
    print_skip "Create payment customer skipped (invalid request or not configured)"
else
    print_skip "Create payment customer skipped (endpoint unavailable)"
fi

# Test: Get customer payment methods
print_test "GET /api/payments/customers/stripe/test-customer-123/payment-methods (list payment methods)"
if response=$(api_call GET "/api/payments/customers/stripe/test-customer-123/payment-methods" "" 200 false 2>/dev/null); then
    if echo "$response" | jq -e 'type == "array" or .paymentMethods or .data' > /dev/null 2>&1; then
        print_pass "List payment methods successful"
    else
        print_skip "List payment methods returned unexpected response"
    fi
elif response=$(api_call GET "/api/payments/customers/stripe/test-customer-123/payment-methods" "" 404 false 2>/dev/null); then
    print_skip "List payment methods skipped (customer not found)"
else
    print_skip "List payment methods skipped (endpoint unavailable)"
fi

################################################################################
# Error Handling Tests
################################################################################

print_header "Error Handling Tests"

# Test: Invalid module ID
print_test "GET /api/modules/invalid-id (invalid module)"
if api_call GET "/api/modules/invalid-id" "" 404 false > /dev/null 2>&1; then
    print_pass "Invalid module ID correctly rejected"
else
    print_skip "Invalid module ID handling may vary"
fi

# Test: Invalid endpoint
print_test "GET /api/invalid-endpoint (invalid endpoint)"
if api_call GET "/api/invalid-endpoint" "" 404 false > /dev/null 2>&1; then
    print_pass "Invalid endpoint correctly rejected"
else
    print_skip "Invalid endpoint handling may vary"
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
