# YouTube Music Interaction Module - API Reference

## Overview

The YouTube Music Interaction Module provides a REST API for managing YouTube Music integration with WaddleBot. All endpoints return JSON responses and use standard HTTP status codes.

## Base URL

```
http://localhost:8025/api/v1
```

In Docker Compose/Kubernetes:
```
http://youtube-music-interaction:8025/api/v1
```

## Common Response Format

All successful responses follow this structure:

```json
{
  "status": "success",
  "data": {},
  "message": "Operation description",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

Error responses:

```json
{
  "status": "error",
  "error": "ERROR_CODE",
  "message": "Human-readable error description",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

## Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 204 | No Content | Successful request with no response body |
| 400 | Bad Request | Invalid request parameters or body |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | User lacks permission for operation |
| 404 | Not Found | Resource does not exist |
| 405 | Method Not Allowed | HTTP method not allowed for endpoint |
| 409 | Conflict | Request conflicts with current state |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Service temporarily unavailable |

## Health & Monitoring Endpoints

### Health Check

**Endpoint**: `GET /health`

**Description**: Basic health check for the module.

**Request**:
```bash
curl http://localhost:8025/health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "module": "youtube_music_interaction_module",
  "version": "2.0.0",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

**Error Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "module": "youtube_music_interaction_module",
  "version": "2.0.0",
  "error": "Database connection failed",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

---

### Kubernetes Health Probe

**Endpoint**: `GET /healthz`

**Description**: Extended health check for Kubernetes liveness/readiness probes.

**Request**:
```bash
curl http://localhost:8025/healthz
```

**Response** (200 OK - fully healthy):
```json
{
  "status": "healthy",
  "module": "youtube_music_interaction_module",
  "version": "2.0.0",
  "checks": {
    "database": "connected",
    "redis": "connected"
  },
  "timestamp": "2026-02-16T12:34:56Z"
}
```

**Response** (503 Service Unavailable - degraded):
```json
{
  "status": "degraded",
  "module": "youtube_music_interaction_module",
  "version": "2.0.0",
  "checks": {
    "database": "connected",
    "redis": "disconnected"
  },
  "errors": {
    "redis": "Connection refused"
  },
  "timestamp": "2026-02-16T12:34:56Z"
}
```

---

### Prometheus Metrics

**Endpoint**: `GET /metrics`

**Description**: Prometheus-formatted metrics for monitoring.

**Request**:
```bash
curl http://localhost:8025/metrics
```

**Response** (200 OK):
```
# HELP waddlebot_info Module information
# TYPE waddlebot_info gauge
waddlebot_info{module="youtube_music_interaction_module",version="2.0.0"} 1

# HELP waddlebot_requests_total Total HTTP requests
# TYPE waddlebot_requests_total counter
waddlebot_requests_total{endpoint="/health",method="GET",status="200"} 42
waddlebot_requests_total{endpoint="/api/v1/status",method="GET",status="200"} 15

# HELP waddlebot_request_duration_seconds Request latency
# TYPE waddlebot_request_duration_seconds histogram
waddlebot_request_duration_seconds_bucket{endpoint="/health",le="0.1"} 40
waddlebot_request_duration_seconds_bucket{endpoint="/health",le="0.5"} 42

# HELP youtube_music_interaction_module_oauth_tokens_total OAuth token operations
# TYPE youtube_music_interaction_module_oauth_tokens_total counter
youtube_music_interaction_module_oauth_tokens_total{operation="exchange"} 5
youtube_music_interaction_module_oauth_tokens_total{operation="refresh"} 12
```

---

## API Endpoints

### Module Status

**Endpoint**: `GET /api/v1/status`

**Description**: Returns the operational status of the module.

**Request**:
```bash
curl http://localhost:8025/api/v1/status
```

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "status": "operational",
    "module": "youtube_music_interaction_module",
    "version": "2.0.0",
    "uptime_seconds": 3600,
    "requests_processed": 157
  },
  "message": "Module is operational",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

---

## OAuth 2.0 Endpoints

### Exchange Authorization Code for Access Token

**Endpoint**: `POST /api/v1/oauth/token`

**Description**: Exchanges an OAuth authorization code for access and refresh tokens.

**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "code": "4/0AdY47_bXxxx...",
  "redirect_uri": "http://localhost:8025/oauth/callback",
  "state": "random_state_value"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "access_token": "ya29.a0AfH6SMBxxx...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "1//0gF6xxx...",
    "scope": "https://www.googleapis.com/auth/youtube.readonly"
  },
  "message": "Token exchanged successfully",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

**Error Response** (400 Bad Request):
```json
{
  "status": "error",
  "error": "INVALID_CODE",
  "message": "Authorization code is invalid or expired",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

---

### Refresh Access Token

**Endpoint**: `POST /api/v1/oauth/refresh`

**Description**: Refreshes an expired access token using a refresh token.

**Headers**:
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "refresh_token": "1//0gF6xxx..."
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "access_token": "ya29.a0AfH6SMByyy...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "https://www.googleapis.com/auth/youtube.readonly"
  },
  "message": "Token refreshed successfully",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

**Error Response** (401 Unauthorized):
```json
{
  "status": "error",
  "error": "INVALID_REFRESH_TOKEN",
  "message": "Refresh token is invalid or revoked",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

---

## Credential Management Endpoints

### Store OAuth Credentials

**Endpoint**: `POST /api/v1/credentials/store`

**Description**: Stores OAuth credentials in the platform_integrations table.

**Headers**:
```
Content-Type: application/json
Authorization: Bearer <admin_token>
```

**Request Body**:
```json
{
  "client_id": "xxx.apps.googleusercontent.com",
  "client_secret": "GOCSPX-xxx",
  "access_token": "ya29.a0AfH6SMBxxx...",
  "refresh_token": "1//0gF6xxx...",
  "community_id": "123456789",
  "user_id": "user_discord_id"
}
```

**Response** (201 Created):
```json
{
  "status": "success",
  "data": {
    "credential_id": 42,
    "platform": "youtube",
    "integration_type": "bot",
    "is_active": true
  },
  "message": "Credentials stored successfully",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

**Error Response** (400 Bad Request):
```json
{
  "status": "error",
  "error": "MISSING_FIELDS",
  "message": "Missing required fields: client_id, client_secret",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

---

### Retrieve Credentials

**Endpoint**: `GET /api/v1/credentials`

**Description**: Retrieves stored OAuth credentials (admin only).

**Headers**:
```
Authorization: Bearer <admin_token>
```

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `community_id` | string | No | - | Filter by community |
| `user_id` | string | No | - | Filter by user |
| `is_active` | boolean | No | true | Filter by active status |

**Request**:
```bash
curl http://localhost:8025/api/v1/credentials?community_id=123456789&is_active=true
```

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "credentials": [
      {
        "credential_id": 42,
        "platform": "youtube",
        "community_id": "123456789",
        "user_id": "user_discord_id",
        "is_active": true,
        "created_at": "2026-02-10T12:34:56Z",
        "updated_at": "2026-02-16T10:20:30Z"
      }
    ],
    "total": 1
  },
  "message": "Credentials retrieved successfully",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

---

### Revoke Credentials

**Endpoint**: `POST /api/v1/credentials/:credential_id/revoke`

**Description**: Revokes OAuth credentials and prevents further use.

**Headers**:
```
Authorization: Bearer <admin_token>
```

**URL Parameters**:
- `credential_id` (required): ID of credential to revoke

**Request**:
```bash
curl -X POST http://localhost:8025/api/v1/credentials/42/revoke \
  -H "Authorization: Bearer <admin_token>"
```

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "credential_id": 42,
    "revoked_at": "2026-02-16T12:34:56Z"
  },
  "message": "Credentials revoked successfully",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

---

## Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_CODE` | 400 | OAuth authorization code is invalid or expired |
| `INVALID_REFRESH_TOKEN` | 401 | Refresh token is invalid or revoked |
| `MISSING_FIELDS` | 400 | Required request fields are missing |
| `INVALID_REQUEST` | 400 | Request format is invalid |
| `UNAUTHORIZED` | 401 | Request lacks valid authentication |
| `FORBIDDEN` | 403 | User lacks required permissions |
| `NOT_FOUND` | 404 | Requested resource does not exist |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `EXTERNAL_API_ERROR` | 502 | YouTube Music API request failed |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVICE_UNAVAILABLE` | 503 | Service is temporarily unavailable |

## Rate Limiting

The module implements rate limiting to prevent abuse:

- **Default Limit**: 100 requests per minute per IP address
- **OAuth Endpoints**: 10 requests per minute per IP address
- **Response Headers**: Includes rate limit information:
  - `X-RateLimit-Limit`: Total requests allowed
  - `X-RateLimit-Remaining`: Requests remaining in window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

When limit exceeded:
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1645011300

{
  "status": "error",
  "error": "RATE_LIMITED",
  "message": "Rate limit exceeded. Reset at 2026-02-16T12:35:00Z",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

## Pagination

List endpoints support pagination:

**Query Parameters**:
| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | integer | 20 | 100 | Results per page |
| `offset` | integer | 0 | - | Number of results to skip |
| `sort` | string | created_at | - | Sort field |
| `order` | string | desc | - | asc or desc |

**Response**:
```json
{
  "status": "success",
  "data": {
    "items": [...],
    "pagination": {
      "total": 45,
      "limit": 20,
      "offset": 0,
      "pages": 3,
      "current_page": 1,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

---

**Last Updated**: 2026-02-16
