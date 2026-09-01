#!/bin/bash
# Waddles OpenWhisk Integration Test
# Tests the full flow: test script → openwhisk-action module → OpenWhisk → response
#
# Usage: ./scripts/test-openwhisk.sh
#
# Prerequisites:
#   docker-compose up -d openwhisk openwhisk-action postgres redis

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
OPENWHISK_HOST="${OPENWHISK_HOST:-localhost}"
OPENWHISK_PORT="${OPENWHISK_PORT:-3233}"
OPENWHISK_AUTH="${OPENWHISK_AUTH:-23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP}"
OPENWHISK_NAMESPACE="${OPENWHISK_NAMESPACE:-guest}"

ACTION_MODULE_HOST="${ACTION_MODULE_HOST:-localhost}"
ACTION_MODULE_PORT="${ACTION_MODULE_PORT:-8082}"
MODULE_SECRET_KEY="${MODULE_SECRET_KEY:-dev-secret-key-for-testing-only-change-in-production}"

ACTION_FILE="$PROJECT_ROOT/action/pushing/openwhisk_action_module/actions/hello.js"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Wait for a service to be healthy
wait_for_service() {
    local name="$1"
    local url="$2"
    local max_attempts="${3:-30}"
    local attempt=1

    log_info "Waiting for $name to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_success "$name is ready"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo ""
    log_error "$name did not become ready after $max_attempts attempts"
    return 1
}

# Deploy action to OpenWhisk
deploy_action() {
    log_info "Deploying hello action to OpenWhisk..."

    if [ ! -f "$ACTION_FILE" ]; then
        log_error "Action file not found: $ACTION_FILE"
        exit 1
    fi

    # Read action code
    local action_code
    action_code=$(cat "$ACTION_FILE")

    # Base64 encode auth
    local auth_b64
    auth_b64=$(echo -n "$OPENWHISK_AUTH" | base64)

    # Create/update action via REST API
    local response
    response=$(curl -s -X PUT \
        "http://${OPENWHISK_HOST}:${OPENWHISK_PORT}/api/v1/namespaces/${OPENWHISK_NAMESPACE}/actions/hello?overwrite=true" \
        -H "Authorization: Basic $auth_b64" \
        -H "Content-Type: application/json" \
        -d "{
            \"namespace\": \"${OPENWHISK_NAMESPACE}\",
            \"name\": \"hello\",
            \"exec\": {
                \"kind\": \"nodejs:default\",
                \"code\": $(echo "$action_code" | jq -Rs .)
            }
        }")

    if echo "$response" | jq -e '.name == "hello"' > /dev/null 2>&1; then
        log_success "Action 'hello' deployed successfully"
        return 0
    else
        log_error "Failed to deploy action: $response"
        return 1
    fi
}

# Get JWT token from openwhisk-action module
get_jwt_token() {
    log_info "Getting JWT token from openwhisk-action module..."

    local response
    response=$(curl -s -X POST \
        "http://${ACTION_MODULE_HOST}:${ACTION_MODULE_PORT}/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{
            \"api_key\": \"${MODULE_SECRET_KEY}\",
            \"service\": \"test-script\"
        }")

    local token
    token=$(echo "$response" | jq -r '.token // empty')

    if [ -n "$token" ]; then
        log_success "JWT token obtained"
        echo "$token"
        return 0
    else
        log_error "Failed to get JWT token: $response"
        return 1
    fi
}

# Invoke action via openwhisk-action module
invoke_action() {
    local token="$1"
    log_info "Invoking hello action via openwhisk-action module..."

    local response
    response=$(curl -s -X POST \
        "http://${ACTION_MODULE_HOST}:${ACTION_MODULE_PORT}/api/v1/actions/invoke" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{
            \"action_name\": \"hello\",
            \"payload\": {},
            \"blocking\": true
        }")

    echo "$response"
}

# Verify response
verify_response() {
    local response="$1"
    log_info "Verifying response..."

    # Check success
    local success
    success=$(echo "$response" | jq -r '.success // false')

    if [ "$success" != "true" ]; then
        log_error "Action invocation failed"
        echo "$response" | jq .
        return 1
    fi

    # Check message in result
    local message
    message=$(echo "$response" | jq -r '.result.message // empty')

    if [ "$message" = "Hello World" ]; then
        log_success "Response verified: message = '$message'"
        return 0
    else
        log_error "Unexpected message: '$message' (expected 'Hello World')"
        echo "Full response:"
        echo "$response" | jq .
        return 1
    fi
}

# Main test flow
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║              Waddles OpenWhisk Integration Test                            ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""

    # Step 1: Wait for OpenWhisk
    wait_for_service "OpenWhisk" "http://${OPENWHISK_HOST}:${OPENWHISK_PORT}/api/v1" || exit 1

    # Step 2: Deploy hello action
    deploy_action || exit 1

    # Step 3: Wait for openwhisk-action module
    wait_for_service "openwhisk-action module" "http://${ACTION_MODULE_HOST}:${ACTION_MODULE_PORT}/health" || exit 1

    # Step 4: Get JWT token
    local token
    token=$(get_jwt_token) || exit 1

    # Step 5: Invoke action via module
    local response
    response=$(invoke_action "$token")

    # Step 6: Verify response
    verify_response "$response" || exit 1

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                              TEST PASSED                                     ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    log_success "OpenWhisk integration test completed successfully!"
    echo ""
    echo "Full response:"
    echo "$response" | jq .
}

main "$@"
