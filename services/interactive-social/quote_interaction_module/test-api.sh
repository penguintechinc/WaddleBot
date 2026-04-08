#!/usr/bin/env bash
################################################################################
# WaddleBot Quote Interaction Module API Test Script
################################################################################
#
# Comprehensive test suite for the Quote Interaction Module API endpoints.
# Tests health checks, quote CRUD operations, search, listing, and pagination.
#
# Usage:
#   ./test-api.sh [OPTIONS]
#
# Options:
#   --help              Show this help message
#   --url URL           Set quote module URL (default: http://localhost:5012)
#   --api-key KEY       Set API key for authenticated endpoints
#   --verbose           Enable verbose output
#   --skip-auth         Skip tests requiring authentication
#
# Environment Variables:
#   QUOTE_URL           Base URL for quote module (default: http://localhost:5012)
#   QUOTE_API_KEY       API key for authenticated endpoints
#   VERBOSE             Enable verbose output (true/false)
#
# Exit Codes:
#   0 - All tests passed
#   1 - One or more tests failed
#
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Configuration
QUOTE_URL="${QUOTE_URL:-http://localhost:5012}"
QUOTE_API_KEY="${QUOTE_API_KEY:-}"
VERBOSE="${VERBOSE:-false}"
SKIP_AUTH=false

# Test data storage
QUOTE_ID=""
COMMUNITY_ID=1

################################################################################
# Helper Functions
################################################################################

print_help() {
    sed -n '2,/^$/p' "$0" | sed 's/^# //g; s/^#//g'
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $*"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $*"
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $*"
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $*"
    fi
}

# Check if required commands are available
check_requirements() {
    local missing=()

    if ! command -v curl &> /dev/null; then
        missing+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        missing+=("jq")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing[*]}"
        log_error "Please install missing dependencies and try again"
        exit 1
    fi
}

# Make HTTP request and return response
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local auth_required="${4:-false}"

    local url="${QUOTE_URL}${endpoint}"
    local headers=(-H "Content-Type: application/json")

    # Add API key header if required and available
    if [[ "$auth_required" == "true" ]] && [[ -n "$QUOTE_API_KEY" ]]; then
        headers+=(-H "X-API-Key: ${QUOTE_API_KEY}")
    fi

    log_verbose "Request: $method $url"
    [[ -n "$data" ]] && log_verbose "Data: $data"

    local response
    local http_code

    if [[ -n "$data" ]]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            "${headers[@]}" \
            -d "$data" 2>&1) || true
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            "${headers[@]}" 2>&1) || true
    fi

    # Extract HTTP code from last line
    http_code=$(echo "$response" | tail -n1)
    response=$(echo "$response" | sed '$d')

    log_verbose "HTTP Code: $http_code"
    log_verbose "Response: $response"

    # Return both response and HTTP code
    echo "$response"
    echo "$http_code"
}

# Run a test case
run_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="${4:-}"
    local expected_code="${5:-200}"
    local auth_required="${6:-false}"
    local check_function="${7:-}"

    ((TESTS_RUN++))

    # Skip authenticated tests if no API key and skip_auth is set
    if [[ "$auth_required" == "true" ]] && [[ -z "$QUOTE_API_KEY" ]] && [[ "$SKIP_AUTH" == "true" ]]; then
        log_skip "$test_name (no API key)"
        ((TESTS_SKIPPED++))
        return 0
    fi

    log_info "Running: $test_name"

    # Make request
    local result
    result=$(make_request "$method" "$endpoint" "$data" "$auth_required")

    local response
    local http_code
    response=$(echo "$result" | head -n -1)
    http_code=$(echo "$result" | tail -n1)

    # Check HTTP code
    if [[ "$http_code" != "$expected_code" ]]; then
        log_error "$test_name - Expected HTTP $expected_code, got $http_code"
        log_verbose "Response: $response"
        ((TESTS_FAILED++))
        return 1
    fi

    # Check if response is valid JSON (unless it's empty or plain text)
    if [[ -n "$response" ]] && [[ "$response" != "null" ]]; then
        # Skip JSON validation for Prometheus metrics (plain text format)
        if [[ "$endpoint" != "/metrics" ]]; then
            if ! echo "$response" | jq . > /dev/null 2>&1; then
                log_error "$test_name - Invalid JSON response"
                log_verbose "Response: $response"
                ((TESTS_FAILED++))
                return 1
            fi
        fi
    fi

    # Run custom check function if provided
    if [[ -n "$check_function" ]]; then
        if ! $check_function "$response"; then
            log_error "$test_name - Custom validation failed"
            log_verbose "Response: $response"
            ((TESTS_FAILED++))
            return 1
        fi
    fi

    log_success "$test_name"
    ((TESTS_PASSED++))
    return 0
}

