# YouTube Live Module API Reference

Complete API documentation for the YouTube Live module endpoints.

## Base URL

```
http://localhost:8006/api/v1
```

## Authentication

Most endpoints do not require authentication for module-to-module communication. However, in production deployments behind a gateway, authentication may be enforced. Check your deployment's ingress configuration.

## Channel Management Endpoints

### Register Channel

Register a YouTube channel for monitoring.

```
POST /api/v1/channels/register
Content-Type: application/json
```

**Request Body:**

```json
{
  "channel_id": "UCxxxxxxxxxx",
  "channel_name": "My Channel Name"
}
```

**Response (200 OK):**

```json
{
  "status": "success",
  "channel_id": "UCxxxxxxxxxx",
  "channel_name": "My Channel Name",
  "registered_at": "2026-02-24T10:30:00Z"
}
```

**Response (400 Bad Request):**

```json
{
  "status": "error",
  "message": "Invalid channel_id format"
}
```

**Response (409 Conflict):**

```json
{
  "status": "error",
  "message": "Channel already registered"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| channel_id | string | Yes | YouTube channel ID (UC prefix) |
| channel_name | string | Yes | Display name for the channel |

---

### Unregister Channel

Stop monitoring a YouTube channel.

```
DELETE /api/v1/channels/{channel_id}
```

**Response (200 OK):**

```json
{
  "status": "success",
  "channel_id": "UCxxxxxxxxxx",
  "message": "Channel unregistered successfully"
}
```

**Response (404 Not Found):**

```json
{
  "status": "error",
  "message": "Channel not found"
}
```

**Path Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| channel_id | string | YouTube channel ID |

---

### List Registered Channels

Retrieve all registered channels and their status.

```
GET /api/v1/channels
```

**Response (200 OK):**

```json
{
  "status": "success",
  "channels": [
    {
      "channel_id": "UCxxxxxxxxxx",
      "channel_name": "My Channel",
      "is_active": true,
      "broadcast_id": "YxxxxxxxxxB",
      "broadcast_title": "Live Stream #123",
      "registered_at": "2026-02-24T09:00:00Z",
      "last_message_at": "2026-02-24T10:35:15Z",
      "error_count": 0
    },
    {
      "channel_id": "UCyyyyyyyyyy",
      "channel_name": "Another Channel",
      "is_active": false,
      "broadcast_id": null,
      "registered_at": "2026-02-24T08:00:00Z",
      "last_message_at": null,
      "error_count": 0
    }
  ],
  "total_channels": 2,
  "active_streams": 1
}
```

**Query Parameters:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| status | string | all | Filter by status: `active`, `inactive`, `error` |
| limit | integer | 50 | Maximum results to return |
| offset | integer | 0 | Pagination offset |

---

## Broadcast Endpoints

### Get Active Broadcasts

Retrieve currently active broadcasts for a channel.

```
GET /api/v1/broadcasts/{channel_id}
```

**Response (200 OK):**

```json
{
  "status": "success",
  "channel_id": "UCxxxxxxxxxx",
  "broadcasts": [
    {
      "broadcast_id": "YxxxxxxxxxB",
      "title": "Live Stream #123",
      "description": "Streaming some gaming today!",
      "status": "live",
      "started_at": "2026-02-24T09:00:00Z",
      "live_chat_id": "Ugxxxxxxxxxxxxxxxxxxx",
      "concurrent_viewers": 245,
      "thumbnail_url": "https://i.ytimg.com/vi/xxx/maxresdefault.jpg"
    }
  ]
}
```

**Response (404 Not Found):**

```json
{
  "status": "error",
  "message": "Channel not found"
}
```

**Path Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| channel_id | string | YouTube channel ID |

---

## Webhook Endpoints

### PubSubHubbub Subscription Verification

YouTube sends a verification challenge during webhook subscription.

```
GET /api/v1/webhook
```

**Query Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| hub.mode | string | `subscribe` or `unsubscribe` |
| hub.topic | string | Topic URL being subscribed to |
| hub.challenge | string | Challenge token to echo back |
| hub.lease_seconds | integer | Lease duration in seconds |

**Response (200 OK):**

Plain text response containing the challenge token:

```
hub.challenge_value
```

---

### PubSubHubbub Notification Callback

Receive stream event notifications from YouTube.

```
POST /api/v1/webhook
Content-Type: application/atom+xml
```

**Request Body:**

Atom XML feed format from YouTube PubSubHubbub service.

**Response (200 OK):**

```json
{
  "status": "success",
  "message": "Webhook processed successfully"
}
```

**Response (400 Bad Request):**

```json
{
  "status": "error",
  "message": "Invalid webhook payload"
}
```

**Important Notes:**

- YouTube sends XML in Atom format
- The module parses XML and extracts stream start/end events
- Events are forwarded to the router API
- Module must respond with 200 OK within 5 seconds or YouTube may retry

---

## Health Check Endpoints

### Health Status

Check module health and readiness.

```
GET /health
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "version": "1.0.0"
}
```

**Response (503 Service Unavailable):**

```json
{
  "status": "unhealthy",
  "message": "Database connection failed"
}
```

---

### Metrics Endpoint

Prometheus-compatible metrics.

```
GET /metrics
```

**Response (200 OK):**

```
# HELP youtube_chat_messages_total Total messages processed
# TYPE youtube_chat_messages_total counter
youtube_chat_messages_total{type="chat"} 1234
youtube_chat_messages_total{type="super_chat"} 45
youtube_chat_messages_total{type="super_sticker"} 12
youtube_chat_messages_total{type="membership"} 8

