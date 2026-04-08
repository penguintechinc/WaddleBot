# Credential Manager Module - Reference

Automatic OAuth2 token lifecycle management and multi-platform credential refresh.

## Overview

The Credential Manager module continuously monitors and refreshes expiring OAuth2 tokens across multiple streaming platforms. It maintains credential freshness through automatic polling, platform-specific OAuth handlers, and intelligent retry logic.

## Key Features

- **Automatic Token Refresh** - Polls database for expiring credentials and refreshes them before expiration
- **Multi-Platform Support** - Twitch, Discord, Slack, YouTube, Spotify, Kick
- **Exponential Backoff Retries** - Intelligent retry logic with configurable backoff
- **Redis Pub/Sub Integration** - Publishes credential refresh events for subscribers
- **Real-Time Monitoring** - Health checks and credential statistics
- **Comprehensive Logging** - Full audit trail of refresh operations

## Configuration

### Environment Variables

```bash
# Service
MODULE_PORT=8050
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Redis (for pub/sub notifications)
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=credentials:

# Refresh Behavior
TOKEN_REFRESH_BUFFER=300            # Refresh 5 minutes before expiry
POLL_INTERVAL=60                    # Check every 60 seconds
MAX_REFRESH_RETRIES=3               # Retry up to 3 times
RETRY_BACKOFF_BASE=5                # 5s, 10s, 20s backoff (exponential)
```

## REST API Endpoints

### Health Check
```
GET /health
```

Returns service health status and metrics.

**Response** (200 OK):
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

**Response** (503 Service Unavailable):
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

**Fields**:
- `status`: "healthy" or "degraded"
- `module`: Service name
- `version`: Service version
- `running`: Whether refresh loop is active
- `last_cycle`: ISO8601 timestamp of last refresh cycle
- `total_refreshed`: Cumulative tokens refreshed
- `total_errors`: Cumulative refresh errors

**Use Case**: Liveness and readiness probes, monitoring dashboards

### Credential Status
```
GET /api/v1/credentials/status
```

Returns breakdown of tracked credentials by platform and integration type.

**Response** (200 OK):
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
    },
    {
      "platform": "discord",
      "integration_type": "bot",
      "total": 5,
      "expiring_soon": 1,
      "expired": 0
    },
    {
      "platform": "slack",
      "integration_type": "user",
      "total": 3,
      "expiring_soon": 0,
      "expired": 0
    }
  ]
}
```

**Response** (503 Service Unavailable):
```json
{
  "error": "Service not initialized"
}
```

**Fields** (per stat):
- `platform`: Integration platform (twitch, discord, slack, youtube, spotify, kick)
- `integration_type`: Type of integration (bot, user, etc.)
- `total`: Total credentials for this platform/type
- `expiring_soon`: Count expiring within TOKEN_REFRESH_BUFFER window
- `expired`: Count already expired

**Notes**:
- "Expiring soon" uses TOKEN_REFRESH_BUFFER (default 5 minutes)
- Only counts active credentials (is_active=true)
- Requires valid database connection

**Use Case**: Monitoring dashboard, admin status page, alerting

### Force Refresh
```
POST /api/v1/credentials/refresh-now
```

Triggers immediate token refresh cycle.

**Request**: No request body required

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Refreshed 5 credentials"
}
```

**Response** (503 Service Unavailable):
```json
{
  "error": "Service not initialized"
}
```

**Notes**:
- Does not block; returns immediately
- Refresh cycle runs asynchronously
- Call `/api/v1/credentials/status` after a moment to see results
- Useful for manual intervention (e.g., after credential rotation)

**Use Case**: Manual token refresh trigger, admin actions, testing

## Supported Platforms

| Platform | OAuth Endpoint | Token Type | Refresh Method |
|----------|---|---|---|
| **Twitch** | oauth.twitch.tv | Bearer | POST /oauth2/token |
| **Discord** | discord.com/api/oauth2 | Bearer | POST /token |
| **Slack** | slack.com/api/oauth.v2 | Bearer | POST /oauth.v2.access |
| **YouTube** | oauth2.googleapis.com | Bearer | POST /token |
| **Spotify** | accounts.spotify.com | Bearer | POST /api/token (Basic auth) |
| **Kick** | kick.com/oauth | Bearer | POST /token |