################################################################################
# Test Validation Functions
################################################################################

check_health_response() {
    local response="$1"

    # Check for status field
    if ! echo "$response" | jq -e '.status' > /dev/null 2>&1; then
        log_error "Missing 'status' field"
        return 1
    fi

    local status
    status=$(echo "$response" | jq -r '.status')

    if [[ "$status" != "healthy" ]]; then
        log_error "Service not healthy: $status"
        return 1
    fi

    # Check for module field
    if ! echo "$response" | jq -e '.module' > /dev/null 2>&1; then
        log_error "Missing 'module' field"
        return 1
    fi

    # Check for version field
    if ! echo "$response" | jq -e '.version' > /dev/null 2>&1; then
        log_error "Missing 'version' field"
        return 1
    fi

    return 0
}

check_healthz_response() {
    local response="$1"

    # Check for status field
    if ! echo "$response" | jq -e '.status' > /dev/null 2>&1; then
        log_error "Missing 'status' field"
        return 1
    fi

    local status
    status=$(echo "$response" | jq -r '.status')

    # Status should be "healthy" or "degraded"
    if [[ "$status" != "healthy" ]] && [[ "$status" != "degraded" ]]; then
        log_error "Invalid status: $status (expected 'healthy' or 'degraded')"
        return 1
    fi

    # Check for checks field
    if ! echo "$response" | jq -e '.checks' > /dev/null 2>&1; then
        log_error "Missing 'checks' field"
        return 1
    fi

    return 0
}

check_quote_response() {
    local response="$1"

    # Check for success field (standardized API response)
    if ! echo "$response" | jq -e '.success' > /dev/null 2>&1; then
        log_error "Missing 'success' field"
        return 1
    fi

    # Check for data field
    if ! echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        log_error "Missing 'data' field"
        return 1
    fi

    return 0
}

check_quote_data_response() {
    local response="$1"

    # Check for data field with quote properties
    if ! echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        log_error "Missing 'data' field"
        return 1
    fi

    # Check for quote ID
    if ! echo "$response" | jq -e '.data.id' > /dev/null 2>&1; then
        log_error "Missing 'data.id' field"
        return 1
    fi

    # Store quote ID for later tests
    QUOTE_ID=$(echo "$response" | jq -r '.data.id')
    log_verbose "Stored quote ID: $QUOTE_ID"

    return 0
}

check_list_quotes_response() {
    local response="$1"

    # Check for data field
    if ! echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        log_error "Missing 'data' field"
        return 1
    fi

    # Check for quotes array
    if ! echo "$response" | jq -e '.data.quotes' > /dev/null 2>&1; then
        log_error "Missing 'data.quotes' field"
        return 1
    fi

    # Check for pagination
    if ! echo "$response" | jq -e '.data.pagination' > /dev/null 2>&1; then
        log_error "Missing 'data.pagination' field"
        return 1
    fi

    # Check for pagination fields
    if ! echo "$response" | jq -e '.data.pagination.limit' > /dev/null 2>&1; then
        log_error "Missing 'data.pagination.limit' field"
        return 1
    fi

    if ! echo "$response" | jq -e '.data.pagination.offset' > /dev/null 2>&1; then
        log_error "Missing 'data.pagination.offset' field"
        return 1
    fi

    if ! echo "$response" | jq -e '.data.pagination.total' > /dev/null 2>&1; then
        log_error "Missing 'data.pagination.total' field"
        return 1
    fi

    if ! echo "$response" | jq -e '.data.pagination.has_more' > /dev/null 2>&1; then
        log_error "Missing 'data.pagination.has_more' field"
        return 1
    fi

    return 0
}

