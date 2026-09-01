#!/bin/bash
################################################################################
# Desktop Go Build Smoke Test for Waddles Premium Desktop
#
# Verifies Premium Desktop Go application:
# 1. Go toolchain installed and version check
# 2. go.mod module name and Go version
# 3. Source structure (cmd/main.go, internal/ packages)
# 4. Branding verification (Waddles in descriptions)
# 5. go build succeeds
# 6. go test passes
# 7. Built binary runs --help with correct branding
#
# Usage: ./tests/smoke/desktop-smoke.sh
#
# Exit codes:
#   0 - All smoke tests passed
#   1 - One or more smoke tests failed
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DESKTOP_PROJECT="${PROJECT_ROOT}/Premium/Desktop"
MAX_BUILD_TIME=120  # 2 minutes max for Go build

TESTS_PASSED=0
TESTS_FAILED=0

################################################################################
# Helper functions
################################################################################
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

record_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    print_success "$1"
}

record_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    print_error "$1"
}

################################################################################
# Test 1: Verify Go is installed and version check
################################################################################
test_go_installed() {
    print_section "Test 1: Go Toolchain"

    if ! command -v go &> /dev/null; then
        record_fail "Go is not installed or not in PATH"
        return 1
    fi

    local go_version
    go_version=$(go version)
    print_info "$go_version"

    # Check version >= 1.23
    local version_num
    version_num=$(go version | grep -oP 'go(\d+\.\d+)' | grep -oP '\d+\.\d+')

    if [ -z "$version_num" ]; then
        print_warn "Could not parse Go version number"
        record_pass "Go is installed (version check skipped)"
        return 0
    fi

    local major minor
    major=$(echo "$version_num" | cut -d. -f1)
    minor=$(echo "$version_num" | cut -d. -f2)

    if [ "$major" -gt 1 ] || ([ "$major" -eq 1 ] && [ "$minor" -ge 23 ]); then
        record_pass "Go version $version_num >= 1.23"
    else
        record_fail "Go version $version_num is below required 1.23"
    fi

    return 0
}

################################################################################
# Test 2: Verify go.mod
################################################################################
test_go_mod() {
    print_section "Test 2: go.mod Validation"

    local gomod="${DESKTOP_PROJECT}/go.mod"

    if [ ! -f "$gomod" ]; then
        record_fail "go.mod not found at $gomod"
        return 1
    fi

    # Check module name
    if grep -q 'module.*waddlebot-bridge' "$gomod"; then
        record_pass "go.mod module name contains 'waddlebot-bridge'"
    else
        local actual_module
        actual_module=$(grep '^module' "$gomod" | head -1)
        record_fail "go.mod module name should contain 'waddlebot-bridge', found: $actual_module"
    fi

    # Check Go version in go.mod
    local go_mod_version
    go_mod_version=$(grep '^go ' "$gomod" | head -1 | awk '{print $2}')
    if [ -n "$go_mod_version" ]; then
        print_info "go.mod Go version: $go_mod_version"
        record_pass "go.mod specifies Go version: $go_mod_version"
    else
        record_fail "go.mod does not specify Go version"
    fi

    return 0
}

################################################################################
# Test 3: Verify source structure
################################################################################
test_source_structure() {
    print_section "Test 3: Source Structure"

    local required_items=(
        "cmd/main.go"
        "internal"
    )

    local missing=0
    for item in "${required_items[@]}"; do
        if [ ! -e "${DESKTOP_PROJECT}/$item" ]; then
            record_fail "Required item not found: $item"
            missing=$((missing + 1))
        else
            print_info "Found: $item"
        fi
    done

    # Check for internal packages
    if [ -d "${DESKTOP_PROJECT}/internal" ]; then
        local pkg_count
        pkg_count=$(find "${DESKTOP_PROJECT}/internal" -name "*.go" -type f | head -50 | wc -l)
        print_info "Found $pkg_count Go files in internal/"
    fi

    if [ $missing -gt 0 ]; then
        return 1
    fi

    record_pass "Source structure is valid"
    return 0
}

