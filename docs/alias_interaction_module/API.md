# Alias Interaction Module — API Reference

## Overview

The Alias Interaction Module exposes a RESTful API for managing and executing aliases. All endpoints operate on JSON payloads with standardized response formats.

**Base URL:** `http://localhost:8010`

**API Version:** v1

**Authentication:** Not required for this version (implement in production)

---

## Table of Contents

1. [Response Format](#response-format)
2. [Status Endpoint](#status-endpoint)
3. [Health Endpoints](#health-endpoints)
4. [Alias Endpoints](#alias-endpoints)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)

---

## Response Format

All responses follow a standard envelope format:

### Success Response

```json
{
  "data": {
    "id": "alias-123",
    "alias_name": "example",
    "command": "example_command"
  },
  "status": "success",
  "timestamp": "2026-02-16T10:30:00Z",
  "request_id": "req-abc123"
}
```

### Error Response

```json
{
  "error": {
    "code": "ALIAS_NOT_FOUND",
    "message": "Requested alias does not exist",
    "details": "alias_name: 'invalid_alias'"
  },
  "status": "error",
  "timestamp": "2026-02-16T10:30:00Z",
  "request_id": "req-abc123"
}
```

---

## Status Endpoint

### GET /api/v1/status

Returns the operational status of the module.

**Parameters:** None

**Request:**
```bash
curl http://localhost:8010/api/v1/status
```

**Response (200 OK):**
```json
{
  "data": {
    "status": "operational",
    "module": "alias_interaction_module"
  },
  "status": "success",
  "timestamp": "2026-02-16T10:30:00Z"
}
```

---

## Health Endpoints

### GET /health

Standard health check endpoint for load balancers and orchestration platforms.

**Parameters:** None

**Request:**
```bash
curl http://localhost:8010/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "alias_interaction_module",
  "version": "2.0.0",
  "timestamp": "2026-02-16T10:30:00Z",
  "uptime_seconds": 3600,
  "database": "connected"
}
```

### GET /metrics

Returns Prometheus-format metrics for monitoring.

**Parameters:** None

**Request:**
```bash
curl http://localhost:8010/metrics
```

**Response (200 OK):**
```
# HELP alias_interaction_requests_total Total requests processed
# TYPE alias_interaction_requests_total counter
alias_interaction_requests_total{endpoint="/api/v1/aliases"} 42
alias_interaction_requests_total{endpoint="/api/v1/aliases/execute"} 127

# HELP alias_interaction_request_duration_seconds Request duration
# TYPE alias_interaction_request_duration_seconds histogram
alias_interaction_request_duration_seconds_bucket{endpoint="/api/v1/aliases",le="0.1"} 38
```

---

## Alias Endpoints

### GET /api/v1/aliases

List all active aliases for a specified community.

**Parameters:**

| Name | Type | Required | Description |
|---|---|---|---|
| `community_id` | string | Yes | The community identifier to filter aliases |

**Request:**
```bash
curl "http://localhost:8010/api/v1/aliases?community_id=community-123"
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "alias-001",
      "community_id": "community-123",
      "alias_name": "diagnose",
      "command": "check_system_status --user {user} --verbose",
      "created_by": "admin-user",
      "created_at": "2026-02-10T14:30:00Z",
      "usage_count": 5,
      "is_active": true
    },
    {
      "id": "alias-002",
      "community_id": "community-123",
      "alias_name": "report",
      "command": "create_incident --title {arg1} --description {all_args}",
      "created_by": "admin-user",
      "created_at": "2026-02-11T09:15:00Z",
      "usage_count": 12,
      "is_active": true
    }
  ],
  "status": "success",
  "count": 2,
  "timestamp": "2026-02-16T10:30:00Z"
}
```

**Error Cases:**

```json
// Missing community_id parameter
{
  "error": {
    "code": "MISSING_PARAMETER",
    "message": "community_id parameter is required"
  },
  "status": "error"
}
```

---

### POST /api/v1/aliases

Create a new alias for a community.

**Parameters:**

| Name | Type | Required | Description |
|---|---|---|---|
| `community_id` | string | Yes | Community identifier |
| `alias_name` | string | Yes | Name of the alias (must be unique within community) |
| `command` | string | Yes | Command template with optional variables |
| `created_by` | string | Yes | User ID of creator |

**Request:**
```bash
curl -X POST http://localhost:8010/api/v1/aliases \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "community-123",
    "alias_name": "quick_check",
    "command": "system_check --format json --user {user}",
    "created_by": "admin-user-456"
  }'
```

**Response (201 Created):**
```json
{
  "data": {
    "id": "alias-789",
    "community_id": "community-123",
    "alias_name": "quick_check",
    "command": "system_check --format json --user {user}",
    "created_by": "admin-user-456",
    "created_at": "2026-02-16T10:30:00Z",
    "usage_count": 0,
    "is_active": true
  },
  "status": "success",
  "timestamp": "2026-02-16T10:30:00Z"
}
```

**Error Cases:**

```json
// Duplicate alias name in community
{
  "error": {
    "code": "DUPLICATE_ALIAS",
    "message": "Alias 'quick_check' already exists in community 'community-123'",
    "status_code": 409
  },
  "status": "error"
}
```

```json
// Invalid command format
{
  "error": {
    "code": "INVALID_COMMAND",
    "message": "Command cannot be empty"
  },
  "status": "error"
}
```

---

### DELETE /api/v1/aliases/<alias_id>

Soft delete an alias (marks is_active as false).

**Parameters:**

| Name | Type | Required | Description |
|---|---|---|---|
| `alias_id` | string (path) | Yes | The ID of the alias to delete |

**Request:**
```bash
curl -X DELETE http://localhost:8010/api/v1/aliases/alias-789
```

**Response (200 OK):**
```json
{
  "data": {
    "message": "Alias deleted",
    "id": "alias-789",
    "is_active": false
  },
  "status": "success",
  "timestamp": "2026-02-16T10:30:00Z"
}
```

**Error Cases:**

```json
// Alias not found
{
  "error": {
    "code": "ALIAS_NOT_FOUND",
    "message": "Alias with ID 'invalid-id' not found"
  },
  "status": "error",
  "status_code": 404
}
```

---

### POST /api/v1/aliases/execute

Execute an alias with variable substitution and return the expanded command.

**Parameters:**

| Name | Type | Required | Description |
|---|---|---|---|
| `alias_name` | string | Yes | Name of the alias to execute |
| `user` | string | Yes | Current user identifier (for {user} substitution) |
| `args` | array | No | Array of arguments for {arg1}, {arg2}, {all_args} substitution |

**Request:**
```bash
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -H "Content-Type: application/json" \
  -d '{
    "alias_name": "quick_check",
    "user": "john_doe",
    "args": []
  }'
```

**Response (200 OK):**
```json
{
  "data": {
    "command": "system_check --format json --user john_doe",
    "alias_name": "quick_check",
    "user": "john_doe",
    "args_count": 0
  },
  "status": "success",
  "timestamp": "2026-02-16T10:30:00Z"
}
```

**Request with Arguments:**
```bash
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -H "Content-Type: application/json" \
  -d '{
    "alias_name": "report",
    "user": "jane_smith",
    "args": ["Database Down", "Production Environment", "Critical"]
  }'
```

**Response (200 OK):**
```json
{
  "data": {
    "command": "create_incident --title Database Down --description Database Down Production Environment Critical",
    "alias_name": "report",
    "user": "jane_smith",
    "args_count": 3,
    "substitutions": {
      "user": "jane_smith",
      "arg1": "Database Down",
      "arg2": "Production Environment",
      "all_args": "Database Down Production Environment Critical"
    }
  },
  "status": "success",
  "timestamp": "2026-02-16T10:30:00Z"
}
```

**Error Cases:**

```json
// Alias not found
{
  "error": {
    "code": "ALIAS_NOT_FOUND",
    "message": "Alias 'invalid_alias' not found or is inactive",
    "status_code": 404
  },
  "status": "error"
}
```

```json
// Missing required parameter
{
  "error": {
    "code": "MISSING_PARAMETER",
    "message": "Parameter 'user' is required for alias execution"
  },
  "status": "error"
}
```

---

## Error Codes

| Code | HTTP Status | Description | Resolution |
|---|---|---|---|
| `SUCCESS` | 200 | Operation completed successfully | None |
| `CREATED` | 201 | Resource created successfully | None |
| `MISSING_PARAMETER` | 400 | Required parameter missing | Provide all required parameters |
| `INVALID_COMMAND` | 400 | Command format invalid | Check command syntax |
| `INVALID_INPUT` | 400 | Input validation failed | Validate request data |
| `ALIAS_NOT_FOUND` | 404 | Requested alias doesn't exist | Verify alias_name or alias_id |
| `DUPLICATE_ALIAS` | 409 | Alias already exists in community | Use different alias_name |
| `DATABASE_ERROR` | 500 | Database operation failed | Check database connection |
| `INTERNAL_ERROR` | 500 | Unexpected server error | Check service logs |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable | Retry after delay |

---

## Request/Response Headers

### Request Headers

```
Content-Type: application/json
Accept: application/json
User-Agent: <client-agent>
```

### Response Headers

```
Content-Type: application/json; charset=utf-8
Date: <server-date>
Server: Hypercorn/WaddleBot
X-Request-ID: <unique-request-id>
X-Response-Time: <milliseconds>
```

---

## Rate Limiting

Current implementation does not enforce rate limiting, but production deployments should implement:

- **Per-IP Limit:** 100 requests per minute
- **Per-Community Limit:** 1000 requests per minute
- **Per-User Limit:** 500 requests per minute
- **Global Limit:** 10,000 requests per minute

Exceeded limits return HTTP 429 (Too Many Requests).

---

## Variable Substitution Reference

When executing aliases, the following variables are available:

| Variable | Description | Example |
|---|---|---|
| `{user}` | Current user from request | `john_doe` |
| `{args}` | All arguments space-separated | `arg1 arg2 arg3` |
| `{arg1}` | First argument (index 0) | `arg1` |
| `{arg2}` | Second argument (index 1) | `arg2` |
| `{all_args}` | All arguments (alias for {args}) | `arg1 arg2 arg3` |

**Important:** Variables are case-sensitive and must match exactly.

---

## Pagination (Future)

Future versions may implement pagination for list endpoints:

```bash
curl "http://localhost:8010/api/v1/aliases?community_id=community-123&limit=20&offset=0"
```

---

## Versioning Strategy

API versions are managed via URL path:

- `/api/v1/*` - Current production version
- `/api/v2/*` - Coming in future major release

Breaking changes trigger new major version. Minor additions are backward compatible.

---

## Examples

### Creating and Executing an Alias

```bash
# 1. Create alias
curl -X POST http://localhost:8010/api/v1/aliases \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "ops-team",
    "alias_name": "check_all",
    "command": "health_check --component {arg1} --user {user}",
    "created_by": "ops-lead"
  }'

# 2. Execute the alias
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -H "Content-Type: application/json" \
  -d '{
    "alias_name": "check_all",
    "user": "ops-tech",
    "args": ["database", "memcached"]
  }'

# Result
# health_check --component database --user ops-tech
```

### Listing and Deleting

```bash
# 1. List all aliases
curl "http://localhost:8010/api/v1/aliases?community_id=ops-team"

# 2. Delete an alias
curl -X DELETE http://localhost:8010/api/v1/aliases/alias-id-here
```
