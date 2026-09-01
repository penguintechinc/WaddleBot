# GCP Functions Action Module - REST API Reference

## Base URL

```
http://localhost:8081/api/v1
```

All requests require JWT authentication via `Authorization: Bearer TOKEN` header, except health and token endpoints.

## Authentication Endpoints

### POST /auth/token - Generate JWT Token

Generate a JWT token for API authentication.

**Request:**
```json
{
  "api_key": "string",
  "service": "string",
  "permissions": ["invoke_functions"]
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

**Example:**
```bash
curl -X POST http://localhost:8081/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "my_api_key",
    "service": "my_service"
  }'
```

**Errors:**
- 401: Invalid API key

---

## Function Invocation Endpoints

### POST /functions/invoke - Invoke Cloud Function

Invoke a Cloud Function with JSON payload.

**Request:**
```json
{
  "project": "string",
  "region": "string",
  "function_name": "string",
  "payload": {"object": "any"},
  "headers": {"object": "optional"}
}
```

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response": "Function output",
  "execution_id": "function-name_1708077045",
  "execution_time_ms": 245
}
```

**Example:**
```bash
curl -X POST http://localhost:8081/api/v1/functions/invoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "project": "my-project",
    "region": "us-central1",
    "function_name": "my-function",
    "payload": {"message": "Hello"}
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing function_name
- 500: GCP API error

---

### POST /functions/invoke-http - Invoke HTTP Function

Invoke an HTTP-triggered function directly via URL.

**Request:**
```json
{
  "url": "string",
  "payload": {"object": "any"},
  "method": "POST",
  "headers": {"object": "optional"},
  "timeout": 30
}
```

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response": "Function output"
}
```

**Example:**
```bash
curl -X POST http://localhost:8081/api/v1/functions/invoke-http \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "url": "https://us-central1-my-project.cloudfunctions.net/my-function",
    "payload": {"data": "test"},
    "method": "POST"
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing url
- 500: HTTP request failed

---

### POST /functions/batch - Batch Invoke Functions

Invoke multiple Cloud Functions concurrently.

**Request:**
```json
{
  "invocations": [
    {
      "project": "string",
      "region": "string",
      "function_name": "string",
      "payload": {"object": "any"},
      "headers": {"object": "optional"}
    }
  ]
}
```

**Response:**
```json
{
  "responses": [
    {"success": true, "status_code": 200},
    {"success": false, "error": "Not found"}
  ],
  "total_count": 2,
  "success_count": 1,
  "failure_count": 1
}
```

**Example - Invoke 3 functions:**
```bash
curl -X POST http://localhost:8081/api/v1/functions/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "invocations": [
      {
        "function_name": "func1",
        "payload": {"id": 1}
      },
      {
        "function_name": "func2",
        "payload": {"id": 2}
      },
      {
        "function_name": "func3",
        "payload": {"id": 3}
      }
    ]
  }'
```

**Parameters:**
- invocations: Array of function invocations (required)
- Max batch size: 100 functions

**Errors:**
- 401: Invalid/missing authentication
- 400: No invocations provided or batch size exceeds limit
- 500: Batch processing error

---

## Function Management Endpoints

### GET /functions/list - List Cloud Functions

List all Cloud Functions in a project and region.

**Query Parameters:**
- project: GCP project ID (optional, uses default)
- region: GCP region (optional, uses default)

**Response:**
```json
{
  "project": "my-project",
  "region": "us-central1",
  "functions": [
    {
      "name": "function-1",
      "status": "ACTIVE",
      "runtime": "python311",
      "entryPoint": "main"
    },
    {
      "name": "function-2",
      "status": "ACTIVE",
      "runtime": "nodejs18",
      "entryPoint": "handler"
    }
  ],
  "count": 2
}
```

**Example:**
```bash
curl "http://localhost:8081/api/v1/functions/list?project=my-project&region=us-central1" \
  -H "Authorization: Bearer TOKEN"
```

**Errors:**
- 401: Invalid/missing authentication
- 500: GCP API error

---

### GET /functions/{function_name}/details - Get Function Details

Get detailed information about a specific Cloud Function.

**Path Parameters:**
- function_name: Name of the Cloud Function

**Query Parameters:**
- project: GCP project ID (optional, uses default)
- region: GCP region (optional, uses default)

**Response:**
```json
{
  "success": true,
  "function": {
    "name": "my-function",
    "status": "ACTIVE",
    "runtime": "python311",
    "entryPoint": "main",
    "sourceArchiveUrl": "gs://bucket/source.zip",
    "httpsTrigger": {
      "url": "https://region-project.cloudfunctions.net/my-function"
    }
  }
}
```

**Example:**
```bash
curl "http://localhost:8081/api/v1/functions/my-function/details?project=my-project&region=us-central1" \
  -H "Authorization: Bearer TOKEN"
