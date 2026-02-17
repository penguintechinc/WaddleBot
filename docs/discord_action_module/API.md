# Discord Action Module - REST API Reference

## Base URL

```
http://localhost:8070/api/v1
```

All requests require JWT authentication via `Authorization: Bearer TOKEN` header, except health and token endpoints.

## Authentication Endpoints

### POST /token - Generate JWT Token

Generate a JWT token for API authentication.

**Request:**
```json
{
  "client_id": "string",
  "client_secret": "string"
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
curl -X POST http://localhost:8070/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "app1",
    "client_secret": "secret123"
  }'
```

**Errors:**
- 400: Missing client_id or client_secret
- 401: Invalid credentials

---

## Message Endpoints

### POST /message - Send Message

Send a text message to a Discord channel.

**Request:**
```json
{
  "channel_id": "string",
  "content": "string",
  "embed": { "object": "optional" }
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "123456789987654321"
}
```

**Example:**
```bash
curl -X POST http://localhost:8070/api/v1/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "channel_id": "123456789",
    "content": "Hello Discord!"
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing channel_id or content
- 500: Discord API error
- 503: Discord credentials not configured

---

### POST /embed - Send Rich Embed

Send a rich embed (formatted message) to a channel.

**Request:**
```json
{
  "channel_id": "string",
  "embed": {
    "title": "string",
    "description": "string",
    "color": 3447003,
    "fields": [
      {
        "name": "Field Name",
        "value": "Field Value",
        "inline": false
      }
    ]
  }
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "123456789987654321"
}
```

**Example:**
```bash
curl -X POST http://localhost:8070/api/v1/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "channel_id": "123456789",
    "embed": {
      "title": "Achievement Unlocked",
      "description": "You earned a badge!",
      "color": 3447003
    }
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing channel_id or embed
- 500: Discord API error

---

### DELETE /message/{channel_id}/{message_id} - Delete Message

Delete a message from a channel.

**Path Parameters:**
- channel_id: Discord channel ID
- message_id: Discord message ID

**Response:**
```json
{
  "success": true
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8070/api/v1/message/123456789/987654321 \
  -H "Authorization: Bearer TOKEN"
```

**Errors:**
- 401: Invalid/missing authentication
- 500: Discord API error (may include "Message not found")

---

### PATCH /message/{channel_id}/{message_id} - Edit Message

Edit an existing message.

**Path Parameters:**
- channel_id: Discord channel ID
- message_id: Discord message ID

**Request:**
```json
{
  "content": "string"
}
```

**Response:**
```json
{
  "success": true
}
```

**Example:**
```bash
curl -X PATCH http://localhost:8070/api/v1/message/123456789/987654321 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "content": "Updated message content"
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing content
- 500: Discord API error

---

## Reaction Endpoints

### POST /reaction - Add Emoji Reaction

Add an emoji reaction to a message.

**Request:**
```json
{
  "channel_id": "string",
  "message_id": "string",
  "emoji": "string"
}
```

**Response:**
```json
{
  "success": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8070/api/v1/reaction \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "channel_id": "123456789",
    "message_id": "987654321",
    "emoji": "👍"
  }'
```

**Emoji Formats:**
- Unicode emoji: "👍", "❤️", "🎉"
- Custom emoji: "name:id"
- Animated emoji: "a:name:id"

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing required fields
- 500: Discord API error (invalid emoji, message not found, etc.)

---

## Role Endpoints

### POST /role - Manage User Role

Add or remove a role from a user.

**Request:**
```json
{
  "guild_id": "string",
  "user_id": "string",
  "role_id": "string",
  "action": "add|remove"
}
```

**Response:**
```json
{
  "success": true
}
```

**Example - Add Role:**
```bash
curl -X POST http://localhost:8070/api/v1/role \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "guild_id": "987654321",
    "user_id": "123456789",
    "role_id": "555555555",
    "action": "add"
  }'
```

**Example - Remove Role:**
```bash
curl -X POST http://localhost:8070/api/v1/role \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "guild_id": "987654321",
    "user_id": "123456789",
    "role_id": "555555555",
    "action": "remove"
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing required fields
- 500: Discord API error (insufficient permissions, role not found, etc.)

