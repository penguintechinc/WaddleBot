# YouTube Live Module Overview

The YouTube Live module is a Python-based message receiver that captures real-time engagement from YouTube Live streams. It polls the YouTube Data API v3 for live chat messages and receives webhook notifications for stream events via PubSubHubbub.

## Purpose

This module enables WaddleBot to:
- Monitor YouTube Live streams for real-time chat messages
- Capture Super Chats and Super Stickers (monetary donations with messages)
- Track channel membership events
- Detect stream start and end events
- Route all captured events to the core router for processing

## Key Capabilities

### Message Types Captured

1. **Chat Messages**: Standard user messages in live chat
2. **Super Chats**: Monetary donations with highlighted messages (prices vary)
3. **Super Stickers**: Animated sticker donations
4. **Membership Events**: New or renewal memberships
5. **Stream Events**: Stream started, stream ended (via webhooks)

### Architecture

The module uses a hybrid approach:

- **Polling Service**: Continuously polls YouTube Data API for live chat messages at configurable intervals
- **Webhook Handler**: Receives PubSubHubbub notifications for stream lifecycle events
- **Credential Manager**: Stores and refreshes OAuth credentials in database with Redis caching
- **Error Resilience**: Automatically removes channels after encountering 10+ consecutive errors

## Technology Stack

- **Language**: Python 3.12
- **Framework**: Quart (async ASGI web framework)
- **HTTP Client**: httpx (async HTTP library)
- **API Version**: YouTube Data API v3
- **Port**: 8006
- **Dependencies**: pydal, python-dotenv, flask_core, platform_receiver

## Integration Points

### Inbound

- YouTube Data API v3 (chat polling)
- YouTube PubSubHubbub service (stream events)

### Outbound

- Router API: Sends captured messages and events via `ROUTER_API_URL`
- Database: Stores channel registrations and OAuth credentials
- Redis: Caches credential refresh tokens

## Workflow

### Message Capture Flow

1. User registers a YouTube channel via `/api/v1/channels/register`
2. ChatPoller discovers active broadcasts for registered channels
3. ChatPoller polls live chat at configured intervals (default 5 seconds)
4. Messages are parsed and categorized (chat, Super Chat, Super Sticker, membership)
5. Messages are routed to core router for processing

### Webhook Flow

1. Module subscribes to channel via `POST /api/v1/webhook/subscribe`
2. YouTube sends verification challenge to `/api/v1/webhook`
3. Module responds with challenge token
4. YouTube sends Atom XML notifications on stream events
5. Module parses XML and forwards events to router

## File Structure

```
trigger/receiver/youtube_live_module/
├── Dockerfile              # Container configuration
├── requirements.txt        # Python dependencies
├── services/
│   ├── youtube_client.py   # YouTube API client
│   ├── chat_poller.py      # Background polling service
│   └── webhook_handler.py  # PubSubHubbub handler
├── routes/
│   ├── channels.py         # Channel management endpoints
│   ├── broadcasts.py       # Broadcast endpoints
│   └── webhooks.py         # Webhook endpoints
├── models/
│   └── schemas.py          # Request/response schemas
├── config.py               # Configuration management
├── app.py                  # Quart application entry point
└── main.py                 # Server startup
```

## Quick Start

See [USAGE.md](USAGE.md) for detailed setup instructions.

```bash
# Start module
export YOUTUBE_API_KEY="your_api_key"
export DATABASE_URL="postgresql://..."
export ROUTER_API_URL="http://router:8000"
python main.py

# Register a channel
curl -X POST http://localhost:8006/api/v1/channels/register \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "UCxxxxxxxxxx", "channel_name": "My Channel"}'

# Start monitoring
# ChatPoller automatically begins polling for active broadcasts
```

## Key Features

- **Multi-platform Event Support**: Captures all types of YouTube Live engagement
- **Automatic Stream Detection**: Discovers and monitors active broadcasts
- **Credential Management**: Secure OAuth token storage and refresh
- **Error Resilience**: Removes problematic channels automatically
- **Configurable Polling**: Adjust polling interval and result limits per deployment
- **Webhook Integration**: Real-time stream event notifications
- **Health Checks**: Built-in `/health` and `/metrics` endpoints
- **Structured Logging**: DEBUG/INFO/WARNING/ERROR output with JSON formatting option

## Next Steps

1. **Setup**: Follow [USAGE.md](USAGE.md) for local development
2. **API Reference**: See [API.md](API.md) for endpoint documentation
3. **Configuration**: Review [CONFIGURATION.md](CONFIGURATION.md) for all environment variables
4. **Architecture**: Understand [ARCHITECTURE.md](ARCHITECTURE.md) for design details
5. **Troubleshooting**: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
6. **Testing**: See [TESTING.md](TESTING.md) for test procedures

## Support & Contributions

For issues, questions, or contributions, refer to the main WaddleBot repository documentation and contribution guidelines.
