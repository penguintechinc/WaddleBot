#!/bin/bash
################################################################################
# Flutter Config Integrity Smoke Test for Gazer Waddles
#
# Validates Flutter Gazer configuration is consistent:
# 1. pubspec.yaml package name and version format
# 2. AndroidManifest.xml required permissions
# 3. build.gradle.kts applicationId
# 4. constants.dart URLs and domain references
# 5. Display names use "Waddles" not "WaddleBot"
# 6. Domain config has production/staging/dev entries
#
# Usage: ./tests/smoke/smoke-flutter-config.sh
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
# Test 1: pubspec.yaml validation
################################################################################
test_pubspec() {
    print_section "Test 1: pubspec.yaml Validation"

    local pubspec="${FLUTTER_PROJECT}/pubspec.yaml"

    if [ ! -f "$pubspec" ]; then
        record_fail "pubspec.yaml not found at $pubspec"
        return 1
    fi

    # Package name should be gazer_waddlebot
    if grep -q '^name: gazer_waddlebot' "$pubspec"; then
        record_pass "Package name is 'gazer_waddlebot'"
    else
        local actual_name
        actual_name=$(grep '^name:' "$pubspec" | head -1)
        record_fail "Package name should be 'gazer_waddlebot', found: $actual_name"
    fi

    # Version should match semver+build format (e.g., 1.0.0+1)
    if grep -qE '^version: [0-9]+\.[0-9]+\.[0-9]+\+[0-9]+' "$pubspec"; then
        local version
        version=$(grep '^version:' "$pubspec" | head -1)
        record_pass "Version format is valid: $version"
    else
        local version
        version=$(grep '^version:' "$pubspec" | head -1)
        record_fail "Version format invalid (expected semver+build): $version"
    fi

    return 0
}

################################################################################
# Test 2: AndroidManifest.xml permissions
################################################################################
test_android_manifest() {
    print_section "Test 2: AndroidManifest.xml Permissions"

    local manifest="${FLUTTER_PROJECT}/android/app/src/main/AndroidManifest.xml"

    if [ ! -f "$manifest" ]; then
        print_warn "AndroidManifest.xml not found - skipping permission checks"
        return 0
    fi

    local required_permissions=(
        "INTERNET"
        "CAMERA"
        "RECORD_AUDIO"
    )

    local missing=0
    for perm in "${required_permissions[@]}"; do
        if grep -q "$perm" "$manifest"; then
            print_info "Permission present: $perm"
        else
            record_fail "Missing required permission: $perm"
            missing=$((missing + 1))
        fi
    done

    if [ "$missing" -eq 0 ]; then
        record_pass "All required Android permissions present"
    fi

    return 0
}

################################################################################
# Test 3: build.gradle.kts applicationId
################################################################################
test_build_gradle() {
    print_section "Test 3: build.gradle.kts Application ID"

    # Check both .kts and .gradle variants
    local gradle_file=""
    if [ -f "${FLUTTER_PROJECT}/android/app/build.gradle.kts" ]; then
        gradle_file="${FLUTTER_PROJECT}/android/app/build.gradle.kts"
    elif [ -f "${FLUTTER_PROJECT}/android/app/build.gradle" ]; then
        gradle_file="${FLUTTER_PROJECT}/android/app/build.gradle"
    fi

    if [ -z "$gradle_file" ]; then
        print_warn "build.gradle(.kts) not found - skipping applicationId check"
        return 0
    fi

    if grep -q 'applicationId' "$gradle_file"; then
        local app_id
        app_id=$(grep 'applicationId' "$gradle_file" | head -1 | sed 's/.*"\(.*\)".*/\1/')
        print_info "applicationId: $app_id"

        if echo "$app_id" | grep -q 'com\.example'; then
            print_warn "applicationId still uses 'com.example' placeholder: $app_id"
        else
            record_pass "applicationId is not a placeholder: $app_id"
        fi
    else
        record_fail "No applicationId found in $gradle_file"
    fi

    return 0
}

