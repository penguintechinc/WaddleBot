# gRPC Integration Guide

High-performance identity lookups via gRPC protocol for inter-service communication.

## Overview

The Identity Core module provides a gRPC service alongside its REST API. gRPC offers:
- **Better Performance**: Binary protocol vs JSON text
- **Streaming**: Bidirectional streaming support
- **Type Safety**: Proto-based type definitions
- **Load Balancing**: Built-in LB support
- **Language Agnostic**: Clients in Python, Go, Node.js, etc.

## Server Configuration

### Port & Address

```
Host: 0.0.0.0
Port: 50030 (configurable via GRPC_PORT env var)
Protocol: gRPC over HTTP/2 (insecure, no TLS in dev)
```

### Environment Variables

```bash
GRPC_PORT=50030                     # gRPC server port
GRPC_MAX_CONCURRENT_STREAMS=100     # Max concurrent requests
GRPC_KEEPALIVE_TIME_MS=10000        # Keep-alive interval
```

## Service Definition

### Service: waddlebot.identity.IdentityService

Proto file location: `/home/penguin/code/waddlebot/libs/grpc_protos/identity.proto`

## RPC Methods

### 1. LookupIdentity

Look up user identity across platforms.

**Signature**:
```protobuf
rpc LookupIdentity(LookupIdentityRequest) returns (LookupIdentityResponse);
```

**Request**:
```protobuf
message LookupIdentityRequest {
  string token = 1;                  # JWT authentication token
  string platform = 2;               # Platform name (twitch, discord, slack, etc.)
  string platform_user_id = 3;       # User ID on the platform
}
```

**Response**:
```protobuf
message LookupIdentityResponse {
  int32 hub_user_id = 1;             # WaddleBot hub user ID
  string username = 2;               # Hub username
  repeated PlatformIdentity platforms = 3;  # All linked platforms
}

message PlatformIdentity {
  string platform = 1;               # Platform name
  string platform_user_id = 2;       # User ID on platform
  string display_name = 3;           # Platform display name
  string avatar_url = 4;             # User's avatar URL
  bool is_verified = 5;              # Account verification status
  string linked_at = 6;              # ISO8601 timestamp
}
```

**Example - Python**:
```python
import grpc
from grpc import aio
from identity_pb2 import LookupIdentityRequest, LookupIdentityResponse
from identity_pb2_grpc import IdentityServiceStub

async def lookup_user():
    async with aio.secure_channel('core-identity:50030', grpc.ssl_channel_credentials()) as channel:
        stub = IdentityServiceStub(channel)
        
        response = await stub.LookupIdentity(
            LookupIdentityRequest(
                token='eyJhbGc...',
                platform='twitch',
                platform_user_id='user123'
            )
        )
        
        print(f"Hub User ID: {response.hub_user_id}")
        print(f"Username: {response.username}")
        for platform in response.platforms:
            print(f"  {platform.platform}: {platform.platform_user_id}")
```

**Example - Go**:
```go
package main

import (
    "context"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    pb "waddlebot/identity"
)

func main() {
    conn, _ := grpc.Dial("core-identity:50030", grpc.WithTransportCredentials(insecure.NewCredentials()))
    defer conn.Close()
    
    client := pb.NewIdentityServiceClient(conn)
    
    resp, _ := client.LookupIdentity(context.Background(), &pb.LookupIdentityRequest{
        Token: "eyJhbGc...",
        Platform: "twitch",
        PlatformUserId: "user123",
    })
    
    fmt.Printf("Hub User ID: %d\n", resp.HubUserId)
    fmt.Printf("Username: %s\n", resp.Username)
}
```

**Example - Node.js**:
```javascript
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const packageDefinition = protoLoader.loadSync('identity.proto');
const proto = grpc.loadPackageDefinition(packageDefinition);

const client = new proto.waddlebot.identity.IdentityService(
  'core-identity:50030',
  grpc.credentials.createInsecure()
);

client.lookupIdentity({
  token: 'eyJhbGc...',
  platform: 'twitch',
  platformUserId: 'user123'
}, (err, response) => {
  if (!err) {
    console.log('Hub User ID:', response.hubUserId);
    console.log('Platforms:', response.platforms);
  }
});
```

### 2. GetLinkedPlatforms

Get all platforms linked to a user.

**Signature**:
```protobuf
rpc GetLinkedPlatforms(GetLinkedPlatformsRequest) returns (GetLinkedPlatformsResponse);
```

