# Lambda Action Module - API Reference

## Overview

The Lambda Action Module provides two interfaces for invoking AWS Lambda functions:

1. **REST API** - HTTP/JSON for third-party integration (port 8080)
2. **gRPC API** - Binary protocol for high-performance processor/router communication (port 50060)

This document details all REST endpoints. For gRPC protocol details, see `grpc_proto/` directory.

## Authentication

All REST API endpoints (except `/health` and `/api/v1/token`) require JWT Bearer token authentication.

### Generating Token

**Endpoint**: `POST /api/v1/token`

Generate a JWT token for API access.

**Request**:
```json
{
  "client_id": "string",
  "client_secret": "string"
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
curl -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "waddlebot",
    "client_secret": "my-secret"
  }'
```

**Response Headers**:
```
Content-Type: application/json
```

**Status Codes**:
- `200 OK` - Token generated successfully
- `400 Bad Request` - Missing client_id or client_secret
- `401 Unauthorized` - Invalid credentials

**Notes**:
- Tokens expire after `JWT_EXPIRATION_SECONDS` (default 3600 seconds = 1 hour)
- Token format: `Bearer <token>` used in Authorization header
- Use same client_id/client_secret for consistent tokens

---

## Health Check

**Endpoint**: `GET /health`

Check module status and configuration.

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "module": "lambda_action_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T21:30:45.123456",
  "config": {
    "module_name": "lambda_action_module",
    "module_version": "1.0.0",
    "grpc_port": 50060,
    "rest_port": 8080,
    "database_configured": true,
    "aws_configured": true,
    "aws_region": "us-east-1",
    "max_concurrent_requests": 100,
    "request_timeout": 30,
    "log_level": "INFO",
    "credentials_from_db": false
  }
}
```

**Example**:
```bash
curl -X GET http://localhost:8080/health | jq '.'
```

**Status Codes**:
- `200 OK` - Module is healthy
- `503 Service Unavailable` - Module is unhealthy (DB connection issue, etc.)

**Notes**:
- No authentication required
- Use for Kubernetes liveness/readiness probes
- Response includes database and AWS configuration status

---

## Invoke Lambda Function (Synchronous)

**Endpoint**: `POST /api/v1/invoke`

Invoke a Lambda function synchronously and wait for response.

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "function_name": "string (required)",
  "payload": "string (required, JSON string)",
  "invocation_type": "RequestResponse|Event|DryRun (optional, default: RequestResponse)",
  "alias": "string (optional)",
  "version": "string (optional)"
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "status_code": 200,
  "payload": "{\"message\": \"Success\"}",
  "executed_version": "$LATEST",
  "log_result": "[logs from function execution]"
}
```

**Response (500 Error)**:
```json
{
  "success": false,
  "error": "Function not found",
  "status_code": 0
}
```

**Example**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"test","client_secret":"secret"}' | jq -r '.token')

curl -X POST http://localhost:8080/api/v1/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "my-function",
    "payload": "{\"input\": \"value\"}",
    "invocation_type": "RequestResponse"
  }' | jq '.'
```

**Status Codes**:
- `200 OK` - Function invoked successfully
- `400 Bad Request` - Missing required fields
- `401 Unauthorized` - Invalid or missing token
- `500 Internal Server Error` - AWS Lambda invocation failed

**Parameters**:
- `function_name`: Exact name of Lambda function (required)
- `payload`: JSON string to pass to function (required, max 6MB)
- `invocation_type`: 
  - `RequestResponse` - Wait for result (default)
  - `Event` - Fire and forget
  - `DryRun` - Validate without executing
- `alias`: Invoke specific alias instead of $LATEST
- `version`: Invoke specific version number

**Response Fields**:
- `success`: Boolean indicating if invocation succeeded
- `status_code`: HTTP status from Lambda (200 = success)
- `payload`: Function output (JSON string)
- `executed_version`: Version that executed ($LATEST, version number, or alias)
- `log_result`: Base64-decoded function logs (if LogType=Tail was used)

---

## Invoke Lambda Asynchronously

**Endpoint**: `POST /api/v1/invoke-async`

Invoke a Lambda function asynchronously (fire-and-forget).

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "function_name": "string (required)",
  "payload": "string (required, JSON string)"
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "status_code": 202,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"test","client_secret":"secret"}' | jq -r '.token')

curl -X POST http://localhost:8080/api/v1/invoke-async \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "my-function",
    "payload": "{\"data\": \"async\"}"
  }' | jq '.'
```