Each platform has a dedicated OAuth handler implementing refresh logic.

## Token Refresh Flow

1. Service starts, initializes DB pool and Redis connection
2. Periodic polling checks for credentials expiring within buffer window
3. For each expiring credential:
   - Get platform-specific OAuth handler
   - Call handler's `refresh_token()` method
   - Update database with new tokens and expiration
   - Publish Redis pub/sub event
4. Exponential backoff retry on failures
5. Continue polling at configured interval

### Retry Logic

Failed refreshes are retried with exponential backoff:

```
Attempt 1: Wait 5s (RETRY_BACKOFF_BASE)
Attempt 2: Wait 10s (RETRY_BACKOFF_BASE * 2)
Attempt 3: Wait 20s (RETRY_BACKOFF_BASE * 4)
Max 3 attempts (MAX_REFRESH_RETRIES)
```

If all retries fail, credential is marked for next cycle.

## Redis Pub/Sub Events

### Channel Format

After successful refresh, publishes to channel:

```
credentials:{platform}:{integration_type}:{scope_id}:refreshed
```

### Example Channels

```
credentials:twitch:bot:12345:refreshed
credentials:discord:user:67890:refreshed
credentials:slack:bot:54321:refreshed
credentials:youtube:bot:99999:refreshed
```

### Message Body

ISO8601 timestamp of refresh:
```
2025-02-05T10:30:15.123456Z
```

### Subscription Example (Node.js)

```javascript
const redis = require('redis');
const client = redis.createClient();

client.subscribe('credentials:twitch:bot:*:refreshed', (message) => {
  console.log('Twitch token refreshed:', message);
  // Trigger dependent services (e.g., reconnect IRC)
});
```

### Subscription Example (Python)

```python
import redis
r = redis.Redis()
pubsub = r.pubsub()
pubsub.psubscribe('credentials:twitch:bot:*:refreshed')

for message in pubsub.listen():
    if message['type'] == 'pmessage':
        print(f"Token refreshed: {message['data']}")
        # Trigger dependent services
```

## Database Schema

### platform_integrations

OAuth credential storage table.

```sql
id (Integer, Primary Key)
platform (String)                   # twitch, discord, slack, youtube, spotify, kick
integration_type (String)           # bot, user, service, etc.
community_id (Integer, Optional)    # Community scope (if applicable)
user_id (Integer, Optional)         # User scope (if applicable)
access_token (String, Encrypted)    # OAuth access token
refresh_token (String, Encrypted)   # OAuth refresh token
client_id (String)                  # OAuth app client ID
client_secret (String, Encrypted)   # OAuth app client secret
token_type (String)                 # "Bearer", etc.
expires_at (Timestamp)              # Token expiration time (UTC)
scopes (Array)                      # OAuth scopes granted (e.g. ["chat:read", "chat:write"])
config_data (JSONB)                 # Platform-specific config (channel IDs, server IDs, etc.)
is_active (Boolean)                 # Soft delete flag
created_at (Timestamp)              # Creation timestamp
updated_at (Timestamp)              # Last update timestamp
last_refreshed_at (Timestamp)       # Last successful refresh
last_refresh_error (String)         # Most recent error message
```

### Index Strategy

```sql
CREATE INDEX platform_integrations_expires_at 
  ON platform_integrations(expires_at) 
  WHERE is_active = true;

CREATE INDEX platform_integrations_platform 
  ON platform_integrations(platform) 
  WHERE is_active = true;

CREATE INDEX platform_integrations_community 
  ON platform_integrations(community_id) 
  WHERE is_active = true;
```

## Error Handling

### Common Error Scenarios

| Scenario | Handling |
|----------|----------|
| Network error | Retry with exponential backoff |
| Invalid credentials | Log error, skip integration, mark for manual review |
| Database error | Log and propagate, may cause service degradation |
| OAuth 401 Unauthorized | Credential may be revoked; skip and log |
| OAuth 429 Rate Limited | Back off and retry |
| Expired refresh token | Mark as invalid; manual re-link required |

