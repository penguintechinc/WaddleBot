#!/bin/bash
################################################################################
# iOS Build Smoke Test for Gazer Waddles
#
# Mirrors android-smoke.sh for iOS builds:
# 1. Flutter environment verification
# 2. iOS project structure validation
# 3. Dependency resolution (flutter pub get)
# 4. Flutter analyze (lint check)
# 5. Info.plist validation (macOS only)
# 6. iOS build (macOS only, skips on Linux)
#
# Usage: ./tests/smoke/ios-smoke.sh
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
FLUTTER_PROJECT="${PROJECT_ROOT}/mobile/flutter_gazer"
MAX_BUILD_TIME=600  # 10 minutes max for iOS build
IS_MACOS=false

if [ "$(uname)" = "Darwin" ]; then
    IS_MACOS=true
fi

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
# Test 1: Verify Flutter is installed
################################################################################
test_flutter_installed() {
    print_section "Test 1: Flutter Installation"

    if ! command -v flutter &> /dev/null; then
        record_fail "Flutter is not installed or not in PATH"
        return 1
    fi

    local flutter_version
    flutter_version=$(flutter --version 2>/dev/null | head -1)
    record_pass "Flutter is installed: $flutter_version"

    # Platform detection
    if [ "$IS_MACOS" = true ]; then
        print_info "Platform: macOS - full iOS testing available"
    else
        print_warn "Platform: $(uname) - iOS build tests will be skipped"
    fi

    return 0
}

################################################################################
# Test 2: Verify iOS project structure
################################################################################
test_project_structure() {
    print_section "Test 2: iOS Project Structure"

    if [ ! -d "${FLUTTER_PROJECT}/ios" ]; then
        record_fail "ios/ directory not found in Flutter project"
        return 1
    fi

    print_info "ios/ directory exists"

    local required_files=(
        "ios/Runner.xcodeproj"
        "ios/Runner/Info.plist"
    )

    local missing_files=0
    for item in "${required_files[@]}"; do
        if [ ! -e "${FLUTTER_PROJECT}/$item" ]; then
            record_fail "Required item not found: $item"
            missing_files=$((missing_files + 1))
        else
            print_info "Found: $item"
        fi
    done

    # Check for Podfile
    if [ -f "${FLUTTER_PROJECT}/ios/Podfile" ]; then
        print_info "Podfile exists"
    else
        print_warn "Podfile not found - may need 'flutter pub get' to generate"
    fi

    if [ $missing_files -gt 0 ]; then
        return 1
    fi

    record_pass "iOS project structure is valid"
    return 0
}

################################################################################
# Test 3: Flutter pub get (dependency resolution)
################################################################################
test_pub_get() {
    print_section "Test 3: Dependency Resolution (flutter pub get)"

    cd "$FLUTTER_PROJECT"

    if flutter pub get 2>&1; then
        record_pass "flutter pub get succeeded"
    else
        record_fail "flutter pub get failed"
        return 1
    fi

    return 0
}

################################################################################
# Test 4: Flutter analyze (lint check)
################################################################################
test_flutter_analyze() {
    print_section "Test 4: Flutter Analyze"

    cd "$FLUTTER_PROJECT"

    local analyze_output
    analyze_output=$(flutter analyze 2>&1) || true
    local exit_code=$?

    if echo "$analyze_output" | grep -q 'No issues found'; then
        record_pass "Flutter analyze: no issues found"
    elif echo "$analyze_output" | grep -qi 'error'; then
        local error_count
        error_count=$(echo "$analyze_output" | grep -ci 'error' || echo "0")
        record_fail "Flutter analyze found errors ($error_count)"
        echo "$analyze_output" | grep -i 'error' | head -10
    else
        # Warnings are acceptable
        record_pass "Flutter analyze passed (warnings may exist)"
    fi

    return 0
}

################################################################################
# Test 5: Info.plist validation (macOS only)
################################################################################
test_info_plist() {
    print_section "Test 5: Info.plist Validation"

    local plist="${FLUTTER_PROJECT}/ios/Runner/Info.plist"

    if [ ! -f "$plist" ]; then
        record_fail "Info.plist not found at $plist"
        return 1
    fi

    if [ "$IS_MACOS" = false ]; then
        print_warn "Skipping detailed Info.plist checks (not on macOS)"
        # Still do basic text-based checks
        if grep -q 'CFBundleDisplayName\|CFBundleName' "$plist"; then
            record_pass "Info.plist contains bundle name keys"
        else
            print_warn "CFBundleDisplayName/CFBundleName not found in Info.plist"
        fi
        return 0
    fi

    # macOS: full plist checks
    # Check for camera usage description
    if grep -q 'NSCameraUsageDescription' "$plist"; then
        record_pass "Info.plist has camera usage description"
    else
        record_fail "Info.plist missing NSCameraUsageDescription"
    fi

    # Check for microphone usage description
    if grep -q 'NSMicrophoneUsageDescription' "$plist"; then
        record_pass "Info.plist has microphone usage description"
    else
        record_fail "Info.plist missing NSMicrophoneUsageDescription"
    fi

    # Check for bundle display name
    if grep -q 'CFBundleDisplayName' "$plist"; then
        record_pass "Info.plist has CFBundleDisplayName"
    else
        print_warn "Info.plist missing CFBundleDisplayName"
    fi

    return 0
}

################################################################################
# Test 6: iOS build (macOS only)
################################################################################
test_ios_build() {
    print_section "Test 6: iOS Build"

    if [ "$IS_MACOS" = false ]; then
        print_warn "Skipping iOS build test (not on macOS)"
        print_info "iOS builds require macOS with Xcode installed"
        return 0
    fi

    # Check if Xcode is available
    if ! command -v xcodebuild &> /dev/null; then
        print_warn "Xcode not installed - skipping iOS build"
        return 0
    fi

    cd "$FLUTTER_PROJECT"

    print_info "Starting iOS build (no-codesign, max ${MAX_BUILD_TIME}s)..."
    local build_start
    build_start=$(date +%s)

    if timeout ${MAX_BUILD_TIME} flutter build ios --no-codesign 2>&1; then
        local build_end
        build_end=$(date +%s)
        local build_duration=$((build_end - build_start))
        record_pass "iOS build succeeded in ${build_duration}s"
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            record_fail "iOS build timed out after ${MAX_BUILD_TIME}s"
        else
            record_fail "iOS build failed with exit code $exit_code"
        fi
        return 1
    fi

    return 0
}

################################################################################
# Main execution
################################################################################
main() {
    print_section "iOS Build Smoke Test Suite"
    echo "Project: $FLUTTER_PROJECT"
    echo "Platform: $(uname)"
    echo "macOS: $IS_MACOS"
    echo ""

    # Run all tests (continue even if some fail)
    test_flutter_installed || true
    test_project_structure || true
    test_pub_get || true
    test_flutter_analyze || true
    test_info_plist || true
    test_ios_build || true

    # Display summary
    print_section "Smoke Test Summary"
    echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
    echo ""

    if [ "$TESTS_FAILED" -gt 0 ]; then
        print_error "iOS SMOKE TESTS FAILED"
        echo "Fix failures before proceeding"
        exit 1
    fi

    print_success "ALL iOS SMOKE TESTS PASSED"
    echo "iOS build is healthy and ready!"
    exit 0
}

# Run main function
main "$@"