---

## Webhook Endpoints

### POST /webhook - Create Webhook

Create a webhook in a Discord channel.

**Request:**
```json
{
  "channel_id": "string",
  "name": "string"
}
```

**Response:**
```json
{
  "success": true,
  "webhook_url": "https://discord.com/api/webhooks/..."
}
```

**Example:**
```bash
curl -X POST http://localhost:8070/api/v1/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "channel_id": "123456789",
    "name": "WaddleBot Notifications"
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing channel_id
- 500: Discord API error (no permissions, etc.)

---

### POST /webhook/send - Send via Webhook

Send a message through a webhook.

**Request:**
```json
{
  "webhook_url": "string",
  "content": "string",
  "embeds": [{ "object": "array" }]
}
```

**Response:**
```json
{
  "success": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8070/api/v1/webhook/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "webhook_url": "https://discord.com/api/webhooks/...",
    "content": "Notification from WaddleBot",
    "embeds": [{
      "title": "Event Occurred",
      "description": "Something happened"
    }]
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing webhook_url or content
- 500: Discord API error (invalid webhook, etc.)

---

## Moderation Endpoints

### POST /moderation/kick - Kick User

Remove a user from a guild.

**Request:**
```json
{
  "guild_id": "string",
  "user_id": "string",
  "reason": "string"
}
```

**Response:**
```json
{
  "success": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8070/api/v1/moderation/kick \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "guild_id": "987654321",
    "user_id": "123456789",
    "reason": "Violating server rules"
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing guild_id or user_id
- 500: Discord API error (no permissions, user not in server, etc.)

---

### POST /moderation/ban - Ban User

Permanently ban a user from a guild.

**Request:**
```json
{
  "guild_id": "string",
  "user_id": "string",
  "reason": "string",
  "delete_message_days": 0
}
```

**Response:**
```json
{
  "success": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8070/api/v1/moderation/ban \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "guild_id": "987654321",
    "user_id": "123456789",
    "reason": "Spam and harassment",
    "delete_message_days": 7
  }'
```

**Parameters:**
- delete_message_days: 0-7, number of days of messages to delete

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing guild_id or user_id
- 500: Discord API error (no permissions, etc.)

---

### POST /moderation/timeout - Timeout User

Temporarily mute a user (prevent message sending).

**Request:**
```json
{
  "guild_id": "string",
  "user_id": "string",
  "duration_seconds": 3600,
  "reason": "string"
}
```

**Response:**
```json
{
  "success": true
}
```

**Example - 1 hour timeout:**
```bash
curl -X POST http://localhost:8070/api/v1/moderation/timeout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "guild_id": "987654321",
    "user_id": "123456789",
    "duration_seconds": 3600,
    "reason": "Spam"
  }'
```

**Errors:**
- 401: Invalid/missing authentication
- 400: Missing required fields
- 500: Discord API error (no permissions, etc.)

---

## System Endpoints

### GET /health - Health Check

Check module health and configuration status.

**Response:**
```json
{
  "status": "healthy",
  "module": "discord_action_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:45.123456",
  "config": {
    "module_name": "discord_action_module",
    "grpc_port": 50051,
    "rest_port": 8070,
    "database_configured": true,
    "discord_token_configured": true
  }
}
```

**Example:**
```bash
curl http://localhost:8070/health
```

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
- 500: Internal Server Error (Discord API error)
- 503: Service Unavailable (credentials not configured)

---

## Rate Limiting

The module enforces Discord API rate limits:

- Global: 50 requests/second
- Per-channel: 5 requests/second

Rate limit headers in response:
- X-RateLimit-Limit
- X-RateLimit-Remaining
- X-RateLimit-Reset

If rate limited, wait until X-RateLimit-Reset timestamp.

---

## Authentication

All API endpoints (except /health and /token) require JWT authentication:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" ...
```

Tokens expire after JWT_EXPIRATION_SECONDS (default: 3600). Request a new token when expired.

---

## Discord API Version

This module uses Discord API v10. Refer to Discord API documentation for additional details:
https://discord.com/developers/docs/reference
