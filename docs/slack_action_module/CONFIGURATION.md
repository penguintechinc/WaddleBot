# Slack Action Module - Configuration Reference

## Environment Variables

All configuration is loaded from environment variables at startup. Values can be overridden at deployment time.

### Slack API Configuration

#### SLACK_BOT_TOKEN
- **Type**: String (OAuth token)
- **Required**: Yes (for production)
- **Format**: `xoxb-...` (50+ characters)
- **Purpose**: OAuth bot token for Slack workspace API calls
- **How to Get**: See USAGE.md for Slack app setup
- **Example**: `SLACK_BOT_TOKEN=xoxb-YOUR_SLACK_BOT_TOKEN`
- **Notes**:
  - Token expires periodically; refresh from admin hub
  - Can be loaded from environment or database
  - If missing, module logs warning but continues

#### SLACK_APP_TOKEN
- **Type**: String (OAuth token, optional)
- **Required**: No
- **Format**: `xapp-...` (if used)
- **Purpose**: App-level token for socket mode (currently unused)
- **Default**: Empty string
- **Notes**: For future socket mode support

### Server Configuration

#### REST_PORT
- **Type**: Integer
- **Required**: No
- **Default**: `8071`
- **Range**: 1024-65535
- **Purpose**: HTTP REST API server port
- **Example**: `REST_PORT=8071`
- **Notes**: Must not conflict with other services

#### GRPC_PORT
- **Type**: Integer
- **Required**: No
- **Default**: `50052`
- **Range**: 1024-65535
- **Purpose**: gRPC server port for receiving tasks from router
- **Example**: `GRPC_PORT=50052`
- **Notes**: Must be unique across action modules

#### GRPC_MAX_WORKERS
- **Type**: Integer
- **Required**: No
- **Default**: `10`
- **Range**: 1-100
- **Purpose**: Maximum number of gRPC worker threads
- **Example**: `GRPC_MAX_WORKERS=20`
- **Notes**: Higher = more concurrent gRPC requests, uses more memory

### Database Configuration

#### DATABASE_URL
- **Type**: String (PostgreSQL connection string)
- **Required**: Yes
- **Format**: `postgresql://user:password@host:port/database`
- **Purpose**: Connection string for PostgreSQL database
- **Example**: `DATABASE_URL=postgresql://mod_action_slack:changeme@postgres:5432/waddlebot`
- **Notes**:
  - Automatically converts `postgresql://` to `postgres://` for PyDAL
  - Credentials should be non-root user with limited permissions
  - Pool size: 10 connections default

#### REDIS_URL
- **Type**: String (Redis connection URL, optional)
- **Required**: No
- **Default**: Empty string
- **Format**: `redis://[user:password@]host:port[/database]`
- **Purpose**: Redis connection for credential refresh notifications
- **Example**: `REDIS_URL=redis://redis:6379/0`
- **Notes**:
  - If set, enables credential refresh listener
  - Watches channel: `credentials:slack:bot:refreshed`
  - If not set, no automatic credential refresh

### Security Configuration

#### MODULE_SECRET_KEY
- **Type**: String (cryptographic key)
- **Required**: Yes (for production)
- **Minimum Length**: 32 characters
- **Purpose**: Secret key for JWT token signing/verification
- **Example**: `MODULE_SECRET_KEY=your-super-secret-key-change-this-in-production`
- **Notes**:
  - Must be same across all instances (shared secret)
  - **NEVER** log or expose this value
  - Generate with: `openssl rand -base64 32`
  - If missing, module logs warning but continues

#### JWT_ALGORITHM
- **Type**: String (constant)
- **Required**: No (hardcoded)
- **Default**: `HS256`
- **Options**: HS256 only (HMAC SHA256)
- **Purpose**: Algorithm for JWT token signing
- **Notes**: Currently hardcoded, not configurable

#### JWT_EXPIRY_SECONDS
- **Type**: Integer (constant)
- **Required**: No (hardcoded)
- **Default**: `3600`
- **Range**: 300-86400 (5 minutes to 24 hours)
- **Purpose**: JWT token expiration time in seconds
- **Notes**: Currently hardcoded, modify in source code if needed

