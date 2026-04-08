#!/bin/bash
#
# WaddleBot Twitch Module - API Test Script
#
# Comprehensive test suite for the Twitch receiver module API endpoints.
# Tests health checks, metrics, and module-specific APIs.
#
# Usage:
#   ./test-api.sh [OPTIONS]
#
# Options:
#   --help              Show this help message
#   --url URL           Override base URL (default: http://localhost:8002)
#   --verbose           Enable verbose curl output
#   --no-color          Disable colored output
#   --timeout SECONDS   Set request timeout (default: 10)
#
# Environment Variables:
#   TWITCH_URL          Base URL for Twitch module (default: http://localhost:8002)
#   TEST_TIMEOUT        Request timeout in seconds (default: 10)
#
# Exit Codes:
#   0 - All tests passed
#   1 - One or more tests failed
#
# Requirements:
#   - curl (for HTTP requests)
#   - jq (for JSON parsing)
#

set -eo pipefail

#=============================================================================
# Configuration & Colors
#=============================================================================

# Default configuration
TWITCH_URL="${TWITCH_URL:-http://localhost:8002}"
TEST_TIMEOUT="${TEST_TIMEOUT:-10}"
VERBOSE=false
USE_COLOR=true

# Color codes
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    BOLD=''
    RESET=''
fi

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
TESTS_TOTAL=0

#=============================================================================
# Helper Functions
#=============================================================================

# Print colored output
print_color() {
    local color=$1
    shift
    if [[ "$USE_COLOR" == "true" ]]; then
        echo -e "${color}$*${RESET}"
    else
        echo "$*"
    fi
}

# Print help message
show_help() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
    exit 0
}

# Check required dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_color "$RED" "ERROR: Missing required dependencies: ${missing_deps[*]}"
        print_color "$YELLOW" "Please install missing dependencies:"
        print_color "$YELLOW" "  Ubuntu/Debian: sudo apt-get install ${missing_deps[*]}"
        print_color "$YELLOW" "  MacOS: brew install ${missing_deps[*]}"
        exit 1
    fi
}

# Test a single endpoint
test_endpoint() {
    local test_name=$1
    local method=$2
    local endpoint=$3
    local expected_status=$4
    local json_checks=$5  # Optional: jq filter to validate JSON response

    TESTS_TOTAL=$((TESTS_TOTAL + 1))

    print_color "$CYAN" "Testing: $test_name"

    local url="${TWITCH_URL}${endpoint}"
    local curl_opts=(-s -w "\n%{http_code}" -X "$method" --max-time "$TEST_TIMEOUT")

    if [[ "$VERBOSE" == "true" ]]; then
        curl_opts+=(-v)
    fi

    # Make request
    local response
    local http_code
    local curl_exit_code=0

    response=$(curl "${curl_opts[@]}" "$url" 2>&1) || curl_exit_code=$?

    if [[ $curl_exit_code -ne 0 ]]; then
        print_color "$RED" "  ✗ FAIL: Connection failed (curl exit code: $curl_exit_code)"
        print_color "$RED" "    URL: $url"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    # Extract HTTP code (last line) and body (everything else)
    http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | sed '$d')

    # Check HTTP status code
    if [[ "$http_code" != "$expected_status" ]]; then
        print_color "$RED" "  ✗ FAIL: Expected HTTP $expected_status, got $http_code"
        print_color "$RED" "    URL: $url"
        print_color "$RED" "    Response: $body"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    # Validate JSON structure if checks provided
    if [[ -n "$json_checks" ]]; then
        local json_result
        json_result=$(echo "$body" | jq -r "$json_checks" 2>&1) || {
            print_color "$RED" "  ✗ FAIL: JSON validation failed"
            print_color "$RED" "    URL: $url"
            print_color "$RED" "    jq filter: $json_checks"
            print_color "$RED" "    Response: $body"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        }

        if [[ "$json_result" == "null" ]] || [[ "$json_result" == "false" ]]; then
            print_color "$RED" "  ✗ FAIL: JSON check returned null/false"
            print_color "$RED" "    URL: $url"
            print_color "$RED" "    jq filter: $json_checks"
            print_color "$RED" "    Result: $json_result"
            print_color "$RED" "    Response: $body"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    fi

    print_color "$GREEN" "  ✓ PASS (HTTP $http_code)"
    if [[ "$VERBOSE" == "true" ]] && [[ -n "$body" ]]; then
        print_color "$BLUE" "    Response: $body"
    fi

    TESTS_PASSED=$((TESTS_PASSED + 1))
    return 0
}

