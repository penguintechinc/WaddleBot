#!/usr/bin/env bash
################################################################################
# WaddleBot Browser Source Core Module API Test Script
################################################################################
# Tests all API endpoints for the Browser Source Core Module
# Exit code: 0 if all tests pass, 1 if any fail
################################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
PASS=0
FAIL=0
SKIP=0
TOTAL=0

# Configuration
BASE_URL="${BROWSER_SOURCE_URL:-http://localhost:8052}"
VERBOSE="${VERBOSE:-false}"

# Helper functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  WaddleBot Browser Source Core Module API Test Suite          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_test() {
    local test_name="$1"
    ((TOTAL++))
    echo -e "${BLUE}[TEST ${TOTAL}]${NC} ${test_name}"
}

print_pass() {
    local message="$1"
    ((PASS++))
    echo -e "  ${GREEN}✓ PASS${NC} - ${message}"
}

print_fail() {
    local message="$1"
    ((FAIL++))
    echo -e "  ${RED}✗ FAIL${NC} - ${message}"
}

print_skip() {
    local message="$1"
    ((SKIP++))
    echo -e "  ${YELLOW}⊘ SKIP${NC} - ${message}"
}

print_summary() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Test Summary                                                  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo -e "Total Tests:  ${TOTAL}"
    echo -e "${GREEN}Passed:       ${PASS}${NC}"
    echo -e "${RED}Failed:       ${FAIL}${NC}"
    echo -e "${YELLOW}Skipped:      ${SKIP}${NC}"
    echo ""

    if [ $FAIL -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        return 1
    fi
}

