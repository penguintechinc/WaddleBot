# Router Module API Documentation

## Overview

The Router Module is Waddles's central command routing system, responsible for receiving events from action modules (Discord, Slack, Twitch, YouTube), routing commands to appropriate interaction modules, and managing responses.

**Base URL:** `http://router-module:8000`
**Version:** 2.0.0
**Module Type:** Core Processing Module

---

## Table of Contents

1. [Health & Status Endpoints](#health--status-endpoints)
2. [Router Endpoints](#router-endpoints)
3. [Admin Endpoints](#admin-endpoints)
4. [Request/Response Models](#requestresponse-models)
5. [Error Handling](#error-handling)
6. [Authentication](#authentication)

---

## Health & Status Endpoints

### GET /health

Basic health check endpoint for Docker/Kubernetes liveness probes.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "module": "router_module",
    "version": "2.0.0",
    "timestamp": "2025-12-16T00:00:00Z"
  }
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### GET /healthz

Kubernetes-compatible health probe with detailed component checks.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "checks": {
      "database": "ok",
      "redis": "ok",
      "grpc": "ok"
    }
  }
}
```

**Response (503 Service Unavailable):**
```json
{
  "success": false,
  "data": {
    "status": "degraded",
    "checks": {
      "database": "ok",
      "redis": "failed",
      "grpc": "ok"
    }
  }
}
```

---

### GET /metrics

Prometheus-compatible metrics endpoint.

**Response (200 OK):**
```text
# HELP router_requests_total Total number of requests processed
# TYPE router_requests_total counter
router_requests_total 12345

# HELP router_request_duration_seconds Request duration in seconds
# TYPE router_request_duration_seconds histogram
router_request_duration_seconds_bucket{le="0.1"} 9500
router_request_duration_seconds_bucket{le="0.5"} 12000
...
```

---

## Router Endpoints

### POST /api/v1/router/events

Process a single event (message, command, interaction, etc.).

**Request Body:**
```json
{
  "platform": "twitch",
  "channel_id": "12345",
  "user_id": "67890",
  "username": "penguin_user",
  "message": "!help",
  "command": "!help",
  "metadata": {
    "display_name": "Penguin User",
    "badges": ["subscriber"]
  }
}
```

**Validation Rules:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `platform` | string | Yes | Must be one of: `twitch`, `discord`, `slack`, `kick` |
| `channel_id` | string | Yes | 1-255 characters, non-empty |
| `user_id` | string | Yes | 1-255 characters, non-empty |
| `username` | string | Yes | 1-255 characters, non-empty |
| `message` | string | Yes | 1-5000 characters, non-empty |
| `command` | string | No | Max 255 characters |
| `metadata` | object | No | Additional event metadata |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_abc123...",
    "command": "!help",
    "module": "core_commands",
    "processed": true,
    "response": {
      "content": "Available commands: !help, !stats, !balance...",
      "type": "message"
    }
  }
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Validation error",
  "details": {
    "field": "platform",
    "message": "Must be one of: twitch, discord, slack, kick"
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/router/events \
  -H "Content-Type: application/json" \
  -H "X-Service-Key: your-api-key" \
  -d '{
    "platform": "twitch",
    "channel_id": "12345",
    "user_id": "67890",
    "username": "penguin_user",
    "message": "!help"
  }'
```

---

### POST /api/v1/router/events/batch

Process multiple events concurrently (up to 100 events).

**Request Body:**
```json
{
  "events": [
    {
      "platform": "twitch",
      "channel_id": "12345",
      "user_id": "67890",
      "username": "user1",
      "message": "!help"
    },
    {
      "platform": "discord",
      "channel_id": "98765",
      "user_id": "43210",
      "username": "user2",
      "message": "!stats"
    }
  ]
}
```

**Validation Rules:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `events` | array | Yes | 1-100 items, each must be valid RouterEventRequest |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "success": true,
        "session_id": "sess_abc123...",
        "command": "!help",
        "processed": true
      },
      {
        "success": true,
        "session_id": "sess_def456...",
        "command": "!stats",
        "processed": true
      }
    ],
    "count": 2
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/router/events/batch \
  -H "Content-Type: application/json" \
  -H "X-Service-Key: your-api-key" \
  -d '{
    "events": [
      {"platform": "twitch", "channel_id": "12345", "user_id": "67890", "username": "user1", "message": "!help"},
      {"platform": "discord", "channel_id": "98765", "user_id": "43210", "username": "user2", "message": "!stats"}
    ]
  }'
```

---

### GET /api/v1/router/commands

List available commands for a community.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | integer | No | Filter by community ID |
| `category` | string | No | Filter by category (e.g., "fun", "moderation") |
| `enabled_only` | boolean | No | Show only enabled commands (default: true) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "command": "!help",
      "module_name": "core_commands",
      "module_url": "http://core-commands:8000",
      "description": "Show available commands",
      "usage": "!help [command]",
      "category": "general",
      "permission_level": "everyone",
      "is_enabled": true,
      "cooldown_seconds": 5,
      "community_id": null
    },
    {
      "command": "!stats",
      "module_name": "stats_module",
      "module_url": "http://stats-module:8000",
      "description": "Show user statistics",
      "usage": "!stats [@user]",
      "category": "fun",
      "permission_level": "everyone",
      "is_enabled": true,
      "cooldown_seconds": 10,
      "community_id": 123
    }
  ]
}
```