**Request**:
```protobuf
message GetLinkedPlatformsRequest {
  string token = 1;                  # JWT authentication token
  int32 hub_user_id = 2;             # WaddleBot hub user ID
}
```

**Response**:
```protobuf
message GetLinkedPlatformsResponse {
  int32 hub_user_id = 1;             # WaddleBot hub user ID
  string username = 2;               # Hub username
  repeated PlatformIdentity platforms = 3;  # All linked platforms
}
```

**Example - Python**:
```python
response = await stub.GetLinkedPlatforms(
    GetLinkedPlatformsRequest(
        token='eyJhbGc...',
        hub_user_id=12345
    )
)

for platform in response.platforms:
    print(f"{platform.platform}: {platform.platform_user_id}")
```

## Error Handling

### gRPC Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| `OK` (0) | Success | |
| `CANCELLED` (1) | Cancelled by client | Request cancelled |
| `UNKNOWN` (2) | Unknown error | Unexpected exception |
| `INVALID_ARGUMENT` (3) | Invalid argument | Missing token |
| `DEADLINE_EXCEEDED` (4) | Deadline exceeded | Request timeout |
| `NOT_FOUND` (5) | Not found | User not found |
| `ALREADY_EXISTS` (6) | Already exists | Duplicate identity |
| `PERMISSION_DENIED` (7) | Permission denied | Invalid token |
| `RESOURCE_EXHAUSTED` (8) | Resource exhausted | Rate limited |
| `FAILED_PRECONDITION` (9) | Failed precondition | Service unavailable |
| `ABORTED` (10) | Aborted | Concurrent modification |
| `OUT_OF_RANGE` (11) | Out of range | Invalid ID |
| `UNIMPLEMENTED` (12) | Not implemented | Method not available |
| `INTERNAL` (13) | Internal error | Database error |
| `UNAVAILABLE` (14) | Unavailable | Service down |
| `DATA_LOSS` (15) | Data loss | Data corruption |
| `UNAUTHENTICATED` (16) | Unauthenticated | Invalid token |

### Error Handling - Python

```python
from grpc import RpcError

try:
    response = await stub.LookupIdentity(request)
except RpcError as e:
    if e.code().name == 'NOT_FOUND':
        print(f"User not found: {e.details()}")
    elif e.code().name == 'UNAUTHENTICATED':
        print(f"Invalid token: {e.details()}")
    elif e.code().name == 'INVALID_ARGUMENT':
        print(f"Invalid request: {e.details()}")
    else:
        print(f"Error: {e.code().name}: {e.details()}")
```

## Testing gRPC Services

### Using grpcurl

```bash
# List available services
grpcurl -plaintext localhost:50030 list

# List methods of IdentityService
grpcurl -plaintext localhost:50030 list waddlebot.identity.IdentityService

# Call LookupIdentity
grpcurl -plaintext \
  -d '{
    "token":"eyJhbGc...",
    "platform":"twitch",
    "platformUserId":"user123"
  }' \
  localhost:50030 waddlebot.identity.IdentityService/LookupIdentity

# Call GetLinkedPlatforms
grpcurl -plaintext \
  -d '{
    "token":"eyJhbGc...",
    "hubUserId":12345
  }' \
  localhost:50030 waddlebot.identity.IdentityService/GetLinkedPlatforms
```

### Using Python grpcurl

```python
import subprocess
import json

def call_grpc_method(method, request_json):
    cmd = [
        'grpcurl',
        '-plaintext',
        '-d', json.dumps(request_json),
        'localhost:50030',
        f'waddlebot.identity.IdentityService/{method}'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

response = call_grpc_method('LookupIdentity', {
    'token': 'eyJhbGc...',
    'platform': 'twitch',
    'platformUserId': 'user123'
})
```

## Proto Compilation

### Regenerate Python Bindings

```bash
cd /home/penguin/code/waddlebot/services/core-identity/identity_core_module
bash compile_protos.sh
```

This generates:
- `identity_pb2.py` - Message classes
- `identity_pb2_grpc.py` - Service stubs

### Manual Compilation

```bash
python -m grpc_tools.protoc \
  -I/home/penguin/code/waddlebot/libs/grpc_protos \
  --python_out=/home/penguin/code/waddlebot/libs/grpc_protos \
  --grpc_python_out=/home/penguin/code/waddlebot/libs/grpc_protos \
  /home/penguin/code/waddlebot/libs/grpc_protos/identity.proto
```