check_search_quotes_response() {
    local response="$1"

    # Check for data field
    if ! echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        log_error "Missing 'data' field"
        return 1
    fi

    # Check for query field
    if ! echo "$response" | jq -e '.data.query' > /dev/null 2>&1; then
        log_error "Missing 'data.query' field"
        return 1
    fi

    # Check for quotes array
    if ! echo "$response" | jq -e '.data.quotes' > /dev/null 2>&1; then
        log_error "Missing 'data.quotes' field"
        return 1
    fi

    # Check for pagination
    if ! echo "$response" | jq -e '.data.pagination' > /dev/null 2>&1; then
        log_error "Missing 'data.pagination' field"
        return 1
    fi

    return 0
}

check_stats_response() {
    local response="$1"

    # Check for data field
    if ! echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        log_error "Missing 'data' field"
        return 1
    fi

    # Check for total_quotes field
    if ! echo "$response" | jq -e '.data.total_quotes' > /dev/null 2>&1; then
        log_error "Missing 'data.total_quotes' field"
        return 1
    fi

    # Check for approved_quotes field
    if ! echo "$response" | jq -e '.data.approved_quotes' > /dev/null 2>&1; then
        log_error "Missing 'data.approved_quotes' field"
        return 1
    fi

    return 0
}

check_status_response() {
    local response="$1"

    # Check for success field (standardized API response)
    if ! echo "$response" | jq -e '.success' > /dev/null 2>&1; then
        log_error "Missing 'success' field"
        return 1
    fi

    local success
    success=$(echo "$response" | jq -r '.success')
    if [[ "$success" != "true" ]]; then
        log_error "Response indicates failure: success=$success"
        return 1
    fi

    # Check for data field
    if ! echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        log_error "Missing 'data' field"
        return 1
    fi

    # Check for status field in data
    if ! echo "$response" | jq -e '.data.status' > /dev/null 2>&1; then
        log_error "Missing 'data.status' field"
        return 1
    fi

    local status
    status=$(echo "$response" | jq -r '.data.status')

    if [[ "$status" != "operational" ]]; then
        log_error "Service not operational: $status"
        return 1
    fi

    # Check for module field in data
    if ! echo "$response" | jq -e '.data.module' > /dev/null 2>&1; then
        log_error "Missing 'data.module' field"
        return 1
    fi

    return 0
}

################################################################################
# Test Cases - Health
################################################################################

test_health() {
    run_test \
        "GET /health" \
        "GET" \
        "/health" \
        "" \
        "200" \
        "false" \
        "check_health_response"
}

test_healthz() {
    run_test \
        "GET /healthz" \
        "GET" \
        "/healthz" \
        "" \
        "200" \
        "false" \
        "check_healthz_response"
}

test_metrics() {
    run_test \
        "GET /metrics" \
        "GET" \
        "/metrics" \
        "" \
        "200" \
        "false"
}

################################################################################
# Test Cases - API Status
################################################################################

test_api_status() {
    run_test \
        "GET /api/v1/status" \
        "GET" \
        "/api/v1/status" \
        "" \
        "200" \
        "false" \
        "check_status_response"
}

################################################################################
# Test Cases - Quote Operations
################################################################################

test_add_quote() {
    local data='{"community_id":1,"text":"This is a test quote","author":"Test Author","platform":"test","is_approved":true}'
    run_test \
        "POST /api/v1/quotes (Add quote)" \
        "POST" \
        "/api/v1/quotes" \
        "$data" \
        "201" \
        "false" \
        "check_quote_data_response"
}

