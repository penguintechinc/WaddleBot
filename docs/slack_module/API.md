# Slack Module API Reference

## HTTP Endpoints

All endpoints are exposed at `http://localhost:8004` in development and on `MODULE_PORT` in production.

### Event Reception Endpoints

#### POST /slack/events
Receives Slack event callbacks including messages, mentions, app_mention, and other events.

**Headers:**
```
X-Slack-Request-Timestamp: {unix_timestamp}
X-Slack-Signature: v0={hmac_sha256_hash}
Content-Type: application/json
```

**Request Body (URL Verification):**
```json
{
  "type": "url_verification",
  "challenge": "3eZbrw1aBZzOo6hc0FzqU8iKAJ6Tm4IvfN0kQhsLJLw"
}
```

**Response:**
```json
{
  "challenge": "3eZbrw1aBZzOo6hc0FzqU8iKAJ6Tm4IvfN0kQhsLJLw"
}
```

**Request Body (Event Callback):**
```json
{
  "type": "event_callback",
  "event_id": "Ev0123456",
  "event_ts": "1609459200.000000",
  "event": {
    "type": "message",
    "channel": "C123456",
    "user": "U123456",
    "text": "hello",
    "ts": "1609459200.000000",
    "thread_ts": "1609459100.000000"
  }
}
```

**Status Codes:**
- `200 OK`: Event processed successfully
- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Invalid signature
- `500 Internal Server Error`: Processing failure

---

#### POST /slack/commands
Receives slash command invocations.

**Request Form Data:**
```
token=gIkuvaNzQIHg97ATvDxqgjtO
team_id=T0001
team_domain=example
channel_id=C2147483705
channel_name=test
user_id=U2147483697
user_name=Steve
command=/waddlebot
text=check balance
response_url=https://hooks.slack.com/commands/1234/5678
trigger_id=13345224609.738474920.8085319811
```

**Response (Immediate):**
```json
{
  "response_type": "in_channel",
  "text": "Command received, processing..."
}
```

**Async Response (via response_url):**
```json
{
  "response_type": "in_channel",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Your balance is **500 WaddleBucks**"
      }
    }
  ]
}
```

**Supported Commands:**
- `/waddlebot` - Main bot command
- `/form` - Submit/view forms
- `/poll` - Create polls
- `/ticket` - Create support tickets
- `/balance` - Check reputation balance
- `/give` - Award reputation
- `/slots` - Slot machine game
- `/duel` - Challenge another user
- `/giveaway` - Create giveaways
- `/quote` - Quote random message
- `/bookmark` - Save important messages
- `/remind` - Set reminders
- `/lfg` - Looking for group
- `/event` - Create/view events
- `/rsvp` - Respond to event invitations
- `/so` - Stack Overflow search
- `/translate` - Translate text
- `/status` - Bot/service status
- `/clip` - Create clips/highlights
- `/alias` - Create command aliases
- `/ask` - Ask AI question
- `/rep` - Manage reputation
- `/label` - Apply labels
- `/top` - Top user/content stats
- `/context` - Thread context info
- `/join` - Join server/group
- `/approve` - Approve pending items
- `/leave` - Leave server/group
- `/linked` - Show linked accounts
- `/link` - Link external accounts

---

#### POST /slack/actions
Receives interactive component actions (button clicks, select menu changes, dialog submissions).

**Request Body (Block Action):**
```json
{
  "type": "block_actions",
  "user": {
    "id": "U123456",
    "name": "alice"
  },
  "api_app_id": "A123456",
  "token": "verification_token",
  "container": {
    "type": "message",
    "message_ts": "1609459200.000000",
    "channel_id": "C123456"
  },
  "trigger_id": "123456.123456.abcdef",
  "team": {
    "id": "T123456",
    "domain": "example"
  },
  "enterprise": null,
  "channel": {
    "id": "C123456",
    "name": "general"
  },
  "message": {
    "type": "message",
    "user": "U654321",
    "ts": "1609459200.000000",
    "text": "Action message"
  },
  "view": null,
  "actions": [
    {
      "type": "button",
      "action_id": "approve_button",
      "block_id": "action_block_1",
      "text": {
        "type": "plain_text",
        "text": "Approve",
        "emoji": true
      },
      "value": "user_id_123",
      "action_ts": "1609459200.123456"
    }
  ]
}
```

**Response (Immediate):**
```json
{
  "response_type": "in_channel",
  "text": "Processing action..."
}
```

**Request Body (View Submission):**
```json
{
  "type": "view_submission",
  "team": {
    "id": "T123456",
    "domain": "example"
  },
  "user": {
    "id": "U123456",
    "name": "alice"
  },
  "api_app_id": "A123456",
  "token": "verification_token",
  "container": {
    "type": "view",
    "view_id": "V123456"
  },
  "trigger_id": "123456.123456.abcdef",
  "view": {
    "id": "V123456",
    "team_id": "T123456",
    "type": "modal",
    "blocks": [...],
    "private_metadata": "",
    "callback_id": "form_submit",
    "state": {
      "values": {
        "block_1": {
          "action_1": {
            "type": "plain_text_input",
            "value": "user input"
          }
        }
      }
    }
  }
}
```

**Response (Success):**
```json
{}
```

**Response (Validation Errors):**
```json
{
  "response_action": "errors",
  "errors": {
    "block_1": "This field is required"
  }
}
```

**Status Codes:**
- `200 OK`: Action processed successfully
- `400 Bad Request`: Invalid action format
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Processing failure