### Performance Configuration

#### MAX_CONCURRENT_REQUESTS
- **Type**: Integer
- **Required**: No
- **Default**: `100`
- **Range**: 10-10000
- **Purpose**: Maximum concurrent HTTP requests allowed
- **Example**: `MAX_CONCURRENT_REQUESTS=200`
- **Notes**: Acts as circuit breaker; requests above limit get 429 Too Many Requests

#### REQUEST_TIMEOUT
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `30`
- **Range**: 5-300
- **Purpose**: HTTP request timeout in seconds
- **Example**: `REQUEST_TIMEOUT=45`
- **Notes**: Slack API calls timing out are retried

### Logging Configuration

#### LOG_LEVEL
- **Type**: String
- **Required**: No
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Purpose**: Logging verbosity level
- **Example**: `LOG_LEVEL=DEBUG`
- **Notes**:
  - DEBUG: Verbose, includes request/response payloads
  - INFO: General operation messages (recommended)
  - WARNING: Alert for potential issues
  - ERROR: Only error messages
  - CRITICAL: Only critical failures

#### LOG_DIR
- **Type**: String (file path)
- **Required**: No
- **Default**: `/var/log/waddlebotlog`
- **Purpose**: Directory for rotating log files
- **Example**: `LOG_DIR=/var/log/slack-action`
- **Notes**:
  - Directory must exist or be creatable by container user
  - Files: `slack_action.log` (main) + rotated backups
  - Rotation: 10MB per file, 5 backups kept

#### ENABLE_SYSLOG
- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Options**: `true`, `false`
- **Purpose**: Enable syslog integration
- **Example**: `ENABLE_SYSLOG=true`
- **Notes**: If true, also configure SYSLOG_HOST, SYSLOG_PORT, SYSLOG_FACILITY

#### SYSLOG_HOST
- **Type**: String (hostname)
- **Required**: No (only if ENABLE_SYSLOG=true)
- **Default**: `localhost`
- **Purpose**: Syslog server hostname
- **Example**: `SYSLOG_HOST=syslog.example.com`

#### SYSLOG_PORT
- **Type**: Integer
- **Required**: No (only if ENABLE_SYSLOG=true)
- **Default**: `514`
- **Range**: 1-65535
- **Purpose**: Syslog server port
- **Example**: `SYSLOG_PORT=514`

#### SYSLOG_FACILITY
- **Type**: String (facility code)
- **Required**: No (only if ENABLE_SYSLOG=true)
- **Default**: `LOCAL0`
- **Options**: `LOCAL0` through `LOCAL7`, `USER`, `DAEMON`, etc.
- **Purpose**: Syslog facility for categorizing logs
- **Example**: `SYSLOG_FACILITY=LOCAL3`

### Module Information (Read-only)

#### MODULE_NAME
- **Type**: String (constant)
- **Value**: `slack_action_module`
- **Purpose**: Identifies module in logs and responses
- **Notes**: Set in code, not configurable

#### MODULE_VERSION
- **Type**: String (constant)
- **Value**: `1.0.0`
- **Purpose**: Module version for compatibility checks
- **Notes**: Set in code, not configurable

## Example .env File

```bash
# ============================================================
# Slack Action Module - Environment Configuration
# ============================================================

# Slack API Credentials
SLACK_BOT_TOKEN=xoxb-YOUR_SLACK_BOT_TOKEN
SLACK_APP_TOKEN=

# Server Ports
REST_PORT=8071
GRPC_PORT=50052
GRPC_MAX_WORKERS=10

# Database
DATABASE_URL=postgresql://mod_action_slack:secure_password_here@postgres:5432/waddlebot
REDIS_URL=redis://redis:6379/0

# Security
MODULE_SECRET_KEY=your-super-secret-key-with-at-least-32-characters-here
# Generate with: openssl rand -base64 32

# Performance
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false
SYSLOG_HOST=localhost
SYSLOG_PORT=514
SYSLOG_FACILITY=LOCAL0
```

## Environment Variable Loading Order