# Print test summary
print_summary() {
    echo ""
    print_color "$BOLD" "═══════════════════════════════════════════════════════════"
    print_color "$BOLD" "                      TEST SUMMARY"
    print_color "$BOLD" "═══════════════════════════════════════════════════════════"

    local pass_color="$GREEN"
    local fail_color="$RED"
    local skip_color="$YELLOW"

    echo -e "${BOLD}Total Tests:${RESET}    $TESTS_TOTAL"
    echo -e "${pass_color}Passed:${RESET}         $TESTS_PASSED"
    echo -e "${fail_color}Failed:${RESET}         $TESTS_FAILED"
    echo -e "${skip_color}Skipped:${RESET}        $TESTS_SKIPPED"

    print_color "$BOLD" "═══════════════════════════════════════════════════════════"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        print_color "$GREEN" "✓ All tests passed!"
        return 0
    else
        print_color "$RED" "✗ Some tests failed"
        return 1
    fi
}

#=============================================================================
# Parse Command Line Arguments
#=============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            ;;
        --url)
            TWITCH_URL="$2"
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
            RESET=''
            shift
            ;;
        --timeout)
            TEST_TIMEOUT="$2"
            shift 2
            ;;
        *)
            print_color "$RED" "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

#=============================================================================
# Pre-flight Checks
#=============================================================================

print_color "$BOLD" "═══════════════════════════════════════════════════════════"
print_color "$BOLD" "     WaddleBot Twitch Module - API Test Suite"
print_color "$BOLD" "═══════════════════════════════════════════════════════════"
echo ""

check_dependencies

print_color "$CYAN" "Configuration:"
echo "  Base URL:        $TWITCH_URL"
echo "  Request Timeout: ${TEST_TIMEOUT}s"
echo "  Verbose Mode:    $VERBOSE"
echo "  Colored Output:  $USE_COLOR"
echo ""

#=============================================================================
# Test Suite
#=============================================================================

print_color "$BOLD" "Starting API tests..."
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Health Check Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print_color "$BOLD" "┌─ Health Check Endpoints"
echo ""

test_endpoint \
    "GET /health - Basic health check" \
    "GET" \
    "/health" \
    "200" \
    '.status == "healthy" and .module == "twitch_module" and .version != null and .timestamp != null'

test_endpoint \
    "GET /healthz - Kubernetes readiness probe" \
    "GET" \
    "/healthz" \
    "200" \
    '.status != null and .module == "twitch_module" and .version != null and .checks != null'

test_endpoint \
    "GET /metrics - Prometheus metrics" \
    "GET" \
    "/metrics" \
    "200" \
    'contains("waddlebot_info") and contains("twitch_module")'

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print_color "$BOLD" "┌─ API Endpoints"
echo ""

test_endpoint \
    "GET /api/v1/status - Module status" \
    "GET" \
    "/api/v1/status" \
    "200" \
    '.status == "operational" and .module == "twitch_module"'

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Error Handling Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print_color "$BOLD" "┌─ Error Handling"
echo ""

test_endpoint \
    "GET /nonexistent - 404 for invalid endpoint" \
    "GET" \
    "/nonexistent" \
    "404"

test_endpoint \
    "POST /health - Method not allowed" \
    "POST" \
    "/health" \
    "405"

echo ""

#=============================================================================
# Print Summary and Exit
#=============================================================================

print_summary
exit_code=$?

exit $exit_code
