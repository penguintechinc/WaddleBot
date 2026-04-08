# Core Identity Service

Combined microservice that merges 3 core WaddleBot modules into a single Quart application on port 8050 (REST API) + 50030 (gRPC).

## Modules Included

1. **Identity Core Module** (port 8050 → `/api/v1`, port 50030 → gRPC)
   - User identity management across platforms
   - Platform linking and cross-platform identity resolution
   - JWT authentication
   - gRPC services for identity lookup and platform resolution

2. **Security Core Module** (port 8050 → `/api/v1/security`, `/api/v1/internal`)
   - Security configuration management per community
   - Content filtering and word blocking
   - Spam detection
   - Warning management system
   - Moderation action logging and synchronization

3. **Credential Manager Module** (port 8050 → `/api/v1/credentials`)
   - OAuth2 token lifecycle management
   - Automatic credential refresh (Twitch, Discord, Slack, YouTube, Spotify, Kick)
   - Redis pub/sub notifications
   - Credential status monitoring

## Architecture

```
/app/
  app.py                              # Combined Quart entry point
  requirements.txt                    # Merged dependencies
  Dockerfile                          # Multi-stage build
  identity_core_module/               # Identity service code
    config.py                         # Identity config
    app.py                            # (REST endpoints in main app.py)
    services/
      grpc_handler.py                 # gRPC servicer implementation
    models/                           # Data models
    flask_core.py                     # Shared utilities
  security_core_module/               # Security service code
    config.py                         # Security config
    services/
      security_service.py             # Config & policy management
      content_filter.py               # Word filtering
      spam_detector.py                # Spam detection
      warning_manager.py              # Warning lifecycle
  credential_manager_module/          # Credential management
    config.py                         # Credential config
    services/
      refresh_service.py              # Token refresh loop
      oauth_handlers.py               # Platform-specific OAuth
  libs/                               # Shared utilities
```

## API Endpoints

### Health & Status
- `GET /healthz` - Liveness probe
- `GET /health` - Health with timestamp
- `GET /api/v1/status` - Unified service status

### Identity
- `GET /api/v1/status` - Identity module status endpoint

### Security Configuration
- `GET /api/v1/security/<community_id>/config` - Get security config
- `PUT /api/v1/security/<community_id>/config` - Update security config
- `GET /api/v1/security/status` - Security module status

### Warnings Management
- `GET /api/v1/security/<community_id>/warnings` - List warnings
  - Query params: `status` (active/expired/all), `page`, `limit`
- `POST /api/v1/security/<community_id>/warnings` - Issue manual warning
- `DELETE /api/v1/security/<community_id>/warnings/<warning_id>` - Revoke warning

### Content Filtering
- `GET /api/v1/security/<community_id>/filter-matches` - View filter match log
  - Query params: `page`, `limit`
- `POST /api/v1/security/<community_id>/blocked-words` - Add blocked words
- `DELETE /api/v1/security/<community_id>/blocked-words` - Remove blocked words

### Moderation
- `GET /api/v1/security/<community_id>/moderation-log` - View moderation actions log
  - Query params: `page`, `limit`

### Security (Internal Service-to-Service)
- `POST /api/v1/internal/check` - Check message against filters (real-time)
- `POST /api/v1/internal/warn` - Issue automated warning
- `POST /api/v1/internal/sync-action` - Sync moderation action across platforms

### Credentials
- `GET /api/v1/credentials/status` - Credential statistics by platform
- `POST /api/v1/credentials/refresh-now` - Force immediate refresh cycle

### gRPC Services (port 50030)
- `waddlebot.identity.IdentityService/LookupIdentity` - Look up identity across platforms
- `waddlebot.identity.IdentityService/GetLinkedPlatforms` - Get all platforms linked to user

## Environment Variables