# HELP youtube_polling_errors_total Total polling errors
# TYPE youtube_polling_errors_total counter
youtube_polling_errors_total{channel_id="UCxxxxxxxxxx"} 0

# HELP youtube_active_streams Active stream count
# TYPE youtube_active_streams gauge
youtube_active_streams 1
```

---

## Status Endpoint

Get detailed module status.

```
GET /api/v1/status
```

**Response (200 OK):**

```json
{
  "status": "operational",
  "timestamp": "2026-02-24T10:35:15Z",
  "poller_running": true,
  "database_connected": true,
  "redis_connected": true,
  "registered_channels": 2,
  "active_broadcasts": 1,
  "messages_processed_today": 5892,
  "last_error": null,
  "uptime_seconds": 3600,
  "version": "1.0.0"
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2026-02-24T10:35:15Z"
}
```

### Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (if auth enabled) |
| 404 | Resource not found |
| 409 | Conflict (e.g., channel already registered) |
| 500 | Internal server error |
| 503 | Service unavailable (dependency issue) |

---

## Rate Limiting

The YouTube Data API v3 enforces quota limits:

- **Standard quota**: 10,000 units per day per API key
- **Chat polling**: ~1 unit per request
- **Channel info**: ~1 unit per request
- **Live broadcast discovery**: ~1 unit per request

Configure polling interval and results per deployment to stay within quota.

---

## Data Models

### Message Object

```json
{
  "message_id": "CjaKGDDUbYECFQGmVAodn4IFKQ",
  "timestamp": "2026-02-24T10:35:15Z",
  "channel_id": "UCxxxxxxxxxx",
  "broadcast_id": "YxxxxxxxxxB",
  "author_id": "UC-user-id-here",
  "author_name": "UserName",
  "author_avatar": "https://yt3.ggpht.com/...",
  "message_type": "chat",
  "text_content": "Great stream!",
  "super_chat_amount": null,
  "super_chat_currency": null,
  "super_sticker_url": null,
  "membership_level": null
}
```

### Stream Event Object

```json
{
  "event_id": "event-id-here",
  "timestamp": "2026-02-24T10:35:15Z",
  "channel_id": "UCxxxxxxxxxx",
  "event_type": "stream_started",
  "broadcast_id": "YxxxxxxxxxB",
  "broadcast_title": "Live Stream Title",
  "video_id": "dQw4w9WgXcQ"
}
```

---

## Request Examples

### cURL Examples

Register a channel:

```bash
curl -X POST http://localhost:8006/api/v1/channels/register \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxxxxxxx",
    "channel_name": "My Channel"
  }'
```

List channels:

```bash
curl http://localhost:8006/api/v1/channels
```

Get active broadcasts:

```bash
curl http://localhost:8006/api/v1/broadcasts/UCxxxxxxxxxx
```

Check health:

```bash
curl http://localhost:8006/health
```

### Python Examples

```python
import httpx
import asyncio

async def register_channel():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8006/api/v1/channels/register",
            json={
                "channel_id": "UCxxxxxxxxxx",
                "channel_name": "My Channel"
            }
        )
        print(response.json())

asyncio.run(register_channel())
```

---

## Response Time SLAs

- Channel registration: < 100ms
- Channel list: < 200ms (50 channels)
- Get broadcasts: < 500ms
- Webhook verification: < 100ms
- Webhook callback: < 1000ms

---

## Pagination

List endpoints support pagination via query parameters:

```
GET /api/v1/channels?limit=20&offset=40
```

Responses include pagination metadata:

```json
{
  "data": [...],
  "pagination": {
    "limit": 20,
    "offset": 40,
    "total": 127,
    "has_more": true
  }
}
```
