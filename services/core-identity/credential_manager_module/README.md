# Credential Manager Module

Automatic OAuth2 token lifecycle management service for WaddleBot. Continuously monitors and refreshes expiring credentials across multiple streaming platforms.

## Features

- **Automatic Token Refresh**: Polls database for expiring credentials and refreshes them before expiration
- **Multi-Platform Support**: Handles OAuth flows for:
  - Twitch
  - Discord
  - Slack
  - YouTube/Google
  - Spotify
  - Kick
- **Exponential Backoff Retries**: Intelligent retry logic with configurable backoff
- **Redis Pub/Sub Integration**: Publishes credential refresh events for subscribers
- **Comprehensive Logging**: Full audit trail of refresh operations
- **Status Monitoring**: Real-time metrics and health checks

## Architecture

### RefreshService (`services/refresh_service.py`)

Main service that:
- Creates PostgreSQL connection pool
- Connects to Redis for pub/sub
- Runs periodic polling loop
- Manages token refresh lifecycle

### OAuth Handlers (`services/oauth_handlers.py`)

Platform-specific implementations for token refresh:
- `BaseOAuthHandler`: Abstract interface
- `TwitchOAuthHandler`: Twitch token endpoint
- `DiscordOAuthHandler`: Discord token endpoint
- `SlackOAuthHandler`: Slack OAuth endpoint
- `YouTubeOAuthHandler`: Google OAuth2 endpoint
- `SpotifyOAuthHandler`: Spotify token endpoint (with Basic auth)
- `KickOAuthHandler`: Kick token endpoint

Each handler implements proper authentication patterns for its platform.

### Configuration (`config.py`)

Environment-based configuration:
- Database URL with automatic conversion
- Redis connection string
- Token refresh buffer (seconds before expiry to refresh)
- Poll interval (check frequency)
- Retry settings (max attempts, backoff)
- Logging configuration

### Application (`app.py`)

Quart-based REST API with endpoints:
- `GET /health` - Service health check
- `GET /api/v1/credentials/status` - Credential statistics
- `POST /api/v1/credentials/refresh-now` - Force refresh cycle

## Configuration

Environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot

# Redis (for pub/sub notifications)
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=credentials:

# Refresh behavior
TOKEN_REFRESH_BUFFER=300        # Refresh 5 minutes before expiry
POLL_INTERVAL=60                # Check every 60 seconds
MAX_REFRESH_RETRIES=3           # Retry up to 3 times
RETRY_BACKOFF_BASE=5            # 5s, 10s, 20s backoff

# Server
MODULE_PORT=8095
LOG_LEVEL=INFO
```

## Database Schema

Requires `platform_integrations` table with fields:

```sql
- id: Integer (primary key)
- platform: String (twitch, discord, slack, youtube, spotify, kick)
- integration_type: String (bot, user, etc.)
- community_id: Integer (optional)
- user_id: Integer (optional)
- access_token: String (encrypted)
- refresh_token: String (encrypted)
- client_id: String
- client_secret: String (encrypted)
- token_type: String (Bearer, etc.)
- expires_at: Timestamp
- scopes: Array of strings
- config_data: JSONB
- is_active: Boolean
- created_at: Timestamp
- updated_at: Timestamp
```

## Token Refresh Flow

1. Service starts, initializes DB pool and Redis connection
2. Periodic polling checks for credentials expiring within buffer window
3. For each expiring credential:
   - Get platform-specific OAuth handler
   - Call handler's refresh_token() method
   - Update database with new tokens and expiration
   - Publish Redis pub/sub event
4. Exponential backoff retry on failures
5. Continue polling at configured interval

## Redis Pub/Sub Events

After successful refresh, publishes to channel:

```
credentials:{platform}:{integration_type}:{community_id}:refreshed
```

Example:
```
credentials:twitch:bot:12345:refreshed
```

Message body: ISO8601 timestamp of refresh

## Health Checks

**Endpoint**: `GET /health`

Response (healthy):
```json
{
  "status": "healthy",
  "module": "credential_manager",
  "version": "1.0.0",
  "running": true,
  "last_cycle": "2025-02-05T10:30:15.123456Z",
  "total_refreshed": 42,
  "total_errors": 2
}
```

Response (degraded):
```json
{
  "status": "degraded",
  "module": "credential_manager",
  "version": "1.0.0",
  "running": false,
  "last_cycle": null,
  "total_refreshed": 0,
  "total_errors": 0
}
```

## Credential Statistics

**Endpoint**: `GET /api/v1/credentials/status`

Returns breakdown by platform and integration type:

```json
{
  "success": true,
  "stats": [
    {
      "platform": "twitch",
      "integration_type": "bot",
      "total": 10,
      "expiring_soon": 2,
      "expired": 0
    }
  ]
}
```

## Force Refresh

**Endpoint**: `POST /api/v1/credentials/refresh-now`

Triggers immediate refresh cycle:

```json
{
  "success": true,
  "message": "Refreshed 5 credentials"
}
```

## Docker Deployment

Build:
```bash
docker build -f core/credential_manager_module/Dockerfile -t credential_manager .
```

Run:
```bash
docker run -e DATABASE_URL=... -e REDIS_URL=... -p 8095:8095 credential_manager
```

## Error Handling

- **Network errors**: Logged and retried with exponential backoff
- **Invalid platforms**: Logged as warning, integration skipped
- **Database errors**: Logged and propagated, may cause service degradation
- **OAuth failures**: Credential marked for retry, logged with details

## Logging

All operations logged with:
- Timestamp
- Log level (INFO, WARNING, ERROR)
- Module name
- Detailed message

Example:
```
2025-02-05 10:30:15 [credential_manager.services.refresh_service] INFO: Refresh cycle: 5 tokens refreshed
2025-02-05 10:31:20 [credential_manager.services.oauth_handlers] WARNING: Twitch token refresh failed: HTTP 401
```

## Performance

- **Connection pooling**: 2-5 PostgreSQL connections
- **Async I/O**: All OAuth calls non-blocking
- **Memory efficient**: Uses __slots__ for service class
- **Concurrent refreshes**: Processes up to 50 credentials per cycle

## Security

- Credentials stored encrypted in database
- No credentials logged or exposed in responses
- HTTPS recommended for all endpoints
- Sensitive config (API secrets) from environment only
- Token refresh uses proper OAuth2 flows

## Troubleshooting

### Service Not Starting

Check:
1. DATABASE_URL is valid PostgreSQL connection
2. REDIS_URL is valid Redis connection
3. Python 3.13 with asyncio support
4. All required dependencies installed

### Tokens Not Refreshing

Check:
1. POLL_INTERVAL is reasonable (not 0 or negative)
2. TOKEN_REFRESH_BUFFER covers your use cases
3. platform_integrations table has active credentials
4. expires_at timestamps are valid
5. OAuth credentials (client_id/secret) are correct

### High Failure Rate

Check:
1. Platform OAuth endpoints are reachable
2. Client credentials not rotated on provider side
3. Rate limits not exceeded (adjust POLL_INTERVAL)
4. Network connectivity to OAuth endpoints

## See Also

- [Waddlebot Architecture](../../docs/ARCHITECTURE.md)
- [Database Schema](../../docs/architecture/database-schema.md)
- [Security Policies](../../docs/SECURITY.md)
