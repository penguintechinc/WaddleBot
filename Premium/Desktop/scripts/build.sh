#!/bin/bash

# WaddleBot Premium Desktop Bridge Build Script
# Builds for macOS Universal and Windows 11

set -e

echo "🤖 WaddleBot Premium Desktop Bridge Build Script"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="waddlebot-bridge"
VERSION="1.0.0"
BUILD_DIR="build"
DIST_DIR="dist"

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

# Check if Go is installed
if ! command -v go &> /dev/null; then
    print_error "Go is not installed or not in PATH"
    exit 1
fi

# Check Go version
GO_VERSION=$(go version | awk '{print $3}')
print_status "Using Go version: $GO_VERSION"

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf $BUILD_DIR $DIST_DIR
mkdir -p $BUILD_DIR $DIST_DIR

# Build module examples
print_status "Building module examples..."
cd internal/modules/examples/system
go build -buildmode=plugin -o ../../../../$BUILD_DIR/system.so system.go
cd ../../../../

# Build macOS Universal Binary
print_status "Building macOS Universal Binary..."
print_status "Building for macOS arm64..."
CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w -X main.version=$VERSION" -o $BUILD_DIR/${APP_NAME}-darwin-arm64 cmd/main.go

print_status "Building for macOS amd64..."
CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w -X main.version=$VERSION" -o $BUILD_DIR/${APP_NAME}-darwin-amd64 cmd/main.go

# Create Universal Binary
print_status "Creating Universal Binary..."
if command -v lipo &> /dev/null; then
    lipo -create -output $BUILD_DIR/${APP_NAME}-darwin-universal $BUILD_DIR/${APP_NAME}-darwin-arm64 $BUILD_DIR/${APP_NAME}-darwin-amd64
    print_status "Universal Binary created successfully"
else
    print_warning "lipo not found, skipping Universal Binary creation"
    cp $BUILD_DIR/${APP_NAME}-darwin-arm64 $BUILD_DIR/${APP_NAME}-darwin-universal
fi

# Build Windows 11 Binary
print_status "Building Windows 11 Binary..."
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags="-s -w -X main.version=$VERSION" -o $BUILD_DIR/${APP_NAME}-windows-amd64.exe cmd/main.go

# Build Linux Binary (for completeness)
print_status "Building Linux Binary..."
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w -X main.version=$VERSION" -o $BUILD_DIR/${APP_NAME}-linux-amd64 cmd/main.go

# Create distribution packages
print_status "Creating distribution packages..."

# macOS Package
print_status "Creating macOS package..."
MACOS_DIR="$DIST_DIR/WaddleBot-Bridge-macOS-$VERSION"
mkdir -p "$MACOS_DIR"
cp $BUILD_DIR/${APP_NAME}-darwin-universal "$MACOS_DIR/waddlebot-bridge"
cp $BUILD_DIR/system.so "$MACOS_DIR/"
cp README.md "$MACOS_DIR/" 2>/dev/null || echo "README.md not found, skipping"
cp LICENSE "$MACOS_DIR/" 2>/dev/null || echo "LICENSE not found, skipping"

# Create macOS startup script
cat > "$MACOS_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./waddlebot-bridge --config config.yaml
EOF
chmod +x "$MACOS_DIR/start.sh"

# Create sample config
cat > "$MACOS_DIR/config.yaml" << 'EOF'
# WaddleBot Bridge Configuration
api-url: "https://api.waddlebot.io"
community-id: ""
user-id: ""
poll-interval: 30
web-port: 8080
web-host: "127.0.0.1"
log-level: "info"
EOF

# Create macOS app bundle
print_status "Creating macOS app bundle..."
APP_BUNDLE="$DIST_DIR/WaddleBot Bridge.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

cp $BUILD_DIR/${APP_NAME}-darwin-universal "$APP_BUNDLE/Contents/MacOS/waddlebot-bridge"
cp $BUILD_DIR/system.so "$APP_BUNDLE/Contents/MacOS/"

# Create Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>waddlebot-bridge</string>
    <key>CFBundleIdentifier</key>
    <string>com.waddlebot.bridge</string>
    <key>CFBundleName</key>
    <string>WaddleBot Bridge</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Windows Package
