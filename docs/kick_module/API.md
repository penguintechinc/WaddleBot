# Kick Module API Documentation

## Overview

The Kick Module exposes HTTP endpoints for webhook reception, health checks, and status monitoring. All responses use standard HTTP status codes and JSON payloads.

## Authentication

### Webhook Signature Verification

Kick platform sends a `X-Signature` header with each webhook request. Signature format:

```
X-Signature: sha256=<hex-encoded-hmac>
```

**Verification Algorithm:**

```python
import hmac
import hashlib

received_signature = request.headers.get('X-Signature', '')
expected_signature = 'sha256=' + hmac.new(
    SECRET_KEY.encode(),
    request.body,
    hashlib.sha256
).hexdigest()

if not hmac.compare_digest(received_signature, expected_signature):
    return 401 Unauthorized
```

All other endpoints require no authentication but should be protected via network policies or API gateway rules.

## Endpoints

### POST /webhook/kick

Receives webhook events from Kick platform.

**Request Headers:**

```
X-Signature: sha256=<hmac-sha256-hex>
Content-Type: application/json
```

**Request Body:**

```json
{
  "event": "chat_message|subscription|raid|etc",
  "created_at": "2026-02-24T12:34:56Z",
  "data": {
    "channel_id": 12345,
    "username": "user_handle",
    "message": "chat text...",
    "...": "event-specific fields"
  }
}
```

**Response (202 Accepted):**

```json
{
  "status": "accepted",
  "event_id": "evt_abc123xyz",
  "timestamp": "2026-02-24T12:34:56.789Z"
}
```

**Response (400 Bad Request):**

```json
{
  "error": "invalid_signature|missing_event|malformed_payload",
  "message": "Human-readable error description",
  "timestamp": "2026-02-24T12:34:56.789Z"
}
```

**Response (401 Unauthorized):**

```json
{
  "error": "signature_mismatch",
  "message": "HMAC-SHA256 verification failed",
  "timestamp": "2026-02-24T12:34:56.789Z"
}
```

**Response (500 Internal Server Error):**

```json
{
  "error": "processing_failed",
  "message": "Exception message or generic failure description",
  "timestamp": "2026-02-24T12:34:56.789Z"
}
```

**Event Types Accepted:**

- `chat_message` - User chat message
- `subscription` - Channel subscription (paid)
- `gifted_subscription` - Gift subscription to another user
- `channel_follow` - User followed channel
- `stream_start` - Livestream started
- `stream_end` - Livestream ended
- `raid` - Channel raid incoming
- `ban` - User banned from channel
- `timeout` - User timeout issued
- `user_banned_from_channel` - Permanent ban applied

**Processing:**

1. Signature verification (401 if fails)
2. Payload parsing (400 if invalid)
3. Event normalization to standard format
4. Async forward to `ROUTER_API_URL`
5. Return 202 immediately (processing continues in background)

### GET /api/v1/status

Returns module health and operational status.

**Response (200 OK):**

```json
{
  "module": "kick",
  "status": "operational|degraded|offline",
  "timestamp": "2026-02-24T12:34:56.789Z",
  "version": "v1.0.0",
  "components": {
    "api": "ok|degraded|error",
    "websocket": "ok|degraded|error",
    "database": "ok|degraded|error",
    "router": "ok|degraded|error"
  },
  "stats": {
    "events_received": 12847,
    "events_processed": 12841,
    "websocket_connections": 3,
    "uptime_seconds": 86400,
    "last_error": "router_timeout_3s_ago"
  }
}
```

**Status Values:**

- `operational`: All systems nominal
- `degraded`: Non-critical systems offline, main service functioning
- `offline`: Service unavailable or critical component down

### GET /health

Simple health check endpoint for load balancers and orchestration platforms.

**Response (200 OK):**

```json
{
  "status": "healthy"
}
```

**Response (503 Service Unavailable):**

```json
{
  "status": "unhealthy"
}
```

Returns 200 if the module is operational enough to handle requests. Returns 503 if critical systems (router connection, database) are unavailable.

### GET /metrics

Prometheus-compatible metrics export.

**Response (200 OK):**

