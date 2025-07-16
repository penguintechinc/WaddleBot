#!/bin/bash

# WaddleBot Premium Android Build Script

set -e

echo "🤖 WaddleBot Premium Android Build Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="WaddleBot Premium"
PACKAGE_NAME="com.waddlebot.premium"
BUILD_TYPE="release"
OUTPUT_DIR="app/build/outputs/apk"
SIGNED_APK_DIR="app/build/outputs/apk/release"

# Check if we're in the right directory
if [ ! -f "app/build.gradle.kts" ]; then
    echo -e "${RED}Error: build.gradle.kts not found. Please run this script from the Android project root.${NC}"
    exit 1
fi

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
print_status "Checking dependencies..."

# Check Java
if ! command -v java &> /dev/null; then
    print_error "Java is not installed or not in PATH"
    exit 1
fi

# Check Android SDK
if [ -z "$ANDROID_HOME" ]; then
    print_error "ANDROID_HOME environment variable is not set"
    exit 1
fi

# Check Gradle
if [ ! -f "gradlew" ]; then
    print_error "Gradle wrapper not found"
    exit 1
fi

# Make gradlew executable
chmod +x gradlew

print_status "Dependencies check passed!"

# Clean previous builds
print_status "Cleaning previous builds..."
./gradlew clean

# Check for keystore (for release builds)
if [ "$BUILD_TYPE" == "release" ]; then
    KEYSTORE_PATH="app/release-key.keystore"
    if [ ! -f "$KEYSTORE_PATH" ]; then
        print_warning "Release keystore not found. Creating debug keystore..."
        
        # Generate debug keystore
        keytool -genkeypair \
            -keystore app/debug.keystore \
            -alias androiddebugkey \
            -keypass android \
            -storepass android \
            -keyalg RSA \
            -keysize 2048 \
            -validity 10000 \
            -dname "CN=Android Debug,O=Android,C=US"
        
        BUILD_TYPE="debug"
        print_warning "Building debug APK instead of release APK"
    fi
fi

# Build the APK
print_status "Building $BUILD_TYPE APK..."
if [ "$BUILD_TYPE" == "release" ]; then
    ./gradlew assembleRelease
else
    ./gradlew assembleDebug
fi

# Check if build was successful
if [ $? -eq 0 ]; then
    print_status "Build completed successfully!"
else
    print_error "Build failed!"
    exit 1
fi

# Find the generated APK
if [ "$BUILD_TYPE" == "release" ]; then
    APK_FILE="$OUTPUT_DIR/release/app-release.apk"
else
    APK_FILE="$OUTPUT_DIR/debug/app-debug.apk"
fi

if [ -f "$APK_FILE" ]; then
    print_status "APK generated: $APK_FILE"
    
    # Get APK size
    APK_SIZE=$(du -h "$APK_FILE" | cut -f1)
    print_status "APK size: $APK_SIZE"
    
    # Copy APK to a more accessible location
    FINAL_APK_NAME="WaddleBot-Premium-${BUILD_TYPE}.apk"
    cp "$APK_FILE" "$FINAL_APK_NAME"
    print_status "APK copied to: $FINAL_APK_NAME"
    
    # Generate APK info
    print_status "APK Information:"
    echo "  - Package: $PACKAGE_NAME"
    echo "  - Build Type: $BUILD_TYPE"
    echo "  - Size: $APK_SIZE"
    echo "  - Location: $(pwd)/$FINAL_APK_NAME"
    
    # Optional: Install APK to connected device
    read -p "Install APK to connected device? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Installing APK to device..."
        adb install -r "$FINAL_APK_NAME"
        if [ $? -eq 0 ]; then
            print_status "APK installed successfully!"
        else
            print_error "Failed to install APK"
        fi
    fi
    
else
    print_error "APK file not found at expected location: $APK_FILE"
    exit 1
fi

# Generate build report
print_status "Generating build report..."
BUILD_REPORT="build-report.txt"
cat > "$BUILD_REPORT" << EOF
WaddleBot Premium Android Build Report
=====================================

Build Date: $(date)
Build Type: $BUILD_TYPE
Package Name: $PACKAGE_NAME
APK Size: $APK_SIZE
APK Location: $(pwd)/$FINAL_APK_NAME

Build Environment:
- Java Version: $(java -version 2>&1 | head -n 1)
- Android SDK: $ANDROID_HOME
- Gradle Version: $(./gradlew --version | grep "Gradle" | head -n 1)

Build Status: SUCCESS
EOF

print_status "Build report generated: $BUILD_REPORT"

echo
echo -e "${GREEN}🎉 Build completed successfully!${NC}"
echo -e "${GREEN}📱 APK ready: $FINAL_APK_NAME${NC}"
echo -e "${GREEN}📊 Build report: $BUILD_REPORT${NC}"
echo

# Optional: Open APK location
if command -v xdg-open &> /dev/null; then
    read -p "Open APK location in file manager? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        xdg-open .
    fi
fi