show_help() {
    cat << EOF
WaddleBot Browser Source Core Module API Test Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -u, --url URL          Set base URL (default: http://localhost:8052)
    -v, --verbose          Enable verbose output
    --skip-health          Skip health check tests
    --skip-api             Skip API endpoint tests

Environment Variables:
    BROWSER_SOURCE_URL     Base URL for the module (default: http://localhost:8052)
    VERBOSE                Enable verbose output (true/false)

Examples:
    # Run all tests with default settings
    $0

    # Run tests against remote server
    $0 -u http://browser-source:8052

    # Run with verbose output
    $0 -v

    # Run with custom URL via environment variable
    BROWSER_SOURCE_URL=http://localhost:9000 $0

Exit Codes:
    0 - All tests passed
    1 - One or more tests failed

EOF
    exit 0
}

check_dependencies() {
    local missing_deps=()

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${RED}Error: Missing required dependencies: ${missing_deps[*]}${NC}"
        echo "Please install them and try again."
        exit 1
    fi
}

verbose_log() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${YELLOW}[VERBOSE]${NC} $1"
    fi
}

# Make HTTP request with error handling
http_get() {
    local endpoint="$1"
    local expected_code="${2:-200}"
    local url="${BASE_URL}${endpoint}"

    verbose_log "GET ${url}"

    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" "${url}" 2>&1)
    http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    verbose_log "HTTP Code: ${http_code}"
    verbose_log "Response Body: ${body}"

    if [ "$http_code" != "$expected_code" ]; then
        return 1
    fi

    echo "$body"
    return 0
}

# Validate JSON response
validate_json() {
    local json="$1"

    if ! echo "$json" | jq empty 2>/dev/null; then
        return 1
    fi
    return 0
}

# Test: Server reachability
test_server_reachable() {
    print_test "Server Reachability"

    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${BASE_URL}/health" | grep -q "200\|503"; then
        print_pass "Server is reachable at ${BASE_URL}"
        return 0
    else
        print_fail "Server is not reachable at ${BASE_URL}"
        return 1
    fi
}

# Test: /health endpoint
test_health() {
    print_test "GET /health - Basic health check"

    local response
    if ! response=$(http_get "/health" 200); then
        print_fail "Health endpoint returned non-200 status"
        return 1
    fi

    if ! validate_json "$response"; then
        print_fail "Response is not valid JSON"
        return 1
    fi

    local status=$(echo "$response" | jq -r '.status')
    if [ "$status" != "healthy" ]; then
        print_fail "Health status is not 'healthy': ${status}"
        return 1
    fi

    local module=$(echo "$response" | jq -r '.module')
    if [ "$module" != "browser_source_core_module" ]; then
        print_fail "Module name mismatch: ${module}"
        return 1
    fi

    local version=$(echo "$response" | jq -r '.version')
    if [ -z "$version" ] || [ "$version" = "null" ]; then
        print_fail "Version is missing or null"
        return 1
    fi

    local timestamp=$(echo "$response" | jq -r '.timestamp')
    if [ -z "$timestamp" ] || [ "$timestamp" = "null" ]; then
        print_fail "Timestamp is missing or null"
        return 1
    fi

    print_pass "Health endpoint returns valid response (version: ${version})"
    return 0
}

# Test: /healthz endpoint
test_healthz() {
    print_test "GET /healthz - Kubernetes liveness/readiness probe"

    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" "${BASE_URL}/healthz" 2>&1)
    http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    verbose_log "HTTP Code: ${http_code}"
    verbose_log "Response Body: ${body}"

    # Accept 200 (healthy) or 503 (degraded)
    if [ "$http_code" != "200" ] && [ "$http_code" != "503" ]; then
        print_fail "Healthz endpoint returned unexpected status: ${http_code}"
        return 1
    fi

    if ! validate_json "$body"; then
        print_fail "Response is not valid JSON"
        return 1
    fi

    local status=$(echo "$body" | jq -r '.status')
    if [ "$status" != "healthy" ] && [ "$status" != "degraded" ] && [ "$status" != "unhealthy" ]; then
        print_fail "Invalid health status: ${status}"
        return 1
    fi

    local module=$(echo "$body" | jq -r '.module')
    if [ "$module" != "browser_source_core_module" ]; then
        print_fail "Module name mismatch: ${module}"
        return 1
    fi

    # Check for required checks object
    local checks=$(echo "$body" | jq -r '.checks')
    if [ "$checks" = "null" ]; then
        print_fail "Health checks object is missing"
        return 1
    fi

    print_pass "Healthz endpoint returns valid response (status: ${status}, code: ${http_code})"
    return 0
}

# Test: /metrics endpoint
test_metrics() {
    print_test "GET /metrics - Prometheus metrics endpoint"

    local response
    if ! response=$(curl -s "${BASE_URL}/metrics" 2>&1); then
        print_fail "Failed to fetch metrics endpoint"
        return 1
    fi

    verbose_log "Metrics response length: ${#response} bytes"

    # Check for Prometheus format headers
    if ! echo "$response" | grep -q "# HELP"; then
        print_fail "Metrics response missing Prometheus format headers"
        return 1
    fi

    if ! echo "$response" | grep -q "# TYPE"; then
        print_fail "Metrics response missing Prometheus type definitions"
        return 1
    fi

    # Check for required metrics
    local required_metrics=(
        "waddlebot_info"
        "waddlebot_requests_total"
        "waddlebot_requests_success_total"
        "waddlebot_requests_error_total"
        "waddlebot_request_duration_seconds"
        "waddlebot_memory_bytes"
        "waddlebot_cpu_percent"
        "waddlebot_open_files"
        "waddlebot_threads"
    )

    local missing_metrics=()
    for metric in "${required_metrics[@]}"; do
        if ! echo "$response" | grep -q "$metric"; then
            missing_metrics+=("$metric")
        fi
    done

    if [ ${#missing_metrics[@]} -ne 0 ]; then
        print_fail "Missing required metrics: ${missing_metrics[*]}"
        return 1
    fi

    # Check for module label
    if ! echo "$response" | grep -q 'module="browser_source_core_module"'; then
        print_fail "Metrics missing module label"
        return 1
    fi

    print_pass "Metrics endpoint returns valid Prometheus format"
    return 0
}

# Test: /api/v1/status endpoint
test_api_status() {
    print_test "GET /api/v1/status - Module status endpoint"

    local response
    if ! response=$(http_get "/api/v1/status" 200); then
        print_fail "Status endpoint returned non-200 status"
        return 1
    fi

    if ! validate_json "$response"; then
        print_fail "Response is not valid JSON"
        return 1
    fi

    local success=$(echo "$response" | jq -r '.success')
    if [ "$success" != "true" ]; then
        print_fail "Response success field is not true"
        return 1
    fi

    local status=$(echo "$response" | jq -r '.data.status')
    if [ "$status" != "operational" ]; then
        print_fail "Module status is not 'operational': ${status}"
        return 1
    fi

    local module=$(echo "$response" | jq -r '.data.module')
    if [ "$module" != "browser_source_core_module" ]; then
        print_fail "Module name mismatch: ${module}"
        return 1
    fi

    local timestamp=$(echo "$response" | jq -r '.timestamp')
    if [ -z "$timestamp" ] || [ "$timestamp" = "null" ]; then
        print_fail "Timestamp is missing or null"
        return 1
    fi

    print_pass "Status endpoint returns valid response"
    return 0
}

# Test: Invalid endpoint (404)
test_invalid_endpoint() {
    print_test "GET /api/v1/nonexistent - Invalid endpoint returns 404"

    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" "${BASE_URL}/api/v1/nonexistent" 2>&1)
    http_code=$(echo "$response" | tail -n1)

    verbose_log "HTTP Code: ${http_code}"

    if [ "$http_code" != "404" ]; then
        print_fail "Expected 404, got ${http_code}"
        return 1
    fi

    print_pass "Invalid endpoint correctly returns 404"
    return 0
}

# Test: Response format consistency
test_response_format() {
    print_test "Response Format Consistency - All API responses follow standard format"

    local response
    if ! response=$(http_get "/api/v1/status" 200); then
        print_fail "Failed to fetch status endpoint"
        return 1
    fi

    # Check for standard response fields
    local success=$(echo "$response" | jq -r '.success')
    local data=$(echo "$response" | jq -r '.data')
    local timestamp=$(echo "$response" | jq -r '.timestamp')

    if [ "$success" = "null" ]; then
        print_fail "Response missing 'success' field"
        return 1
    fi

    if [ "$data" = "null" ]; then
        print_fail "Response missing 'data' field"
        return 1
    fi

    if [ "$timestamp" = "null" ]; then
        print_fail "Response missing 'timestamp' field"
        return 1
    fi

    # Validate timestamp format (ISO 8601)
    if ! echo "$timestamp" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'; then
        print_fail "Timestamp not in ISO 8601 format: ${timestamp}"
        return 1
    fi

    print_pass "All responses follow standard format"
    return 0
}

# Parse command line arguments
SKIP_HEALTH=false
SKIP_API=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-health)
            SKIP_HEALTH=true
            shift
            ;;
        --skip-api)
            SKIP_API=true
            shift
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header

    echo "Configuration:"
    echo "  Base URL: ${BASE_URL}"
    echo "  Verbose:  ${VERBOSE}"
    echo ""

    check_dependencies

    # Run tests
    test_server_reachable || true

    if [ "$SKIP_HEALTH" = "false" ]; then
        test_health || true
        test_healthz || true
        test_metrics || true
    else
        ((TOTAL += 3))
        ((SKIP += 3))
        echo -e "${YELLOW}[SKIP]${NC} Health check tests skipped"
    fi

    if [ "$SKIP_API" = "false" ]; then
        test_api_status || true
        test_invalid_endpoint || true
        test_response_format || true
    else
        ((TOTAL += 3))
        ((SKIP += 3))
        echo -e "${YELLOW}[SKIP]${NC} API endpoint tests skipped"
    fi

    # Print summary and exit
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main
