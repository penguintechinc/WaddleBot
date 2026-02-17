# Slack Action Module - REST API Reference

## Authentication

All endpoints except `/health` and `/api/v1/token` require JWT bearer token authentication.

### Header Format

```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

### Token Generation Endpoint

**POST** `/api/v1/token`

Generate a JWT token for API authentication.

**Request Body:**
```json
{
  "api_key": "your-module-secret-key",
  "client_id": "optional-client-identifier"
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
  "module": "slack_action_module",
  "version": "1.0.0",
  "grpc_port": 50052,
  "rest_port": 8071
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

## Messages

### Send Message

**POST** `/api/v1/message`

Send a message to a Slack channel.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "channel_id": "string",
  "text": "string",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Bold text*"
      }
    }
  ],
  "thread_ts": "string (optional)"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message_ts": "1234567890.123456",
  "channel_id": "C01234567"
}
```

**Response (500 Internal Server Error):**
```json
{
  "error": "channel_not_found"
}
```

**Error Cases:**
- `channel_not_found` - Channel ID does not exist
- `not_in_channel` - Bot not in channel
- `invalid_auth` - Bot token invalid or expired
- `rate_limited` - Rate limit exceeded
- `message_not_found` - Message TS invalid (for updates)

---

### Send Ephemeral Message

**POST** `/api/v1/ephemeral`

Send a message visible only to a specific user.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "channel_id": "string",
  "user_id": "string",
  "text": "string"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "channel_id": "C01234567",
  "user_id": "U01234567"
}
```

**Error Responses:**
- `400 Bad Request` - Missing required fields
- `500 Internal Server Error` - Slack API error

---

### Update Message

**PUT** `/api/v1/message/{channel_id}/{ts}`

Update an existing message.

**Authentication:** Required (Bearer token)

**Path Parameters:**
- `channel_id` - Slack channel ID (e.g., `C01234567`)
- `ts` - Message timestamp (e.g., `1234567890.123456`)

**Request Body:**
```json
{
  "community_id": "string",
  "text": "string (optional)",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Updated content"
      }
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message_ts": "1234567890.123456",
  "channel_id": "C01234567"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid channel_id or ts format
- `500 Internal Server Error` - Message not found or edit failed

---

### Delete Message

**DELETE** `/api/v1/message/{channel_id}/{ts}`

Delete a message.

**Authentication:** Required (Bearer token)

**Path Parameters:**
- `channel_id` - Slack channel ID
- `ts` - Message timestamp

**Request Body:**
```json
{
  "community_id": "string"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "channel_id": "C01234567"
}
```

**Error Responses:**
- `404 Not Found` - Message not found
- `500 Internal Server Error` - Deletion failed

---

## Reactions

### Add Reaction

**POST** `/api/v1/reaction`

Add an emoji reaction to a message.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "channel_id": "string",
  "ts": "string",
  "emoji": "string"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "channel_id": "C01234567",
  "ts": "1234567890.123456",
  "emoji": "thumbsup"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid emoji name
- `500 Internal Server Error` - Slack API error

---

### Remove Reaction

**DELETE** `/api/v1/reaction`

Remove an emoji reaction from a message.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "channel_id": "string",
  "ts": "string",
  "emoji": "string"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "channel_id": "C01234567",
  "emoji": "thumbsup"
}
```

**Error Responses:**
- `500 Internal Server Error` - Removal failed

---

## Files

### Upload File

**POST** `/api/v1/file`

Upload a file to a Slack channel.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "channel_id": "string",
  "file_content_base64": "string",
  "filename": "string",
  "title": "string (optional)"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "file_id": "F01234567",
  "channel_id": "C01234567"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid base64 encoding
- `413 Payload Too Large` - File size exceeds limit
- `500 Internal Server Error` - Upload failed

**File Size Limits:**
- Maximum 20 MB per file
- Base64 encoded size must be less than 25 MB

---

## Channel Management

### Create Channel

**POST** `/api/v1/channel`

Create a new Slack channel.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "name": "string",
  "is_private": false
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "channel_id": "C01234567",
  "name": "team-announcements"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid channel name
- `409 Conflict` - Channel already exists
- `500 Internal Server Error` - Creation failed

**Channel Name Rules:**
- 80 characters maximum
- Lowercase alphanumeric, dashes, and underscores only
- Must start with a letter

---

### Invite Users to Channel

**POST** `/api/v1/channel/invite`

Invite one or more users to a channel.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "channel_id": "string",
  "user_ids": ["U01234567", "U02345678"]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "channel_id": "C01234567",
  "invited_count": 2
}
```

**Error Responses:**
- `400 Bad Request` - Invalid user IDs
- `404 Not Found` - Channel not found
- `500 Internal Server Error` - Invitation failed

---

### Kick User from Channel

**POST** `/api/v1/channel/kick`

Remove a user from a channel.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "channel_id": "string",
  "user_id": "string"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "channel_id": "C01234567",
  "user_id": "U01234567"
}
```

