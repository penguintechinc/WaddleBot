# Trigger Streaming Service

Combined microservice that unifies 3 streaming platform trigger modules into a single Quart application on port 8101.

## Modules Included

1. **Twitch Module** (port 8101 → `/api/v1/twitch`, `/eventsub`)
   - IRC bot with persistent connection to monitored channels
   - EventSub webhook handler for real-time events
   - Channel manager with automatic refresh
   - Viewer tracking and metrics polling

2. **YouTube Live Module** (port 8101 → `/api/v1/youtube`, `/webhook`)
   - Chat poller for continuous monitoring of live broadcasts
   - PubSubHubbub webhook handler for push notifications
   - Live broadcast discovery and status tracking

3. **Kick Module** (port 8101 → `/api/v1/kick`, `/webhook`)
   - Webhook-only event receiver
   - Event type mapping and routing to event processor
   - HMAC-SHA256 signature verification

## Architecture

```
/app/
  app.py                        # Combined Quart entry point
  config.py                     # Unified configuration (Twitch, YouTube, Kick)
  requirements.txt              # Merged dependencies
  Dockerfile                    # Multi-stage build
  twitch_module/                # Twitch service code
    config.py
    services/
      viewer_tracker.py         # Poll and track viewer counts
      twitch_bot.py            # IRC bot connection and message handling
      channel_manager.py       # Manage bot channel subscriptions
      eventsub_handler.py      # Twitch EventSub webhook validation/processing
  youtube_live_module/          # YouTube service code
    config.py
    services/
      youtube_client.py        # API client for channel/broadcast info
      chat_poller.py           # Continuous polling of live chat
      webhook_handler.py       # PubSubHubbub subscription/callback handler
  kick_module_flask/            # Kick service code
    config.py
  libs/                         # Shared Flask/Quart utilities
```

## API Endpoints

### Health & Status
- `GET /healthz` - Liveness probe
- `GET /health` - Health with timestamp
- `GET /api/v1/status` - Unified status (all platforms)

### Twitch

#### Bot Management
- `GET /api/v1/twitch/bot/channels` - List channels bot is connected to
- `POST /api/v1/twitch/bot/send` - Send message to a channel

#### EventSub Webhooks
- `POST /eventsub/webhook` - Receive Twitch EventSub events (auto-verified)

### YouTube Live

#### Channel Management
- `POST /api/v1/youtube/channels/register` - Register channel for monitoring (starts chat polling, optionally subscribes to webhook)
- `DELETE /api/v1/youtube/channels/<channel_id>` - Unregister channel (stops polling)
- `GET /api/v1/youtube/channels` - List monitored channels

#### Broadcast Discovery
- `GET /api/v1/youtube/broadcasts/<channel_id>` - Get active live broadcasts for a channel

#### PubSubHubbub Webhooks
- `GET /webhook` - Verify PubSubHubbub subscription (hub.challenge)
- `POST /webhook` - Receive live channel notifications

### Kick

#### Webhooks
- `POST /webhook/kick` - Receive Kick events (signature verified)

## Background Tasks

The service maintains persistent connections for real-time event streaming:

### Twitch
- **IRC Bot** - Active connection to all monitored Twitch channels; maintains persistent connection with automatic reconnect, receives chat messages and channel events
- **Channel Manager** - Periodically refreshes channel list from database; adds/removes bot from channels as needed (interval: `CHANNEL_REFRESH_INTERVAL`)
- **Viewer Tracker** - Polls Twitch API for viewer counts on monitored channels (interval: `VIEWER_POLL_INTERVAL`)

### YouTube Live
- **Chat Poller** - Continuously polls live chat for monitored broadcasts; detects new streams via API and begins polling immediately
- **Webhook Handler** - Listens for PubSubHubbub notifications when channels go live or stream metadata changes

### Kick
- **Webhook Handler** - Stateless, receives HTTP POST events; validates signature and forwards to event router

## Environment Variables

### Twitch Configuration
```bash
# Required for IRC bot
TWITCH_BOT_ENABLED=true
TWITCH_BOT_TOKEN=oauth:xxxx...         # OAuth token for bot account
TWITCH_BOT_NICK=bot_username            # Bot's Twitch username
TWITCH_CLIENT_ID=your-client-id
TWITCH_CLIENT_SECRET=your-client-secret
TWITCH_ACCESS_TOKEN=xxxx...             # App access token for API calls

# Required for EventSub
EVENTSUB_ENABLED=true
EVENTSUB_SECRET=your-eventsub-secret    # Webhook signature verification
EVENTSUB_CALLBACK_URL=https://domain.com/eventsub/webhook

# Optional: Viewer tracking
VIEWER_TRACKING_ENABLED=true
VIEWER_POLL_INTERVAL=60                 # Seconds between API polls
HUB_API_URL=http://hub-api:8000         # Hub service URL
SERVICE_API_KEY=service-key-for-hub     # Auth to Hub service

# Channel refresh
CHANNEL_REFRESH_INTERVAL=300             # Seconds between DB refresh
ROUTER_API_URL=http://event-router:8000  # Event router URL
```

### YouTube Configuration
```bash
YOUTUBE_API_KEY=your-youtube-api-key
```

### Kick Configuration
```bash
KICK_WEBHOOK_SECRET=your-kick-secret     # HMAC secret for signature verification
ROUTER_API_URL=http://event-router:8000  # Event router URL
```

### Shared Configuration
```bash
# Service
MODULE_NAME=trigger-streaming
MODULE_VERSION=1.0.0
MODULE_PORT=8101
MODULE_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Logging
LOG_LEVEL=INFO
```

## Building

### Local Build
```bash
docker build -t trigger-streaming:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8101:8101 \
  -e TWITCH_BOT_TOKEN=oauth:xxxx \
  -e TWITCH_CLIENT_ID=xxxx \
  -e TWITCH_CLIENT_SECRET=xxxx \
  -e YOUTUBE_API_KEY=xxxx \
  -e KICK_WEBHOOK_SECRET=xxxx \
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot \
  trigger-streaming:latest
```

## Ports

- **8101** - HTTP REST API (all 3 modules)

## Service Key Authentication

All non-health endpoints require the `X-Service-Key` header:

```bash
curl -H "X-Service-Key: your-secret-key" http://localhost:8101/api/v1/status
```

Health endpoints are exempt:
```bash
curl http://localhost:8101/healthz
curl http://localhost:8101/health
```

## Database Schema

The service reads from the WaddleBot database:

- **Servers** - Platform-specific channel configurations (Twitch, YouTube, Kick)
- **CommunityServers** - Links servers to communities for event routing

All database access uses penguin-dal with `migrate=False` (schema via Alembic only).

## Logging

Uses `flask_core.setup_aaa_logging()` with structured JSON logging:
- Startup/shutdown events for all platform modules
- Background task status (bot connection, poller state, webhook handlers)
- Event processing and router submission
- Signature verification failures (Twitch EventSub, Kick webhooks)

## Event Routing

All three platforms forward received events to a central event router service:

```
Twitch → Event Router (via TwitchBotService, EventSubHandler)
YouTube → Event Router (via ChatPoller, WebhookHandler)
Kick → Event Router (via process_kick_event)
```

Event payload structure:
```json
{
  "platform": "twitch|youtube|kick",
  "server_id": "channel_id|broadcaster_id",
  "user_id": "user_uuid",
  "username": "username",
  "message": "message text",
  "event_type": "chat|subscription|raid|etc",
  "raw_event": {}
}
```
