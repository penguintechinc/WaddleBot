# Twitch Module API Reference

## Overview

The Twitch Module exposes HTTP endpoints for webhook ingestion, status queries, channel management, and message sending. All endpoints are asynchronous (Quart/ASGI).

## Core Endpoints

### Health & Status

#### `GET /health`

Check service health (liveness probe).

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "v1.2.0",
  "uptime_seconds": 3600,
  "timestamp": "2025-02-24T10:30:00Z"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "reason": "database_connection_failed",
  "timestamp": "2025-02-24T10:30:00Z"
}
```

**Query Parameters**:
- `type=ready`: Readiness probe (checks database, cache, Twitch API connectivity)

**Example**:
```bash
curl http://localhost:8002/health
curl http://localhost:8002/health?type=ready
```

---

#### `GET /api/v1/status`

Detailed service status and configuration.

**Response** (200 OK):
```json
{
  "service": "twitch-module",
  "version": "v1.2.0",
  "uptime_seconds": 3600,
  "bot": {
    "enabled": true,
    "connected": true,
    "nickname": "WaddleBot",
    "active_channels": 42,
    "total_channels": 50
  },
  "eventsub": {
    "enabled": true,
    "connected": true,
    "subscriptions_active": 210,
    "last_webhook": "2025-02-24T10:29:30Z"
  },
  "viewer_tracking": {
    "enabled": true,
    "channels_tracked": 42,
    "last_poll": "2025-02-24T10:29:45Z",
    "total_viewers_cached": 15420
  },
  "cache": {
    "type": "redis",
    "connected": true,
    "keys_cached": 8500
  },
  "metrics": {
    "messages_processed_24h": 125000,
    "events_processed_24h": 4200,
    "errors_24h": 12,
    "avg_latency_ms": 45.3
  }
}
```

**Example**:
```bash
curl http://localhost:8002/api/v1/status
```

---

#### `GET /metrics`

Prometheus-format metrics for monitoring.

**Response** (200 OK):
```
# HELP twitch_messages_total Total messages received and processed
# TYPE twitch_messages_total counter
twitch_messages_total{source="irc"} 125000
twitch_messages_total{source="eventsub"} 4200

# HELP twitch_message_latency_ms Message processing latency in milliseconds
# TYPE twitch_message_latency_ms histogram
twitch_message_latency_ms_bucket{le="10"} 50000
twitch_message_latency_ms_bucket{le="50"} 120000
twitch_message_latency_ms_bucket{le="100"} 129000

# HELP twitch_errors_total Total errors by type
# TYPE twitch_errors_total counter
twitch_errors_total{type="auth"} 2
twitch_errors_total{type="api"} 8
twitch_errors_total{type="webhook_verification"} 2

# HELP twitch_channels_active Active monitored channels
# TYPE twitch_channels_active gauge
twitch_channels_active 42

