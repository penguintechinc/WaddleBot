# Identity Core Module - API Reference

## Overview

The Identity Core Module provides unified cross-platform identity management for Waddles. It supports both REST API (via Quart) and gRPC services for identity linking, user authentication, and platform integration.

**Module Version:** 2.0.0
**Module Name:** identity_core_module

## Base URLs

| Protocol | Default URL | Port | Environment Variable |
|----------|-------------|------|---------------------|
| REST API | http://localhost:8050 | 8050 | `MODULE_PORT` |
| gRPC | localhost:50030 | 50030 | `GRPC_PORT` |

## Authentication

Most endpoints require authentication via API key or session token.

### API Key Authentication

```http
X-API-Key: your-api-key-here
```

### Session Token Authentication

```http
Authorization: Bearer your-session-token
```

---

## REST API Endpoints

### Health & Monitoring

#### GET /health

Basic health check endpoint for service monitoring.

**Response:**
```json
{
  "status": "healthy",
  "module": "identity_core_module",
  "version": "2.0.0",
  "timestamp": "2025-12-16T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is unhealthy

---

#### GET /healthz

Kubernetes liveness probe endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Codes:**
- `200 OK` - Service is alive
- `503 Service Unavailable` - Service needs restart

---

#### GET /metrics

Prometheus metrics endpoint for monitoring.

**Response Format:** Prometheus text-based exposition format

```
# HELP module_info Module information
# TYPE module_info gauge
module_info{module="identity_core_module",version="2.0.0"} 1
```

**Status Codes:**
- `200 OK` - Metrics available

---

#### GET /api/v1/status

Module operational status.

**Response:**
```json
{
  "status": "operational",
  "module": "identity_core_module"
}
```

**Status Codes:**
- `200 OK` - Module is operational

---

### Identity Linking

#### POST /identity/link

Initiate cross-platform identity linking process.

**Authentication:** Required (API Key or Session Token)

**Request Body:**
```json
{
  "platform": "twitch",
  "platform_id": "user123456",
  "platform_username": "coolstreamer"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| platform | string | Yes | Platform name (twitch, discord, youtube, etc.) |
| platform_id | string | Yes | Platform-specific user ID |
| platform_username | string | Yes | Platform username/display name |

**Response:**
```json
{
  "verification_id": "ver_abc123",
  "verification_code": "WXYZ-1234",
  "expires_at": "2025-12-16T11:30:00Z",
  "message": "Verification code sent. Please verify within 1 hour."
}
```

**Status Codes:**
- `200 OK` - Link initiated successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `409 Conflict` - Identity already linked

**Example:**
```bash
curl -X POST http://localhost:8050/identity/link \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "twitch",
    "platform_id": "123456789",
    "platform_username": "streamername"
  }'
```

---

#### POST /identity/verify

Verify platform identity with verification code.

**Authentication:** Required

**Request Body:**
```json
{
  "verification_code": "WXYZ-1234",
  "platform": "twitch"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| verification_code | string | Yes | Code from link initiation |
| platform | string | Yes | Platform being verified |

**Response:**
```json
{
  "success": true,
  "user_id": 42,
  "platform": "twitch",
  "linked_at": "2025-12-16T10:45:00Z"
}
```

**Status Codes:**
- `200 OK` - Verification successful
- `400 Bad Request` - Invalid verification code
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Verification code not found or expired

---

#### DELETE /identity/unlink

Remove platform identity link.

**Authentication:** Required

**Request Body:**
```json
{
  "platform": "twitch",
  "platform_id": "123456789"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Platform identity unlinked successfully"
}
```

**Status Codes:**
- `200 OK` - Unlinked successfully
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Identity link not found

---

### Identity Lookup

#### GET /identity/user/{user_id}

Get all platform identities for a hub user.

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | integer | Hub user ID |

**Response:**
```json
{
  "user_id": 42,
  "username": "waddle_user",
  "identities": [
    {
      "platform": "twitch",
      "platform_user_id": "123456789",
      "platform_username": "streamername",
      "linked_at": "2025-01-01T00:00:00Z",
      "is_primary": true
    },
    {
      "platform": "discord",
      "platform_user_id": "987654321",
      "platform_username": "discordname",
      "linked_at": "2025-01-02T00:00:00Z",
      "is_primary": false
    }
  ]
}
```

**Status Codes:**
- `200 OK` - User found
- `401 Unauthorized` - Authentication required
- `404 Not Found` - User not found

---

#### GET /identity/platform/{platform}/{platform_id}

Lookup hub user by platform identity.

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| platform | string | Platform name |
| platform_id | string | Platform-specific user ID |

**Response:**
```json
{
  "user_id": 42,
  "display_name": "Waddle User",
  "platform": "twitch",
  "platform_user_id": "123456789",
  "platform_username": "streamername",
  "linked_at": "2025-01-01T00:00:00Z"
}
```

**Status Codes:**
- `200 OK` - Platform user found
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Platform identity not found

---

### Verification Management

#### GET /identity/pending

Get pending verification requests for current user.

**Authentication:** Required

**Response:**
```json
{
  "pending_verifications": [
    {
      "verification_id": "ver_abc123",
      "platform": "youtube",
      "platform_username": "youtubechannel",
      "created_at": "2025-12-16T10:30:00Z",
      "expires_at": "2025-12-16T11:30:00Z"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Pending verifications retrieved
- `401 Unauthorized` - Authentication required

---

#### POST /identity/resend

Resend verification code.

**Authentication:** Required

**Request Body:**
```json
{
  "verification_id": "ver_abc123"
}
```

**Response:**
```json
{
  "success": true,
  "verification_code": "ABCD-5678",
  "expires_at": "2025-12-16T11:45:00Z"
}
```

**Status Codes:**
- `200 OK` - Code resent
- `400 Bad Request` - Invalid verification ID
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Verification not found or expired

---

### API Key Management

#### POST /identity/api-keys

Create new API key.

**Authentication:** Required

**Request Body:**
```json
{
  "name": "My API Key",
  "expires_in_days": 365
}
```

**Response:**
```json
{
  "api_key": "wbt_1234567890abcdef",
  "key_id": "key_xyz789",
  "name": "My API Key",
  "created_at": "2025-12-16T10:30:00Z",
  "expires_at": "2026-12-16T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - API key created
- `401 Unauthorized` - Authentication required

---

#### GET /identity/api-keys

List all API keys for current user.

**Authentication:** Required

**Response:**
```json
{
  "api_keys": [
    {
      "key_id": "key_xyz789",
      "name": "My API Key",
      "created_at": "2025-12-16T10:30:00Z",
      "expires_at": "2026-12-16T10:30:00Z",
      "last_used": "2025-12-16T10:45:00Z"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Keys retrieved
- `401 Unauthorized` - Authentication required

---

#### POST /identity/api-keys/{key_id}/regenerate

Regenerate API key (invalidates old key).

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| key_id | string | API key ID |

**Response:**
```json
{
  "api_key": "wbt_newkey9876543210",
  "key_id": "key_xyz789",
  "expires_at": "2026-12-16T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Key regenerated
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Key not found

---

#### DELETE /identity/api-keys/{key_id}

Revoke API key.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "message": "API key revoked successfully"
}
```

**Status Codes:**
- `200 OK` - Key revoked
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Key not found

---

### User Authentication

#### POST /auth/register

Register new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "username": "myusername"
}
```

**Response:**
```json
{
  "user_id": 42,
  "email": "user@example.com",
  "username": "myusername",
  "created_at": "2025-12-16T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Registration successful
- `400 Bad Request` - Invalid input
- `409 Conflict` - Email or username already exists

---

#### POST /auth/login

Login to account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user_id": 42,
  "username": "myusername",
  "expires_at": "2025-12-17T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Login successful
- `401 Unauthorized` - Invalid credentials

---

#### GET /auth/profile

Get current user profile.

**Authentication:** Required

**Response:**
```json
{
  "user_id": 42,
  "email": "user@example.com",
  "username": "myusername",
  "display_name": "My Display Name",
  "avatar_url": "https://example.com/avatar.png",
  "created_at": "2025-12-16T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Profile retrieved
- `401 Unauthorized` - Authentication required

---

#### PUT /auth/profile

Update user profile.

**Authentication:** Required

**Request Body:**
```json
{
  "display_name": "New Display Name",
  "avatar_url": "https://example.com/new-avatar.png"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": 42,
  "display_name": "New Display Name",
  "updated_at": "2025-12-16T10:45:00Z"
}
```

**Status Codes:**
- `200 OK` - Profile updated
- `401 Unauthorized` - Authentication required

---

#### POST /auth/logout

Logout and invalidate session.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

**Status Codes:**
- `200 OK` - Logout successful
- `401 Unauthorized` - Authentication required

---

### Statistics & Monitoring

#### GET /identity/stats

Get identity statistics (admin only).

**Authentication:** Required (Admin)

**Response:**
```json
{
  "total_users": 1542,
  "total_identities": 3284,
  "identities_by_platform": {
    "twitch": 1542,
    "discord": 987,
    "youtube": 755
  },
  "new_users_last_30_days": 45,
  "active_verifications": 12
}
```

**Status Codes:**
- `200 OK` - Statistics retrieved
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Admin access required

---

#### GET /identity/health

Identity service health check.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "grpc_server": "running"
}
```

**Status Codes:**
- `200 OK` - Service healthy
- `503 Service Unavailable` - Service unhealthy

---

## gRPC API

### Service Definition

**Package:** `waddlebot.identity`
**Service:** `IdentityService`

### Proto File

Located at: `/home/penguin/code/Waddles/libs/grpc_protos/identity.proto`

---

### RPC Methods

#### LookupIdentity

Lookup user identity across platforms.

**Request:**
```protobuf
message LookupIdentityRequest {
    string token = 1;
    string platform = 2;
    string platform_user_id = 3;
}
```

**Response:**
```protobuf
message LookupIdentityResponse {
    bool success = 1;
    int32 hub_user_id = 2;
    string username = 3;
    repeated PlatformIdentity linked_platforms = 4;
    waddlebot.common.Error error = 5;
}
```

**Example (grpcurl):**
```bash
grpcurl -plaintext \
  -d '{
    "token": "test-token",
    "platform": "twitch",
    "platform_user_id": "123456789"
  }' \
  localhost:50030 \
  waddlebot.identity.IdentityService/LookupIdentity
```

---

#### GetLinkedPlatforms

Get all platforms linked to a user.

**Request:**
```protobuf
message GetLinkedPlatformsRequest {
    string token = 1;
    int32 hub_user_id = 2;
}
```

**Response:**
```protobuf
message GetLinkedPlatformsResponse {
    bool success = 1;
    repeated PlatformIdentity platforms = 2;
    waddlebot.common.Error error = 3;
}
```

**Example (grpcurl):**
```bash
grpcurl -plaintext \
  -d '{
    "token": "test-token",
    "hub_user_id": 42
  }' \
  localhost:50030 \
  waddlebot.identity.IdentityService/GetLinkedPlatforms
```

---

### Data Types

#### PlatformIdentity

```protobuf
message PlatformIdentity {
    string platform = 1;
    string platform_user_id = 2;
    string platform_username = 3;
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| INVALID_REQUEST | 400 | Malformed request data |
| UNAUTHORIZED | 401 | Missing or invalid authentication |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource already exists |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Internal server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable |

---

## Rate Limiting

Rate limits apply per API key or user session:

- **Default:** 100 requests per minute
- **Burst:** 200 requests per minute

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1702729200
```

---

## Supported Platforms

| Platform | Code | Description |
|----------|------|-------------|
| Twitch | twitch | Twitch streaming platform |
| Discord | discord | Discord chat platform |
| YouTube | youtube | YouTube video platform |
| Kick | kick | Kick streaming platform |
| TikTok | tiktok | TikTok short video platform |

---

## Best Practices

### Security
- Always use HTTPS in production
- Store API keys securely (environment variables, secrets manager)
- Rotate API keys regularly
- Never commit API keys to version control

### Performance
- Use gRPC for high-throughput identity lookups
- Cache user identity data client-side with short TTL
- Batch requests when possible

### Error Handling
- Implement exponential backoff for retries
- Log all error responses for debugging
- Validate input data before making requests

---

## Changelog

### Version 2.0.0
- Added gRPC support for identity lookups
- Implemented cross-platform identity linking
- Added API key management endpoints
- Enhanced health check endpoints
- Added Prometheus metrics support