**Example:**
```bash
# List all commands
curl http://localhost:8000/api/v1/router/commands

# Filter by community
curl "http://localhost:8000/api/v1/router/commands?community_id=123"

# Filter by category
curl "http://localhost:8000/api/v1/router/commands?category=fun"
```

---

### POST /api/v1/router/responses

Receive response from an interaction module after command execution.

**Request Body:**
```json
{
  "event_id": "evt_abc123...",
  "response": "Command executed successfully!",
  "platform": "twitch",
  "channel_id": "12345"
}
```

**Validation Rules:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `event_id` | string | Yes | 1-255 characters, non-empty |
| `response` | string | Yes | 1-5000 characters, non-empty |
| `platform` | string | Yes | Must be one of: `twitch`, `discord`, `slack`, `kick` |
| `channel_id` | string | Yes | 1-255 characters, non-empty |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Response received"
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/router/responses \
  -H "Content-Type: application/json" \
  -H "X-Service-Key: your-api-key" \
  -d '{
    "event_id": "evt_abc123",
    "response": "Command executed!",
    "platform": "twitch",
    "channel_id": "12345"
  }'
```

---

### GET /api/v1/router/metrics

Get router performance metrics.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "requests_processed": 12345,
    "avg_response_time_ms": 45.2,
    "cache_hit_rate": 0.85
  }
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/router/metrics
```

---

## Admin Endpoints

### GET /api/v1/admin/status

Get administrative status information.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "operational"
  }
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/admin/status
```

---

## Request/Response Models

### RouterEventRequest

Used by `POST /api/v1/router/events`

```python
{
  "platform": str,           # Required: twitch, discord, slack, kick
  "channel_id": str,         # Required: 1-255 chars
  "user_id": str,           # Required: 1-255 chars
  "username": str,          # Required: 1-255 chars
  "message": str,           # Required: 1-5000 chars
  "command": str,           # Optional: max 255 chars
  "metadata": dict          # Optional: additional data
}
```

### RouterBatchRequest

Used by `POST /api/v1/router/events/batch`

```python
{
  "events": [               # Required: 1-100 RouterEventRequest items
    RouterEventRequest,
    ...
  ]
}
```

### RouterResponseRequest

Used by `POST /api/v1/router/responses`

```python
{
  "event_id": str,          # Required: 1-255 chars
  "response": str,          # Required: 1-5000 chars
  "platform": str,          # Required: twitch, discord, slack, kick
  "channel_id": str         # Required: 1-255 chars
}
```

---

## Error Handling

### Error Response Format

All errors follow the standard Waddles error format:

```json
{
  "success": false,
  "error": "Error message",
  "details": {
    "field": "fieldName",
    "constraint": "validation rule"
  },
  "timestamp": "2025-12-16T00:00:00Z"
}
```

### HTTP Status Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Validation error or malformed request |
| 404 | Not Found | Endpoint or resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service degraded or unavailable |

### Common Error Scenarios

#### Rate Limit Exceeded
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

#### Validation Error
```json
{
  "success": false,
  "error": "Validation error",
  "details": {
    "field": "platform",
    "message": "Must be one of: twitch, discord, slack, kick"
  }
}
```

#### Command Not Found
```json
{
  "success": false,
  "error": "Unknown command: !invalid",
  "help_url": "/commands"
}
```

#### Module Disabled
```json
{
  "success": false,
  "error": "The 'inventory_module' module is disabled for this community"
}
```

---

## Authentication

### Service API Key

All internal service-to-service requests require the `X-Service-Key` header:

```bash
curl -H "X-Service-Key: your-service-key" \
  http://localhost:8000/api/v1/router/events
```

### JWT Token (gRPC)

For gRPC requests, JWT tokens are automatically generated with:
- Service name: `router_module`
- Expiry: 1 hour
- Signature: HS256 with `SECRET_KEY`

---

## Rate Limiting

### Default Limits

- **Command Execution:** 60 requests per 60 seconds per user+command
- **Batch Processing:** 100 events maximum per request
- **API Endpoints:** 1000 requests per minute per IP (configurable)

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1702684800
```

---

## Event Types

The router handles various event types:

| Event Type | Description | Example Message |
|------------|-------------|-----------------|
| `chatMessage` | Regular chat message | "Hello world!" |
| `slashCommand` | Discord/Slack slash command | `/help` |
| `interaction` | Button click, modal submit | N/A |
| `stream_online` | Stream started | N/A |
| `stream_offline` | Stream ended | N/A |
| `subscription` | New subscriber | N/A |
| `gift_subscription` | Gifted subscription | N/A |
| `follow` | New follower | N/A |
| `raid` | Channel raid | N/A |
| `cheer` | Bits/cheer | N/A |