test_get_quote() {
    if [[ -z "$QUOTE_ID" ]]; then
        log_skip "GET /api/v1/quotes/{id} (no quote ID)"
        ((TESTS_SKIPPED++))
        return 0
    fi

    run_test \
        "GET /api/v1/quotes/$QUOTE_ID" \
        "GET" \
        "/api/v1/quotes/$QUOTE_ID" \
        "" \
        "200" \
        "false" \
        "check_quote_response"
}

test_get_random_quote() {
    run_test \
        "GET /api/v1/quotes/random/1 (Get random quote)" \
        "GET" \
        "/api/v1/quotes/random/1" \
        "" \
        "200" \
        "false" \
        "check_quote_response"
}

test_list_quotes() {
    run_test \
        "GET /api/v1/quotes/list/1 (List quotes)" \
        "GET" \
        "/api/v1/quotes/list/1" \
        "" \
        "200" \
        "false" \
        "check_list_quotes_response"
}

test_list_quotes_with_pagination() {
    run_test \
        "GET /api/v1/quotes/list/1?limit=10&offset=0 (List with pagination)" \
        "GET" \
        "/api/v1/quotes/list/1?limit=10&offset=0" \
        "" \
        "200" \
        "false" \
        "check_list_quotes_response"
}

test_list_quotes_approved_only() {
    run_test \
        "GET /api/v1/quotes/list/1?approved=true (List approved quotes)" \
        "GET" \
        "/api/v1/quotes/list/1?approved=true" \
        "" \
        "200" \
        "false" \
        "check_list_quotes_response"
}

test_search_quotes() {
    run_test \
        "GET /api/v1/quotes/search/1?q=test (Search quotes)" \
        "GET" \
        "/api/v1/quotes/search/1?q=test" \
        "" \
        "200" \
        "false" \
        "check_search_quotes_response"
}

test_search_quotes_with_pagination() {
    run_test \
        "GET /api/v1/quotes/search/1?q=quote&limit=5&offset=0 (Search with pagination)" \
        "GET" \
        "/api/v1/quotes/search/1?q=quote&limit=5&offset=0" \
        "" \
        "200" \
        "false" \
        "check_search_quotes_response"
}

test_search_quotes_short_query() {
    run_test \
        "GET /api/v1/quotes/search/1?q=a (Search with short query - should fail)" \
        "GET" \
        "/api/v1/quotes/search/1?q=a" \
        "" \
        "400" \
        "false"
}

test_get_quotes_by_author() {
    run_test \
        "GET /api/v1/quotes/author/1?author=Test (Get by author)" \
        "GET" \
        "/api/v1/quotes/author/1?author=Test" \
        "" \
        "200" \
        "false" \
        "check_list_quotes_response"
}

test_update_quote() {
    if [[ -z "$QUOTE_ID" ]]; then
        log_skip "PUT /api/v1/quotes/{id} (no quote ID)"
        ((TESTS_SKIPPED++))
        return 0
    fi

    local data='{"text":"Updated quote text","author":"Updated Author"}'
    run_test \
        "PUT /api/v1/quotes/$QUOTE_ID (Update quote)" \
        "PUT" \
        "/api/v1/quotes/$QUOTE_ID" \
        "$data" \
        "200" \
        "false" \
        "check_quote_response"
}

test_delete_quote() {
    if [[ -z "$QUOTE_ID" ]]; then
        log_skip "DELETE /api/v1/quotes/{id} (no quote ID)"
        ((TESTS_SKIPPED++))
        return 0
    fi

    run_test \
        "DELETE /api/v1/quotes/$QUOTE_ID (Delete quote)" \
        "DELETE" \
        "/api/v1/quotes/$QUOTE_ID" \
        "" \
        "200" \
        "false" \
        "check_quote_response"
}