```

**Errors:**
- 401: Invalid/missing authentication
- 404: Function not found
- 500: GCP API error

---

## Statistics Endpoints

### GET /stats - Get Module Statistics

Get invocation statistics and module information.

**Response:**
```json
{
  "module": "gcp_functions_action_module",
  "version": "1.0.0",
  "stats": {
    "total_invocations": 156,
    "successful_invocations": 152,
    "failed_invocations": 4,
    "average_execution_time_ms": 342,
    "grpc_port": 50061,
    "rest_port": 8081,
    "gcp_project": "my-project",
    "gcp_region": "us-central1"
  },
  "timestamp": "2026-02-16T10:30:45.123456"
}
```

**Example:**
```bash
curl "http://localhost:8081/api/v1/stats" \
  -H "Authorization: Bearer TOKEN"
```

**Errors:**
- 401: Invalid/missing authentication
- 500: Database query error

---

## System Endpoints

### GET /health - Health Check

Check module health and GCP connectivity.

**Response:**
```json
{
  "status": "healthy",
  "module": "gcp_functions_action_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:45.123456",
  "database": "connected",
  "gcp_project": "my-project",
  "gcp_region": "us-central1",
  "grpc_port": 50061,
  "rest_port": 8081
}
```

**Example:**
```bash
curl http://localhost:8081/health
```

**Status Values:**
- "healthy": All systems operational
- "unhealthy": One or more systems down

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error message describing the issue"
}
```

Common HTTP Status Codes:
- 200: Success
- 400: Bad Request (validation error)
- 401: Unauthorized (authentication failed)
- 404: Not Found (resource doesn't exist)
- 500: Internal Server Error (GCP API error)

---

## Error Messages

### Authentication Errors

**Missing Authorization Header:**
```json
{"error": "Missing or invalid Authorization header"}
```

**Invalid Token:**
```json
{"error": "Invalid or expired token"}
```

**Invalid API Key:**
```json
{"error": "Invalid API key"}
```

### Validation Errors

**Missing Required Parameter:**
```json
{"error": "function_name is required"}
```

**Batch Size Exceeded:**
```json
{"error": "Batch size exceeds maximum of 100"}
```

### GCP API Errors

**Permission Denied:**
```json
{"success": false, "error": "Permission denied calling Google API"}
```

**Not Found:**
```json
{"success": false, "error": "Function not found"}
```

**Timeout:**
```json
{"success": false, "error": "Function execution timeout"}
```

---

## Request/Response Examples

### Example 1: Simple Function Invocation

**Request:**
```bash
curl -X POST http://localhost:8081/api/v1/functions/invoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "project": "my-project",
    "region": "us-central1",
    "function_name": "process-data",
    "payload": {
      "user_id": 12345,
      "action": "process"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response": "{"result": "processed"}",
  "execution_id": "process-data_1708077045",
  "execution_time_ms": 523
}
```

### Example 2: Batch Processing

**Request:**
```bash
curl -X POST http://localhost:8081/api/v1/functions/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "invocations": [
      {"function_name": "transform", "payload": {"data": "a"}},
      {"function_name": "transform", "payload": {"data": "b"}},
      {"function_name": "transform", "payload": {"data": "c"}}
    ]
  }'
```

**Response:**
```json
{
  "responses": [
    {"success": true, "status_code": 200, "response": "..."},
    {"success": true, "status_code": 200, "response": "..."},
    {"success": true, "status_code": 200, "response": "..."}
  ],
  "total_count": 3,
  "success_count": 3,
  "failure_count": 0
}
```

---

## Rate Limiting

The module enforces basic rate limiting:

- Max concurrent workers: 20
- Request timeout: 30 seconds per request
- Function timeout: 60 seconds per invocation
- Max batch size: 100 functions

For higher limits, adjust MAX_WORKERS and FUNCTION_TIMEOUT in configuration.

---

## Authentication

All API endpoints (except /health and /auth/token) require JWT authentication:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" ...
```

Tokens expire after JWT_EXPIRATION_SECONDS (default: 3600). Request a new token when expired.

---

## GCP Cloud Functions API Version

This module uses GCP Cloud Functions API v2. Refer to GCP documentation:
https://cloud.google.com/functions/docs/reference/rest/v2
