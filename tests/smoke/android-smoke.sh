#!/bin/bash
################################################################################
# Android Build Smoke Test for Gazer Waddles
#
# This smoke test verifies that:
# 1. Flutter environment is properly configured
# 2. Android debug APK builds successfully
# 3. APK file is generated and valid
# 4. Build completes within reasonable time
#
# Usage: ./tests/smoke/android-smoke.sh
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
BUILD_SCRIPT="${FLUTTER_PROJECT}/scripts/build-android.sh"
MAX_BUILD_TIME=300  # 5 minutes max for debug build

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
# Test 1: Verify Flutter is installed and configured
################################################################################
test_flutter_installed() {
    print_section "Test 1: Flutter Installation"

    if ! command -v flutter &> /dev/null; then
        record_fail "Flutter is not installed or not in PATH"
        return 1
    fi

    local flutter_version=$(flutter --version | head -1)
    record_pass "Flutter is installed: $flutter_version"
    return 0
}

################################################################################
# Test 2: Verify build script exists and is executable
################################################################################
test_build_script_exists() {
    print_section "Test 2: Build Script Validation"

    if [ ! -f "$BUILD_SCRIPT" ]; then
        record_fail "Build script not found at $BUILD_SCRIPT"
        return 1
    fi

    if [ ! -x "$BUILD_SCRIPT" ]; then
        record_fail "Build script is not executable"
        return 1
    fi

    record_pass "Build script exists and is executable"
    return 0
}

################################################################################
# Test 3: Verify Flutter project structure
################################################################################
test_project_structure() {
    print_section "Test 3: Flutter Project Structure"

    local required_files=(
        "pubspec.yaml"
        "lib/main.dart"
    )

    local missing_files=0
    for file in "${required_files[@]}"; do
        if [ ! -f "${FLUTTER_PROJECT}/$file" ]; then
            record_fail "Required file not found: $file"
            missing_files=$((missing_files + 1))
        fi
    done

    # Check for Android directory (may need initialization)
    if [ ! -d "${FLUTTER_PROJECT}/android" ]; then
        record_fail "Android directory not found - run 'flutter create .' to initialize"
        missing_files=$((missing_files + 1))
    else
        print_info "Android directory exists"
    fi

    if [ $missing_files -gt 0 ]; then
        return 1
    fi

    record_pass "Required Flutter project files present"
    return 0
}

################################################################################
# Test 4: Clean any previous build artifacts
################################################################################
test_clean_build() {
    print_section "Test 4: Clean Build Environment"

    cd "$FLUTTER_PROJECT"

    if [ -d "build" ]; then
        print_info "Removing previous build artifacts..."
        rm -rf build
    fi

    record_pass "Build environment cleaned"
    return 0
}

################################################################################
# Test 5: Build debug APK
################################################################################
test_build_apk() {
    print_section "Test 5: Build Debug APK"

    cd "$FLUTTER_PROJECT"

    print_info "Starting debug APK build (max ${MAX_BUILD_TIME}s)..."
    local build_start=$(date +%s)

    # Run build script with timeout
    if timeout ${MAX_BUILD_TIME} bash "$BUILD_SCRIPT" --debug; then
        local build_end=$(date +%s)
        local build_duration=$((build_end - build_start))
        record_pass "Debug APK built successfully in ${build_duration}s"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            record_fail "Build timed out after ${MAX_BUILD_TIME}s"
        else
            record_fail "Build failed with exit code $exit_code"
        fi
        return 1
    fi
}

################################################################################
# Test 6: Verify APK file exists and is valid
################################################################################
test_apk_valid() {
    print_section "Test 6: APK File Validation"

    local debug_apk="${FLUTTER_PROJECT}/build/app/outputs/apk/debug/app-debug.apk"

    # Check if APK exists
    if [ ! -f "$debug_apk" ]; then
        record_fail "Debug APK not found at expected location: $debug_apk"
        return 1
    fi

    # Check if APK is a valid ZIP/APK file (APKs are ZIP archives)
    if ! file "$debug_apk" | grep -qE "Zip|Android package"; then
        record_fail "Debug APK is not a valid ZIP/APK file"
        return 1
    fi

    # Check APK size (should be at least 1MB for a Flutter app)
    local apk_size=$(stat -c%s "$debug_apk" 2>/dev/null || stat -f%z "$debug_apk" 2>/dev/null)
    local min_size=$((1024 * 1024))  # 1MB

    if [ "$apk_size" -lt "$min_size" ]; then
        record_fail "Debug APK size ($apk_size bytes) is suspiciously small (< 1MB)"
        return 1
    fi

    local apk_size_mb=$((apk_size / 1024 / 1024))
    record_pass "Debug APK is valid (${apk_size_mb}MB)"
    return 0
}

################################################################################
# Test 7: Verify APK contains expected Flutter components
################################################################################
test_apk_contents() {
    print_section "Test 7: APK Contents Validation"

    local debug_apk="${FLUTTER_PROJECT}/build/app/outputs/apk/debug/app-debug.apk"

    # Check for essential Flutter/Android components
    local required_components=(
        "AndroidManifest.xml"
        "classes.dex"
        "lib/"
    )

    local missing_components=0
    for component in "${required_components[@]}"; do
        if ! unzip -l "$debug_apk" | grep -q "$component"; then
            record_fail "APK missing required component: $component"
            missing_components=$((missing_components + 1))
        fi
    done

    if [ $missing_components -gt 0 ]; then
        return 1
    fi

    record_pass "APK contains all required components"
    return 0
}

################################################################################
# Main execution
################################################################################
main() {
    print_section "Android Build Smoke Test Suite"
    echo "Project: $FLUTTER_PROJECT"
    echo "Build Script: $BUILD_SCRIPT"
    echo ""

    # Run all tests (continue even if some fail)
    test_flutter_installed || true
    test_build_script_exists || true
    test_project_structure || true
    test_clean_build || true
    test_build_apk || true
    test_apk_valid || true
    test_apk_contents || true

    # Display summary
    print_section "Smoke Test Summary"
    echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
    echo ""

    if [ "$TESTS_FAILED" -gt 0 ]; then
        print_error "ANDROID SMOKE TESTS FAILED"
        echo "Fix failures before proceeding"
        exit 1
    fi

    print_success "ALL ANDROID SMOKE TESTS PASSED"
    echo "Android build is healthy and ready!"
    exit 0
}

# Run main function
main "$@"
