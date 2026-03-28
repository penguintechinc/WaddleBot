#!/bin/bash
# Build script for Slack Action Module

set -e

echo "==================================="
echo "Slack Action Module - Build Script"
echo "==================================="

# Generate proto files
echo ""
echo "Step 1: Generating gRPC proto files..."
python3 -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    ./proto/slack_action.proto

echo "✓ Proto files generated successfully"

# Build Docker image
echo ""
echo "Step 2: Building Docker image..."
docker build -t waddlebot/slack-action:latest .

echo "✓ Docker image built successfully"

# Show image info
echo ""
echo "Docker image information:"
docker images waddlebot/slack-action:latest

echo ""
echo "==================================="
echo "Build completed successfully!"
echo "==================================="
echo ""
echo "To run the container:"
echo "  docker run -d -p 8071:8071 -p 50052:50052 \\"
echo "    -e SLACK_BOT_TOKEN=your-token \\"
echo "    -e DATABASE_URL=your-db-url \\"
echo "    -e MODULE_SECRET_KEY=your-secret \\"
echo "    waddlebot/slack-action:latest"
echo ""