---

#### POST /slack/shortcuts
Receives global and message shortcuts.

**Request Body (Global Shortcut):**
```json
{
  "type": "shortcut",
  "callback_id": "create_incident",
  "trigger_id": "123456.123456.abcdef",
  "user": {
    "id": "U123456",
    "name": "alice"
  },
  "team": {
    "id": "T123456",
    "domain": "example"
  },
  "enterprise": null,
  "api_app_id": "A123456",
  "token": "verification_token"
}
```

**Request Body (Message Shortcut):**
```json
{
  "type": "shortcut",
  "callback_id": "bookmark_message",
  "trigger_id": "123456.123456.abcdef",
  "user": {
    "id": "U123456",
    "name": "alice"
  },
  "team": {
    "id": "T123456",
    "domain": "example"
  },
  "channel": {
    "id": "C123456",
    "name": "general"
  },
  "message_ts": "1609459200.000000",
  "api_app_id": "A123456",
  "token": "verification_token"
}
```

**Response:**
```json
{}
```

**Status Codes:**
- `200 OK`: Shortcut processed successfully
- `400 Bad Request`: Invalid request format
- `500 Internal Server Error`: Processing failure

---

### Health & Status Endpoints

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "v1.0.0",
  "uptime_seconds": 3600,
  "database": "connected",
  "redis": "connected"
}
```

**Status Codes:**
- `200 OK`: Service healthy
- `503 Service Unavailable`: Service unhealthy

---

#### GET /metrics
Prometheus metrics endpoint (if metrics enabled).

**Response (Prometheus format):**
```
# HELP slack_events_total Total slack events processed
# TYPE slack_events_total counter
slack_events_total{type="message"} 1234
slack_events_total{type="slash_command"} 567

# HELP slack_event_processing_seconds Event processing duration
# TYPE slack_event_processing_seconds histogram
slack_event_processing_seconds_bucket{le=0.1} 1234
```

**Status Codes:**
- `200 OK`: Metrics retrieved successfully
- `404 Not Found`: Metrics endpoint not enabled

---

## Request/Response Normalization

### Normalized Event Format (Router Input)

All events from `/slack/events`, `/slack/commands`, `/slack/actions`, `/slack/shortcuts` are normalized to this format before sending to the router:

```python
{
    "platform": "slack",
    "entity_id": "{team_id}:{channel_id}",
    "message_type": "slashCommand|chatMessage|mention|interaction|shortcut",
    "user_id": "U...",
    "timestamp": "1609459200.000000",
    "content": "command text or message content",
    "user_name": "alice",
    "channel_name": "general",
    "is_bot": False,
    "thread_ts": "1609459100.000000",  # if in thread
    "metadata": {
        # Type-specific metadata
        "command": "/waddlebot",
        "action_id": "approve_button",
        "trigger_id": "123.456.abc",
        "response_url": "https://hooks.slack.com/...",
        "is_ephemeral": False
    }
}
```

### Response Format (Router Output)

Router responses are formatted for Slack posting:

```json
{
    "response_type": "in_channel|ephemeral",
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Response text"
            }
        }
    ],
    "thread_ts": "1609459100.000000",  # if replying in thread
    "replace_original": false,
    "delete_original": false
}
```

---

## Error Responses

### Standard Error Format

```json
{
    "error": "error_code",
    "message": "Human-readable error message",
    "details": {
        "field": "specific error details"
    }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_signature` | 401 | Slack signature validation failed |
| `invalid_token` | 401 | Bot token invalid or expired |
| `invalid_request` | 400 | Malformed request |
| `command_not_found` | 404 | Unknown slash command |
| `validation_error` | 422 | Input validation failed |
| `router_error` | 502 | Router service unavailable |
| `database_error` | 500 | Database connection error |
| `internal_error` | 500 | Unexpected server error |

---

## Rate Limiting

Slack enforces the following rate limits:

| Endpoint | Limit | Window |
|----------|-------|--------|
| /slack/commands | 300 | 60 seconds per team |
| /slack/events | 300 | 60 seconds per team |
| /slack/actions | 300 | 60 seconds per team |
| Response URL posts | 30 | 60 seconds per endpoint |

Module implements exponential backoff with jitter for rate limit handling.

---

## Async Response Handling

For commands with long processing times, use the `response_url` callback:

```python
import aiohttp

async def send_async_response(response_url: str, blocks: list):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            response_url,
            json={"blocks": blocks}
        ) as resp:
            return await resp.json()
```

**Constraints:**
- Response must be sent within 5 minutes of command invocation
- Only 3 async responses per command
- URL is single-use for most webhooks (token lifetime ~60 minutes)

---

## Socket Mode (WebSocket)

When `USE_SOCKET_MODE=true`, no HTTP endpoints are exposed for event reception. Instead, the module connects to Slack's WebSocket:

**Connection:**
```
wss://wss-primary.slack.com/...
```

**Frame Types:**
- `hello` - Initial connection handshake
- `events-api` - Event callback wrapper
- `interactive` - User interaction wrapper
- `shortcuts` - Shortcut invocation
- `slash_commands` - Slash command invocation
- `disconnect` - Graceful disconnect
- `ack` - Acknowledgment required

**Response Flow:**
1. Receive frame with envelope_id
2. Process event
3. Send `{"envelope_id": "...", "payload": {...}}` acknowledgment
4. Send `{"envelope_id": "...", "payload": {...}}` for async response (if needed)

Module handles reconnection, heartbeat, and frame ordering automatically.
