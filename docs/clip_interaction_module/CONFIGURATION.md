# Clip Interaction Module - Configuration Guide

Complete configuration reference for the Clip Interaction Module, including environment variables, startup parameters, and runtime options.

## Environment Variables

All configuration is managed via environment variables. Create a `.env` file in the module root or set variables in your deployment environment.

### Core Configuration

#### MODULE_PORT

The port on which the Quart application listens.

```env
MODULE_PORT=8098
```

- **Type**: Integer
- **Default**: 8098
- **Range**: 1024-65535
- **Notes**: Must not conflict with other services on the host

#### LOG_LEVEL

Controls logging verbosity.

```env
LOG_LEVEL=INFO
```

- **Type**: String (enum)
- **Options**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Default**: INFO
- **Recommendations**:
  - `DEBUG`: Local development only
  - `INFO`: Production (standard)
  - `WARNING`: High-traffic environments
  - `ERROR`: Troubleshooting specific issues

#### SECRET_KEY

Secret key for session and JWT validation. Generated at startup if not provided.

```env
SECRET_KEY=your-secret-key-min-32-chars
```

- **Type**: String
- **Min Length**: 32 characters
- **Default**: Generated (UUID4 + random string)
- **Security**: Never commit to version control; use secret management system
- **Rotation**: Update and restart service (sessions will invalidate)

### Database Configuration

#### DATABASE_URL

PostgreSQL connection string for persistence.

```env
DATABASE_URL=postgresql://user:password@localhost:5432/waddlebot
```

- **Type**: PostgreSQL URI
- **Format**: `postgresql://[user[:password]@][netloc][:port][/dbname]`
- **Default**: None (required)
- **Connection Pool**:
  - Min connections: 5
  - Max connections: 20
  - Timeout: 30 seconds
  - Idle cleanup: 300 seconds

**Development Example:**

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/waddlebot_dev
```

**Production Example:**

```env
DATABASE_URL=postgresql://clip_user:SecurePassword123@db.internal.penguintech.io:5432/waddlebot
```

#### REDIS_URL

Redis connection string for caching and session storage.

```env
REDIS_URL=redis://localhost:6379
```

- **Type**: Redis URI
- **Format**: `redis://[:password@]host[:port][/db]`
- **Default**: None (optional, caching disabled if not provided)
- **DB**: 0 (default), use /1 through /15 for multi-app setups
- **Timeout**: 5 seconds

**Development Example:**

```env
REDIS_URL=redis://localhost:6379/1
```

**Production with Auth:**

```env
REDIS_URL=redis://:SecurePassword@redis.internal.penguintech.io:6379/1
```

### Service Integration

#### CORE_API_URL

URL for core-api module (community validation, user info).

```env
CORE_API_URL=http://core-api:8000
```

- **Type**: HTTP URL
- **Default**: `http://core-api:8000`
- **Used For**: Community lookup, user validation, auth checks
- **Timeout**: 10 seconds
- **Retry**: 3 attempts with exponential backoff

#### ROUTER_API_URL

URL for router module (event distribution, notifications).

```env
ROUTER_API_URL=http://router:8001
```

- **Type**: HTTP URL
- **Default**: `http://router:8001`
- **Used For**: Clip created events, highlight marked events
- **Timeout**: 10 seconds
- **Retry**: 3 attempts with exponential backoff

#### TWITCH_MODULE_URL

URL for action-twitch module (clip creation proxy).

```env
TWITCH_MODULE_URL=http://action-twitch:8010
```

- **Type**: HTTP URL
- **Default**: `http://action-twitch:8010`
- **Used For**: Proxying clip creation requests to Twitch API
- **Timeout**: 30 seconds (Twitch API can be slow)
- **Retry**: 2 attempts (idempotent endpoint)

### Application Settings

#### CORS_ORIGINS

Comma-separated list of allowed CORS origins.

```env
CORS_ORIGINS=http://localhost:3000,https://admin.waddlebot.io
```

- **Type**: Comma-separated string
- **Default**: `http://localhost:3000` (dev only)
- **Format**: Full URLs with protocol and port
- **Wildcard**: Not recommended for production

#### CLIP_RETENTION_DAYS

Number of days to retain bookmark data.

```env
CLIP_RETENTION_DAYS=365
```

- **Type**: Integer
- **Default**: 365
- **Range**: 7-3650
- **Notes**: Clips marked as highlights are never auto-deleted
- **Cleanup**: Runs nightly via scheduled job

#### MAX_REELS_PER_COMMUNITY

Maximum number of reels a community can create.

```env
MAX_REELS_PER_COMMUNITY=100
```

