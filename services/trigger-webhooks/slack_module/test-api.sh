#!/bin/bash

################################################################################
# WaddleBot Slack Module API Test Script
################################################################################
#
# Comprehensive API testing script for the Slack Module (slack_module)
#
# Usage:
#   ./test-api.sh [options]
#
# Options:
#   --help              Show this help message
#   --url URL           Set base URL (default: http://localhost:8004)
#   --verbose           Enable verbose curl output
#   --no-color          Disable colored output
#
# Environment Variables:
#   SLACK_URL           Base URL for Slack module (default: http://localhost:8004)
#   NO_COLOR            Disable colored output if set to 1
#
# Exit Codes:
#   0 - All tests passed
#   1 - One or more tests failed
#
################################################################################

set -euo pipefail

################################################################################
# Configuration
################################################################################

# Default values
SLACK_URL="${SLACK_URL:-http://localhost:8004}"
VERBOSE=false
USE_COLOR=true

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
TOTAL_TESTS=0

# Temp file for response storage
RESPONSE_FILE=$(mktemp)
HEADERS_FILE=$(mktemp)

# Cleanup on exit
trap 'rm -f "$RESPONSE_FILE" "$HEADERS_FILE"' EXIT

################################################################################
# Color Codes
################################################################################

if [[ "${NO_COLOR:-0}" == "1" ]]; then
    USE_COLOR=false
fi

if [[ "$USE_COLOR" == "true" ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    BOLD=''
    NC=''
fi

################################################################################
# Helper Functions
################################################################################

print_banner() {
    echo -e "${BOLD}${CYAN}"
    echo "════════════════════════════════════════════════════════════════════"
    echo "  WaddleBot Slack Module API Test Suite"
    echo "════════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${BLUE}Target URL:${NC} $SLACK_URL"
    echo -e "${BLUE}Timestamp:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
}

print_help() {
    sed -n '/^# Usage:/,/^################################################################################$/p' "$0" | sed 's/^# \?//'
    exit 0
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $*"
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $*"
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

print_separator() {
    echo -e "${CYAN}────────────────────────────────────────────────────────────────────${NC}"
}

print_summary() {
    echo ""
    echo -e "${BOLD}${CYAN}"
    echo "════════════════════════════════════════════════════════════════════"
    echo "  Test Summary"
    echo "════════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${BOLD}Total Tests:${NC}   $TOTAL_TESTS"
    echo -e "${GREEN}${BOLD}Passed:${NC}        $TESTS_PASSED"
    echo -e "${RED}${BOLD}Failed:${NC}        $TESTS_FAILED"
    echo -e "${YELLOW}${BOLD}Skipped:${NC}       $TESTS_SKIPPED"
    echo ""

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}✓ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}${BOLD}✗ Some tests failed!${NC}"
        return 1
    fi
}

################################################################################
# HTTP Request Functions
################################################################################

make_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local description="$4"

    ((TOTAL_TESTS++))

    log_info "Testing: $description"

    local curl_opts=(-s -w "\n%{http_code}" -o "$RESPONSE_FILE" -D "$HEADERS_FILE")

    if [[ "$VERBOSE" == "true" ]]; then
        curl_opts+=(-v)
    fi

    # Build curl command
    local url="${SLACK_URL}${endpoint}"

    if [[ -n "$data" ]]; then
        curl_opts+=(-X "$method" -H "Content-Type: application/json" -d "$data")
    else
        curl_opts+=(-X "$method")
    fi

    # Execute request
    local http_response
    http_response=$(curl "${curl_opts[@]}" "$url" 2>&1 || echo "000")

    # Extract HTTP status code (last line)
    local http_code
    http_code=$(echo "$http_response" | tail -n1)

    # Read response body
    local response_body
    response_body=$(cat "$RESPONSE_FILE")

    echo "$http_code" "$response_body"
}