# HELP twitch_viewers_tracked Total unique viewers tracked
# TYPE twitch_viewers_tracked gauge
twitch_viewers_tracked 15420
```

**Example**:
```bash
curl http://localhost:8002/metrics
```

---

### EventSub Webhooks

#### `POST /eventsub/webhook`

Receive Twitch EventSub webhook events. **All requests must include `Twitch-Eventsub-Message-Id` header and valid HMAC-SHA256 signature.**

**Headers** (Required):
```
Twitch-Eventsub-Message-Id: <uuid>
Twitch-Eventsub-Timestamp: <ISO-8601>
Twitch-Eventsub-Signature: sha256=<hmac>
Content-Type: application/json
```

**Body** (Example: channel.subscribe):
```json
{
  "subscription": {
    "id": "sub-123",
    "status": "enabled",
    "type": "channel.subscribe",
    "version": "1",
    "condition": {
      "broadcaster_user_id": "12345"
    },
    "transport": {
      "method": "webhook",
      "callback": "https://waddlebot.penguintech.cloud/eventsub/webhook"
    },
    "created_at": "2025-02-24T10:00:00Z"
  },
  "event": {
    "user_id": "67890",
    "user_login": "subscriber_user",
    "user_name": "Subscriber User",
    "broadcaster_user_id": "12345",
    "broadcaster_user_login": "channel_owner",
    "broadcaster_user_name": "Channel Owner",
    "tier": "1000",
    "is_gift": false
  }
}
```

**Response** (200 OK):
```json
{
  "status": "received",
  "message_id": "sub-123",
  "type": "channel.subscribe"
}
```

**Supported Event Types**:
- `channel.subscribe` - New subscription
- `channel.subscription.gift` - Gift subscription
- `channel.raid` - Channel raid
- `channel.follow` - New follower (requires OAuth scope)
- `channel.cheer` - Bits/cheer donation
- `stream.online` - Stream went live
- `stream.offline` - Stream ended

**Status Codes**:
- `200 OK` - Event processed successfully
- `400 Bad Request` - Missing headers or invalid JSON
- `403 Forbidden` - HMAC signature verification failed
- `409 Conflict` - Duplicate message ID (already processed)
- `500 Internal Server Error` - Processing error (retry will be attempted)

**Example**:
```bash
curl -X POST http://localhost:8002/eventsub/webhook \
  -H "Twitch-Eventsub-Message-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -H "Twitch-Eventsub-Timestamp: 2025-02-24T10:30:00Z" \
  -H "Twitch-Eventsub-Signature: sha256=abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription": { ... },
    "event": { ... }
  }'
```

---

### Bot Management

#### `GET /api/v1/bot/channels`

List all monitored channels and their status.

**Query Parameters**:
- `status`: Filter by status (`joined`, `joining`, `failed`, `all`) — default: `all`
- `limit`: Max results (default: 100, max: 1000)
- `offset`: Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "channels": [
    {
      "channel_id": "12345",
      "channel_name": "example_channel",
      "status": "joined",
      "joined_at": "2025-02-20T08:00:00Z",
      "viewer_count": 420,
      "is_live": true,
      "last_message": "2025-02-24T10:29:45Z"
    },
    {
      "channel_id": "67890",
      "channel_name": "another_channel",
      "status": "joined",
      "joined_at": "2025-02-19T12:00:00Z",
      "viewer_count": 1200,
      "is_live": false,
      "last_message": "2025-02-24T10:25:30Z"
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

**Example**:
```bash
curl http://localhost:8002/api/v1/bot/channels
curl http://localhost:8002/api/v1/bot/channels?status=joined&limit=10
```

---

#### `POST /api/v1/bot/send`

Send a message to a Twitch channel (internal API).

**Headers** (Required):
```
Authorization: Bearer <SERVICE_API_KEY>
Content-Type: application/json
```

**Body**:
```json
{
  "channel_id": "12345",
  "message": "Hello, viewers!",
  "is_broadcaster_command": false,
  "reply_to_message_id": "msg-123"
}
```

**Response** (200 OK):
```json
{
  "status": "sent",
  "message_id": "sent-456",
  "channel_id": "12345",
  "message": "Hello, viewers!",
  "sent_at": "2025-02-24T10:30:01Z"
}
```

**Response** (400 Bad Request):
```json
{
  "error": "invalid_channel_id",
  "details": "Channel 12345 not in joined channels"
}
```

**Status Codes**:
- `200 OK` - Message sent successfully
- `400 Bad Request` - Invalid channel or message format
- `401 Unauthorized` - Missing/invalid API key
- `403 Forbidden` - Channel not joined
- `429 Too Many Requests` - Rate limit exceeded (Twitch allows ~20 msgs/30s per channel)
- `500 Internal Server Error` - Send failed (will retry)

**Notes**:
- Messages automatically split if exceeding 500 characters
- API key validated against `SERVICE_API_KEY` environment variable
- Only available from internal services (router, hub, etc.)

**Example**:
```bash
curl -X POST http://localhost:8002/api/v1/bot/send \
  -H "Authorization: Bearer secret-api-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "12345",
    "message": "Hello, viewers!"
  }'
