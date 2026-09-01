#!/bin/bash

################################################################################
# Flutter Android Build Script for Gazer WaddleBot
#
# This script automates the Android build process for flutter_gazer, including:
# - Flutter dependency management
# - APK building (debug and release variants)
# - APK verification and analysis
# - Optional device installation
#
# Usage: ./scripts/build-android.sh [OPTIONS]
# Options:
#   -d, --debug              Build debug APK only
#   -r, --release            Build release APK only
#   --install                Install built APK to connected device
#   --analyze                Show detailed APK analysis
#   -v, --verbose            Enable verbose output
#   -h, --help               Show this help message
################################################################################

set -o pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_DIR}/build"
ANDROID_DIR="${PROJECT_DIR}/android"
OUTPUT_DIR="${BUILD_DIR}/app/outputs/apk"
BUILD_LOG_DIR="${BUILD_DIR}/logs"

# Build options
BUILD_DEBUG=false
BUILD_RELEASE=false
INSTALL_APK=false
SHOW_ANALYSIS=false
VERBOSE=false

# Build tracking
BUILD_START_TIME=$(date +%s)

################################################################################
# Function: Print colored output
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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_section() {
    echo -e "\n${CYAN}=================================================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}=================================================================================${NC}\n"
}

################################################################################
# Function: Display help message
################################################################################
show_help() {
    grep '^#' "$0" | grep -E '^\s*#\s+(Usage|Options|Examples)' -A 20 | head -30
    cat << 'EOF'

Examples:
  ./scripts/build-android.sh                    # Build both debug and release
  ./scripts/build-android.sh --debug            # Debug build only
  ./scripts/build-android.sh --release          # Release build only
  ./scripts/build-android.sh --debug --install  # Build debug and install
  ./scripts/build-android.sh -r --analyze       # Release with APK analysis
EOF
}

################################################################################
# Function: Check for required tools
################################################################################
check_requirements() {
    print_section "Checking Requirements"

    local missing_tools=0

    # Check Flutter
    if ! command -v flutter &> /dev/null; then
        print_error "Flutter is not installed or not in PATH"
        print_error "Please install Flutter from https://flutter.dev/docs/get-started/install"
        missing_tools=$((missing_tools + 1))
    else
        local flutter_version=$(flutter --version | head -1)
        print_success "$flutter_version"
    fi

    # Check Java/Android SDK
    if ! command -v java &> /dev/null; then
        print_error "Java is not installed"
        missing_tools=$((missing_tools + 1))
    else
        local java_version=$(java -version 2>&1 | head -1)
        print_success "Java: $java_version"
    fi

    # Check Android SDK
    if [ -z "$ANDROID_HOME" ]; then
        print_warning "ANDROID_HOME is not set - Android SDK tools may not be accessible"
    else
        print_success "ANDROID_HOME: $ANDROID_HOME"
    fi

    # Check Git (optional but recommended)
    if ! command -v git &> /dev/null; then
        print_warning "Git is not installed - version control features will be unavailable"
    else
        print_success "Git is available"
    fi

    if [ $missing_tools -gt 0 ]; then
        print_error "Missing $missing_tools required tool(s)"
        return 1
    fi

    return 0
}

################################################################################
# Function: Fetch Flutter dependencies
################################################################################
fetch_dependencies() {
    print_section "Fetching Flutter Dependencies"

    if [ "$VERBOSE" = true ]; then
        flutter pub get
    else
        flutter pub get 2>&1 | grep -E "(packages|^Getting|error|warning)" || true
    fi

    if [ $? -eq 0 ]; then
        print_success "Dependencies fetched successfully"
        return 0
    else
        print_error "Failed to fetch dependencies"
        return 1
    fi
}

################################################################################
# Function: Verify project structure
################################################################################
verify_project_structure() {
    print_section "Verifying Project Structure"

    local required_files=(
        "pubspec.yaml"
        "lib/main.dart"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "${PROJECT_DIR}/$file" ]; then
            print_error "Required file not found: $file"
            return 1
        else
            print_success "Found: $file"
        fi
    done

    # Check for Android build file (supports both Groovy and Kotlin DSL)
    if [ -f "${PROJECT_DIR}/android/app/build.gradle" ]; then
        print_success "Found: android/app/build.gradle (Groovy)"
    elif [ -f "${PROJECT_DIR}/android/app/build.gradle.kts" ]; then
        print_success "Found: android/app/build.gradle.kts (Kotlin)"
    else
        print_error "No Android build file found (build.gradle or build.gradle.kts)"
        return 1
    fi

    return 0
}

################################################################################
# Function: Build debug APK
################################################################################
build_debug_apk() {
    print_section "Building Debug APK"

    local debug_start=$(date +%s)

    if [ "$VERBOSE" = true ]; then
        flutter build apk --debug
    else
        flutter build apk --debug 2>&1 | tail -20
    fi

    if [ $? -eq 0 ]; then
        local debug_end=$(date +%s)
        local debug_duration=$((debug_end - debug_start))
        print_success "Debug APK built successfully in ${debug_duration}s"
        return 0
    else
        print_error "Failed to build debug APK"
        return 1
    fi
}

