#!/bin/bash
# YouTube Action Module Build Script

set -e

echo "==================================="
echo "YouTube Action Module Build Script"
echo "==================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running in virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "Not running in a virtual environment"
fi

# Generate protobuf files
echo ""
echo "Step 1: Generating protobuf files..."
python3 -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    ./proto/youtube_action.proto

if [ $? -eq 0 ]; then
    print_status "Protobuf files generated successfully"
else
    print_error "Failed to generate protobuf files"
    exit 1
fi

# Build Docker image
echo ""
echo "Step 2: Building Docker image..."
docker build -t waddlebot/youtube-action:latest .

if [ $? -eq 0 ]; then
    print_status "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    exit 1
fi

# Optional: Tag with version
if [ -n "$1" ]; then
    echo ""
    echo "Step 3: Tagging image with version $1..."
    docker tag waddlebot/youtube-action:latest waddlebot/youtube-action:$1
    print_status "Image tagged as waddlebot/youtube-action:$1"
fi

echo ""
print_status "Build complete!"
echo ""
echo "To run the container:"
echo "  docker run -d --name youtube-action -p 8073:8073 -p 50054:50054 --env-file .env waddlebot/youtube-action:latest"
echo ""
echo "To view logs:"
echo "  docker logs -f youtube-action"
echo ""
