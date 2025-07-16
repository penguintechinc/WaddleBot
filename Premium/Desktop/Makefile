# WaddleBot Premium Desktop Bridge Makefile

.PHONY: all build clean deps test lint install uninstall dev help

# Configuration
APP_NAME = waddlebot-bridge
VERSION = 1.0.0
BUILD_DIR = build
DIST_DIR = dist
GO_VERSION = 1.21

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Default target
all: clean deps build

# Build all targets
build:
	@echo "$(GREEN)[INFO]$(NC) Building WaddleBot Premium Desktop Bridge..."
	@chmod +x scripts/build.sh
	@./scripts/build.sh

# Build for specific platform
build-windows:
	@echo "$(GREEN)[INFO]$(NC) Building for Windows..."
	@mkdir -p $(BUILD_DIR)
	@CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags="-s -w -X main.version=$(VERSION)" -o $(BUILD_DIR)/$(APP_NAME)-windows-amd64.exe cmd/main.go

build-macos:
	@echo "$(GREEN)[INFO]$(NC) Building for macOS..."
	@mkdir -p $(BUILD_DIR)
	@CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w -X main.version=$(VERSION)" -o $(BUILD_DIR)/$(APP_NAME)-darwin-amd64 cmd/main.go
	@CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w -X main.version=$(VERSION)" -o $(BUILD_DIR)/$(APP_NAME)-darwin-arm64 cmd/main.go

build-linux:
	@echo "$(GREEN)[INFO]$(NC) Building for Linux..."
	@mkdir -p $(BUILD_DIR)
	@CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w -X main.version=$(VERSION)" -o $(BUILD_DIR)/$(APP_NAME)-linux-amd64 cmd/main.go

# Build modules
build-modules:
	@echo "$(GREEN)[INFO]$(NC) Building modules..."
	@mkdir -p $(BUILD_DIR)
	@cd internal/modules/examples/system && go build -buildmode=plugin -o ../../../../$(BUILD_DIR)/system.so system.go

# Clean build artifacts
clean:
	@echo "$(GREEN)[INFO]$(NC) Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR) $(DIST_DIR)

# Install dependencies
deps:
	@echo "$(GREEN)[INFO]$(NC) Installing dependencies..."
	@go mod download
	@go mod tidy

# Run tests
test:
	@echo "$(GREEN)[INFO]$(NC) Running tests..."
	@go test -v ./...

# Run linter
lint:
	@echo "$(GREEN)[INFO]$(NC) Running linter..."
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run; \
	else \
		echo "$(YELLOW)[WARNING]$(NC) golangci-lint not found, skipping lint"; \
	fi

# Format code
fmt:
	@echo "$(GREEN)[INFO]$(NC) Formatting code..."
	@go fmt ./...

# Run in development mode
dev:
	@echo "$(GREEN)[INFO]$(NC) Running in development mode..."
	@go run cmd/main.go --log-level debug

# Install the application
install: build
	@echo "$(GREEN)[INFO]$(NC) Installing $(APP_NAME)..."
	@sudo cp $(BUILD_DIR)/$(APP_NAME)-$(shell go env GOOS)-$(shell go env GOARCH) /usr/local/bin/$(APP_NAME)
	@echo "$(GREEN)[INFO]$(NC) Installation complete. Run with: $(APP_NAME)"

# Uninstall the application
uninstall:
	@echo "$(GREEN)[INFO]$(NC) Uninstalling $(APP_NAME)..."
	@sudo rm -f /usr/local/bin/$(APP_NAME)
	@echo "$(GREEN)[INFO]$(NC) Uninstallation complete"

# Generate documentation
docs:
	@echo "$(GREEN)[INFO]$(NC) Generating documentation..."
	@if command -v godoc >/dev/null 2>&1; then \
		echo "Documentation server starting at http://localhost:6060"; \
		godoc -http=:6060; \
	else \
		echo "$(YELLOW)[WARNING]$(NC) godoc not found, install with: go install golang.org/x/tools/cmd/godoc@latest"; \
	fi

# Check Go version
check-go:
	@echo "$(GREEN)[INFO]$(NC) Checking Go version..."
	@go version
	@echo "$(GREEN)[INFO]$(NC) Required Go version: $(GO_VERSION)"

# Security audit
security:
	@echo "$(GREEN)[INFO]$(NC) Running security audit..."
	@if command -v gosec >/dev/null 2>&1; then \
		gosec ./...; \
	else \
		echo "$(YELLOW)[WARNING]$(NC) gosec not found, install with: go install github.com/securecodewarrior/gosec/v2/cmd/gosec@latest"; \
	fi

# Show build info
info:
	@echo "$(GREEN)[INFO]$(NC) Build Information:"
	@echo "App Name: $(APP_NAME)"
	@echo "Version: $(VERSION)"
	@echo "Build Directory: $(BUILD_DIR)"
	@echo "Distribution Directory: $(DIST_DIR)"
	@echo "Go Version: $(shell go version)"
	@echo "Platform: $(shell go env GOOS)/$(shell go env GOARCH)"

# Release build
release: clean deps test lint build
	@echo "$(GREEN)[INFO]$(NC) Release build completed!"

# Help
help:
	@echo "WaddleBot Premium Desktop Bridge Makefile"
	@echo "=========================================="
	@echo ""
	@echo "Available targets:"
	@echo "  all           - Clean, install deps, and build (default)"
	@echo "  build         - Build all platforms"
	@echo "  build-windows - Build for Windows"
	@echo "  build-macos   - Build for macOS"
	@echo "  build-linux   - Build for Linux"
	@echo "  build-modules - Build plugin modules"
	@echo "  clean         - Clean build artifacts"
	@echo "  deps          - Install dependencies"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linter"
	@echo "  fmt           - Format code"
	@echo "  dev           - Run in development mode"
	@echo "  install       - Install the application"
	@echo "  uninstall     - Uninstall the application"
	@echo "  docs          - Generate documentation"
	@echo "  check-go      - Check Go version"
	@echo "  security      - Run security audit"
	@echo "  info          - Show build information"
	@echo "  release       - Full release build"
	@echo "  help          - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make build              # Build all platforms"
	@echo "  make build-windows      # Build for Windows only"
	@echo "  make dev                # Run in development mode"
	@echo "  make release            # Full release build"