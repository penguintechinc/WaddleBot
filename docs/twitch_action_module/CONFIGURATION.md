# Twitch Action Module - Configuration Reference

## Environment Variables

All configuration is loaded from environment variables at startup.

### Twitch API Configuration

#### TWITCH_CLIENT_ID
- **Type**: String
- **Required**: Yes (for production)
- **Format**: Alphanumeric string
- **Purpose**: Twitch application client ID
- **Example**: `TWITCH_CLIENT_ID=your-client-id-here`
- **Where to Get**: https://dev.twitch.tv/console/apps → Your App → Client ID
- **Notes**:
  - Can be loaded from environment or database
  - If missing, module logs warning but continues

#### TWITCH_CLIENT_SECRET
- **Type**: String
- **Required**: Yes (for production)
- **Format**: Random alphanumeric string
- **Purpose**: Twitch application secret for OAuth
- **Example**: `TWITCH_CLIENT_SECRET=your-secret-here`
- **Where to Get**: https://dev.twitch.tv/console/apps → Your App → Client Secret
- **Notes**:
  - **NEVER** commit to version control
  - **NEVER** log this value
  - Store in secure secret manager
  - Can be rotated at https://dev.twitch.tv/console/apps

#### TWITCH_API_BASE_URL
- **Type**: String (constant)
- **Required**: No
- **Default**: `https://api.twitch.tv/helix`
- **Purpose**: Base URL for Twitch Helix API
- **Notes**: Hardcoded in source, not normally changed

### Server Configuration

#### REST_PORT
- **Type**: Integer
- **Required**: No
- **Default**: `8072`
- **Range**: 1024-65535
- **Purpose**: HTTP REST API server port
- **Example**: `REST_PORT=8072`
- **Notes**: Must not conflict with other services

#### GRPC_PORT
- **Type**: Integer
- **Required**: No
- **Default**: `50053`
- **Range**: 1024-65535
- **Purpose**: gRPC server port for receiving tasks
- **Example**: `GRPC_PORT=50053`
- **Notes**: Must be unique across action modules

#### MODULE_PORT
- **Type**: Integer
- **Required**: No (deprecated)
- **Default**: `8072`
- **Purpose**: Legacy port configuration (use REST_PORT)
- **Notes**: Kept for backward compatibility

### Database Configuration

#### DATABASE_URL
- **Type**: String (PostgreSQL connection string)
- **Required**: Yes
- **Format**: `postgresql://user:password@host:port/database`
- **Purpose**: Connection string for PostgreSQL database
- **Example**: `DATABASE_URL=postgresql://mod_action_twitch:changeme@postgres:5432/waddlebot`
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
  - Watches channel: `credentials:twitch:bot:refreshed`

#### CREDENTIAL_CHANNEL
- **Type**: String (constant)
- **Required**: No
- **Default**: `credentials:twitch:bot:refreshed`
- **Purpose**: Redis channel for credential notifications
- **Notes**: Hardcoded in config, not configurable

### Security Configuration

#### MODULE_SECRET_KEY
- **Type**: String (cryptographic key)
- **Required**: Yes (for production)
- **Minimum Length**: 32 characters
- **Default**: `waddlebot_twitch_action_secret_change_me_in_production`
- **Purpose**: Secret key for JWT token signing/verification
- **Example**: `MODULE_SECRET_KEY=your-super-secret-key-change-this`
- **Notes**:
  - Must be same across all instances
  - **NEVER** log or expose this value
  - Generate with: `openssl rand -base64 32`
  - Default triggers warning in logs

#### JWT_ALGORITHM
- **Type**: String (constant)
- **Required**: No
- **Default**: `HS256`
- **Options**: HS256 only
- **Purpose**: Algorithm for JWT token signing
- **Notes**: Hardcoded, not configurable

#### JWT_EXPIRATION_SECONDS
- **Type**: Integer (constant)
- **Required**: No
- **Default**: `3600`
- **Range**: 300-86400
- **Purpose**: JWT token expiration time in seconds
- **Notes**: Hardcoded, modify in source code if needed

### Performance Configuration

#### MAX_WORKERS
- **Type**: Integer
- **Required**: No
- **Default**: `20`
- **Range**: 1-100
- **Purpose**: Maximum concurrent worker threads
- **Example**: `MAX_WORKERS=50`
- **Notes**: Higher = more memory usage

#### REQUEST_TIMEOUT
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `30`
- **Range**: 5-300
- **Purpose**: HTTP request timeout
- **Example**: `REQUEST_TIMEOUT=45`
- **Notes**: Twitch API calls timing out are retried

#### MAX_BATCH_SIZE
- **Type**: Integer
- **Required**: No
- **Default**: `100`
- **Range**: 1-1000
- **Purpose**: Maximum actions per batch request
- **Example**: `MAX_BATCH_SIZE=200`
- **Notes**: Requests exceeding this get 413 error

#### TOKEN_REFRESH_BUFFER
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `300`
- **Range**: 60-3600
- **Purpose**: Proactive token refresh before expiry
- **Example**: `TOKEN_REFRESH_BUFFER=600`
- **Notes**: Refresh if expires in less than this many seconds

### Logging Configuration

#### LOG_LEVEL
- **Type**: String
- **Required**: No
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Purpose**: Logging verbosity level
- **Example**: `LOG_LEVEL=DEBUG`