```bash
# Service
MODULE_NAME=core-identity
MODULE_VERSION=1.0.0
MODULE_PORT=8050                    # REST API port
MODULE_HOST=0.0.0.0
GRPC_PORT=50030                     # gRPC server port

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Security
SERVICE_API_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
SECRET_KEY=your-flask-secret        # For identity module

# Redis (Credential Manager)
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=credentials:

# Credential Refresh
TOKEN_REFRESH_BUFFER=300            # Refresh 5 min before expiry
POLL_INTERVAL=60                    # Check every 60 seconds
MAX_REFRESH_RETRIES=3               # Retry up to 3 times
RETRY_BACKOFF_BASE=5                # 5s, 10s, 20s backoff

# Logging
LOG_LEVEL=INFO

# Router Integration (Identity)
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router
```

## Building

### Local Build
```bash
docker build -t core-identity:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8050:8050 \
  -p 50030:50030 \
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot \
  -e REDIS_URL=redis://localhost:6379/0 \
  -e SERVICE_API_KEY=secret-key \
  -e JWT_SECRET_KEY=jwt-secret \
  core-identity:latest
```

## Ports

- **8050** - HTTP REST API (all 3 modules)
- **50030** - gRPC service (Identity module only)

## Authentication

### REST API
All non-health endpoints require the `X-Service-Key` header:

```bash
curl -H "X-Service-Key: your-secret-key" http://localhost:8050/api/v1/security/1/config
```

Health endpoints are exempt:
```bash
curl http://localhost:8050/healthz
curl http://localhost:8050/health
```

### gRPC
gRPC services require JWT token in metadata:

```bash
grpcurl -H "authorization: Bearer <jwt-token>" \
  -plaintext \
  -d '{"token":"<jwt>","platform":"twitch","platform_user_id":"user123"}' \
  localhost:50030 waddlebot.identity.IdentityService/LookupIdentity
```

## Database Schema

The service initializes database tables for all 3 modules:

### Identity Core
- `users` - User profiles
- `platform_identities` - Cross-platform identity mapping
- `platform_links` - User→platform linking relationships

### Security Core
- `security_policies` - Per-community security configuration
- `content_filters` - Blocked word lists
- `filter_matches` - Content filter match log
- `warnings` - User warning records
- `moderation_log` - Moderation actions log

### Credential Manager
- `platform_integrations` - OAuth credentials for platforms
  - Stores encrypted access/refresh tokens
  - Tracks expiration times
  - Supports: Twitch, Discord, Slack, YouTube, Spotify, Kick

All use PyDAL with `migrate=False` (schema via Alembic only).

## Logging

Uses `flask_core.setup_aaa_logging()` with structured JSON logging:
- All startup/shutdown events logged
- Service key violations logged
- Per-module initialization status tracked
- gRPC server lifecycle events
- Credential refresh cycles and errors
- Security policy changes

## Credential Refresh Flow

1. Service starts, initializes DB pool and Redis connection
2. Periodic polling checks for credentials expiring within buffer window
3. For each expiring credential:
   - Get platform-specific OAuth handler
   - Call handler's refresh_token() method
   - Update database with new tokens and expiration
   - Publish Redis pub/sub event
4. Exponential backoff retry on failures
5. Continue polling at configured interval

### Redis Pub/Sub Events

After successful refresh, publishes to channel:

```
credentials:{platform}:{integration_type}:{scope_id}:refreshed
```

Example:
```
credentials:twitch:bot:12345:refreshed
```

Message body: ISO8601 timestamp of refresh

## Startup Sequence

1. **Database** - Initialize PyDAL connection pool
2. **gRPC** - Start gRPC server on port 50030 (background)
3. **Security Services** - Initialize security_service, spam_detector, content_filter, warning_manager
4. **Credentials** - Start RefreshService if Redis and credential config valid
5. **REST API** - Start Quart on port 8050 via Hypercorn

Each module initialization is logged with detailed error messages.

## Related Documentation

See `docs/` folder for detailed integration guides:
- `docs/IDENTITY_CORE.md` - Identity module reference
- `docs/SECURITY_CORE.md` - Security module reference
- `docs/CREDENTIAL_MANAGER.md` - Credential manager reference
- `docs/GRPC_INTEGRATION.md` - gRPC service details
