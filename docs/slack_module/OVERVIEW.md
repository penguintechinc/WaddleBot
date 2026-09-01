# Slack Module Overview

The Slack Module is a Python-based receiver service that bridges Slack workspaces to WaddleBot's central router, enabling community management features, moderation, reputation systems, and interactive workflows directly within Slack.

## Module Purpose

The Slack Module provides real-time bidirectional communication with Slack workspaces:
- **Inbound**: Receives messages, slash commands, interactions (buttons, select menus), modal submissions, and shortcuts
- **Outbound**: Executes responses including message posting, modal displays, ephemeral notifications, and cross-workspace command routing
- **Normalization**: Converts Slack events to platform-agnostic WaddleBot format for router processing

## Core Capabilities

### Event Reception
- **Slash Commands** (24 total): `/waddlebot`, `/form`, `/poll`, `/ticket`, `/balance`, `/give`, `/slots`, `/duel`, `/giveaway`, `/quote`, `/bookmark`, `/remind`, `/lfg`, `/event`, `/rsvp`, `/so`, `/translate`, `/status`, `/clip`, `/alias`, `/ask`, `/rep`, `/label`, `/top`, `/context`, `/join`, `/approve`, `/leave`, `/linked`, `/link`
- **Chat Messages**: Direct messages, channel messages, mention detection
- **Interactions**: Button clicks, dropdown selections (both block actions and view submissions)
- **Shortcuts**: Both global and message-level shortcuts
- **Modal Events**: Submission, closure, value changes

### Response Execution
- **Direct Messages**: Ephemeral (private) or in-channel responses
- **Modal Displays**: Dynamic form submission, validation feedback
- **Message Updates**: Editing existing message blocks
- **Rich Formatting**: Full Block Kit support for buttons, selects, rich text, dividers, sections

### Authentication & Authorization
- **Credential Management**: Per-workspace Slack bot token and signing secret storage in database
- **Admin Validation**: Privileged command access control via stored user roles
- **Token Refresh**: Redis-backed credential caching with automatic refresh

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Slack Workspace(s)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴──────────────┐
        │                           │
    HTTP Mode              Socket Mode (Dev)
  (Production)             (Local Development)
        │                           │
        ▼                           ▼
┌──────────────────────────────────────────────────┐
│   Slack Module (Python 3.12, Quart + Hypercorn)  │
│                  Port 8004                       │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │        SlackBoltService                    │ │
│  │  - Event routing & handling                │ │
│  │  - Command/interaction execution           │ │
│  │  - Response formatting & posting           │ │
│  └────────────────────────────────────────────┘ │
│                     │                           │
│  ┌────────────────────────────────────────────┐ │
│  │       BlockKitBuilder                      │ │
│  │  - Modal composition                       │ │
│  │  - Button/select generation                │ │
│  │  - Rich text formatting                    │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
┌──────────────────────────────────────────────────┐
│  Event Normalization & Router Interface         │
│  - entity_id: team_id:channel_id                │
│  - message_type: slashCommand|chatMessage|...   │
│  - platform: "slack"                            │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│    WaddleBot Router (Central Processing)         │
│  - Command execution                            │
│  - Business logic                               │
│  - Response routing back to Slack               │
└──────────────────────────────────────────────────┘
```

## Operational Modes

### HTTP Mode (Production)
- Slack sends events via webhooks to `POST /slack/events`
- Module validates request signatures using `SLACK_SIGNING_SECRET`
- Slash commands routed to `POST /slack/commands`
- Interactive actions routed to `POST /slack/actions`
- Shortcuts routed to `POST /slack/shortcuts`
- **Best for**: Cloud deployments, multiple workspaces, high throughput

### Socket Mode (Development)
- Module connects to Slack via WebSocket using `SLACK_APP_TOKEN`
- Bi-directional real-time communication
- No webhook URL exposure required
- **Best for**: Local development, testing, debugging without tunneling

## Technology Stack

| Component | Details |
|-----------|---------|
| Language | Python 3.12 |
| Web Framework | Quart (async ASGI) with Hypercorn server |
| Slack Integration | slack-bolt 1.18.0+, slack-sdk 3.21.0+ |
| HTTP Client | aiohttp, httpx |
| Database | PyDAL (multi-database support) |
| Cache | Redis (credential/token refresh) |
| Environment | python-dotenv, 12-factor app compliance |

## Event Normalization

All Slack events are normalized to platform-agnostic format:

```python
{
    "platform": "slack",
    "entity_id": "{team_id}:{channel_id}",
    "message_type": "slashCommand|chatMessage|mention|interaction|shortcut",
    "user_id": "U...",
    "timestamp": "1234567890.000000",
    "content": "command text or message",
    "metadata": {
        # Command-specific metadata
        "command": "/waddlebot",
        "channel_name": "general",
        "is_ephemeral": true,
        # Or interaction-specific
        "action_id": "button_approve",
        "value": "user_123"
    }
}
```

## Environment Configuration

Essential environment variables:

```bash
MODULE_PORT=8004                    # HTTP server port
DATABASE_URL=postgresql://...       # PyDAL database connection
CORE_API_URL=http://...             # Core API service
ROUTER_API_URL=http://...           # Router API service
LOG_LEVEL=INFO                      # Logging verbosity
SECRET_KEY=...                      # CSRF/security tokens
SLACK_BOT_TOKEN=xoxb-...            # Slack app token
SLACK_SIGNING_SECRET=...            # Webhook signature validation
SLACK_APP_TOKEN=xapp-...            # Socket Mode token (if using)
USE_SOCKET_MODE=false               # Enable Socket Mode
REDIS_URL=redis://...               # Token cache (optional)
```

## Security Considerations

- **Request Validation**: All webhook signatures verified against `SLACK_SIGNING_SECRET`
- **Token Management**: Bot tokens stored in encrypted database columns, cached in Redis with TTL
- **Admin Commands**: Privileged commands validated against user roles in database
- **Ephemeral Responses**: Sensitive information returned as ephemeral (private) messages
- **Input Sanitization**: All user inputs validated before router forwarding

## Performance Characteristics

- **Concurrency**: Async/await pattern supports hundreds of concurrent connections
- **Latency**: Sub-100ms event processing for simple commands (p99)
- **Throughput**: 1000+ events/sec capability in production
- **Socket Mode**: Best effort delivery, reconnection handling automatic
- **HTTP Mode**: 3-second response deadline per Slack specification

## Integration Points

- **WaddleBot Router**: RESTful API for command execution, response retrieval
- **Core API**: User/role lookups, admin validation
- **Database**: Workspace credentials, user role mappings, command metadata
- **Redis**: Credential caching, rate limiting (future)

## Failure Handling

| Scenario | Behavior |
|----------|----------|
| Router unavailable | 503 response, auto-retry with exponential backoff |
| Invalid token | Credential refresh from database, retry once |
| Command timeout (>3s) | Delayed response via response URL or modal follow-up |
| Modal validation failure | Error message in validation response, user re-prompted |
| Slack API rate limit | Queued retries with exponential backoff |

## Next Steps

- **[CONFIGURATION.md](CONFIGURATION.md)**: Detailed setup and environment variables
- **[USAGE.md](USAGE.md)**: Running the module and operational procedures
- **[API.md](API.md)**: HTTP endpoints and request/response formats
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Service design, slash commands, interactions
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**: Debugging and common issues
- **[TESTING.md](TESTING.md)**: Testing procedures and mock data
- **[RELEASE_NOTES.md](RELEASE_NOTES.md)**: Version history and breaking changes