################################################################################
# Function: Build release APK
################################################################################
build_release_apk() {
    print_section "Building Release APK"

    local release_start=$(date +%s)

    if [ "$VERBOSE" = true ]; then
        flutter build apk --release
    else
        flutter build apk --release 2>&1 | tail -20
    fi

    if [ $? -eq 0 ]; then
        local release_end=$(date +%s)
        local release_duration=$((release_end - release_start))
        print_success "Release APK built successfully in ${release_duration}s"
        return 0
    else
        print_error "Failed to build release APK"
        return 1
    fi
}

################################################################################
# Function: Verify APK files exist and are valid
################################################################################
verify_apk_files() {
    print_section "Verifying APK Files"

    local apk_count=0
    local failed=0

    # Check debug APK
    if [ "$BUILD_DEBUG" = true ]; then
        local debug_apk="${PROJECT_DIR}/build/app/outputs/apk/debug/app-debug.apk"
        if [ -f "$debug_apk" ]; then
            if file "$debug_apk" | grep -qE "Zip|Android package"; then
                print_success "Debug APK verified: $(basename "$debug_apk")"
                apk_count=$((apk_count + 1))
            else
                print_error "Debug APK is not a valid ZIP/APK file"
                failed=$((failed + 1))
            fi
        else
            print_error "Debug APK not found at $debug_apk"
            failed=$((failed + 1))
        fi
    fi

    # Check release APK
    if [ "$BUILD_RELEASE" = true ]; then
        local release_apk="${PROJECT_DIR}/build/app/outputs/apk/release/app-release.apk"
        if [ -f "$release_apk" ]; then
            if file "$release_apk" | grep -qE "Zip|Android package"; then
                print_success "Release APK verified: $(basename "$release_apk")"
                apk_count=$((apk_count + 1))
            else
                print_error "Release APK is not a valid ZIP/APK file"
                failed=$((failed + 1))
            fi
        else
            print_error "Release APK not found at $release_apk"
            failed=$((failed + 1))
        fi
    fi

    if [ $failed -gt 0 ]; then
        return 1
    fi

    return 0
}

################################################################################
# Function: Display APK information
################################################################################
display_apk_info() {
    print_section "APK Build Output"

    if [ "$BUILD_DEBUG" = true ]; then
        local debug_apk="${PROJECT_DIR}/build/app/outputs/apk/debug/app-debug.apk"
        if [ -f "$debug_apk" ]; then
            local debug_size=$(du -h "$debug_apk" | cut -f1)
            local debug_size_bytes=$(stat -f%z "$debug_apk" 2>/dev/null || stat -c%s "$debug_apk" 2>/dev/null)
            print_info "Debug APK:"
            echo -e "  ${GREEN}Location:${NC} $debug_apk"
            echo -e "  ${GREEN}Size:${NC} $debug_size"
        fi
    fi

    if [ "$BUILD_RELEASE" = true ]; then
        local release_apk="${PROJECT_DIR}/build/app/outputs/apk/release/app-release.apk"
        if [ -f "$release_apk" ]; then
            local release_size=$(du -h "$release_apk" | cut -f1)
            local release_size_bytes=$(stat -f%z "$release_apk" 2>/dev/null || stat -c%s "$release_apk" 2>/dev/null)
            print_info "Release APK:"
            echo -e "  ${GREEN}Location:${NC} $release_apk"
            echo -e "  ${GREEN}Size:${NC} $release_size"
        fi
    fi
}

################################################################################
# Function: Analyze APK in detail
################################################################################
analyze_apk() {
    if [ "$SHOW_ANALYSIS" = false ]; then
        return 0
    fi

    print_section "APK Analysis"

    if [ "$BUILD_DEBUG" = true ]; then
        local debug_apk="${PROJECT_DIR}/build/app/outputs/apk/debug/app-debug.apk"
        if [ -f "$debug_apk" ]; then
            print_info "Debug APK Contents:"
            if command -v zipinfo &> /dev/null; then
                zipinfo -1 "$debug_apk" | head -20
                echo "  ... (use 'zipinfo $debug_apk' for full listing)"
            else
                unzip -l "$debug_apk" | head -25
                echo "  ... (use 'unzip -l $debug_apk' for full listing)"
            fi
        fi
    fi

    if [ "$BUILD_RELEASE" = true ]; then
        local release_apk="${PROJECT_DIR}/build/app/outputs/apk/release/app-release.apk"
        if [ -f "$release_apk" ]; then
            print_info "Release APK Contents:"
            if command -v zipinfo &> /dev/null; then
                zipinfo -1 "$release_apk" | head -20
                echo "  ... (use 'zipinfo $release_apk' for full listing)"
            else
                unzip -l "$release_apk" | head -25
                echo "  ... (use 'unzip -l $release_apk' for full listing)"
            fi
        fi
    fi
}