1. **Default values** (in source code)
2. **Environment variables** (from system/shell/docker)
3. **Database credentials** (loaded on startup if configured)
4. **Runtime validation** (on app startup)

Example priority:

```
SLACK_BOT_TOKEN loaded from:
  1. First, environment variable SLACK_BOT_TOKEN (if set)
  2. Then, database platform_integrations table (if DB accessible)
  3. If neither, use empty string (warning logged)
```

## Docker Compose Configuration Example

```yaml
version: '3.8'

services:
  slack-action-module:
    image: waddlebot/slack-action-module:1.0.0
    container_name: slack-action-module
    ports:
      - "8071:8071"
      - "50052:50052"
    environment:
      # Slack
      SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN}

      # Ports
      REST_PORT: 8071
      GRPC_PORT: 50052
      GRPC_MAX_WORKERS: 10

      # Database
      DATABASE_URL: postgresql://mod_action_slack:${DB_PASSWORD}@postgres:5432/waddlebot
      REDIS_URL: redis://redis:6379/0

      # Security
      MODULE_SECRET_KEY: ${MODULE_SECRET_KEY}

      # Performance
      MAX_CONCURRENT_REQUESTS: 100
      REQUEST_TIMEOUT: 30

      # Logging
      LOG_LEVEL: INFO
      LOG_DIR: /var/log/waddlebotlog
      ENABLE_SYSLOG: "false"

    depends_on:
      - postgres
      - redis
    networks:
      - waddlebot
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8071/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    volumes:
      - logs:/var/log/waddlebotlog

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: waddlebot
      POSTGRES_USER: mod_action_slack
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    networks:
      - waddlebot

  redis:
    image: redis:7
    networks:
      - waddlebot

volumes:
  logs:

networks:
  waddlebot:
    driver: bridge
```

## Environment Variables File (.env.example)

Create `.env` from `.env.example`:

```bash
cp .env.example .env
# Edit .env with actual values
```

## Configuration Validation

On startup, the module validates:

```python
errors = []
warnings = []

# Required checks
if not DATABASE_URL:
    errors.append("DATABASE_URL is required")

# Warning checks
if not SLACK_BOT_TOKEN:
    warnings.append("SLACK_BOT_TOKEN not configured")

if not MODULE_SECRET_KEY:
    warnings.append("MODULE_SECRET_KEY not configured")

# Exit if critical errors
if errors:
    logger.error(f"Configuration errors: {', '.join(errors)}")
    sys.exit(1)

# Log warnings but continue
for warning in warnings:
    logger.warning(warning)
```

## Credential Refresh

The module supports dynamic credential refresh:

### Via Environment Variable
1. Change `SLACK_BOT_TOKEN` in deployment system
2. Restart container
3. New token loaded automatically

### Via Database
1. Update `platform_integrations` table:
   ```sql
   UPDATE platform_integrations
   SET access_token = 'xoxb-new-token'
   WHERE platform = 'slack'
   AND integration_type = 'bot'
   AND is_active = TRUE;
   ```
2. Publish to Redis (if enabled):
   ```bash
   redis-cli PUBLISH credentials:slack:bot:refreshed '{"timestamp": 1234567890}'
   ```
3. Module automatically reloads token (no restart needed)

### Token Refresh Best Practices
- Rotate tokens monthly minimum
- Store old tokens briefly for gradual rollover
- Monitor for invalid_auth errors (indicates stale token)
- Implement token refresh before expiration in admin hub

## Performance Tuning

### For High Throughput
```bash
# Increase workers and requests
GRPC_MAX_WORKERS=50
MAX_CONCURRENT_REQUESTS=500
REQUEST_TIMEOUT=60
```

### For Resource-Constrained Environments
```bash
# Reduce workers and memory usage
GRPC_MAX_WORKERS=5
MAX_CONCURRENT_REQUESTS=50
REQUEST_TIMEOUT=15
LOG_LEVEL=WARNING
```

### For Debugging
```bash
# Verbose logging
LOG_LEVEL=DEBUG
SYSLOG_HOST=localhost
SYSLOG_PORT=514
ENABLE_SYSLOG=true
```