### Error Logging

All operations logged with:
- Timestamp
- Log level (INFO, WARNING, ERROR)
- Module: credential_manager
- Platform name
- Integration type
- Error details

Example:
```
2025-02-05 10:30:15 [credential_manager] INFO: Refresh cycle: 5 tokens refreshed, 0 errors
2025-02-05 10:31:20 [credential_manager] WARNING: Twitch token refresh failed (attempt 1/3): HTTP 401
2025-02-05 10:31:25 [credential_manager] WARNING: Twitch token refresh failed (attempt 2/3): HTTP 401
2025-02-05 10:31:30 [credential_manager] ERROR: Twitch token refresh failed (all retries exhausted): Credential may be revoked
```

## Performance Characteristics

- **Connection pooling**: 2-5 PostgreSQL connections
- **Async I/O**: All OAuth calls non-blocking
- **Memory efficient**: Uses `__slots__` for service class
- **Concurrent refreshes**: Processes up to 50 credentials per cycle
- **Typical cycle time**: 10-30 seconds (depends on credential count and platform latency)

## Security Considerations

- Credentials stored encrypted in database
- No credentials logged or exposed in responses
- HTTPS recommended for all endpoints
- Sensitive config (API secrets) from environment only
- Token refresh uses proper OAuth2 flows
- Per-service database user with SELECT/UPDATE only

## Troubleshooting

### Service Not Starting

Check:
1. DATABASE_URL is valid PostgreSQL connection
2. REDIS_URL is valid Redis connection (if pub/sub needed)
3. Python 3.13+ with asyncio support
4. All required dependencies installed

### Tokens Not Refreshing

Check:
1. POLL_INTERVAL is reasonable (not 0 or negative)
2. TOKEN_REFRESH_BUFFER covers your use cases
3. platform_integrations table has active credentials
4. expires_at timestamps are valid
5. OAuth credentials (client_id/secret) are correct
6. Check logs for specific refresh errors

### High Failure Rate

Check:
1. Platform OAuth endpoints are reachable
2. Client credentials not rotated on provider side
3. Rate limits not exceeded (adjust POLL_INTERVAL)
4. Network connectivity to OAuth endpoints
5. Check `/health` endpoint for degradation

### Monitor Refresh Health

```bash
# Check service health
curl http://localhost:8050/health | jq .

# Monitor in loop
while true; do
  echo "=== $(date) ==="
  curl -s http://localhost:8050/health | jq '.total_refreshed, .total_errors'
  sleep 30
done
```

## Integration Examples

### Listen for Token Refreshes

```python
import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
pubsub = r.pubsub()

# Subscribe to all Twitch bot refreshes
pubsub.psubscribe('credentials:twitch:bot:*:refreshed')

for message in pubsub.listen():
    if message['type'] == 'pmessage':
        channel = message['channel']
        timestamp = message['data']
        
        # Parse channel: credentials:twitch:bot:12345:refreshed
        parts = channel.split(':')
        platform = parts[1]
        community_id = parts[3]
        
        print(f"Token refreshed: {platform} for community {community_id}")
        # Trigger reconnect or other dependent action
```

### Monitor Credential Stats

```python
import requests
import json

response = requests.get('http://localhost:8050/api/v1/credentials/status')
stats = response.json()['stats']

# Group by platform
by_platform = {}
for stat in stats:
    platform = stat['platform']
    if platform not in by_platform:
        by_platform[platform] = {'total': 0, 'expiring': 0}
    by_platform[platform]['total'] += stat['total']
    by_platform[platform]['expiring'] += stat['expiring_soon']

# Alert if many expiring
for platform, counts in by_platform.items():
    pct = counts['expiring'] / counts['total'] * 100 if counts['total'] > 0 else 0
    if pct > 10:
        print(f"WARNING: {pct}% of {platform} tokens expiring soon!")
```

## Related Documentation

- [Core Identity Service README](../README.md) - Combined service overview
- [API.md](../credential_manager_module/API.md) - Detailed API reference
- [Database Schema](../../docs/architecture/database-schema.md)
