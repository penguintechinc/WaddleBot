# Twitch Module Configuration

## Environment Variables

All environment variables are read from `.env` file or passed directly. Required variables must be set for the service to start.

### Core Service

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MODULE_PORT` | int | 8002 | No | HTTP server port |
| `LOG_LEVEL` | string | `info` | No | Logging level: `debug`, `info`, `warning`, `error` |
| `ENVIRONMENT` | string | `development` | No | `development`, `staging`, `production` |

### Database

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATABASE_URL` | string | - | Yes | PostgreSQL connection string: `postgresql://user:pass@host:5432/dbname` |
| `DB_POOL_SIZE` | int | 10 | No | Connection pool size |
| `DB_TIMEOUT` | int | 30 | No | Connection timeout (seconds) |

### Twitch IRC Bot

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `TWITCH_CLIENT_ID` | string | - | Yes | Twitch application client ID |
| `TWITCH_CLIENT_SECRET` | string | - | Yes | Twitch application client secret |
| `TWITCH_ACCESS_TOKEN` | string | - | Yes | Twitch OAuth access token (for API calls) |
| `TWITCH_BOT_TOKEN` | string | - | Yes | Twitch OAuth token for bot account (IRC) |
| `TWITCH_BOT_NICK` | string | `WaddleBot` | No | Bot nickname in Twitch chat |
| `TWITCH_BOT_ENABLED` | bool | `true` | No | Enable IRC bot service |
| `TWITCH_BOT_RECONNECT_ATTEMPTS` | int | 5 | No | Max reconnection attempts before backoff |
| `TWITCH_BOT_RECONNECT_INTERVAL` | int | 5 | No | Reconnection interval (seconds) |

### EventSub Webhooks

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `EVENTSUB_SECRET` | string | - | Yes | Twitch EventSub webhook secret (for HMAC verification) |
| `EVENTSUB_CALLBACK_URL` | string | - | Yes | Public webhook callback URL (e.g., `https://waddlebot.penguintech.cloud/eventsub/webhook`) |
| `EVENTSUB_ENABLED` | bool | `true` | No | Enable EventSub webhook receiver |
| `EVENTSUB_SUBSCRIPTION_TYPES` | string | `channel.subscribe,channel.raid,channel.follow,channel.cheer,stream.online,stream.offline` | No | Comma-separated EventSub event types to subscribe to |
| `EVENTSUB_DEDUP_WINDOW` | int | 5000 | No | Number of recent message IDs to track for deduplication |

### Channel Management

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CHANNEL_REFRESH_INTERVAL` | int | 300 | No | Channel list refresh interval (seconds) |
| `CHANNEL_JOIN_TIMEOUT` | int | 10 | No | Timeout for joining a channel (seconds) |
| `CHANNEL_MESSAGE_SPLIT_LENGTH` | int | 500 | No | Max characters per message before splitting |

### Viewer Tracking

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `VIEWER_TRACKING_ENABLED` | bool | `true` | No | Enable viewer presence tracking |
| `VIEWER_POLL_INTERVAL` | int | 60 | No | Chatters API poll interval (seconds) |
| `VIEWER_POLL_TIMEOUT` | int | 10 | No | Chatters API request timeout (seconds) |
| `VIEWER_CACHE_TTL` | int | 300 | No | Viewer cache TTL (seconds) |
| `VIEWER_ACTIVITY_RETENTION` | int | 3600 | No | How long to track viewer activity (seconds) |

### Caching

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CACHE_TYPE` | string | `memory` | No | Cache backend: `memory` or `redis` |
| `REDIS_URL` | string | - | If `CACHE_TYPE=redis` | Redis connection: `redis://[:password]@host:6379/0` |
| `CACHE_TTL` | int | 3600 | No | Default cache TTL (seconds) |
| `CHANNEL_CACHE_TTL` | int | 300 | No | Channel list cache TTL (seconds) |

### API Integration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ROUTER_API_URL` | string | - | Yes | waddlebot-router API base URL (e.g., `http://router:8001`) |
| `ROUTER_API_KEY` | string | - | Yes | Router API authentication key |
| `HUB_API_URL` | string | - | Yes | Hub API base URL (e.g., `http://hub:8000`) |
| `HUB_API_KEY` | string | - | Yes | Hub API authentication key |
| `SERVICE_API_KEY` | string | - | Yes | Service API key (for `/api/v1/bot/send`, etc.) |
| `API_TIMEOUT` | int | 30 | No | HTTP request timeout (seconds) |
| `API_RETRY_ATTEMPTS` | int | 3 | No | HTTP request retry attempts |
| `API_RETRY_BACKOFF` | float | 1.5 | No | Retry backoff multiplier |