```
# HELP kick_webhook_received_total Total webhooks received
# TYPE kick_webhook_received_total counter
kick_webhook_received_total 12847

# HELP kick_webhook_rejected_total Total webhooks rejected (signature/format)
# TYPE kick_webhook_rejected_total counter
kick_webhook_rejected_total 3

# HELP kick_event_processed_total Total events processed and forwarded
# TYPE kick_event_processed_total counter
kick_event_processed_total{event_type="chat"} 8234
kick_event_processed_total{event_type="subscription"} 1205
kick_event_processed_total{event_type="raid"} 847
kick_event_processed_total{event_type="moderation"} 142

# HELP kick_websocket_connections_active Active WebSocket connections
# TYPE kick_websocket_connections_active gauge
kick_websocket_connections_active 3

# HELP kick_router_api_latency_ms Router API response latency
# TYPE kick_router_api_latency_ms histogram
kick_router_api_latency_ms_bucket{le="100"} 6234
kick_router_api_latency_ms_bucket{le="500"} 6841
kick_router_api_latency_ms_bucket{le="1000"} 6900
kick_router_api_latency_ms_bucket{le="+Inf"} 6934

# HELP kick_websocket_reconnect_total WebSocket reconnection attempts
# TYPE kick_websocket_reconnect_total counter
kick_websocket_reconnect_total 12
```

## Event Payload Examples

### ChatMessage Event

**Webhook Payload:**

```json
{
  "event": "chat_message",
  "created_at": "2026-02-24T12:34:56Z",
  "data": {
    "channel_id": 12345,
    "chatroom_id": 67890,
    "username": "user_handle",
    "user_id": 54321,
    "message": "Hello everyone!",
    "message_id": "msg_xyz789",
    "badges": ["moderator", "subscriber"],
    "is_verified": false,
    "profile_pic_url": "https://..."
  }
}
```

**Normalized Output (to Router):**

```json
{
  "platform": "kick",
  "event_type": "chat",
  "channel_id": "12345",
  "user": {
    "id": "54321",
    "username": "user_handle",
    "display_name": "user_handle",
    "avatar_url": "https://...",
    "badges": ["moderator", "subscriber"]
  },
  "content": "Hello everyone!",
  "metadata": {
    "message_id": "msg_xyz789",
    "chatroom_id": "67890",
    "is_verified": false
  }
}
```

### SubscriptionEvent

**Webhook Payload:**

```json
{
  "event": "subscription",
  "created_at": "2026-02-24T12:34:56Z",
  "data": {
    "channel_id": 12345,
    "username": "subscriber_user",
    "user_id": 55555,
    "tier": "1",
    "months": 3
  }
}
```

**Normalized Output:**

```json
{
  "platform": "kick",
  "event_type": "subscription",
  "channel_id": "12345",
  "user": {
    "id": "55555",
    "username": "subscriber_user"
  },
  "metadata": {
    "tier": "1",
    "months": 3,
    "is_gift": false
  }
}
```

### RaidEvent

**Webhook Payload:**

```json
{
  "event": "raid",
  "created_at": "2026-02-24T12:34:56Z",
  "data": {
    "channel_id": 12345,
    "raider_username": "raiding_channel",
    "raider_channel_id": 11111,
    "viewer_count": 245
  }
}
```

**Normalized Output:**

```json
{
  "platform": "kick",
  "event_type": "raid",
  "channel_id": "12345",
  "user": {
    "id": "11111",
    "username": "raiding_channel"
  },
  "metadata": {
    "viewer_count": 245
  }
}
```

## Error Handling

### Common Error Scenarios

| Status | Error Code | Cause | Resolution |
|--------|-----------|-------|-----------|
| 400 | `invalid_signature` | HMAC mismatch | Verify SECRET_KEY matches Kick console |
| 400 | `missing_event` | No "event" field | Check payload structure |
| 400 | `malformed_payload` | JSON parse error | Validate JSON syntax |
| 401 | `signature_mismatch` | Signature verification failed | Check timestamp freshness |
| 500 | `processing_failed` | Router API unreachable | Check ROUTER_API_URL configuration |
| 500 | `database_error` | DB connection failed | Check DATABASE_URL and connection limits |

### Retry Behavior

Webhook requests that receive 5xx responses should be retried by Kick platform with exponential backoff. The module returns 202 Accepted immediately upon receiving valid webhooks; if processing fails asynchronously, it logs errors but does not re-signal the client.

## Rate Limiting

No explicit rate limiting implemented at module level. Platform-level limits apply:

- Kick API: 100 requests per minute (for REST calls via KickAPI)
- WebSocket: 1 connection per monitored channel
- Webhook: No documented limit (depends on stream activity)

## Timeout Values

- Webhook signature verification: &lt;10ms
- Router API calls: 10s default (configurable)
- Database queries: 5s default
- WebSocket connection: 30s
- WebSocket reconnect backoff: 1s → 30s max

## See Also

- [Configuration Guide](CONFIGURATION.md)
- [Usage Examples](USAGE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
