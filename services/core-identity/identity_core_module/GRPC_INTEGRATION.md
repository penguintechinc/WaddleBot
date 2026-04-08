# gRPC Integration for Identity Core Module

## Overview

This document describes the gRPC server integration added to the identity_core_module. The module now supports both REST API (via Quart) and gRPC services for identity lookups and platform linking.

## Architecture

### gRPC Services

The Identity Service provides two RPC methods:

1. **LookupIdentity** - Look up user identity across platforms
   - Input: Authentication token, platform name, platform user ID
   - Output: Hub user ID, username, linked platforms list

2. **GetLinkedPlatforms** - Get all platforms linked to a user
   - Input: Authentication token, hub user ID
   - Output: List of linked platform identities

### Proto Definition

The service definition is located in the shared proto directory:
- **File**: `/home/penguin/code/WaddleBot/libs/grpc_protos/identity.proto`

Proto structure includes:
- `IdentityService` - Main service definition
- `LookupIdentityRequest` / `LookupIdentityResponse` - Request/response for identity lookup
- `GetLinkedPlatformsRequest` / `GetLinkedPlatformsResponse` - Request/response for platform listing
- `PlatformIdentity` - Data structure for linked platform information

## Files Modified/Created

### New Files

1. **`services/grpc_handler.py`**
   - Pure Python implementation of gRPC servicer
   - Contains `IdentityServiceServicer` class with:
     - `verify_token()` - JWT token verification
     - `LookupIdentity()` - Identity lookup RPC method
     - `GetLinkedPlatforms()` - Platform listing RPC method
   - Data classes for request/response types
   - Comprehensive logging and error handling

2. **`compile_protos.sh`**
   - Bash script to compile proto files to Python
   - Handles grpcio-tools installation
   - Generates `*_pb2.py` and `*_grpc.py` files

### Modified Files

1. **`requirements.txt`**
   - Added `grpcio>=1.67.0`
   - Added `grpcio-tools>=1.67.0`
   - Resolved merge conflict (chose HEAD version of httpx)

2. **`config.py`**
   - Added `GRPC_PORT` configuration
   - Default: 50030 (can be overridden via GRPC_PORT environment variable)

3. **`app.py`**
   - Added gRPC server initialization in `startup()` hook
   - Added `_start_grpc_server()` coroutine for async gRPC server startup
   - Added `shutdown()` hook for graceful gRPC server shutdown
   - Imports IdentityServiceServicer from grpc_handler
   - gRPC server runs alongside REST API on separate port

## Configuration

### Environment Variables

```bash
# REST API port (Quart/Hypercorn)
MODULE_PORT=8050

# gRPC server port
GRPC_PORT=50030

# Database connection
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot

# API URLs
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Security
SECRET_KEY=change-me-in-production

# Logging
LOG_LEVEL=INFO
```

## Startup Behavior

When the identity_core_module starts:

1. Quart REST API server initializes on `0.0.0.0:8050`
2. gRPC server initializes on `0.0.0.0:50030`
3. Both servers run concurrently
4. Graceful shutdown of both servers on termination

## Proto Compilation

To regenerate Python gRPC code from proto files:

```bash
cd /home/penguin/code/WaddleBot/core/identity_core_module
bash compile_protos.sh
```

This will:
1. Check for protoc installation
2. Install grpcio-tools if needed
3. Generate Python bindings in `/home/penguin/code/WaddleBot/libs/grpc_protos/`

## Current Implementation Details

### IdentityServiceServicer

The servicer class (`/home/penguin/code/WaddleBot/core/identity_core_module/services/grpc_handler.py`) provides:

- **Data Classes** (pure Python):
  - `PlatformIdentity` - Represents a linked platform
  - `LookupIdentityRequest` - Request for identity lookup
  - `LookupIdentityResponse` - Response with user info
  - `GetLinkedPlatformsRequest` - Request for platform list
  - `GetLinkedPlatformsResponse` - Response with platforms

- **Methods**:
  - `verify_token()` - Validates JWT tokens (placeholder implementation)
  - `LookupIdentity()` - Implements identity lookup RPC
  - `GetLinkedPlatforms()` - Implements platform listing RPC

- **Features**:
  - Comprehensive error handling
  - Token authentication verification
  - Structured logging
  - Dataclass-based request/response handling

## Future Enhancements

1. **Proto Compilation**: Integrate automatic proto file compilation during build
2. **Database Integration**: Connect servicer methods to actual database queries
3. **JWT Verification**: Implement proper JWT token verification using SECRET_KEY
4. **gRPC Reflection**: Enable gRPC reflection for better client discovery
5. **Interceptors**: Add gRPC interceptors for logging, metrics, and auth
6. **Testing**: Add unit tests for servicer methods

## Testing

To test the gRPC service, you can:

1. Start the module: `python3 app.py`
2. Use grpcurl to test:
   ```bash
   # Check service health
   grpcurl -plaintext localhost:50030 list

   # Test LookupIdentity RPC
   grpcurl -plaintext \
     -d '{"token":"test-token","platform":"twitch","platform_user_id":"user123"}' \
     localhost:50030 waddlebot.identity.IdentityService/LookupIdentity
   ```

## References

- gRPC: https://grpc.io/docs/
- Proto3 Syntax: https://developers.google.com/protocol-buffers/docs/proto3
- Python gRPC: https://grpc.io/docs/languages/python/
- WaddleBot Proto Definitions: `/home/penguin/code/WaddleBot/libs/grpc_protos/`
