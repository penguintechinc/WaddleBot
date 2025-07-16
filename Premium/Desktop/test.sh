#!/bin/bash

# WaddleBot Bridge Test Runner
# This script runs all unit tests and integration tests for the WaddleBot Bridge

set -e

echo "🤖 WaddleBot Bridge Test Runner"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✓ $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}✗ $message${NC}"
            ;;
        "INFO")
            echo -e "${YELLOW}ℹ $message${NC}"
            ;;
    esac
}

# Check if we're in the right directory
if [ ! -f "go.mod" ]; then
    print_status "ERROR" "go.mod not found. Please run this script from the project root."
    exit 1
fi

# Check if Go is installed
if ! command -v go &> /dev/null; then
    print_status "ERROR" "Go is not installed or not in PATH"
    exit 1
fi

print_status "INFO" "Go version: $(go version)"

# Clean up any previous test artifacts
print_status "INFO" "Cleaning up previous test artifacts..."
go clean -testcache

# Download dependencies
print_status "INFO" "Downloading dependencies..."
go mod download

# Run unit tests
print_status "INFO" "Running unit tests..."
UNIT_TEST_PACKAGES="./internal/..."

if go test -v -race -coverprofile=coverage.out $UNIT_TEST_PACKAGES; then
    print_status "SUCCESS" "Unit tests passed"
else
    print_status "ERROR" "Unit tests failed"
    exit 1
fi

# Run integration tests
print_status "INFO" "Running integration tests..."
if go test -v -race -tags=integration ./...; then
    print_status "SUCCESS" "Integration tests passed"
else
    print_status "ERROR" "Integration tests failed"
    exit 1
fi

# Generate coverage report
if [ -f "coverage.out" ]; then
    print_status "INFO" "Generating coverage report..."
    go tool cover -html=coverage.out -o coverage.html
    
    # Calculate coverage percentage
    COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}')
    print_status "SUCCESS" "Coverage report generated: coverage.html"
    print_status "INFO" "Total coverage: $COVERAGE"
    
    # Check if coverage is above threshold
    COVERAGE_NUM=$(echo $COVERAGE | sed 's/%//')
    if (( $(echo "$COVERAGE_NUM >= 80" | bc -l) )); then
        print_status "SUCCESS" "Coverage above 80% threshold"
    else
        print_status "ERROR" "Coverage below 80% threshold"
    fi
fi

# Run linter if available
if command -v golangci-lint &> /dev/null; then
    print_status "INFO" "Running linter..."
    if golangci-lint run; then
        print_status "SUCCESS" "Linter passed"
    else
        print_status "ERROR" "Linter found issues"
        exit 1
    fi
else
    print_status "INFO" "golangci-lint not found, skipping linter"
fi

# Run go vet
print_status "INFO" "Running go vet..."
if go vet ./...; then
    print_status "SUCCESS" "go vet passed"
else
    print_status "ERROR" "go vet found issues"
    exit 1
fi

# Run go fmt check
print_status "INFO" "Checking code formatting..."
UNFORMATTED=$(go fmt ./...)
if [ -z "$UNFORMATTED" ]; then
    print_status "SUCCESS" "Code is properly formatted"
else
    print_status "ERROR" "Code formatting issues found:"
    echo "$UNFORMATTED"
    exit 1
fi

# Check for security issues if gosec is available
if command -v gosec &> /dev/null; then
    print_status "INFO" "Running security scan..."
    if gosec ./...; then
        print_status "SUCCESS" "Security scan passed"
    else
        print_status "ERROR" "Security issues found"
        exit 1
    fi
else
    print_status "INFO" "gosec not found, skipping security scan"
fi

# Run benchmarks if requested
if [ "$1" = "bench" ]; then
    print_status "INFO" "Running benchmarks..."
    go test -bench=. -benchmem ./...
fi

# Final summary
echo ""
echo "🎉 All tests completed successfully!"
echo "================================"
print_status "SUCCESS" "Unit tests: PASSED"
print_status "SUCCESS" "Integration tests: PASSED"
print_status "SUCCESS" "Code quality checks: PASSED"

if [ -f "coverage.html" ]; then
    print_status "INFO" "Coverage report: coverage.html"
fi

echo ""
echo "To run specific test categories:"
echo "  Unit tests only:        go test ./internal/..."
echo "  Integration tests only: go test -tags=integration ./..."
echo "  With benchmarks:        ./test.sh bench"
echo "  Coverage report:        go tool cover -html=coverage.out"