```

---

## Router Integration Endpoints

These endpoints are called by the router to send responses back to Twitch.

#### `POST /api/v1/messages` (from Router)

Called by waddlebot-router to send message response to Twitch chat.

**Headers** (Required):
```
Authorization: Bearer <ROUTER_API_KEY>
Content-Type: application/json
```

**Body**:
```json
{
  "channel_id": "12345",
  "user_id": "67890",
  "message": "Command response here",
  "context": {
    "original_message_id": "msg-123",
    "command": "!ping"
  }
}
```

**Response** (200 OK):
```json
{
  "status": "sent",
  "message_ids": ["sent-456", "sent-457"],
  "split_count": 2,
  "timestamp": "2025-02-24T10:30:01Z"
}
```

---

## Leaderboard Integration

#### `POST /api/v1/leaderboards/viewers/{channel_id}` (from Module to Hub)

Sent by ViewerTracker to Hub API to update real-time viewer presence.

**Headers** (Required):
```
Authorization: Bearer <HUB_API_KEY>
Content-Type: application/json
```

**Body**:
```json
{
  "channel_id": "12345",
  "viewers": [
    {
      "user_id": "u1",
      "user_login": "viewer1",
      "event": "join",
      "timestamp": "2025-02-24T10:30:00Z"
    },
    {
      "user_id": "u2",
      "user_login": "viewer2",
      "event": "heartbeat",
      "timestamp": "2025-02-24T10:30:00Z"
    },
    {
      "user_id": "u3",
      "user_login": "viewer3",
      "event": "leave",
      "timestamp": "2025-02-24T10:29:45Z"
    }
  ],
  "poll_timestamp": "2025-02-24T10:30:00Z"
}
```

---

## Error Handling

All endpoints return errors in standard format:

```json
{
  "error": "<error_code>",
  "message": "<human-readable message>",
  "details": "<optional debugging info>",
  "correlation_id": "corr-123",
  "timestamp": "2025-02-24T10:30:00Z"
}
```

**Common Error Codes**:
- `invalid_request` - Malformed request
- `unauthorized` - Missing/invalid authentication
- `forbidden` - Access denied (channel not joined, etc.)
- `not_found` - Resource not found
- `rate_limit_exceeded` - Too many requests
- `external_api_error` - Twitch API failed
- `internal_error` - Service error

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/v1/bot/send` | 20 messages | 30 seconds per channel |
| `/eventsub/webhook` | Unlimited | Per webhook (Twitch enforces) |
| `/api/v1/status` | 100 | 1 minute |
| `/metrics` | 100 | 1 minute |

---

## Authentication

**Service API Key** (`SERVICE_API_KEY`):
- Required for `/api/v1/bot/send`, `/api/v1/messages` (from router)
- Format: `Authorization: Bearer <key>`
- 32+ character random string

**EventSub Verification** (HMAC-SHA256):
- All webhooks verified via signature header
- Signature = `sha256=<hmac(secret, message_id+timestamp+body)>`
- Timestamp must be within 10 minutes of current time
- Prevents replay attacks and webhook spoofing

---

## Examples

### Send a message via bot
```bash
curl -X POST http://localhost:8002/api/v1/bot/send \
  -H "Authorization: Bearer my-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "12345",
    "message": "Hello, community!"
  }'
```

### Check service status
```bash
curl http://localhost:8002/api/v1/status | jq .
```

### Verify webhook delivery
```bash
# Check metrics for webhook delivery rate
curl http://localhost:8002/metrics | grep twitch_eventsub
```

### Debug channel status
```bash
curl http://localhost:8002/api/v1/bot/channels?status=joined | jq '.channels[] | {name: .channel_name, viewers: .viewer_count, live: .is_live}'
```
