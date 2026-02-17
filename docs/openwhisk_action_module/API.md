# OpenWhisk Action Module - API Reference

## Overview

The OpenWhisk Action Module provides REST and gRPC interfaces for invoking OpenWhisk actions, sequences, web actions, and triggers.

All REST endpoints (except `/health`) require JWT Bearer token authentication.

## Authentication

### Generate Token

**Endpoint**: `POST /api/v1/auth/token`

Generate JWT token for API access.

**Request**:
```json
{
  "api_key": "string (required)",
  "service": "string (optional)"
}
```

**Response (200 OK)**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

**Example**:
```bash
curl -X POST http://localhost:8082/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"my-api-key","service":"waddlebot"}'
```

**Status Codes**:
- `200 OK` - Token generated
- `400 Bad Request` - Missing api_key
- `401 Unauthorized` - Invalid API key

---

## Health Check

**Endpoint**: `GET /health`

Check module status and configuration.

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "module": "openwhisk_action_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T21:30:45.123456",
  "database": "connected",
  "grpc_port": 50062,
  "rest_port": 8082,
  "openwhisk_api_host": "https://openwhisk.cloud.ibm.com",
  "namespace": "guest"
}
```

**Example**:
```bash
curl -X GET http://localhost:8082/health | jq '.'
```

**Status Codes**:
- `200 OK` - Module healthy
- `503 Service Unavailable` - Database or OpenWhisk connection issue

---

## Invoke Action (Blocking)

**Endpoint**: `POST /api/v1/actions/invoke`

Invoke an action synchronously and wait for result.

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "action_name": "string (required)",
  "namespace": "string (optional, default: OPENWHISK_NAMESPACE)",
  "payload": "object (optional, default: {})",
  "blocking": "boolean (optional, default: true)",
  "timeout": "integer (optional, in milliseconds)"
}
```

**Response (200 OK)**:
```json
{
  "execution_id": "exec_1645123456789",
  "success": true,
  "activation_id": "3e27a4f0b4d94fcb27a4f0b4d94fcb2",
  "result": {
    "message": "Hello from OpenWhisk"
  },
  "status": "success",
  "duration": 125
}
```

**Example**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8082/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"key"}' | jq -r '.token')

curl -X POST http://localhost:8082/api/v1/actions/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_name": "my-action",
    "payload": {"name": "WaddleBot"},
    "blocking": true
  }' | jq '.'
```

**Status Codes**:
- `200 OK` - Action invoked successfully
- `400 Bad Request` - Missing action_name
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Action execution failed

---

## Invoke Action (Async)

**Endpoint**: `POST /api/v1/actions/invoke-async`

Invoke an action asynchronously (fire-and-forget).

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "action_name": "string (required)",
  "namespace": "string (optional)",
  "payload": "object (optional)"
}
```

**Response (200 OK)**:
```json
{
  "execution_id": "exec_1645123456789",
  "success": true,
  "activation_id": "3e27a4f0b4d94fcb27a4f0b4d94fcb2"
}
```

**Example**:
```bash
curl -X POST http://localhost:8082/api/v1/actions/invoke-async \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_name": "long-running-action",
    "payload": {"data": "async"}
  }' | jq '.'
```

**Status Codes**:
- `200 OK` - Action queued
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Queuing failed

---

## Invoke Sequence

**Endpoint**: `POST /api/v1/sequences/invoke`

Invoke a sequence (chained actions).

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "sequence_name": "string (required)",
  "namespace": "string (optional)",
  "payload": "object (optional)"
}
```

**Response (200 OK)**:
```json
{
  "execution_id": "exec_1645123456789",
  "success": true,
  "activation_id": "3e27a4f0b4d94fcb27a4f0b4d94fcb2",
  "result": {
    "final_output": "result"
  },
  "duration": 250
}
```

**Example**:
```bash
curl -X POST http://localhost:8082/api/v1/sequences/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sequence_name": "transform->validate->save",
    "payload": {"input": "data"}
  }' | jq '.'
```

**Status Codes**:
- `200 OK` - Sequence executed
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Execution failed

---

## Invoke Web Action

**Endpoint**: `POST /api/v1/web-actions/invoke`

Invoke a web-enabled action with HTTP context.

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "action_name": "string (required)",
  "package_name": "string (optional, default: default)",
  "namespace": "string (optional)",
  "payload": "object (optional)",
  "method": "GET|POST|PUT|DELETE (optional, default: POST)",
  "headers": "object (optional)"
}
```

**Response (200 OK)**:
```json
{
  "execution_id": "exec_1645123456789",
  "success": true,
  "response": {
    "status": 200,
    "body": "HTML or JSON response"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:8082/api/v1/web-actions/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_name": "hello",
    "package_name": "default",
    "method": "POST",
    "headers": {"X-Custom": "value"},
    "payload": {}
  }' | jq '.'
```

**Status Codes**:
- `200 OK` - Web action invoked
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Invocation failed

---

## Fire Trigger

**Endpoint**: `POST /api/v1/triggers/fire`

