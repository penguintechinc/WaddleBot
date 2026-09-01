#!/bin/bash
# =============================================================================
# Waddles Master API Test Runner
# Runs all REST and gRPC API tests across all modules
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
QUICK_MODE="${QUICK:-false}"
GRPC_ONLY="${GRPC_ONLY:-false}"
REST_ONLY="${REST_ONLY:-false}"

# Counters
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║         Waddles Master API Test Runner                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

run_test_script() {
    local script="$1"
    local name="$2"

    echo -e "\n${YELLOW}▶ Running: $name${NC}"

    if [ ! -f "$script" ]; then
        echo -e "${YELLOW}  ⊘ Script not found: $script${NC}"
        TOTAL_SKIPPED=$((TOTAL_SKIPPED + 1))
        return 0
    fi

    if [ ! -x "$script" ]; then
        chmod +x "$script"
    fi

    if timeout 120 bash "$script" ${QUICK_MODE:+--quick} 2>&1; then
        echo -e "${GREEN}  ✓ $name passed${NC}"
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
    else
        echo -e "${RED}  ✗ $name failed${NC}"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
    fi
}

run_rest_tests() {
    print_section "REST API Tests"

    # Core modules
    echo -e "\n${CYAN}Core Modules:${NC}"
    run_test_script "$PROJECT_ROOT/core/reputation_module/test-api.sh" "Reputation Module"
    run_test_script "$PROJECT_ROOT/core/identity_core_module/test-api.sh" "Identity Core Module"
    run_test_script "$PROJECT_ROOT/core/browser_source_core_module/test-api.sh" "Browser Source Module"
    run_test_script "$PROJECT_ROOT/core/labels_core_module/test-api.sh" "Labels Core Module"
    run_test_script "$PROJECT_ROOT/core/community_module/test-api.sh" "Community Module"
    run_test_script "$PROJECT_ROOT/core/ai_researcher_module/test-api.sh" "AI Researcher Module"

    # Processing modules
    echo -e "\n${CYAN}Processing Modules:${NC}"
    run_test_script "$PROJECT_ROOT/processing/router_module/test-api.sh" "Router Module"

    # Action modules (REST)
    echo -e "\n${CYAN}Action Modules (REST):${NC}"
    run_test_script "$PROJECT_ROOT/action/pushing/discord_action_module/test-api.sh" "Discord Action (REST)"
    run_test_script "$PROJECT_ROOT/action/pushing/slack_action_module/test-api.sh" "Slack Action (REST)"
    run_test_script "$PROJECT_ROOT/action/pushing/twitch_action_module/test-api.sh" "Twitch Action (REST)"
    run_test_script "$PROJECT_ROOT/action/pushing/youtube_action_module/test-api.sh" "YouTube Action (REST)"

    # Trigger modules
    echo -e "\n${CYAN}Trigger Modules:${NC}"
    run_test_script "$PROJECT_ROOT/trigger/receiver/discord_module/test-api.sh" "Discord Trigger"
    run_test_script "$PROJECT_ROOT/trigger/receiver/twitch_module/test-api.sh" "Twitch Trigger"
    run_test_script "$PROJECT_ROOT/trigger/receiver/slack_module/test-api.sh" "Slack Trigger"

    # Admin/Hub
    echo -e "\n${CYAN}Admin/Hub:${NC}"
    run_test_script "$PROJECT_ROOT/admin/hub_module/test-api.sh" "Hub Module"
}

run_grpc_tests() {
    print_section "gRPC API Tests"

    if ! command -v grpcurl &> /dev/null; then
        echo -e "${YELLOW}grpcurl not installed - skipping gRPC tests${NC}"
        echo "Install with: go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest"
        return 0
    fi

    echo -e "\n${CYAN}Action Modules (gRPC):${NC}"
    run_test_script "$PROJECT_ROOT/action/pushing/discord_action_module/test-api-grpc.sh" "Discord Action (gRPC)"
    run_test_script "$PROJECT_ROOT/action/pushing/slack_action_module/test-api-grpc.sh" "Slack Action (gRPC)"
    run_test_script "$PROJECT_ROOT/action/pushing/twitch_action_module/test-api-grpc.sh" "Twitch Action (gRPC)"
    run_test_script "$PROJECT_ROOT/action/pushing/youtube_action_module/test-api-grpc.sh" "YouTube Action (gRPC)"
    run_test_script "$PROJECT_ROOT/action/pushing/lambda_action_module/test-api-grpc.sh" "Lambda Action (gRPC)"
    run_test_script "$PROJECT_ROOT/action/pushing/gcp_functions_action_module/test-api-grpc.sh" "GCP Functions (gRPC)"
    run_test_script "$PROJECT_ROOT/action/pushing/openwhisk_action_module/test-api-grpc.sh" "OpenWhisk (gRPC)"
}

print_summary() {
    print_section "Test Summary"

    local total=$((TOTAL_PASSED + TOTAL_FAILED + TOTAL_SKIPPED))

    echo -e "Total Tests:   $total"
    echo -e "${GREEN}Passed:        $TOTAL_PASSED${NC}"
    echo -e "${RED}Failed:        $TOTAL_FAILED${NC}"
    echo -e "${YELLOW}Skipped:       $TOTAL_SKIPPED${NC}"

    if [ $TOTAL_FAILED -gt 0 ]; then
        echo -e "\n${RED}╔══════════════════════════════════════╗${NC}"
        echo -e "${RED}║  Some tests failed!                  ║${NC}"
        echo -e "${RED}╚══════════════════════════════════════╝${NC}"
        exit 1
    else
        echo -e "\n${GREEN}╔══════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  All tests passed!                   ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
        exit 0
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick|-q)
            QUICK_MODE=true
            shift
            ;;
        --grpc-only)
            GRPC_ONLY=true
            shift
            ;;
        --rest-only)
            REST_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --quick, -q     Run tests in quick mode"
            echo "  --grpc-only     Only run gRPC tests"
            echo "  --rest-only     Only run REST tests"
            echo "  --help, -h      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Main
main() {
    print_banner

    echo "Project Root: $PROJECT_ROOT"
    echo "Quick Mode: $QUICK_MODE"
    echo "gRPC Only: $GRPC_ONLY"
    echo "REST Only: $REST_ONLY"

    if [ "$GRPC_ONLY" != "true" ]; then
        run_rest_tests
    fi

    if [ "$REST_ONLY" != "true" ]; then
        run_grpc_tests
    fi

    print_summary
}

main "$@"
