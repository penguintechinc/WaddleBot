#!/bin/bash

# gRPC Proto Compilation Script
# Generates Python gRPC code from proto definitions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROTO_DIR="$PROJECT_ROOT/libs/grpc_protos"

echo "Compiling gRPC proto files..."
echo "Proto directory: $PROTO_DIR"
echo "Output directory: $PROTO_DIR"

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "Error: protoc is not installed"
    echo "Install with: sudo apt-get install protobuf-compiler"
    exit 1
fi

# Check if grpcio-tools is installed
python3 -c "import grpc_tools" 2>/dev/null || {
    echo "Installing grpcio-tools..."
    pip install grpcio-tools>=1.67.0
}

# Compile identity.proto
echo "Compiling identity.proto..."
python3 -m grpc_tools.protoc \
    -I "$PROTO_DIR" \
    --python_out="$PROTO_DIR" \
    --pyi_out="$PROTO_DIR" \
    --grpc_python_out="$PROTO_DIR" \
    "$PROTO_DIR/identity.proto"

echo "Proto compilation complete!"
echo "Generated files:"
ls -la "$PROTO_DIR"/*pb2.py 2>/dev/null || echo "No pb2 files generated"
ls -la "$PROTO_DIR"/*grpc.py 2>/dev/null || echo "No grpc files generated"