- **Type**: Integer
- **Default**: 100
- **Range**: 10-1000
- **Policy**: Enforced at reel creation time

#### MAX_CLIPS_PER_REEL

Maximum number of clips per reel.

```env
MAX_CLIPS_PER_REEL=50
```

- **Type**: Integer
- **Default**: 50
- **Range**: 2-500
- **Policy**: Enforced at reel creation time

### Performance & Caching

#### CACHE_TTL_SECONDS

Time-to-live for cached clip queries.

```env
CACHE_TTL_SECONDS=300
```

- **Type**: Integer (seconds)
- **Default**: 300
- **Range**: 60-3600
- **Applied To**: Clip list queries, overlay data
- **Note**: Higher values reduce DB load but may return stale data

#### ENABLE_QUERY_CACHE

Enable/disable Redis caching for read operations.

```env
ENABLE_QUERY_CACHE=true
```

- **Type**: Boolean
- **Default**: true
- **Note**: Requires REDIS_URL to be configured

#### REQUEST_TIMEOUT_SECONDS

HTTP request timeout for external service calls.

```env
REQUEST_TIMEOUT_SECONDS=30
```

- **Type**: Integer (seconds)
- **Default**: 30
- **Range**: 5-120
- **Note**: Individual service timeouts may override this

### Development Settings

#### DEBUG_MODE

Enable debug mode (verbose logging, no minification).

```env
DEBUG_MODE=false
```

- **Type**: Boolean
- **Default**: false
- **Warning**: Never enable in production

#### ENABLE_SWAGGER_UI

Enable interactive API documentation at /docs.

```env
ENABLE_SWAGGER_UI=true
```

- **Type**: Boolean
- **Default**: true
- **Note**: Disable in production for security

#### PROXY_HEADER_TRUST_LEVEL

Trust level for X-Forwarded-* headers.

```env
PROXY_HEADER_TRUST_LEVEL=2
```

- **Type**: Integer
- **Options**:
  - 0: Disabled (direct requests only)
  - 1: Single proxy hop (local LB)
  - 2: Multiple hops (CDN + LB)
- **Default**: 2
- **Used For**: Getting real client IP, detecting HTTPS

## Configuration Examples

### Local Development

```env
# Local Development (.env)
MODULE_PORT=8098
LOG_LEVEL=DEBUG
DEBUG_MODE=true
ENABLE_SWAGGER_UI=true

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/waddlebot_dev
REDIS_URL=redis://localhost:6379/1

CORE_API_URL=http://localhost:8000
ROUTER_API_URL=http://localhost:8001
TWITCH_MODULE_URL=http://localhost:8010

SECRET_KEY=dev-secret-key-at-least-32-characters-long
CACHE_TTL_SECONDS=60
CLIP_RETENTION_DAYS=7
```

### Docker Compose Development

```yaml
# docker-compose.yml excerpt (service name: interactive-clip)
services:
  interactive-clip:
    image: waddlebot-clip-interaction:latest
    ports:
      - "8098:8098"
    environment:
      MODULE_PORT: 8098
      LOG_LEVEL: INFO
      DATABASE_URL: postgresql://postgres:postgres@db:5432/waddlebot
      REDIS_URL: redis://redis:6379/1
      CORE_API_URL: http://core-api:8000
      ROUTER_API_URL: http://router:8001
      TWITCH_MODULE_URL: http://action-twitch:8010
      SECRET_KEY: ${SECRET_KEY:-dev-key-change-in-production}
    depends_on:
      - db
      - redis
```

### Production Deployment

```env
# Production (.env)
MODULE_PORT=8098
LOG_LEVEL=INFO
DEBUG_MODE=false
ENABLE_SWAGGER_UI=false

DATABASE_URL=postgresql://clip_user:${DB_PASSWORD}@db.prod.internal:5432/waddlebot
REDIS_URL=redis://:${REDIS_PASSWORD}@redis.prod.internal:6379/1

CORE_API_URL=http://core-api.internal:8000
ROUTER_API_URL=http://router.internal:8001
TWITCH_MODULE_URL=http://action-twitch.internal:8010

CORS_ORIGINS=https://admin.waddlebot.io,https://waddlebot.io
SECRET_KEY=${PRODUCTION_SECRET_KEY}
CACHE_TTL_SECONDS=600
CLIP_RETENTION_DAYS=365
MAX_REELS_PER_COMMUNITY=200
PROXY_HEADER_TRUST_LEVEL=2
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: clip-interaction-config
  namespace: waddlebot
data:
  MODULE_PORT: "8098"
  LOG_LEVEL: "INFO"
  DEBUG_MODE: "false"
  ENABLE_SWAGGER_UI: "false"
  CACHE_TTL_SECONDS: "600"
  CLIP_RETENTION_DAYS: "365"
  CORE_API_URL: "http://core-api:8000"
  ROUTER_API_URL: "http://router:8001"
  TWITCH_MODULE_URL: "http://action-twitch:8010"
---
apiVersion: v1
kind: Secret
metadata:
  name: clip-interaction-secrets
  namespace: waddlebot
type: Opaque
stringData:
  DATABASE_URL: postgresql://user:pass@db:5432/waddlebot
  REDIS_URL: redis://:password@redis:6379/1
  SECRET_KEY: your-production-secret-key-here
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: clip-interaction
  namespace: waddlebot
spec:
  template:
    spec:
      containers:
      - name: clip-interaction
        image: clip-interaction:v1.0.0
        ports:
        - containerPort: 8098
        envFrom:
        - configMapRef:
            name: clip-interaction-config
        - secretRef:
            name: clip-interaction-secrets
```

