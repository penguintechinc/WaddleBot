# Kick Module Overview

## Purpose

The Kick Module is a real-time event receiver and chat integration service for the Kick streaming platform. It operates in dual mode as both a webhook receiver (HTTP) and a Pusher-based WebSocket client, enabling seamless integration of Kick platform events into the WaddleBot ecosystem.

## Key Capabilities

- **Webhook Event Reception**: Receives and validates HMAC-SHA256 signed events from Kick platform
- **Real-Time Chat Integration**: Connects to live chatrooms via Pusher WebSocket for instant message handling
- **Event Normalization**: Translates Kick platform events into standardized WaddleBot event format
- **Chat Message Processing**: Handles text messages, subscriptions, gifts, follows, and moderation events
- **Stream Lifecycle Management**: Tracks stream start/end events for context-aware processing

## Core Components

### KickAPI Service
A lightweight REST client for Kick API v2 interactions:
- Get channel information and livestream status
- Retrieve chatroom metadata
- Send chat messages programmatically
- Validate channel existence

### KickChatClient Service
Pusher-based WebSocket client for real-time chat:
- Connects to Kick's Pusher infrastructure (us2 cluster)
- Subscribes to channel-specific chatrooms
- Handles subscription, message, gift, and moderation events
- Automatic reconnection with exponential backoff

## Architecture

```
┌─────────────────┐
│  Kick Platform  │
└────────┬────────┘
         │
    ┌────┴────┐
    │          │
    v          v
[HTTP Webhooks]  [Pusher WebSocket]
    │              │
    v              v
POST /webhook/kick  KickChatClient
    │              │
    └──────┬───────┘
           │
           v
    Event Normalization
           │
           v
    Router API Integration
```

## Event Flow

1. **Webhook Events**: Kick platform sends signed HTTP POST requests to `/webhook/kick`
2. **Signature Validation**: HMAC-SHA256 verification using `KICK_WEBHOOK_SECRET`
3. **Chat Events**: KickChatClient receives Pusher messages in parallel
4. **Event Normalization**: Both sources converted to standard event schema
5. **Router Integration**: Normalized events forwarded to `ROUTER_API_URL`
6. **Processing**: Router delegates to appropriate command processors

## Supported Event Types

| Kick Event | Normalized Type | Processing |
|-----------|-----------------|-----------|
| ChatMessage | chat | Text content, user info, badges |
| Subscription | subscription | Subscriber tier, duration |
| GiftedSubscription | gift_subscription | Gift count, tier, recipient |
| ChannelFollow | follow | First-time or repeat follow |
| StreamStart | stream_start | Livestream activation |
| StreamEnd | stream_end | Livestream termination |
| Raid | raid | Raider info, viewer count |
| Ban/Timeout | moderation | Duration, reason |

## Integration Points

- **Core API** (`CORE_API_URL`): User context, channel configuration
- **Router API** (`ROUTER_API_URL`): Event distribution and processing
- **Database** (`DATABASE_URL`): Event history, user mappings, cache
- **Redis** (`REDIS_URL`): Session state, rate limiting, temporary cache

## Environment Configuration

```bash
MODULE_PORT=8007              # Service HTTP port
DATABASE_URL=...              # PostgreSQL connection string
CORE_API_URL=...              # Core service endpoint
ROUTER_API_URL=...            # Router service endpoint
LOG_LEVEL=INFO                # Logging verbosity
SECRET_KEY=...                # Session encryption
KICK_WEBHOOK_SECRET=...       # Webhook HMAC secret
KICK_PUSHER_KEY=...           # Pusher application key
KICK_PUSHER_CLUSTER=us2       # Pusher cluster
REDIS_URL=...                 # Redis connection string
```

## Module Status

- **Status Endpoint**: `GET /api/v1/status` (JSON with module health)
- **Health Check**: `GET /health` (200 if operational)
- **Metrics**: `GET /metrics` (Prometheus format)

## Dependencies

- **quart**: Async Python web framework (alternative to Flask)
- **hypercorn**: ASGI server for Quart
- **aiohttp**: Async HTTP client (KickAPI calls)
- **pysher**: Pusher WebSocket client library
- **psycopg2-binary**: PostgreSQL adapter
- **pydal**: Database abstraction layer
- **python-dotenv**: Environment configuration
- **flask_core**: Shared WaddleBot utilities
- **platform_receiver**: Event normalization base classes

## Performance Characteristics

- **Connection Pool**: 10 concurrent HTTP connections (configurable)
- **Pusher Subscriptions**: 1 per tracked channel (memory-efficient)
- **Chat Latency**: &lt;500ms message to processing
- **WebSocket Reconnect**: Exponential backoff (1s → 30s max)
- **Event Throughput**: 1000+ events/second capacity

## Monitoring & Observability

- Structured JSON logging to stdout
- Prometheus-compatible metrics endpoint
- Error tracking via Router API failures
- Chat connection status monitoring
- Event processing latency tracking

## See Also

- [API Documentation](API.md)
- [Configuration Guide](CONFIGURATION.md)
- [Architecture Details](ARCHITECTURE.md)
- [Usage Examples](USAGE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