## Connection Management

### Connection Pooling (Python)

```python
# Create channel once, reuse
channel = aio.secure_channel('core-identity:50030', grpc.ssl_channel_credentials())
stub = IdentityServiceStub(channel)

# Keep channel alive for multiple calls
response1 = await stub.LookupIdentity(request1)
response2 = await stub.GetLinkedPlatforms(request2)

# Close when done
await channel.close()
```

### Connection Pooling (Go)

```go
// Create connection once, reuse
conn, _ := grpc.Dial("core-identity:50030", grpc.WithTransportCredentials(insecure.NewCredentials()))
defer conn.Close()

client := pb.NewIdentityServiceClient(conn)

// Multiple calls reuse same connection
resp1, _ := client.LookupIdentity(ctx, req1)
resp2, _ := client.GetLinkedPlatforms(ctx, req2)
```

## Performance Considerations

### Latency

- Typical request: 10-50ms
- Database lookup: 5-20ms
- Token verification: 5-10ms
- Network overhead: <5ms (local)

### Throughput

- Single server: 1000+ requests/second
- With 4 workers: 4000+ requests/second

### Best Practices

1. **Connection Reuse**: Keep channels alive, don't create per-request
2. **Batch Requests**: Use multiple stub calls in sequence
3. **Timeouts**: Set reasonable deadlines on requests
4. **Retry Logic**: Implement exponential backoff for transient failures
5. **Circuit Breaker**: Fail fast if service degraded

### Timeout Example - Python

```python
ctx = aio.metadata.CallCredentials('authorization', f'Bearer {token}')

# 5 second timeout
call = stub.LookupIdentity(
    request,
    timeout=5.0
)

try:
    response = await call
except grpc.RpcError as e:
    if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
        print("Request timeout")
```

## Metadata & Headers

### Authorization Metadata

```python
# Add auth header
metadata = [
    ('authorization', f'Bearer {jwt_token}')
]

response = await stub.LookupIdentity(
    request,
    metadata=metadata
)
```

### Request Metadata - Python

```python
# Add custom metadata
metadata = [
    ('authorization', f'Bearer {token}'),
    ('x-request-id', 'req-12345'),
    ('user-agent', 'my-client/1.0')
]

response = await stub.LookupIdentity(request, metadata=metadata)
```

## Deployment Considerations

### Dockerfile Health Check

```dockerfile
# Check gRPC service health
HEALTHCHECK --interval=30s --timeout=3s \
  CMD grpcurl -plaintext localhost:50030 list || exit 1
```

### Kubernetes Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: core-identity-grpc
spec:
  ports:
  - port: 50030
    targetPort: 50030
    protocol: TCP
    name: grpc
  selector:
    app: core-identity
```

### Kubernetes Probe

```yaml
containers:
- name: core-identity
  ports:
  - containerPort: 50030
    name: grpc
  livenessProbe:
    exec:
      command:
      - grpcurl
      - -plaintext
      - localhost:50030
      - list
    initialDelaySeconds: 10
    periodSeconds: 10
```

## Security

### Token Verification

All gRPC requests require valid JWT token. Token is verified using:
- `SECRET_KEY` from config
- `JWT_ALGORITHM` (default: HS256)
- Expected `aud` claim: "core-identity"

Invalid tokens return `UNAUTHENTICATED` (status 16).

### Mutual TLS (Future)

For production, enable mTLS:

```python
credentials = grpc.ssl_channel_credentials(
    root_certificates=open('ca.pem', 'rb').read(),
    private_key=open('client.key', 'rb').read(),
    certificate_chain=open('client.pem', 'rb').read()
)

channel = aio.secure_channel('core-identity:50030', credentials)
```

## Monitoring & Observability

### Metrics to Track

- Request latency (p50, p95, p99)
- Error rate by status code
- Throughput (requests/second)
- Active connections

### Logging Example - Python

```python
import logging

logging.basicConfig(level=logging.DEBUG)

response = await stub.LookupIdentity(request)
# Debug logging shows request/response details
```

## Related Documentation

- [Core Identity Service README](../README.md) - Combined service overview
- [IDENTITY_CORE.md](./IDENTITY_CORE.md) - Identity module REST API
- [Proto Definition](../../libs/grpc_protos/identity.proto)