---

## Command Processing Flow

```
1. Event received via POST /api/v1/router/events
2. Generate session ID
3. Check rate limits (60/60s per user+command)
4. Parse command (!help, #stats, etc.)
5. Look up command in registry
6. Check if module is enabled for community
7. Check command cooldown
8. Execute command via HTTP or gRPC
9. Store response in cache
10. Track activity in hub module
11. Track reputation in reputation module
12. Check for workflow triggers
13. Return response to caller
```

---

## Redis Streams Integration

When `STREAM_PIPELINE_ENABLED=true`, the router can publish/consume events from Redis Streams:

### Stream Names

| Stream | Purpose |
|--------|---------|
| `waddlebot:stream:events:inbound` | Incoming events from action modules |
| `waddlebot:stream:events:commands` | Parsed commands |
| `waddlebot:stream:events:actions` | Actions to be executed |
| `waddlebot:stream:events:responses` | Module responses |

### Consumer Groups

- **Group:** `waddlebot-router`
- **Consumers:** `router-{pid}-{index}` (4 consumers by default)
- **Batch Size:** 10 events per read
- **Block Time:** 1000ms

---

## Translation Support

The router includes automatic message translation:

1. **Detection:** Detect source language with confidence score
2. **Skip Conditions:** Message too short, already in target language, low confidence
3. **Token Preservation:** Preserve @mentions, !commands, emotes, URLs during translation
4. **Caption Overlay:** Send translated captions to browser source module
5. **Caching:** 3-tier caching (memory, Redis, database)

**Configuration (per community):**
```json
{
  "translation": {
    "enabled": true,
    "default_language": "en",
    "min_words": 5,
    "confidence_threshold": 0.7,
    "preprocessing": {
      "preserve_mentions": true,
      "preserve_commands": true,
      "preserve_emotes": true,
      "preserve_urls": true
    }
  }
}
```

---

## Workflow Integration

The router automatically triggers workflows based on commands and events:

1. Query `workflows` table for matching triggers
2. Check trigger type: `command` or `event`
3. Execute workflow via gRPC or REST
4. Pass event data as trigger context

**Example Workflow Trigger:**
```sql
SELECT workflow_id FROM workflows
WHERE entity_id = '12345'
  AND is_active = true
  AND status = 'published'
  AND trigger_type = 'command'
  AND trigger_config->>'command' = '!giveaway'
```

---

## gRPC Integration

The router uses gRPC for efficient communication with core modules:

### Supported Modules

- **Hub Internal:** Activity tracking, message recording
- **Reputation:** Event recording for score adjustments
- **Workflow:** Workflow execution
- **Browser Source:** Caption display

### Connection Options

```python
options = [
    ('grpc.keepalive_time_ms', 30000),
    ('grpc.keepalive_timeout_ms', 10000),
    ('grpc.keepalive_permit_without_calls', True),
    ('grpc.http2.max_pings_without_data', 0),
]
```

### Retry Logic

- **Max Retries:** 3 (configurable)
- **Backoff:** Exponential (0.5s, 1s, 2s)
- **Timeout:** 30 seconds (configurable per call)
- **Fallback:** Automatic REST fallback on gRPC failure

---

## Performance Considerations

### Caching Strategy

| Cache Type | TTL | Size | Purpose |
|------------|-----|------|---------|
| Redis Command Cache | 300s | Unlimited | Command definitions |
| Redis Entity Cache | 600s | Unlimited | Entity → Community mapping |
| Redis Module Status | 300s | Unlimited | Module enabled/disabled state |
| Memory Response Cache | 3600s | In-memory dict | Recent module responses |

### Concurrent Processing

- **Max Workers:** 20 (configurable via `ROUTER_MAX_WORKERS`)
- **Max Concurrent:** 100 (configurable via `ROUTER_MAX_CONCURRENT`)
- **Request Timeout:** 30 seconds (configurable via `ROUTER_REQUEST_TIMEOUT`)

---

## Examples

### Complete Event Processing Example

```python
import aiohttp

async def process_chat_command():
    async with aiohttp.ClientSession() as session:
        event = {
            "platform": "twitch",
            "channel_id": "12345",
            "user_id": "67890",
            "username": "penguin_user",
            "message": "!balance",
            "metadata": {
                "display_name": "Penguin User",
                "badges": ["subscriber", "moderator"]
            }
        }

        async with session.post(
            "http://router-module:8000/api/v1/router/events",
            json=event,
            headers={"X-Service-Key": "your-api-key"}
        ) as resp:
            result = await resp.json()
            print(result)
            # {
            #   "success": true,
            #   "data": {
            #     "session_id": "sess_abc123...",
            #     "command": "!balance",
            #     "module": "economy_module",
            #     "response": {
            #       "content": "Your balance: 1,234 coins"
            #     }
            #   }
            # }
```

---

## See Also

- [CONFIGURATION.md](./CONFIGURATION.md) - Environment variables and configuration
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture and design
- [USAGE.md](./USAGE.md) - Usage examples and workflows
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues and solutions
