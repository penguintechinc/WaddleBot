# Twitch Action Module - REST API Reference

## Authentication

All endpoints except `/health` and `/api/v1/auth/token` require JWT bearer token authentication.

### Header Format

```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

### Token Generation Endpoint

**POST** `/api/v1/auth/token`

Generate a JWT token for API authentication.

**Request Body:**
```json
{
  "api_key": "your-module-secret-key",
  "service": "optional-service-identifier"
}
```

**Response (200 OK):**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 3600
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid API key

---

## Health Check

**GET** `/health`

Health check endpoint. No authentication required.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "module": "twitch_action_module",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00",
  "database": "connected",
  "grpc_port": 50053,
  "rest_port": 8072
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "error": "database connection failed"
}
```

---

## Action Execution

### Execute Single Action

**POST** `/api/v1/actions/execute`

Execute a single Twitch action synchronously.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "action_type": "send_chat_message",
  "broadcaster_id": "123456789",
  "request_id": "optional-request-id",
  "parameters": {
    "message": "Hello Twitch!"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "action_type": "send_chat_message",
  "broadcaster_id": "123456789",
  "request_id": "optional-request-id",
  "data": {
    "message_id": "msg_123"
  }
}
```

**Response (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "token_expired",
  "action_type": "send_chat_message",
  "message": "OAuth token expired. Please reauthorize."
}
```

**Supported Action Types:**
- `send_chat_message` - Send message to channel chat
- `create_clip` - Create clip from live stream
- `moderate_chat` - Moderate chat (ban, timeout, etc.)

**Error Cases:**
- `token_expired` - Broadcaster's OAuth token expired
- `invalid_auth` - Token invalid or revoked
- `broadcaster_not_found` - Broadcaster ID not found or offline
- `invalid_parameters` - Missing or invalid action parameters
- `rate_limited` - Twitch rate limit exceeded

---

### Execute Batch Actions

**POST** `/api/v1/actions/batch`