**Error Responses:**
- `404 Not Found` - User or channel not found
- `500 Internal Server Error` - Removal failed

---

### Set Channel Topic

**PUT** `/api/v1/channel/topic`

Set or update the channel topic (description).

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "channel_id": "string",
  "topic": "string"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "channel_id": "C01234567",
  "topic": "Team announcements and updates"
}
```

**Error Responses:**
- `400 Bad Request` - Topic too long (max 250 chars)
- `500 Internal Server Error` - Update failed

---

## Modals and Interactive Components

### Open Modal

**POST** `/api/v1/modal`

Open an interactive modal dialog in Slack.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": "string",
  "trigger_id": "string",
  "view": {
    "type": "modal",
    "callback_id": "string",
    "title": {
      "type": "plain_text",
      "text": "Modal Title"
    },
    "submit": {
      "type": "plain_text",
      "text": "Submit"
    },
    "blocks": []
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "view_id": "V01234567"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid view structure
- `500 Internal Server Error` - Modal open failed

**View Structure:**
- Must conform to Slack Block Kit modal specification
- Maximum 100 blocks per view
- Trigger ID expires after 3 seconds

---

## History

### Get Action History

**GET** `/api/v1/history/{community_id}`

Retrieve action history for a community.

**Authentication:** Required (Bearer token)

**Path Parameters:**
- `community_id` - Community identifier

**Query Parameters:**
- `limit` - Number of records to return (default: 100, max: 1000)

**Response (200 OK):**
```json
{
  "history": [
    {
      "id": 1,
      "community_id": "acme-community",
      "action_type": "send_message",
      "channel_id": "C01234567",
      "success": true,
      "error": null,
      "created_at": "2024-01-15T10:30:00Z",
      "details": {
        "message_ts": "1234567890.123456"
      }
    },
    {
      "id": 2,
      "community_id": "acme-community",
      "action_type": "add_reaction",
      "channel_id": "C01234567",
      "success": true,
      "error": null,
      "created_at": "2024-01-15T10:31:00Z",
      "details": {
        "emoji": "thumbsup",
        "ts": "1234567890.123456"
      }
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request` - Invalid limit parameter
- `500 Internal Server Error` - Database query failed

**Action Types in History:**
- `send_message`
- `ephemeral_message`
- `update_message`
- `delete_message`
- `add_reaction`
- `remove_reaction`
- `upload_file`
- `create_channel`
- `invite_users`
- `kick_user`
- `set_topic`
- `open_modal`

---

## Error Handling

All error responses follow this format:

```json
{
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
| `409 Conflict` | Resource already exists (e.g., channel) |
| `413 Payload Too Large` | Request body exceeds size limit |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server error or Slack API error |
| `503 Service Unavailable` | Database or dependency unavailable |

### Common Slack API Errors

| Error Code | Meaning | Solution |
|-----------|---------|----------|
| `invalid_auth` | Token invalid or expired | Refresh SLACK_BOT_TOKEN |
| `token_revoked` | Token has been revoked | Reinstall app to workspace |
| `channel_not_found` | Channel ID invalid | Verify channel ID format |
| `not_in_channel` | Bot not member of channel | Manually invite bot or use `channels.invite` |
| `no_permission` | Missing required scopes | Grant required OAuth scopes |
| `rate_limited` | Too many requests | Implement exponential backoff |
| `message_not_found` | Message TS invalid | Verify message still exists |
| `file_not_uploaded` | File upload failed | Check file size and format |
| `user_not_found` | User ID invalid | Verify user ID exists |

---

## Rate Limiting

The module implements rate limiting at 100 concurrent requests by default.

**Headers in Response:**
```
X-Rate-Limit-Limit: 100
X-Rate-Limit-Remaining: 95
X-Rate-Limit-Reset: 1234567890
```

When rate limit exceeded (HTTP 429):
```json
{
  "error": "rate_limited",
  "message": "Too many requests. Retry after 60 seconds.",
  "retry_after": 60
}
```

---

## Request/Response Examples

### Full Request Cycle

```bash
# 1. Generate token
curl -X POST http://localhost:8071/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "secret", "client_id": "app"}' \
  -w "\n%{http_code}\n"

# 2. Use token in request
curl -X POST http://localhost:8071/api/v1/message \
  -H "Authorization: Bearer eyJ0eXAi..." \
  -H "Content-Type: application/json" \
  -d '{"community_id": "test", "channel_id": "C123", "text": "Hello"}' \
  -w "\n%{http_code}\n"

# 3. Check history
curl http://localhost:8071/api/v1/history/test?limit=10 \
  -H "Authorization: Bearer eyJ0eXAi..." \
  -w "\n%{http_code}\n"
```
