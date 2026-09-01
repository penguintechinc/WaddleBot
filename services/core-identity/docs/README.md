# Core Identity Service - Documentation Index

Complete reference documentation for the combined Core Identity Service (Identity Core + Security Core + Credential Manager).

## Quick Navigation

### Service Overview
- **[Core Identity Service README](../README.md)** - Service overview, ports, all API endpoints, environment variables, building & running

### Module Reference Guides

1. **[IDENTITY_CORE.md](./IDENTITY_CORE.md)** - User identity management
   - Cross-platform identity mapping
   - Platform linking
   - REST and gRPC endpoints
   - Authentication via JWT

2. **[SECURITY_CORE.md](./SECURITY_CORE.md)** - Security policies & moderation
   - Per-community security configuration
   - Content filtering and blocked words
   - Spam detection
   - Warning management system
   - Moderation action logging

3. **[CREDENTIAL_MANAGER.md](./CREDENTIAL_MANAGER.md)** - OAuth2 token lifecycle
   - Multi-platform credential refresh (Twitch, Discord, Slack, YouTube, Spotify, Kick)
   - Redis pub/sub events
   - Token refresh monitoring
   - Error handling and retry logic

4. **[GRPC_INTEGRATION.md](./GRPC_INTEGRATION.md)** - gRPC service details
   - gRPC server configuration
   - Service methods (LookupIdentity, GetLinkedPlatforms)
   - Proto compilation
   - Client examples (Python, Go, Node.js)
   - Testing with grpcurl
   - Performance and monitoring

## By Use Case

### I want to...

**Look up a user's identity across platforms**
→ See [IDENTITY_CORE.md](./IDENTITY_CORE.md) - REST API or gRPC methods

**Set up security policies for my community**
→ See [SECURITY_CORE.md](./SECURITY_CORE.md) - Configuration Management endpoints

**Check if a message is spam or filtered**
→ See [SECURITY_CORE.md](./SECURITY_CORE.md) - Real-Time Message Check endpoint (`/api/v1/internal/check`)

**Monitor credential refresh status**
→ See [CREDENTIAL_MANAGER.md](./CREDENTIAL_MANAGER.md) - Credential Status endpoint

**Subscribe to token refresh events**
→ See [CREDENTIAL_MANAGER.md](./CREDENTIAL_MANAGER.md) - Redis Pub/Sub Events section

**Build a gRPC client for identity lookups**
→ See [GRPC_INTEGRATION.md](./GRPC_INTEGRATION.md) - Service Definition and Client Examples

**Issue a warning to a user**
→ See [SECURITY_CORE.md](./SECURITY_CORE.md) - Warning Management endpoints

**Debug credential refresh failures**
→ See [CREDENTIAL_MANAGER.md](./CREDENTIAL_MANAGER.md) - Error Handling and Troubleshooting

## API Endpoints Summary

### Health & Status
```
GET /healthz                                    # Liveness probe
GET /health                                     # Health with timestamp
GET /api/v1/status                              # Unified service status
```

### Identity (REST)
```
GET /api/v1/status                              # Identity module status
```

### Identity (gRPC)
```
waddlebot.identity.IdentityService/LookupIdentity
waddlebot.identity.IdentityService/GetLinkedPlatforms
```

### Security
```
GET    /api/v1/security/<community_id>/config
PUT    /api/v1/security/<community_id>/config
GET    /api/v1/security/<community_id>/warnings
POST   /api/v1/security/<community_id>/warnings
DELETE /api/v1/security/<community_id>/warnings/<warning_id>
GET    /api/v1/security/<community_id>/filter-matches
POST   /api/v1/security/<community_id>/blocked-words
DELETE /api/v1/security/<community_id>/blocked-words
GET    /api/v1/security/<community_id>/moderation-log
GET    /api/v1/security/status
```

### Security (Internal Service-to-Service)
```
POST   /api/v1/internal/check                   # Check message against filters
POST   /api/v1/internal/warn                    # Issue automated warning
POST   /api/v1/internal/sync-action             # Sync moderation action
```

### Credentials
```
GET    /api/v1/credentials/status               # Credential statistics
POST   /api/v1/credentials/refresh-now          # Force immediate refresh
```

## Configuration Reference