################################################################################
# Test 4: Branding verification
################################################################################
test_branding() {
    print_section "Test 4: Branding Verification"

    local main_go="${DESKTOP_PROJECT}/cmd/main.go"

    if [ ! -f "$main_go" ]; then
        record_fail "cmd/main.go not found"
        return 1
    fi

    # Short/Long descriptions should contain "Waddles"
    if grep -q 'Waddles' "$main_go"; then
        record_pass "cmd/main.go contains 'Waddles' branding"
    else
        record_fail "cmd/main.go does not contain 'Waddles' branding"
    fi

    # Config paths should still use ".waddlebot-bridge"
    local config_go="${DESKTOP_PROJECT}/internal/config/config.go"
    if [ -f "$config_go" ]; then
        if grep -q 'waddlebot-bridge\|waddlebot' "$config_go"; then
            record_pass "Config paths use 'waddlebot' identifier"
        else
            print_warn "Could not confirm 'waddlebot' in config paths"
        fi
    else
        print_warn "config.go not found - skipping config path check"
    fi

    return 0
}

################################################################################
# Test 5: Go build
################################################################################
test_go_build() {
    print_section "Test 5: Go Build"

    cd "$DESKTOP_PROJECT"

    print_info "Running go build ./cmd/ (max ${MAX_BUILD_TIME}s)..."
    local build_start
    build_start=$(date +%s)

    if timeout ${MAX_BUILD_TIME} go build -o /tmp/waddlebot-bridge-smoke-test ./cmd/ 2>&1; then
        local build_end
        build_end=$(date +%s)
        local build_duration=$((build_end - build_start))
        record_pass "go build succeeded in ${build_duration}s"
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            record_fail "go build timed out after ${MAX_BUILD_TIME}s"
        else
            record_fail "go build failed with exit code $exit_code"
        fi
        return 1
    fi

    return 0
}

################################################################################
# Test 6: Go test
################################################################################
test_go_test() {
    print_section "Test 6: Go Test"

    cd "$DESKTOP_PROJECT"

    print_info "Running go test -short ./..."
    if go test -short ./... 2>&1; then
        record_pass "go test -short passed"
    else
        record_fail "go test -short failed"
        return 1
    fi

    return 0
}

################################################################################
# Test 7: Binary help output
################################################################################
test_binary_help() {
    print_section "Test 7: Binary Help Output"

    local binary="/tmp/waddlebot-bridge-smoke-test"

    if [ ! -f "$binary" ]; then
        print_warn "Binary not found (build may have failed) - skipping help test"
        return 0
    fi

    local help_output
    help_output=$("$binary" --help 2>&1) || true

    if echo "$help_output" | grep -qi 'Waddles\|waddles'; then
        record_pass "Binary --help output contains 'Waddles' branding"
    else
        record_fail "Binary --help output does not contain 'Waddles' branding"
        echo "Help output (first 5 lines):"
        echo "$help_output" | head -5
    fi

    # Cleanup
    rm -f "$binary"

    return 0
}

################################################################################
# Main execution
################################################################################
main() {
    print_section "Desktop Go Build Smoke Test Suite"
    echo "Project: $DESKTOP_PROJECT"
    echo ""

    # Run all tests (continue even if some fail)
    test_go_installed || true
    test_go_mod || true
    test_source_structure || true
    test_branding || true
    test_go_build || true
    test_go_test || true
    test_binary_help || true

    # Display summary
    print_section "Smoke Test Summary"
    echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
    echo ""

    if [ "$TESTS_FAILED" -gt 0 ]; then
        print_error "DESKTOP SMOKE TESTS FAILED"
        echo "Fix failures before proceeding"
        exit 1
    fi

    print_success "ALL DESKTOP SMOKE TESTS PASSED"
    echo "Desktop Go build is healthy and ready!"
    exit 0
}

# Run main function
main "$@"