################################################################################
# Function: Install APK to connected device
################################################################################
install_apk() {
    if [ "$INSTALL_APK" = false ]; then
        return 0
    fi

    print_section "Installing APK to Device"

    # Check for connected devices
    if ! command -v adb &> /dev/null; then
        print_error "adb not found - cannot install APK without Android Debug Bridge"
        print_info "Please ensure ANDROID_HOME is set and adb is in PATH"
        return 1
    fi

    local device_count=$(adb devices | grep -c "device$")
    if [ "$device_count" -eq 0 ]; then
        print_error "No connected Android devices or emulators found"
        print_info "Available devices:"
        adb devices
        return 1
    fi

    print_success "Found $device_count connected device(s)"

    # Install based on build type
    if [ "$BUILD_RELEASE" = true ]; then
        local release_apk="${PROJECT_DIR}/build/app/outputs/apk/release/app-release.apk"
        if [ -f "$release_apk" ]; then
            print_info "Installing release APK..."
            adb install -r "$release_apk"
            if [ $? -eq 0 ]; then
                print_success "Release APK installed successfully"
            else
                print_error "Failed to install release APK"
                return 1
            fi
        fi
    elif [ "$BUILD_DEBUG" = true ]; then
        local debug_apk="${PROJECT_DIR}/build/app/outputs/apk/debug/app-debug.apk"
        if [ -f "$debug_apk" ]; then
            print_info "Installing debug APK..."
            adb install -r "$debug_apk"
            if [ $? -eq 0 ]; then
                print_success "Debug APK installed successfully"
            else
                print_error "Failed to install debug APK"
                return 1
            fi
        fi
    fi

    return 0
}

################################################################################
# Function: Generate build summary
################################################################################
generate_summary() {
    local build_end=$(date +%s)
    local total_duration=$((build_end - BUILD_START_TIME))

    print_section "Build Summary"

    local build_variants=""
    if [ "$BUILD_DEBUG" = true ]; then
        build_variants="${build_variants}Debug"
    fi
    if [ "$BUILD_RELEASE" = true ]; then
        if [ -n "$build_variants" ]; then
            build_variants="${build_variants} + Release"
        else
            build_variants="Release"
        fi
    fi

    echo -e "${GREEN}Build Variants:${NC} $build_variants"
    echo -e "${GREEN}Total Build Time:${NC} ${total_duration}s"
    echo -e "${GREEN}Output Directory:${NC} ${BUILD_DIR}/app/outputs/apk"

    if [ "$BUILD_DEBUG" = true ] && [ -f "${PROJECT_DIR}/build/app/outputs/apk/debug/app-debug.apk" ]; then
        local debug_size=$(du -h "${PROJECT_DIR}/build/app/outputs/apk/debug/app-debug.apk" | cut -f1)
        echo -e "${GREEN}Debug APK Size:${NC} $debug_size"
    fi

    if [ "$BUILD_RELEASE" = true ] && [ -f "${PROJECT_DIR}/build/app/outputs/apk/release/app-release.apk" ]; then
        local release_size=$(du -h "${PROJECT_DIR}/build/app/outputs/apk/release/app-release.apk" | cut -f1)
        echo -e "${GREEN}Release APK Size:${NC} $release_size"
    fi

    if [ "$INSTALL_APK" = true ]; then
        echo -e "${GREEN}Installation:${NC} Attempted"
    fi

    print_success "Build completed successfully!"
}

################################################################################
# Function: Cleanup and exit with status
################################################################################
exit_with_status() {
    local status=$1
    local message=$2

    if [ $status -ne 0 ]; then
        print_section "Build Failed"
        print_error "$message"
        exit $status
    fi
}

################################################################################
# Parse command-line arguments
################################################################################
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--debug)
                BUILD_DEBUG=true
                shift
                ;;
            -r|--release)
                BUILD_RELEASE=true
                shift
                ;;
            --install)
                INSTALL_APK=true
                shift
                ;;
            --analyze)
                SHOW_ANALYSIS=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Default to both debug and release if neither specified
    if [ "$BUILD_DEBUG" = false ] && [ "$BUILD_RELEASE" = false ]; then
        BUILD_DEBUG=true
        BUILD_RELEASE=true
    fi
}

################################################################################
# Main execution
################################################################################
main() {
    print_section "Flutter Android Build - Gazer WaddleBot"

    # Parse arguments
    parse_arguments "$@"

    # Run build steps
    check_requirements || exit_with_status 1 "Failed requirement checks"
    verify_project_structure || exit_with_status 1 "Project structure verification failed"
    fetch_dependencies || exit_with_status 1 "Failed to fetch dependencies"

    # Build APKs
    if [ "$BUILD_DEBUG" = true ]; then
        build_debug_apk || exit_with_status 1 "Debug APK build failed"
    fi

    if [ "$BUILD_RELEASE" = true ]; then
        build_release_apk || exit_with_status 1 "Release APK build failed"
    fi

    # Verify and display results
    verify_apk_files || exit_with_status 1 "APK verification failed"
    display_apk_info
    analyze_apk
    install_apk || exit_with_status 1 "APK installation failed"

    # Generate summary and exit successfully
    generate_summary
    exit 0
}

# Run main function with all arguments
main "$@"