Fire a trigger to activate rules.

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "trigger_name": "string (required)",
  "namespace": "string (optional)",
  "payload": "object (optional)"
}
```

**Response (200 OK)**:
```json
{
  "execution_id": "exec_1645123456789",
  "success": true,
  "activation_id": "3e27a4f0b4d94fcb27a4f0b4d94fcb2"
}
```

**Example**:
```bash
curl -X POST http://localhost:8082/api/v1/triggers/fire \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "my-trigger",
    "payload": {"event": "user.created"}
  }' | jq '.'
```

**Status Codes**:
- `200 OK` - Trigger fired
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Trigger fire failed

---

## Get Activation Details

**Endpoint**: `GET /api/v1/activations/<activation_id>`

Retrieve details about a specific activation.

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `namespace` (optional) - Namespace for activation

**Response (200 OK)**:
```json
{
  "success": true,
  "activation_id": "3e27a4f0b4d94fcb27a4f0b4d94fcb2",
  "action_name": "my-action",
  "namespace": "guest",
  "start": 1645123456789,
  "end": 1645123456914,
  "duration": 125,
  "status": "success",
  "result": {
    "message": "result"
  },
  "logs": [
    "log line 1",
    "log line 2"
  ]
}
```

**Example**:
```bash
curl -X GET "http://localhost:8082/api/v1/activations/3e27a4f0b4d94fcb27a4f0b4d94fcb2?namespace=guest" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Status Codes**:
- `200 OK` - Activation retrieved
- `401 Unauthorized` - Invalid token
- `404 Not Found` - Activation not found
- `500 Internal Server Error` - Retrieval failed

---

## List Actions

**Endpoint**: `GET /api/v1/actions`

List available actions in namespace.

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `namespace` (optional) - Namespace to list
- `limit` (optional, default: 30) - Max results
- `skip` (optional, default: 0) - Pagination skip

**Response (200 OK)**:
```json
{
  "success": true,
  "actions": [
    {
      "name": "my-action",
      "namespace": "guest",
      "kind": "nodejs:14",
      "updated": 1645123456789
    }
  ]
}
```

**Example**:
```bash
curl -X GET "http://localhost:8082/api/v1/actions?limit=50&skip=0" \
  -H "Authorization: Bearer $TOKEN" | jq '.actions'
```

**Status Codes**:
- `200 OK` - Actions listed
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Listing failed

---

## Get Module Statistics

**Endpoint**: `GET /api/v1/stats`

Get module execution statistics.

**Authentication**: Required (Bearer token)

**Response (200 OK)**:
```json
{
  "module": "openwhisk_action_module",
  "version": "1.0.0",
  "stats": {
    "total_executions": 1250,
    "successful_executions": 1200,
    "failed_executions": 50,
    "grpc_port": 50062,
    "rest_port": 8082
  },
  "timestamp": "2026-02-16T21:30:45.123456"
}
```

**Example**:
```bash
curl -X GET http://localhost:8082/api/v1/stats \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Status Codes**:
- `200 OK` - Statistics retrieved
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Retrieval failed

---

## Error Responses

All errors follow standard format:

```json
{
  "error": "Error description",
  "status_code": 400
}
```

### Common Errors

| Status | Error | Meaning |
|--------|-------|---------|
| 400 | Missing action_name | Required field not provided |
| 401 | Missing Authorization header | No Bearer token |
| 401 | Invalid or expired token | Token validation failed |
| 404 | Action not found | Action doesn't exist |
| 500 | Namespace error | Invalid namespace |
| 503 | Service unavailable | OpenWhisk unreachable |

---

## Request Size Limits

- **Maximum payload**: 1 MB
- **Maximum batch size**: 100 executions

---

## Rate Limiting

- **Max workers**: 20 (configurable)
- **Request timeout**: 30 seconds (configurable)

---

## Code Examples

### Python Client

```python
import requests

class OpenWhiskClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.token = self._get_token(api_key)
    
    def _get_token(self, api_key):
        r = requests.post(
            f"{self.base_url}/api/v1/auth/token",
            json={"api_key": api_key}
        )
        return r.json()["token"]
    
    def invoke(self, action_name, payload=None):
        r = requests.post(
            f"{self.base_url}/api/v1/actions/invoke",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "action_name": action_name,
                "payload": payload or {},
                "blocking": True
            }
        )
        return r.json()

# Usage
client = OpenWhiskClient("http://localhost:8082", "my-api-key")
result = client.invoke("my-action", {"data": "test"})
print(result)
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

class OpenWhiskClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.token = null;
  }

  async getToken() {
    const response = await axios.post(
      `${this.baseUrl}/api/v1/auth/token`,
      { api_key: this.apiKey }
    );
    this.token = response.data.token;
    return this.token;
  }

  async invoke(actionName, payload = {}) {
    if (!this.token) await this.getToken();
    const response = await axios.post(
      `${this.baseUrl}/api/v1/actions/invoke`,
      {
        action_name: actionName,
        payload: payload,
        blocking: true
      },
      { headers: { Authorization: `Bearer ${this.token}` } }
    );
    return response.data;
  }
}

// Usage
const client = new OpenWhiskClient('http://localhost:8082', 'my-api-key');
const result = await client.invoke('my-action', { data: 'test' });
console.log(result);
```

---

See also:
- [Configuration](CONFIGURATION.md)
- [Testing](TESTING.md)
- [Troubleshooting](TROUBLESHOOTING.md)