### Monitoring & Observability

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `METRICS_ENABLED` | bool | `true` | No | Enable Prometheus metrics endpoint |
| `METRICS_PORT` | int | 8002 | No | Metrics port (same as main port if not set) |
| `TRACE_ENABLED` | bool | `false` | No | Enable distributed tracing (OpenTelemetry) |
| `TRACE_EXPORTER_URL` | string | - | If `TRACE_ENABLED=true` | Trace exporter URL (e.g., OTLP collector) |

---

## Configuration Files

### `.env` Example

```bash
# Core
MODULE_PORT=8002
LOG_LEVEL=info
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://waddle_user:securepassword@postgres.internal:5432/waddlebot_db
DB_POOL_SIZE=20
DB_TIMEOUT=30

# Twitch Bot
TWITCH_CLIENT_ID=abc123def456ghi789
TWITCH_CLIENT_SECRET=xyz789abc456def123
TWITCH_ACCESS_TOKEN=oauth_token_here_long_string
TWITCH_BOT_TOKEN=oauth_bot_token_here
TWITCH_BOT_NICK=WaddleBot
TWITCH_BOT_ENABLED=true

# EventSub
EVENTSUB_SECRET=eventsub_secret_here_min_32_chars
EVENTSUB_CALLBACK_URL=https://waddlebot.penguintech.cloud/eventsub/webhook
EVENTSUB_ENABLED=true

# Channels
CHANNEL_REFRESH_INTERVAL=300
CHANNEL_MESSAGE_SPLIT_LENGTH=500

# Viewer Tracking
VIEWER_TRACKING_ENABLED=true
VIEWER_POLL_INTERVAL=60

# Cache
CACHE_TYPE=redis
REDIS_URL=redis://:password@redis.internal:6379/0

# APIs
ROUTER_API_URL=http://router:8001
ROUTER_API_KEY=router_secret_key_here
HUB_API_URL=http://hub:8000
HUB_API_KEY=hub_secret_key_here
SERVICE_API_KEY=service_secret_key_here
```

### Docker Compose Example

```yaml
services:
  twitch-module:
    image: waddlebot/twitch-module:latest
    container_name: twitch-module
    ports:
      - "8002:8002"
    environment:
      MODULE_PORT: 8002
      LOG_LEVEL: info
      DATABASE_URL: postgresql://waddle_user:securepassword@postgres:5432/waddlebot_db
      TWITCH_CLIENT_ID: ${TWITCH_CLIENT_ID}
      TWITCH_CLIENT_SECRET: ${TWITCH_CLIENT_SECRET}
      TWITCH_ACCESS_TOKEN: ${TWITCH_ACCESS_TOKEN}
      TWITCH_BOT_TOKEN: ${TWITCH_BOT_TOKEN}
      EVENTSUB_SECRET: ${EVENTSUB_SECRET}
      EVENTSUB_CALLBACK_URL: https://waddlebot.penguintech.cloud/eventsub/webhook
      ROUTER_API_URL: http://router:8001
      ROUTER_API_KEY: ${ROUTER_API_KEY}
      HUB_API_URL: http://hub:8000
      HUB_API_KEY: ${HUB_API_KEY}
      SERVICE_API_KEY: ${SERVICE_API_KEY}
      CACHE_TYPE: redis
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      - router
      - hub
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    networks:
      - waddlebot

  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    networks:
      - waddlebot

networks:
  waddlebot:
    driver: bridge
```

### Kubernetes ConfigMap/Secret Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: twitch-module-config
  namespace: waddlebot
data:
  MODULE_PORT: "8002"
  LOG_LEVEL: "info"
  ENVIRONMENT: "production"
  TWITCH_BOT_NICK: "WaddleBot"
  TWITCH_BOT_ENABLED: "true"
  EVENTSUB_ENABLED: "true"
  EVENTSUB_CALLBACK_URL: "https://waddlebot.penguintech.cloud/eventsub/webhook"
  CHANNEL_REFRESH_INTERVAL: "300"
  CHANNEL_MESSAGE_SPLIT_LENGTH: "500"
  VIEWER_TRACKING_ENABLED: "true"
  VIEWER_POLL_INTERVAL: "60"
  CACHE_TYPE: "redis"
  ROUTER_API_URL: "http://router:8001"
  HUB_API_URL: "http://hub:8000"

