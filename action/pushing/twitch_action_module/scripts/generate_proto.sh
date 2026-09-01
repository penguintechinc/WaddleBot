#!/bin/bash
# Generate gRPC code from proto file

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MODULE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$MODULE_DIR"

echo "Generating gRPC code from proto files..."

python3 -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    ./proto/twitch_action.proto

echo "gRPC code generated successfully!"
echo "Files created:"
echo "  - proto/twitch_action_pb2.py"
echo "  - proto/twitch_action_pb2_grpc.py"
