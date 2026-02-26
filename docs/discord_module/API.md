# Discord Module API Documentation

## HTTP Endpoints

All endpoints are served on port 8003 (configurable via `MODULE_PORT`).

### Status Endpoint

```http
GET /api/v1/status
```

Returns the current status of the Discord bot service.

**Response:**
```json
{
  "status": "ok",
  "bot_id": "1234567890",
  "bot_name": "WaddleBot",
  "guilds_count": 45,
  "latency_ms": 125,
  "uptime_seconds": 3600,
  "version": "v0.1.0"
}
```

**Status Codes:**
- `200 OK` - Service is running normally
- `503 Service Unavailable` - Bot is not connected or experiencing issues

### Guilds Endpoint

```http
GET /api/v1/bot/guilds
```

Lists all Discord guilds (servers) the bot is currently connected to.

**Query Parameters:**
- `limit` (optional, default: 100) - Maximum number of guilds to return
- `offset` (optional, default: 0) - Pagination offset

**Response:**
```json
{
  "guilds": [
    {
      "id": "123456789",
      "name": "WaddleBot Community",
      "icon_url": "https://cdn.discordapp.com/icons/123456789/abc123.png",
      "member_count": 2540,
      "joined_at": "2026-01-15T10:30:00Z",
      "owner_id": "987654321"
    }
  ],
  "total": 45,
  "limit": 100,
  "offset": 0
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved guilds
- `503 Service Unavailable` - Bot not connected

### Health Check Endpoint

```http
GET /health
```

Simple health check for load balancers and monitoring systems.

**Response:**
```
OK
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is unhealthy

### Metrics Endpoint

```http
GET /metrics
```

Prometheus-format metrics for monitoring.

**Response (text/plain):**
```
# HELP discord_bot_events_total Total Discord events processed
# TYPE discord_bot_events_total counter
discord_bot_events_total{event_type="slash_command"} 1254
discord_bot_events_total{event_type="message"} 3421
discord_bot_events_total{event_type="interaction"} 892

# HELP discord_bot_latency_ms Discord API latency in milliseconds
# TYPE discord_bot_latency_ms gauge
discord_bot_latency_ms 125

# HELP discord_bot_guilds_total Number of connected guilds
# TYPE discord_bot_guilds_total gauge
discord_bot_guilds_total 45

# HELP process_uptime_seconds Process uptime in seconds
# TYPE process_uptime_seconds gauge
process_uptime_seconds 3600
```

**Status Codes:**
- `200 OK` - Metrics available
- `503 Service Unavailable` - Metrics unavailable

## Internal Event Format

Events forwarded to the router use the following normalized format:

```json
{
  "entity_id": "guild:channel",
  "message_type": "slashCommand",
  "platform": "discord",
  "user_id": "987654321",
  "guild_id": "123456789",
  "channel_id": "channel123",
  "message_id": "msg123",
  "content": "waddlebot help",
  "interaction_token": "interaction_token_xyz",
  "timestamp": "2026-02-24T10:15:30Z",
  "metadata": {
    "command_name": "balance",
    "command_group": "waddlebot",
    "options": {
      "user": "someuser"
    }
  }
}
```

## Event Types

### Slash Command Event

Triggered when a user uses a slash command (e.g., `/balance`).

```json
{
  "message_type": "slashCommand",
  "metadata": {
    "command_name": "balance",
    "command_group": "waddlebot",
    "options": {
      "user": "optional_username"
    }
  }
}
```

### Chat Message Event

Triggered when a user sends a regular message with a prefix (e.g., `!help`).

```json
{
  "message_type": "chatMessage",
  "content": "!help",
  "metadata": {
    "prefix": "!",
    "command": "help"
  }
}
```

### Interaction Event

Triggered when a user interacts with buttons, select menus, or modals.

```json
{
  "message_type": "interaction",
  "metadata": {
    "interaction_type": "button",
    "interaction_id": "button_accept_123",
    "interaction_values": ["option_1"]
  }
}
```

## Response Format

The router returns responses in the following format, which the Discord module renders:

```json
{
  "type": "embed",
  "content": {
    "title": "Balance",
    "description": "Your current balance is 1000 gold",
    "color": "0xFFD700",
    "fields": [
      {
        "name": "Gold",
        "value": "1000",
        "inline": true
      }
    ]
  },
  "components": [
    {
      "type": "button",
      "label": "Give",
      "custom_id": "give_100",
      "style": "primary"
    }
  ]
}
```

## Response Types

### Text Response

Simple text message.

```json
{
  "type": "text",
  "content": "Your balance is 1000 gold"
}
```

### Embed Response

Rich Discord embed with formatting, colors, and fields.

```json
{
  "type": "embed",
  "content": {
    "title": "Balance",
    "description": "User balance information",
    "color": "0xFFD700",
    "fields": [
      {
        "name": "Gold",
        "value": "1000",
        "inline": true
      }
    ]
  }
}
```

### Button Response

Embed with interactive buttons.

```json
{
  "type": "button",
  "components": [
    {
      "type": "button",
      "label": "Accept",
      "custom_id": "accept_trade_123",
      "style": "success"
    }
  ]
}
```

### Select Response

Embed with dropdown menu.

```json
{
  "type": "select",
  "components": [
    {
      "type": "select",
      "placeholder": "Choose an option",
      "options": [
        {
          "label": "Option 1",
          "value": "opt1"
        }
      ]
    }
  ]
}
```

### Modal Response

Interactive form for collecting user input.

```json
{
  "type": "modal",
  "title": "Feedback Form",
  "custom_id": "feedback_form_123",
  "fields": [
    {
      "type": "text",
      "label": "Feedback",
      "custom_id": "feedback_text",
      "required": true,
      "max_length": 1000
    }
  ]
}
```

## Error Responses

All endpoints return error responses in the following format:

```json
{
  "error": "error_code",
  "message": "Human-readable error description",
  "timestamp": "2026-02-24T10:15:30Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `bot_not_connected` | 503 | Discord bot is not connected |
| `invalid_guild_id` | 400 | Guild ID is invalid or bot not in guild |
| `rate_limited` | 429 | Discord API rate limit exceeded |
| `unauthorized` | 401 | Request lacks valid authorization |
| `internal_error` | 500 | Internal server error |

## Rate Limiting

Discord API rate limits are enforced by py-cord and the Discord service. The module automatically handles rate limiting with exponential backoff.

If a request exceeds rate limits, you'll receive:

```json
{
  "error": "rate_limited",
  "message": "Rate limit exceeded. Retry after 60 seconds",
  "retry_after": 60
}
```

## Message Splitting

Discord has a 2000-character limit per message. The Discord module automatically splits long responses across multiple messages with automatic linking.

If a response exceeds 2000 characters, it will be split into multiple embeds with sequential numbering:

```
Message 1/3:
[Embed with title "Results (1/3)"]

Message 2/3:
[Embed with title "Results (2/3)"]

Message 3/3:
[Embed with title "Results (3/3)"]
```

## Interaction Context

All interactions include context information that the router can use:

```json
{
  "interaction_token": "aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvdmVyc2lvbnM=",
  "interaction_id": "1234567890123456789",
  "user_id": "987654321",
  "guild_id": "123456789",
  "channel_id": "channel123",
  "timestamp": "2026-02-24T10:15:30Z"
}
```

This context is stored during interaction handling and allows the router to respond to interactions asynchronously.
