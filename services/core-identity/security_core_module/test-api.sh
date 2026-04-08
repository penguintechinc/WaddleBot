#!/bin/bash
# Test API script for Security Core Module
# Tests all endpoints with proper error handling

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SECURITY_URL="${SECURITY_URL:-http://localhost:8041}"
COMMUNITY_ID="${COMMUNITY_ID:-1}"
VERBOSE="${VERBOSE:-false}"

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4

    print_info "Testing: $description"

    if [ "$VERBOSE" = "true" ]; then
        echo "  URL: $SECURITY_URL$endpoint"
        echo "  Method: $method"
        if [ -n "$data" ]; then
            echo "  Data: $data"
        fi
    fi

    if [ -n "$data" ]; then
        response=$(curl -s -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$SECURITY_URL$endpoint")
    else
        response=$(curl -s -X "$method" "$SECURITY_URL$endpoint")
    fi

    if [ "$VERBOSE" = "true" ]; then
        echo "  Response: $response"
    fi

    # Check if response contains "success": true
    if echo "$response" | grep -q '"success": *true'; then
        print_success "$description"
        return 0
    else
        print_error "$description"
        echo "  Response: $response"
        return 1
    fi
}

# Main test execution
main() {
    echo "========================================="
    echo "Security Core Module API Tests"
    echo "========================================="
    echo "URL: $SECURITY_URL"
    echo "Community ID: $COMMUNITY_ID"
    echo "========================================="
    echo

    # Test health endpoints
    print_info "Testing health endpoints..."
    api_call GET "/health" "" "Health check"
    api_call GET "/healthz" "" "Kubernetes health check"
    echo

    # Test public API endpoints
    print_info "Testing public API endpoints..."
    api_call GET "/api/v1/security/status" "" "Module status"
    api_call GET "/api/v1/security/$COMMUNITY_ID/config" "" "Get security config"
    api_call GET "/api/v1/security/$COMMUNITY_ID/warnings?status=active" "" "Get active warnings"
    api_call GET "/api/v1/security/$COMMUNITY_ID/filter-matches" "" "Get filter matches"
    api_call GET "/api/v1/security/$COMMUNITY_ID/moderation-log" "" "Get moderation log"
    echo

    # Test config update
    print_info "Testing config update..."
    api_call PUT "/api/v1/security/$COMMUNITY_ID/config" \
        '{"spam_detection_enabled": true, "spam_message_threshold": 10}' \
        "Update security config"
    echo

    # Test warning issuance
    print_info "Testing warning system..."
    api_call POST "/api/v1/security/$COMMUNITY_ID/warnings" \
        '{"platform": "discord", "platform_user_id": "123456", "warning_reason": "Test warning", "issued_by": 1}' \
        "Issue manual warning"
    echo

    # Test blocked words management
    print_info "Testing content filter..."
    api_call POST "/api/v1/security/$COMMUNITY_ID/blocked-words" \
        '{"words": ["testword1", "testword2"]}' \
        "Add blocked words"
    api_call DELETE "/api/v1/security/$COMMUNITY_ID/blocked-words" \
        '{"words": ["testword1"]}' \
        "Remove blocked words"
    echo

    # Test internal API endpoints
    print_info "Testing internal API endpoints..."
    api_call POST "/api/v1/internal/check" \
        '{"community_id": '"$COMMUNITY_ID"', "platform": "discord", "platform_user_id": "123456", "message": "Test message"}' \
        "Check message"
    api_call POST "/api/v1/internal/warn" \
        '{"community_id": '"$COMMUNITY_ID"', "platform": "discord", "platform_user_id": "123456", "warning_type": "spam", "warning_reason": "Auto-detected spam"}' \
        "Issue automated warning"
    api_call POST "/api/v1/internal/sync-action" \
        '{"community_id": '"$COMMUNITY_ID"', "platform": "discord", "platform_user_id": "123456", "action_type": "warn", "action_reason": "Spam detected", "sync_to_platforms": ["twitch"]}' \
        "Sync moderation action"
    echo

    echo "========================================="
    echo "All tests completed!"
    echo "========================================="
}

# Handle script arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Environment variables:"
    echo "  SECURITY_URL      Security module URL (default: http://localhost:8041)"
    echo "  COMMUNITY_ID      Community ID to test with (default: 1)"
    echo "  VERBOSE           Print detailed output (default: false)"
    echo
    echo "Examples:"
    echo "  $0"
    echo "  SECURITY_URL=http://security:8041 $0"
    echo "  VERBOSE=true $0"
    exit 0
fi

# Run tests
main