## Validation & Startup Checks

The module performs the following validation on startup:

| Check | Requirement | Failure Behavior |
|-------|-------------|------------------|
| PORT availability | Port must be free | Fatal error |
| DATABASE_URL format | Valid PostgreSQL URI | Fatal error |
| Database connection | Successful connection | Fatal error |
| REDIS_URL (if set) | Valid Redis URI | Warning, cache disabled |
| SERVICE URLs | Reachable in 30 seconds | Warning, retry at runtime |
| SECRET_KEY | Min 32 chars or generate | Generate if missing |

View startup logs:

```bash
docker logs waddlebot-clip-interaction 2>&1 | grep -E "Starting|Error|Config"
```

## Secrets Management

### Best Practices

1. **Never commit secrets** to version control
2. **Use secret management** (Vault, AWS Secrets Manager, K8s Secrets)
3. **Rotate secrets** on schedule (quarterly minimum)
4. **Audit access** to production secrets
5. **Different values** per environment (dev/staging/prod)

### Loading from Files

For Docker deployments, mount secret files and reference them:

```bash
#!/bin/bash
export DATABASE_URL=$(cat /run/secrets/db_url)
export REDIS_URL=$(cat /run/secrets/redis_url)
export SECRET_KEY=$(cat /run/secrets/secret_key)
hypercorn app.py --bind 0.0.0.0:8098
```

### Docker Secrets (Swarm)

```bash
# Create secrets
echo "postgresql://user:pass@db:5432/waddlebot" | docker secret create db_url -
echo "redis://:password@redis:6379/1" | docker secret create redis_url -
echo "production-secret-key-here" | docker secret create secret_key -

# Use in service
docker service create --secret db_url --secret redis_url --secret secret_key \
  clip-interaction:latest
```

## Configuration Validation

Validate configuration before deployment:

```bash
#!/bin/bash
# Validate required vars
required_vars=("MODULE_PORT" "DATABASE_URL" "CORE_API_URL" "ROUTER_API_URL" "TWITCH_MODULE_URL")

for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: Missing required variable: $var"
    exit 1
  fi
done

# Validate URLs
for var in "CORE_API_URL" "ROUTER_API_URL" "TWITCH_MODULE_URL"; do
  if ! [[ "${!var}" =~ ^http ]]; then
    echo "ERROR: $var must be a valid HTTP URL"
    exit 1
  fi
done

echo "All configuration valid"
```

## Hot Reload

Configuration changes that do NOT require restart:

- `LOG_LEVEL` (affects new requests)
- `CACHE_TTL_SECONDS` (affects cache behavior)

Configuration changes that REQUIRE restart:

- `DATABASE_URL` (connection pool)
- `REDIS_URL` (cache backend)
- Any service URL change
- `SECRET_KEY` (session validation)

## Troubleshooting Configuration

### Connection Refused

```
Error: Failed to connect to database
```

**Check**:

```bash
# Verify database is running
psql -h localhost -U postgres -d waddlebot_dev

# Verify connection string
echo $DATABASE_URL

# Check firewall
nc -zv db.host 5432
```

### Redis Connection Issues

```
Error: Connection refused (redis)
```

**Check**:

```bash
# Verify Redis is running
redis-cli ping

# Verify connection string
echo $REDIS_URL

# Check Redis port
netstat -tlnp | grep 6379
```

### Service Not Found

```
Error: Failed to reach core-api
```

**Check**:

```bash
# Verify service URL
curl -v $CORE_API_URL/health

# Check DNS
nslookup core-api

# Check network connectivity
ping core-api
```