test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local expected_status="$3"
    local description="$4"
    local data="${5:-}"
    local validate_json="${6:-true}"

    log_info "${BOLD}${method}${NC} ${endpoint}"

    # Make request
    local result
    result=$(make_request "$method" "$endpoint" "$data" "$description")

    local http_code
    http_code=$(echo "$result" | awk '{print $1}')

    local response_body
    response_body=$(echo "$result" | cut -d' ' -f2-)

    # Check if request failed completely
    if [[ "$http_code" == "000" ]]; then
        log_failure "$description - Connection failed"
        ((TESTS_FAILED++))
        if [[ "$VERBOSE" == "true" ]]; then
            echo "  Response: $response_body"
        fi
        return 1
    fi

    # Validate status code
    local status_match=false
    if [[ "$http_code" == "$expected_status" ]]; then
        status_match=true
    fi

    # Validate JSON if requested
    local json_valid=true
    if [[ "$validate_json" == "true" ]]; then
        if ! echo "$response_body" | jq empty 2>/dev/null; then
            json_valid=false
        fi
    fi

    # Determine test result
    if [[ "$status_match" == "true" ]] && [[ "$json_valid" == "true" ]]; then
        log_success "$description (HTTP $http_code)"
        ((TESTS_PASSED++))

        if [[ "$VERBOSE" == "true" ]]; then
            echo "  Response body:"
            echo "$response_body" | jq '.' 2>/dev/null || echo "$response_body"
        fi

        return 0
    else
        log_failure "$description"
        ((TESTS_FAILED++))

        if [[ "$status_match" == "false" ]]; then
            echo "  Expected HTTP $expected_status, got HTTP $http_code"
        fi

        if [[ "$json_valid" == "false" ]]; then
            echo "  Invalid JSON response"
        fi

        echo "  Response body:"
        echo "$response_body" | jq '.' 2>/dev/null || echo "$response_body"

        return 1
    fi
}

test_json_field() {
    local endpoint="$1"
    local field_path="$2"
    local expected_value="$3"
    local description="$4"

    ((TOTAL_TESTS++))

    log_info "Testing: $description"

    # Make request
    local result
    result=$(make_request "GET" "$endpoint" "" "$description")

    local http_code
    http_code=$(echo "$result" | awk '{print $1}')

    local response_body
    response_body=$(echo "$result" | cut -d' ' -f2-)

    # Check if request succeeded
    if [[ "$http_code" != "200" ]]; then
        log_failure "$description - HTTP $http_code"
        ((TESTS_FAILED++))
        return 1
    fi

    # Extract field value
    local actual_value
    actual_value=$(echo "$response_body" | jq -r "$field_path" 2>/dev/null)

    if [[ $? -ne 0 ]]; then
        log_failure "$description - Failed to extract field '$field_path'"
        ((TESTS_FAILED++))
        return 1
    fi

    # Compare values
    if [[ "$actual_value" == "$expected_value" ]]; then
        log_success "$description: $field_path = $actual_value"
        ((TESTS_PASSED++))
        return 0
    else
        log_failure "$description: Expected '$expected_value', got '$actual_value'"
        ((TESTS_FAILED++))
        return 1
    fi
}

################################################################################
# Test Functions
################################################################################

test_health_endpoints() {
    print_separator
    echo -e "${BOLD}Testing Health Endpoints${NC}"
    print_separator

    # Test /health endpoint
    test_endpoint "GET" "/health" "200" "Basic health check endpoint" "" "true"
    test_json_field "/health" ".status" "healthy" "Health endpoint returns 'healthy' status"
    test_json_field "/health" ".module" "slack_module" "Health endpoint returns correct module name"

    # Test /healthz endpoint (Kubernetes readiness/liveness)
    test_endpoint "GET" "/healthz" "200" "Kubernetes health probe endpoint" "" "true"
    test_json_field "/healthz" ".status" "healthy" "Healthz endpoint returns 'healthy' status"
    test_json_field "/healthz" ".module" "slack_module" "Healthz endpoint returns correct module name"
    test_json_field "/healthz" ".checks.memory" "ok" "Healthz endpoint checks memory"
    test_json_field "/healthz" ".checks.cpu" "ok" "Healthz endpoint checks CPU"
}

