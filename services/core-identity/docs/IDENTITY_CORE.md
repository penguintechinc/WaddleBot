# Identity Core Module - Reference

User identity management and cross-platform identity resolution.

## Overview

The Identity Core module manages user identities across multiple platforms (Twitch, Discord, Slack, YouTube, etc.). It provides both REST API and gRPC interfaces for identity lookup, platform linking, and cross-platform identity resolution.

## Key Features

- **Cross-Platform Identity Mapping** - Link user identities across multiple platforms
- **Platform Linking** - Establish and manage connections between hub users and platform accounts
- **Identity Lookup** - Resolve identity across platforms via REST or gRPC
- **JWT Authentication** - Token-based authentication for API access
- **gRPC Service** - High-performance identity lookups via gRPC

## Configuration

### Environment Variables

```bash
# Service Port (REST API)
MODULE_PORT=8050
MODULE_HOST=0.0.0.0

# gRPC Server
GRPC_PORT=50030

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Authentication
SECRET_KEY=change-me-in-production
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256

# Router Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Logging
LOG_LEVEL=INFO
```

## REST API Endpoints

### Status
- `GET /api/v1/status` - Identity module status
  - Returns: Module name, version, operational status

## gRPC Services

### Port
- **50030** - gRPC service port

### Service: waddlebot.identity.IdentityService

#### RPC: LookupIdentity

Look up user identity across platforms.

**Request**:
```protobuf
message LookupIdentityRequest {
  string token = 1;                  # JWT authentication token
  string platform = 2;               # Platform name (twitch, discord, etc.)
  string platform_user_id = 3;       # User ID on the platform
}
```

**Response**:
```protobuf
message LookupIdentityResponse {
  int32 hub_user_id = 1;             # WaddleBot hub user ID
  string username = 2;               # Hub username
  repeated PlatformIdentity platforms = 3;  # Linked platforms
}
```

**Example Usage**:
```bash
grpcurl -plaintext \
  -d '{"token":"<jwt>","platform":"twitch","platform_user_id":"user123"}' \
  localhost:50030 waddlebot.identity.IdentityService/LookupIdentity
```

#### RPC: GetLinkedPlatforms

Get all platforms linked to a user.

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

message PlatformIdentity {
  string platform = 1;               # Platform name
  string platform_user_id = 2;       # User ID on platform
  string display_name = 3;           # Platform display name
  string avatar_url = 4;             # User's avatar
  bool is_verified = 5;              # Account verification status
  string linked_at = 6;              # ISO8601 timestamp
}
```

**Example Usage**:
```bash
grpcurl -plaintext \
  -d '{"token":"<jwt>","hub_user_id":12345}' \
  localhost:50030 waddlebot.identity.IdentityService/GetLinkedPlatforms
```

## Database Schema

### users
User profile table in identity database.

```sql
id (Integer, Primary Key)
username (String)
email (String, Unique)
hub_user_id (Integer)
is_active (Boolean)
created_at (Timestamp)
updated_at (Timestamp)
```

### platform_identities
Cross-platform identity mapping.

```sql
id (Integer, Primary Key)
hub_user_id (Integer, Foreign Key → users.hub_user_id)
platform (String)                    # twitch, discord, slack, youtube, etc.
platform_user_id (String)
platform_username (String)
is_verified (Boolean)
avatar_url (String)
created_at (Timestamp)
updated_at (Timestamp)
```

### platform_links
User-to-platform linking relationships.

```sql
id (Integer, Primary Key)
user_id (Integer, Foreign Key → users.id)
platform (String)
platform_user_id (String)
scopes (Array of Strings)           # OAuth scopes granted
is_active (Boolean)
linked_at (Timestamp)
unlinked_at (Timestamp)
created_at (Timestamp)
updated_at (Timestamp)
```

## Authentication

### JWT Token Requirements

All gRPC and protected REST endpoints require JWT token:

```json
{
  "sub": "user123",
  "iss": "https://auth-service.example.com",
  "aud": ["core-identity"],
  "iat": 1234567890,
  "exp": 1234571490,
  "scope": "identity:read identity:write",
  "tenant": "hub"
}
```

### Token Verification

Token is verified using `SECRET_KEY` and `JWT_ALGORITHM`:

```python
jwt.decode(
    token,
    key=SECRET_KEY,
    algorithms=[JWT_ALGORITHM],
    audience="core-identity"
)
```

## Error Handling

### Common gRPC Errors

| Code | Meaning |
|------|---------|
| `INVALID_ARGUMENT` | Missing or invalid token, platform, or user ID |
| `UNAUTHENTICATED` | Token verification failed |
| `NOT_FOUND` | User or platform identity not found |
| `PERMISSION_DENIED` | Insufficient permissions for requested action |
| `INTERNAL` | Unexpected server error |

### Example Error Response

```protobuf
message Status {
  int32 code = 1;                    # gRPC status code
  string message = 2;                # Error message
  string details = 3;                # Additional context
}
```

## Logging

All operations logged with:
- Timestamp
- Log level (INFO, WARNING, ERROR)
- Module: identity_core
- Detailed message

Example:
```
2025-02-05 10:30:15 [identity_core] INFO: Platform identity lookup successful: user_id=123, platform=twitch
2025-02-05 10:31:20 [identity_core] ERROR: Token verification failed: Invalid signature
```

## Integration Patterns

### Looking Up Cross-Platform Identity

```python
# gRPC client (Python)
import grpc
from grpc import aio

channel = aio.secure_channel('localhost:50030', grpc.ssl_channel_credentials())
stub = IdentityServiceStub(channel)

response = await stub.LookupIdentity(
    LookupIdentityRequest(
        token=jwt_token,
        platform='twitch',
        platform_user_id='user123'
    )
)

hub_user_id = response.hub_user_id
linked_platforms = response.platforms
```

### Checking Linked Platforms

```python
response = await stub.GetLinkedPlatforms(
    GetLinkedPlatformsRequest(
        token=jwt_token,
        hub_user_id=12345
    )
)

for platform in response.platforms:
    print(f"{platform.platform}: {platform.platform_user_id}")
```

## Performance Considerations

- gRPC connections: Keep channels alive for connection pooling
- Database queries: Indexed lookups on platform, platform_user_id
- Token verification: Cached for 5 minutes per unique token
- Response size: Typical <5KB per request

## Security Considerations

- Tokens never logged or exposed in responses
- Platform user IDs treated as identifiers, not secrets
- All database queries parameterized
- gRPC requests require valid JWT with correct audience

## Related Documentation

- [Core Identity Service README](../README.md) - Combined service overview
- [GRPC_INTEGRATION.md](./GRPC_INTEGRATION.md) - gRPC setup and details
- [Database Schema](../../docs/architecture/database-schema.md)