### Environment Variables (All Modules)
```bash
# Service
MODULE_PORT=8050                    # REST API port
GRPC_PORT=50030                     # gRPC port
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://...
DB_POOL_SIZE=10

# Security
SERVICE_API_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
SECRET_KEY=your-flask-secret        # Identity module

# Redis (Credential Manager)
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=credentials:

# Token Refresh
TOKEN_REFRESH_BUFFER=300            # 5 min before expiry
POLL_INTERVAL=60                    # Check every 60s
MAX_REFRESH_RETRIES=3
RETRY_BACKOFF_BASE=5
```

See individual module docs for additional configuration options.

## Database Tables

### Identity Core
- `users` - User profiles
- `platform_identities` - Cross-platform identity mapping
- `platform_links` - Platform linking relationships

### Security Core
- `security_policies` - Per-community config
- `content_filters` - Blocked word lists
- `filter_matches` - Filter match log
- `warnings` - Warning records
- `moderation_log` - Moderation actions

### Credential Manager
- `platform_integrations` - OAuth credentials

See individual module docs for detailed schema information.

## Architecture Overview

```
core-identity (port 8050)
├── Identity Core Module (port 50030 gRPC)
│   ├── REST: /api/v1/status
│   └── gRPC: LookupIdentity, GetLinkedPlatforms
├── Security Core Module
│   ├── /api/v1/security/* (config, warnings, filters)
│   └── /api/v1/internal/* (message check, warn, sync)
└── Credential Manager Module
    └── /api/v1/credentials/* (status, refresh)
```

## Supported Platforms

**Credential Refresh**: Twitch, Discord, Slack, YouTube, Spotify, Kick

**Identity Resolution**: Any platform (configurable via platform_identities table)

## Common Tasks

### Issue a Warning
1. Call `POST /api/v1/security/<community_id>/warnings` with platform, user, reason
2. Returns warning ID and expiration timestamp
3. See [SECURITY_CORE.md](./SECURITY_CORE.md) - Issue Manual Warning

### Check a Message
1. Call `POST /api/v1/internal/check` with community, platform, user, message
2. Returns allowed/blocked with reason
3. See [SECURITY_CORE.md](./SECURITY_CORE.md) - Real-Time Message Check

### Look Up User Identity
**Via REST**: Not available (use gRPC)
**Via gRPC**: Call `LookupIdentity` RPC with token, platform, platform_user_id
**See**: [GRPC_INTEGRATION.md](./GRPC_INTEGRATION.md) - LookupIdentity

### Monitor Token Refresh
1. Call `GET /api/v1/credentials/status` for current stats
2. Subscribe to Redis channel `credentials:*:*:*:refreshed` for events
3. See [CREDENTIAL_MANAGER.md](./CREDENTIAL_MANAGER.md) - Redis Pub/Sub Events

### Set Community Security Policy
1. Call `PUT /api/v1/security/<community_id>/config` with max_warnings, thresholds, etc.
2. See [SECURITY_CORE.md](./SECURITY_CORE.md) - Update Community Security Config

## Error Responses

### Common HTTP Status Codes
- **200** - Success
- **400** - Bad request (invalid parameters)
- **404** - Endpoint/resource not found
- **500** - Internal server error
- **503** - Service unavailable/degraded

### Common gRPC Status Codes
- **OK** (0) - Success
- **INVALID_ARGUMENT** (3) - Missing/invalid token, platform, user ID
- **UNAUTHENTICATED** (16) - Token verification failed
- **NOT_FOUND** (5) - User or identity not found
- **INTERNAL** (13) - Server error (database, etc.)

See individual module docs for detailed error handling.

## Performance Characteristics

| Metric | Value |
|--------|-------|
| REST request latency | 10-100ms |
| gRPC request latency | 10-50ms |
| Token refresh cycle time | 10-30s (for 100 credentials) |
| Max throughput (single server) | 1000+ req/s |
| Max throughput (4 workers) | 4000+ req/s |

## Security Considerations

- All credentials stored encrypted in database
- gRPC and REST require JWT authentication
- Service-to-service auth via X-Service-Key header (REST) or JWT metadata (gRPC)
- No credentials exposed in API responses or logs
- Token refresh uses proper OAuth2 flows

## Related Documentation

- **Project-wide**: [Waddlebot Architecture](../../docs/ARCHITECTURE.md)
- **Database**: [Database Schema](../../docs/architecture/database-schema.md)
- **Security**: [Security Policies](../../docs/SECURITY.md)