**Status Codes**:
- `200 OK` - Invocation queued successfully
- `400 Bad Request` - Missing required fields
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Invocation failed

**Notes**:
- Returns immediately with request_id
- Function executes independently in AWS Lambda
- No results returned
- Useful for long-running or non-blocking operations

---

## Batch Invoke

**Endpoint**: `POST /api/v1/batch`

Invoke multiple Lambda functions in a batch.

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "invocations": [
    {
      "function_name": "string (required)",
      "payload": "string (required)",
      "invocation_type": "RequestResponse (optional)",
      "alias": "string (optional)",
      "version": "string (optional)"
    }
  ]
}
```

**Response (200 OK)**:
```json
{
  "results": [
    {
      "success": true,
      "status_code": 200,
      "payload": "{\"result\": \"data\"}",
      "error": null,
      "executed_version": "$LATEST",
      "log_result": ""
    },
    {
      "success": false,
      "status_code": 0,
      "payload": null,
      "error": "Function not found",
      "executed_version": null,
      "log_result": ""
    }
  ]
}
```

**Example**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"test","client_secret":"secret"}' | jq -r '.token')

curl -X POST http://localhost:8080/api/v1/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "invocations": [
      {
        "function_name": "func1",
        "payload": "{\"id\": 1}"
      },
      {
        "function_name": "func2",
        "payload": "{\"id\": 2}"
      }
    ]
  }' | jq '.'
```

**Status Codes**:
- `200 OK` - Batch processed
- `400 Bad Request` - Missing invocations list
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Processing failed

**Notes**:
- Processes invocations sequentially
- Each invocation result included in response
- If one fails, others still execute
- No transaction support (partial success possible)

---

## List Lambda Functions

**Endpoint**: `GET /api/v1/functions`

List all Lambda functions in the AWS account.

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `max_items` (optional, default: 50) - Maximum functions to return
- `next_marker` (optional) - Pagination marker

**Response (200 OK)**:
```json
{
  "success": true,
  "functions": [
    {
      "function_name": "my-function",
      "function_arn": "arn:aws:lambda:us-east-1:123456789:function:my-function",
      "runtime": "python3.11",
      "role": "arn:aws:iam::123456789:role/lambda-role",
      "handler": "index.handler",
      "code_size": 1024,
      "description": "My test function",
      "timeout": 30,
      "memory_size": 128,
      "last_modified": "2026-02-16T21:30:00.000Z",
      "version": "$LATEST"
    }
  ],
  "next_marker": null
}
```

**Example**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"test","client_secret":"secret"}' | jq -r '.token')

curl -X GET "http://localhost:8080/api/v1/functions?max_items=50" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Status Codes**:
- `200 OK` - Functions listed successfully
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - AWS API call failed

**Response Fields**:
- `function_name`: Name of the function
- `function_arn`: AWS ARN for the function
- `runtime`: Execution runtime (python3.11, nodejs18.x, etc.)
- `role`: IAM role ARN
- `handler`: Handler function location
- `code_size`: Code size in bytes
- `timeout`: Function timeout in seconds
- `memory_size`: Allocated memory in MB
- `last_modified`: Last modification timestamp
- `version`: Version identifier

---

## Get Function Configuration

**Endpoint**: `GET /api/v1/functions/<function_name>`

Get detailed configuration for a specific Lambda function.

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `function_name` - Name of the Lambda function