################################################################################
# Test 4: constants.dart URLs and domain references
################################################################################
test_constants_dart() {
    print_section "Test 4: constants.dart URL Validation"

    local constants="${FLUTTER_PROJECT}/lib/config/constants.dart"

    if [ ! -f "$constants" ]; then
        print_warn "constants.dart not found at $constants - skipping URL checks"
        return 0
    fi

    # URLs should point to waddlebot.io
    if grep -q 'waddlebot\.io' "$constants"; then
        record_pass "constants.dart contains waddlebot.io URLs"
    else
        print_warn "No waddlebot.io URLs found in constants.dart"
    fi

    # No "waddles.io" in Dart sources
    local bad_domain_count
    bad_domain_count=$(grep -r 'waddles\.io' "${FLUTTER_PROJECT}/lib/" 2>/dev/null | wc -l)

    if [ "$bad_domain_count" -eq 0 ]; then
        record_pass "No 'waddles.io' references in Dart sources"
    else
        record_fail "Found $bad_domain_count references to 'waddles.io' in Dart sources"
        grep -r 'waddles\.io' "${FLUTTER_PROJECT}/lib/" 2>/dev/null | head -5 || true
    fi

    return 0
}

################################################################################
# Test 5: Display names use "Waddles"
################################################################################
test_display_names() {
    print_section "Test 5: Display Name Validation"

    # Check UI-facing strings show "Waddles" not "WaddleBot"
    local dart_files_with_waddlebot
    dart_files_with_waddlebot=$(grep -rl 'WaddleBot' "${FLUTTER_PROJECT}/lib/" 2>/dev/null | grep -v '.dart_tool' || true)

    if [ -n "$dart_files_with_waddlebot" ]; then
        local count
        count=$(echo "$dart_files_with_waddlebot" | wc -l)
        record_fail "Found $count Dart files still containing 'WaddleBot' display name"
        echo "$dart_files_with_waddlebot" | head -5
    else
        record_pass "No Dart files contain 'WaddleBot' display name (correctly using 'Waddles')"
    fi

    # Check that "Waddles" appears in key UI files
    local main_dart="${FLUTTER_PROJECT}/lib/main.dart"
    local app_dart="${FLUTTER_PROJECT}/lib/app.dart"

    local found_waddles=false
    for f in "$main_dart" "$app_dart"; do
        if [ -f "$f" ] && grep -q 'Waddles' "$f"; then
            found_waddles=true
            break
        fi
    done

    if [ "$found_waddles" = true ]; then
        record_pass "Found 'Waddles' branding in main app files"
    else
        print_warn "Could not confirm 'Waddles' branding in main.dart or app.dart"
    fi

    return 0
}

################################################################################
# Test 6: Domain config validation
################################################################################
test_domain_config() {
    print_section "Test 6: Domain Configuration"

    local domain_config="${FLUTTER_PROJECT}/lib/models/domain_config.dart"

    if [ ! -f "$domain_config" ]; then
        print_warn "domain_config.dart not found - skipping domain config checks"
        return 0
    fi

    # Check for production/staging/dev domain entries
    local environments=("production" "staging" "dev")
    local found=0

    for env in "${environments[@]}"; do
        if grep -qi "$env" "$domain_config"; then
            found=$((found + 1))
            print_info "Found '$env' environment in domain_config.dart"
        fi
    done

    if [ "$found" -ge 2 ]; then
        record_pass "Domain config has multiple environment entries ($found found)"
    elif [ "$found" -eq 1 ]; then
        print_warn "Domain config has only 1 environment entry (expected multiple)"
    else
        print_warn "No environment entries found in domain_config.dart"
    fi

    return 0
}

################################################################################
# Main execution
################################################################################
main() {
    print_section "Flutter Config Integrity Smoke Test Suite"
    echo "Flutter Project: $FLUTTER_PROJECT"
    echo ""

    # Run all tests (continue even if some fail)
    test_pubspec || true
    test_android_manifest || true
    test_build_gradle || true
    test_constants_dart || true
    test_display_names || true
    test_domain_config || true

    # Display summary
    print_section "Smoke Test Summary"
    echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
    echo ""

    if [ "$TESTS_FAILED" -gt 0 ]; then
        print_error "FLUTTER CONFIG SMOKE TESTS FAILED"
        echo "Fix failures before proceeding"
        exit 1
    fi

    print_success "ALL FLUTTER CONFIG SMOKE TESTS PASSED"
    echo "Flutter configuration is consistent and correct!"
    exit 0
}

# Run main function
main "$@"