---
apiVersion: v1
kind: Secret
metadata:
  name: twitch-module-secrets
  namespace: waddlebot
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@postgres:5432/waddlebot_db"
  TWITCH_CLIENT_ID: "abc123def456ghi789"
  TWITCH_CLIENT_SECRET: "xyz789abc456def123"
  TWITCH_ACCESS_TOKEN: "oauth_token_here"
  TWITCH_BOT_TOKEN: "oauth_bot_token_here"
  EVENTSUB_SECRET: "eventsub_secret_here"
  ROUTER_API_KEY: "router_secret_key_here"
  HUB_API_KEY: "hub_secret_key_here"
  SERVICE_API_KEY: "service_secret_key_here"
  REDIS_URL: "redis://redis:6379/0"
```

---

## Startup Procedure

1. **Validate Environment**: All required variables must be set, or startup fails with error details
2. **Database Connection**: Connect to PostgreSQL; create tables if they don't exist (via migrations)
3. **Cache Initialization**: Connect to Redis (if enabled) or initialize in-memory cache
4. **Twitch OAuth**: Validate tokens with Twitch API; get bot user info
5. **Channel Load**: Load all channels from database; start joining channels
6. **Bot Connection**: Establish IRC connection to Twitch TMI
7. **EventSub Subscribe**: Register webhook subscriptions with Twitch EventSub API
8. **Viewer Tracker**: Start 60s polling loop for chatters API
9. **HTTP Server**: Start Quart/Hypercorn server on `MODULE_PORT`
10. **Health Status**: Mark service as healthy; return 200 on `/health`

---

## Logging Configuration

### Log Levels

- `debug` - All events, API calls, cache operations (verbose)
- `info` - Service lifecycle, important events, errors
- `warning` - Recoverable errors, degraded functionality
- `error` - Fatal errors, service failures

### Log Format

Structured JSON format:

```json
{
  "timestamp": "2025-02-24T10:30:00Z",
  "level": "info",
  "service": "twitch-module",
  "component": "TwitchBotService",
  "message": "Channel joined successfully",
  "channel_id": "12345",
  "channel_name": "example_channel",
  "correlation_id": "corr-abc123",
  "duration_ms": 1234
}
```

### Log Output

- **stdout**: All logs (containerized environment)
- **File** (optional): `/var/log/twitch-module.log` (if `LOG_FILE=/var/log/twitch-module.log` set)

---

## Performance Tuning

### Database
- `DB_POOL_SIZE=20` - Increase for high concurrency (20+ channels)
- `DB_TIMEOUT=30` - Increase if network latency is high

### Viewer Tracking
- `VIEWER_POLL_INTERVAL=60` - Decrease for faster updates (minimum 30s)
- `VIEWER_CACHE_TTL=300` - Increase to reduce API calls

### Caching
- `CACHE_TYPE=redis` - Use Redis for distributed caching (better than in-memory)
- `CHANNEL_CACHE_TTL=300` - Adjust based on channel change frequency

### API Calls
- `API_RETRY_ATTEMPTS=3` - Increase for unstable networks
- `API_TIMEOUT=30` - Adjust based on network latency

---

## Troubleshooting Configuration

### Bot Won't Connect
- Verify `TWITCH_BOT_TOKEN` is valid (refresh if expired)
- Check `TWITCH_BOT_NICK` matches bot account username

### EventSub Webhooks Not Received
- Verify `EVENTSUB_SECRET` matches Twitch console
- Verify `EVENTSUB_CALLBACK_URL` is publicly accessible
- Check logs for HMAC verification errors

### Viewer Tracking Not Working
- Verify `VIEWER_TRACKING_ENABLED=true`
- Check that channels have `is_live=true` (only active streams tracked)
- Verify `VIEWER_POLL_INTERVAL` is not too high

### Database Connection Failed
- Verify `DATABASE_URL` syntax and credentials
- Check network connectivity to database host
- Verify PostgreSQL is running and accepting connections