Execute multiple actions in a single batch request.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "actions": [
    {
      "action_type": "send_chat_message",
      "broadcaster_id": "123456789",
      "request_id": "msg_1",
      "parameters": {
        "message": "Message 1"
      }
    },
    {
      "action_type": "send_chat_message",
      "broadcaster_id": "123456789",
      "request_id": "msg_2",
      "parameters": {
        "message": "Message 2"
      }
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "results": [
    {
      "request_id": "msg_1",
      "success": true,
      "action_type": "send_chat_message",
      "broadcaster_id": "123456789",
      "data": {
        "message_id": "msg_123"
      }
    },
    {
      "request_id": "msg_2",
      "success": true,
      "action_type": "send_chat_message",
      "broadcaster_id": "123456789",
      "data": {
        "message_id": "msg_124"
      }
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request` - No actions provided
- `413 Payload Too Large` - Batch size exceeds limit (default 100)
- `500 Internal Server Error` - Processing failed

---

## Token Management

### Store OAuth Token

**POST** `/api/v1/tokens/store`

Store OAuth token for a broadcaster.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "broadcaster_id": "123456789",
  "access_token": "access_token_here",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600,
  "scopes": ["chat:edit", "chat:read", "clips:edit"]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Token stored successfully"
}
```

**Error Responses:**
- `400 Bad Request` - Missing required fields
- `500 Internal Server Error` - Database error

**Required Fields:**
- `broadcaster_id` - Twitch user ID
- `access_token` - OAuth access token
- `refresh_token` - OAuth refresh token
- `expires_in` - Seconds until token expires

---

### Revoke OAuth Token

**POST** `/api/v1/tokens/revoke`

Revoke stored OAuth token for a broadcaster.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "broadcaster_id": "123456789"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Token revoked successfully"
}
```

**Error Responses:**
- `400 Bad Request` - Missing broadcaster_id
- `404 Not Found` - Token not found for broadcaster
- `500 Internal Server Error` - Revocation failed

---

## Statistics

### Get Module Statistics

**GET** `/api/v1/stats`

Retrieve module statistics and configuration.

**Authentication:** Required (Bearer token)

**Response (200 OK):**
```json
{
  "module": "twitch_action_module",
  "version": "1.0.0",
  "stats": {
    "registered_broadcasters": 42,
    "grpc_port": 50053,
    "rest_port": 8072
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

**Error Responses:**
- `500 Internal Server Error` - Statistics retrieval failed

---

## Action Parameters Reference

### send_chat_message

Send a message to broadcaster's chat.

**Parameters:**
```json
{
  "message": "Hello Twitch chat!",
  "reply_to_message_id": "optional-parent-message-id"
}
```

**Response Data:**
```json
{
  "message_id": "msg_12345",
  "timestamp": 1234567890
}
```

**Requirements:**
- `chat:edit` scope required
- Broadcaster must be live or channel must exist
- Message max 500 characters
- Rate limit: 1 message per second per channel

---

### create_clip

Create a clip from live broadcast.

**Parameters:**
```json
{
  "title": "Epic Moment",
  "has_delay": false
}
```

**Response Data:**
```json
{
  "id": "clip_12345",
  "url": "https://clips.twitch.tv/...",
  "edit_url": "https://clips.twitch.tv/.../edit"
}
```

**Requirements:**
- `clips:edit` scope required
- Broadcaster must be live
- Title max 30 characters

---

### moderate_chat

Perform moderation action in chat.

**Parameters:**
```json
{
  "action": "ban",
  "target_user_id": "987654321",
  "reason": "optional-reason",
  "duration_seconds": "optional-for-timeout"
}
```

**Supported Actions:**
- `ban` - Permanently ban user from channel
- `unban` - Unban previously banned user
- `timeout` - Temporarily ban user (requires duration_seconds)
- `untimeout` - Remove timeout from user
- `slow_mode_on` - Enable slow mode
- `slow_mode_off` - Disable slow mode

**Response Data:**
```json
{
  "action": "ban",
  "target_user_id": "987654321",
  "duration_seconds": null,
  "timestamp": 1234567890
}
```

**Requirements:**
- `moderator:manage:chat_settings` scope required
- Caller must be channel moderator or broadcaster

---

## Error Handling

All error responses follow this format:

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable error message"
}
```

### Common HTTP Status Codes

| Status | Meaning |
|--------|---------|
| `200 OK` | Request successful |
| `400 Bad Request` | Invalid request parameters |
| `401 Unauthorized` | Authentication failed or missing |
| `403 Forbidden` | Token valid but insufficient permissions |
| `404 Not Found` | Resource not found |
| `413 Payload Too Large` | Request body exceeds size limit |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server error or Twitch API error |
| `503 Service Unavailable` | Database or dependency unavailable |

### Common Twitch API Errors

| Error Code | Meaning | Solution |
|-----------|---------|----------|
| `invalid_auth` | OAuth token invalid | Re-authenticate broadcaster |
| `token_expired` | Token expired, needs refresh | Module will auto-refresh |
| `not_found` | Broadcaster not found | Verify broadcaster_id |
| `broadcaster_offline` | Channel not live | Wait for broadcaster to go live |
| `rate_limited` | API rate limit exceeded | Retry with exponential backoff |
| `invalid_parameters` | Missing/invalid action parameters | Check required fields |
| `insufficient_permissions` | Scope missing for action | Request additional scopes |

---

## Rate Limiting

Twitch API rate limits:
- **1 message per second** per channel
- **50 API requests per second** per app
- **20 file uploads per second** per workspace

Module implementation:
- Queues excess requests
- Implements exponential backoff
- Tracks rate limit status
- Auto-retries after reset

**Headers in Response:**
```
X-Ratelimit-Limit: 50
X-Ratelimit-Remaining: 45
X-Ratelimit-Reset: 1234567890
```

When rate limited (HTTP 429):
```json
{
  "success": false,
  "error": "rate_limited",
  "message": "Rate limit exceeded. Retry after 60 seconds.",
  "retry_after": 60
}
```

---

## Request/Response Examples

### Full Request Cycle

```bash
# 1. Generate token
TOKEN=$(curl -s -X POST http://localhost:8072/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "secret", "service": "chatbot"}' | jq -r '.token')

echo "Token: $TOKEN"

# 2. Send single message
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "send_chat_message",
    "broadcaster_id": "123456789",
    "parameters": {
      "message": "Hello Twitch!"
    }
  }'

# 3. Send batch messages
curl -X POST http://localhost:8072/api/v1/actions/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "actions": [
      {
        "action_type": "send_chat_message",
        "broadcaster_id": "123456789",
        "request_id": "msg_1",
        "parameters": {"message": "Message 1"}
      },
      {
        "action_type": "send_chat_message",
        "broadcaster_id": "123456789",
        "request_id": "msg_2",
        "parameters": {"message": "Message 2"}
      }
    ]
  }'

# 4. Store token for broadcaster
curl -X POST http://localhost:8072/api/v1/tokens/store \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broadcaster_id": "123456789",
    "access_token": "access_...",
    "refresh_token": "refresh_...",
    "expires_in": 3600,
    "scopes": ["chat:edit", "chat:read"]
  }'

# 5. Get statistics
curl http://localhost:8072/api/v1/stats \
  -H "Authorization: Bearer $TOKEN"
```

---

## Action Response Schema

All action responses follow this schema:

```json
{
  "success": true|false,
  "action_type": "action_name",
  "broadcaster_id": "123456789",
  "request_id": "optional-id",
  "message": "Status message",
  "error": "Error code (if failed)",
  "data": {
    "field1": "value1",
    "field2": "value2"
  },
  "timestamp": 1234567890
}
```

**Fields:**
- `success` - Boolean indicating success
- `action_type` - Type of action executed
- `broadcaster_id` - Target broadcaster
- `request_id` - Optional tracking ID from request
- `message` - Human-readable status
- `error` - Error code (if failed)
- `data` - Action-specific response data
- `timestamp` - Unix timestamp of execution