print_status "Creating Windows package..."
WINDOWS_DIR="$DIST_DIR/WaddleBot-Bridge-Windows-$VERSION"
mkdir -p "$WINDOWS_DIR"
cp $BUILD_DIR/${APP_NAME}-windows-amd64.exe "$WINDOWS_DIR/waddlebot-bridge.exe"
cp $BUILD_DIR/system.so "$WINDOWS_DIR/" 2>/dev/null || true  # May not work on Windows
cp README.md "$WINDOWS_DIR/" 2>/dev/null || echo "README.md not found, skipping"
cp LICENSE "$WINDOWS_DIR/" 2>/dev/null || echo "LICENSE not found, skipping"

# Create Windows batch file
cat > "$WINDOWS_DIR/start.bat" << 'EOF'
@echo off
cd /d "%~dp0"
waddlebot-bridge.exe --config config.yaml
pause
EOF

# Create sample config for Windows
cat > "$WINDOWS_DIR/config.yaml" << 'EOF'
# WaddleBot Bridge Configuration
api-url: "https://api.waddlebot.io"
community-id: ""
user-id: ""
poll-interval: 30
web-port: 8080
web-host: "127.0.0.1"
log-level: "info"
EOF

# Create archives
print_status "Creating archives..."
cd $DIST_DIR

# macOS Archive
if command -v tar &> /dev/null; then
    tar -czf "WaddleBot-Bridge-macOS-$VERSION.tar.gz" "WaddleBot-Bridge-macOS-$VERSION"
    print_status "macOS archive created: WaddleBot-Bridge-macOS-$VERSION.tar.gz"
fi

# Windows Archive
if command -v zip &> /dev/null; then
    zip -r "WaddleBot-Bridge-Windows-$VERSION.zip" "WaddleBot-Bridge-Windows-$VERSION"
    print_status "Windows archive created: WaddleBot-Bridge-Windows-$VERSION.zip"
fi

# App Bundle Archive
if command -v tar &> /dev/null; then
    tar -czf "WaddleBot-Bridge-macOS-App-$VERSION.tar.gz" "WaddleBot Bridge.app"
    print_status "macOS app bundle created: WaddleBot-Bridge-macOS-App-$VERSION.tar.gz"
fi

cd ..

# Generate checksums
print_status "Generating checksums..."
cd $DIST_DIR
if command -v shasum &> /dev/null; then
    shasum -a 256 *.tar.gz *.zip > checksums.txt 2>/dev/null || true
    print_status "Checksums generated"
elif command -v sha256sum &> /dev/null; then
    sha256sum *.tar.gz *.zip > checksums.txt 2>/dev/null || true
    print_status "Checksums generated"
fi
cd ..

# Build summary
print_status "Build Summary:"
echo "=============================================="
echo "Version: $VERSION"
echo "Build Directory: $BUILD_DIR"
echo "Distribution Directory: $DIST_DIR"
echo ""
echo "Built Binaries:"
ls -la $BUILD_DIR/
echo ""
echo "Distribution Packages:"
ls -la $DIST_DIR/
echo ""

# Get binary sizes
print_status "Binary Sizes:"
echo "macOS Universal: $(du -h $BUILD_DIR/${APP_NAME}-darwin-universal | cut -f1)"
echo "Windows x64: $(du -h $BUILD_DIR/${APP_NAME}-windows-amd64.exe | cut -f1)"
echo "Linux x64: $(du -h $BUILD_DIR/${APP_NAME}-linux-amd64 | cut -f1)"

echo ""
echo -e "${GREEN}🎉 Build completed successfully!${NC}"
echo -e "${GREEN}📦 Distribution packages are ready in the $DIST_DIR directory${NC}"
echo ""
echo "Installation Instructions:"
echo "=========================="
echo "macOS: Extract the .tar.gz file and run ./start.sh"
echo "Windows: Extract the .zip file and run start.bat"
echo "Or use the macOS app bundle by double-clicking the .app file"
echo ""
echo "Before running, configure your community-id and user-id in config.yaml"