test_metrics_endpoints() {
    print_separator
    echo -e "${BOLD}Testing Metrics Endpoints${NC}"
    print_separator

    # Test /metrics endpoint (Prometheus format)
    test_endpoint "GET" "/metrics" "200" "Prometheus metrics endpoint" "" "false"

    # Validate metrics format
    ((TOTAL_TESTS++))
    log_info "Validating Prometheus metrics format"

    local result
    result=$(make_request "GET" "/metrics" "" "Metrics format validation")

    local response_body
    response_body=$(echo "$result" | cut -d' ' -f2-)

    # Check for required metric lines
    local metrics_valid=true
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

    for metric in "${required_metrics[@]}"; do
        if ! echo "$response_body" | grep -q "$metric"; then
            log_warning "  Missing metric: $metric"
            metrics_valid=false
        fi
    done

    if [[ "$metrics_valid" == "true" ]]; then
        log_success "Prometheus metrics format validation"
        ((TESTS_PASSED++))
    else
        log_failure "Prometheus metrics format validation - Missing required metrics"
        ((TESTS_FAILED++))
    fi
}

test_api_endpoints() {
    print_separator
    echo -e "${BOLD}Testing API Endpoints${NC}"
    print_separator

    # Test /api/v1/status endpoint
    test_endpoint "GET" "/api/v1/status" "200" "API status endpoint" "" "true"
    test_json_field "/api/v1/status" ".success" "true" "API status returns success"
    test_json_field "/api/v1/status" ".data.status" "operational" "API status is operational"
    test_json_field "/api/v1/status" ".data.module" "slack_module" "API status returns correct module name"
}

test_invalid_endpoints() {
    print_separator
    echo -e "${BOLD}Testing Invalid Endpoints${NC}"
    print_separator

    # Test 404 for non-existent endpoint
    test_endpoint "GET" "/api/v1/nonexistent" "404" "Non-existent endpoint returns 404" "" "false"

    # Test 404 for invalid path
    test_endpoint "GET" "/invalid/path" "404" "Invalid path returns 404" "" "false"
}

test_http_methods() {
    print_separator
    echo -e "${BOLD}Testing HTTP Methods${NC}"
    print_separator

    # Test unsupported method on GET-only endpoint
    test_endpoint "POST" "/health" "405" "POST to GET-only endpoint returns 405" "" "false"
    test_endpoint "PUT" "/health" "405" "PUT to GET-only endpoint returns 405" "" "false"
    test_endpoint "DELETE" "/health" "405" "DELETE to GET-only endpoint returns 405" "" "false"
}

################################################################################
# Main Execution
################################################################################

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                print_help
                ;;
            --url)
                SLACK_URL="$2"
                shift 2
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --no-color)
                USE_COLOR=false
                RED=''
                GREEN=''
                YELLOW=''
                BLUE=''
                CYAN=''
                BOLD=''
                NC=''
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

check_dependencies() {
    local missing_deps=()

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo -e "${RED}Error: Missing required dependencies:${NC}"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        echo ""
        echo "Please install missing dependencies and try again."
        exit 1
    fi
}

check_service_availability() {
    log_info "Checking if Slack module is available at $SLACK_URL"

    if ! curl -s -f -o /dev/null --connect-timeout 5 "$SLACK_URL/health"; then
        log_failure "Cannot connect to Slack module at $SLACK_URL"
        echo ""
        echo "Please ensure:"
        echo "  1. The Slack module is running"
        echo "  2. The URL is correct (use --url or set SLACK_URL environment variable)"
        echo "  3. No firewall is blocking the connection"
        echo ""
        exit 1
    fi

    log_success "Slack module is available"
    echo ""
}

main() {
    parse_args "$@"

    print_banner

    check_dependencies
    check_service_availability

    # Run all test suites
    test_health_endpoints
    test_metrics_endpoints
    test_api_endpoints
    test_invalid_endpoints
    test_http_methods

    # Print summary
    print_summary

    # Return appropriate exit code
    if [[ $TESTS_FAILED -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