################################################################################
# Test Cases - Statistics
################################################################################

test_quote_stats() {
    run_test \
        "GET /api/v1/quotes/stats/1 (Get quote stats)" \
        "GET" \
        "/api/v1/quotes/stats/1" \
        "" \
        "200" \
        "false" \
        "check_stats_response"
}

################################################################################
# Test Cases - Error Handling
################################################################################

test_invalid_endpoint() {
    run_test \
        "GET /api/v1/nonexistent (404 Not Found)" \
        "GET" \
        "/api/v1/nonexistent" \
        "" \
        "404" \
        "false"
}

test_invalid_method() {
    run_test \
        "DELETE /api/v1/status (405 Method Not Allowed)" \
        "DELETE" \
        "/api/v1/status" \
        "" \
        "405" \
        "false"
}

test_missing_required_fields() {
    local data='{"community_id":1}'
    run_test \
        "POST /api/v1/quotes (Missing required field)" \
        "POST" \
        "/api/v1/quotes" \
        "$data" \
        "400" \
        "false"
}

test_get_nonexistent_quote() {
    run_test \
        "GET /api/v1/quotes/99999 (Get nonexistent quote)" \
        "GET" \
        "/api/v1/quotes/99999" \
        "" \
        "404" \
        "false"
}

################################################################################
# Main Execution
################################################################################

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                print_help
                exit 0
                ;;
            --url)
                QUOTE_URL="$2"
                shift 2
                ;;
            --api-key)
                QUOTE_API_KEY="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE="true"
                shift
                ;;
            --skip-auth)
                SKIP_AUTH="true"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done

    # Check requirements
    check_requirements

    # Print test configuration
    echo ""
    log_info "======================================================================"
    log_info "WaddleBot Quote Interaction Module API Test Suite"
    log_info "======================================================================"
    log_info "Quote Module URL: $QUOTE_URL"
    log_info "API Key: ${QUOTE_API_KEY:+[SET]}${QUOTE_API_KEY:-[NOT SET]}"
    log_info "Verbose: $VERBOSE"
    log_info "Skip Auth Tests: $SKIP_AUTH"
    log_info "======================================================================"
    echo ""

    # Run tests
    log_info "Running Health & Metrics Tests..."
    test_health
    test_healthz
    test_metrics
    echo ""

    log_info "Running API Status Tests..."
    test_api_status
    echo ""

    log_info "Running Quote Operations Tests..."
    test_add_quote
    test_get_quote
    test_get_random_quote
    test_list_quotes
    test_list_quotes_with_pagination
    test_list_quotes_approved_only
    test_update_quote
    test_delete_quote
    echo ""

    log_info "Running Search & Filter Tests..."
    test_search_quotes
    test_search_quotes_with_pagination
    test_search_quotes_short_query
    test_get_quotes_by_author
    echo ""

    log_info "Running Statistics Tests..."
    test_quote_stats
    echo ""

    log_info "Running Error Handling Tests..."
    test_invalid_endpoint
    test_invalid_method
    test_missing_required_fields
    test_get_nonexistent_quote
    echo ""

    # Print summary
    echo ""
    log_info "======================================================================"
    log_info "Test Summary"
    log_info "======================================================================"
    log_info "Total Tests:  $TESTS_RUN"
    log_success "Passed:       $TESTS_PASSED"
    log_error "Failed:       $TESTS_FAILED"
    log_skip "Skipped:      $TESTS_SKIPPED"
    log_info "======================================================================"
    echo ""

    # Print module information
    echo -e "${BLUE}Module Information:${NC}"
    echo -e "  URL: ${QUOTE_URL}"
    echo -e "  Module: quote_interaction_module"
    echo -e "  Expected Port: 5012"
    echo -e "  Database: PostgreSQL"
    echo ""

    # Exit with appropriate code
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Some tests failed!"
        exit 1
    else
        log_success "All tests passed!"
        exit 0
    fi
}

# Run main function
main "$@"