**Response (200 OK)**:
```json
{
  "success": true,
  "config": {
    "function_name": "my-function",
    "function_arn": "arn:aws:lambda:us-east-1:123456789:function:my-function",
    "runtime": "python3.11",
    "role": "arn:aws:iam::123456789:role/lambda-role",
    "handler": "index.handler",
    "code_size": 1024,
    "description": "My test function",
    "timeout": 30,
    "memory_size": 128,
    "last_modified": "2026-02-16T21:30:00.000Z",
    "version": "$LATEST"
  }
}
```

**Example**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"test","client_secret":"secret"}' | jq -r '.token')

curl -X GET http://localhost:8080/api/v1/functions/my-function \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Status Codes**:
- `200 OK` - Configuration retrieved
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - AWS API call failed

**Notes**:
- Returns same configuration fields as list endpoint
- More efficient than listing all functions if you know the name
- Includes both configuration and runtime metadata

---

## Error Responses

All error responses follow standard format:

```json
{
  "error": "Error description",
  "status_code": 400
}
```

### Common Error Codes

| Status | Error | Meaning |
|--------|-------|---------|
| 400 | Missing function_name or payload | Required field not provided |
| 401 | Missing or invalid authorization header | No Bearer token provided |
| 401 | Invalid or expired token | Token validation failed |
| 500 | Function not found | Lambda function doesn't exist |
| 500 | Service error | AWS Lambda service error |
| 503 | Service unavailable | Database or AWS API unreachable |

---

## Rate Limiting

The module supports configurable rate limiting:

- **MAX_CONCURRENT_REQUESTS**: Maximum concurrent invocations (default: 100)
- **REQUEST_TIMEOUT**: Timeout per request in seconds (default: 30)

If rate limit exceeded, return `429 Too Many Requests`.

---

## Request/Response Size Limits

- **Maximum payload size**: 6 MB (AWS Lambda limit)
- **Maximum response size**: 6 MB
- **Maximum batch size**: 100 invocations per batch

---

## Database Logging

Every successful or failed invocation is logged to `lambda_invocations` table:

```sql
SELECT * FROM lambda_invocations 
WHERE invoked_at > NOW() - INTERVAL '1 hour'
ORDER BY invoked_at DESC
LIMIT 100;
```

---

## Code Examples

### Python Client Library

```python
import requests

class LambdaActionClient:
    def __init__(self, base_url, client_id, client_secret):
        self.base_url = base_url
        self.token = self._get_token(client_id, client_secret)
    
    def _get_token(self, client_id, client_secret):
        r = requests.post(
            f"{self.base_url}/api/v1/token",
            json={"client_id": client_id, "client_secret": client_secret}
        )
        return r.json()["token"]
    
    def invoke(self, function_name, payload):
        r = requests.post(
            f"{self.base_url}/api/v1/invoke",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "function_name": function_name,
                "payload": str(payload),
                "invocation_type": "RequestResponse"
            }
        )
        return r.json()

# Usage
client = LambdaActionClient("http://localhost:8080", "test", "secret")
result = client.invoke("my-function", {"data": "test"})
print(result)
```

### JavaScript Client

```javascript
const axios = require('axios');

class LambdaActionClient {
  constructor(baseUrl, clientId, clientSecret) {
    this.baseUrl = baseUrl;
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this.token = null;
  }

  async getToken() {
    const response = await axios.post(
      `${this.baseUrl}/api/v1/token`,
      {
        client_id: this.clientId,
        client_secret: this.clientSecret
      }
    );
    this.token = response.data.token;
    return this.token;
  }

  async invoke(functionName, payload) {
    if (!this.token) await this.getToken();
    const response = await axios.post(
      `${this.baseUrl}/api/v1/invoke`,
      {
        function_name: functionName,
        payload: JSON.stringify(payload),
        invocation_type: 'RequestResponse'
      },
      {
        headers: { Authorization: `Bearer ${this.token}` }
      }
    );
    return response.data;
  }
}

// Usage
const client = new LambdaActionClient('http://localhost:8080', 'test', 'secret');
const result = await client.invoke('my-function', { data: 'test' });
console.log(result);
```

---

## See Also

- [Configuration Reference](CONFIGURATION.md)
- [Testing Guide](TESTING.md)
- [Troubleshooting](TROUBLESHOOTING.md)