#### LOG_DIR
- **Type**: String (file path)
- **Required**: No
- **Default**: `/var/log/waddlebotlog`
- **Purpose**: Directory for rotating log files
- **Example**: `LOG_DIR=/var/log/twitch-action`
- **Notes**:
  - Directory must be creatable by container user
  - Rotation: 10MB per file, 5 backups kept

#### ENABLE_SYSLOG
- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Options**: `true`, `false`
- **Purpose**: Enable syslog integration
- **Example**: `ENABLE_SYSLOG=true`

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
- **Type**: String
- **Required**: No (only if ENABLE_SYSLOG=true)
- **Default**: `LOCAL0`
- **Options**: `LOCAL0` through `LOCAL7`
- **Purpose**: Syslog facility code
- **Example**: `SYSLOG_FACILITY=LOCAL3`

### Module Information (Read-only)

#### MODULE_NAME
- **Type**: String (constant)
- **Value**: `twitch_action_module`
- **Purpose**: Identifies module in logs
- **Notes**: Set in code, not configurable

#### MODULE_VERSION
- **Type**: String (constant)
- **Value**: `1.0.0`
- **Purpose**: Module version
- **Notes**: Set in code, not configurable

## Example .env File

```bash
# ============================================================
# Twitch Action Module - Environment Configuration
# ============================================================

# Twitch API Credentials
TWITCH_CLIENT_ID=your-client-id-here
TWITCH_CLIENT_SECRET=your-secret-here

# Server Ports
REST_PORT=8072
GRPC_PORT=50053

# Database
DATABASE_URL=postgresql://mod_action_twitch:secure_password_here@postgres:5432/waddlebot
REDIS_URL=redis://redis:6379/0

# Security
MODULE_SECRET_KEY=your-super-secret-key-with-at-least-32-characters
# Generate with: openssl rand -base64 32

# Performance
MAX_WORKERS=20
REQUEST_TIMEOUT=30
MAX_BATCH_SIZE=100
TOKEN_REFRESH_BUFFER=300

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false
SYSLOG_HOST=localhost
SYSLOG_PORT=514
SYSLOG_FACILITY=LOCAL0
```

## Docker Compose Configuration Example

```yaml
version: '3.8'

services:
  twitch-action-module:
    image: waddlebot/twitch-action-module:1.0.0
    container_name: twitch-action-module
    ports:
      - "8072:8072"
      - "50053:50053"
    environment:
      # Twitch
      TWITCH_CLIENT_ID: ${TWITCH_CLIENT_ID}
      TWITCH_CLIENT_SECRET: ${TWITCH_CLIENT_SECRET}

      # Ports
      REST_PORT: 8072
      GRPC_PORT: 50053

      # Database
      DATABASE_URL: postgresql://mod_action_twitch:${DB_PASSWORD}@postgres:5432/waddlebot
      REDIS_URL: redis://redis:6379/0

      # Security
      MODULE_SECRET_KEY: ${MODULE_SECRET_KEY}

      # Performance
      MAX_WORKERS: 20
      REQUEST_TIMEOUT: 30
      MAX_BATCH_SIZE: 100
      TOKEN_REFRESH_BUFFER: 300

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
      test: ["CMD", "curl", "-f", "http://localhost:8072/health"]
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
      POSTGRES_USER: mod_action_twitch
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

## Configuration Validation

On startup, the module validates:

```python
errors = []
warnings = []

# Required checks
if not DATABASE_URL:
    errors.append("DATABASE_URL is required")

# Warning checks
if not TWITCH_CLIENT_ID:
    warnings.append("TWITCH_CLIENT_ID not configured")

if not TWITCH_CLIENT_SECRET:
    warnings.append("TWITCH_CLIENT_SECRET not configured")

if MODULE_SECRET_KEY == "waddlebot_twitch_action_secret_change_me_in_production":
    warnings.append("MODULE_SECRET_KEY is default value - change for production")

# Exit if critical errors
if errors:
    logger.error(f"Configuration errors: {errors}")
    sys.exit(1)

# Log warnings but continue
for warning in warnings:
    logger.warning(warning)
```

## Performance Tuning

### For High Throughput
```bash
# Increase workers for more concurrent actions
MAX_WORKERS=50
MAX_BATCH_SIZE=500
REQUEST_TIMEOUT=60
TOKEN_REFRESH_BUFFER=600
```

### For Resource-Constrained Environments
```bash
# Reduce workers and memory
MAX_WORKERS=5
MAX_BATCH_SIZE=50
REQUEST_TIMEOUT=15
LOG_LEVEL=WARNING
```

### For Debugging
```bash
# Verbose logging
LOG_LEVEL=DEBUG
SYSLOG_HOST=localhost
ENABLE_SYSLOG=true
```

## Token Refresh Timing

The `TOKEN_REFRESH_BUFFER` controls when tokens are proactively refreshed:

```
Token Lifetime: 0 -------- 3600 seconds

Default Buffer: 300 seconds (5 minutes)
├─ Refresh at: 3600 - 300 = 3300 seconds
└─ Gives 5 minute buffer before expiry

Large Buffer (600s): Refresh at 3000s
├─ 10 minute buffer before expiry
└─ More proactive, fewer auth errors

Small Buffer (60s): Refresh at 3540s
├─ 1 minute buffer before expiry
└─ Fewer unnecessary refreshes, risk of timeout
```

Recommendation: Keep default 300 seconds for most uses.
