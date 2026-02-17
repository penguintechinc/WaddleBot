# YouTube Action Module - Configuration Reference

## Environment Variables

All configuration is loaded from environment variables at startup.

### OAuth Configuration

#### YOUTUBE_CLIENT_ID
- **Type**: String
- **Required**: Yes (for production)
- **Format**: `*.apps.googleusercontent.com`
- **Purpose**: OAuth 2.0 client ID from Google Cloud Console
- **Example**: `YOUTUBE_CLIENT_ID=123456789.apps.googleusercontent.com`
- **Where to Get**: https://console.cloud.google.com → Credentials → OAuth Client ID
- **Notes**:
  - Must have YouTube Data API v3 enabled
  - Can be loaded from environment or database

#### YOUTUBE_CLIENT_SECRET
- **Type**: String
- **Required**: Yes (for production)
- **Format**: Random alphanumeric string
- **Purpose**: OAuth 2.0 client secret
- **Example**: `YOUTUBE_CLIENT_SECRET=your-secret-here`
- **Where to Get**: https://console.cloud.google.com → Credentials → OAuth Client ID
- **Notes**:
  - **NEVER** commit to version control
  - **NEVER** log this value
  - Store in secure secret manager

#### YOUTUBE_REDIRECT_URI
- **Type**: String (URL)
- **Required**: No
- **Default**: `http://localhost:8073/oauth/callback`
- **Purpose**: OAuth callback URL for authorization code flow
- **Example**: `YOUTUBE_REDIRECT_URI=https://yourdomain.com/oauth/callback`
- **Notes**:
  - Must match exactly in Google Cloud Console
  - Must be HTTPS in production
  - Can be multiple URIs in Google Cloud

#### YOUTUBE_API_VERSION
- **Type**: String (constant)
- **Required**: No
- **Default**: `v3`
- **Purpose**: YouTube Data API version
- **Notes**: Hardcoded, not normally changed

### Server Configuration

#### REST_PORT
- **Type**: Integer
- **Required**: No
- **Default**: `8073`
- **Range**: 1024-65535
- **Purpose**: HTTP REST API server port
- **Example**: `REST_PORT=8073`

#### GRPC_PORT
- **Type**: Integer
- **Required**: No
- **Default**: `50054`
- **Range**: 1024-65535
- **Purpose**: gRPC server port
- **Example**: `GRPC_PORT=50054`

### Database Configuration

#### DATABASE_URL
- **Type**: String (PostgreSQL connection)
- **Required**: Yes
- **Format**: `postgresql://user:password@host:port/database`
- **Purpose**: PostgreSQL connection string
- **Example**: `DATABASE_URL=postgresql://mod_action_youtube:changeme@postgres:5432/waddlebot`
- **Notes**:
  - Automatically converts `postgresql://` to `postgres://` for PyDAL
  - Should use non-root user
  - Pool size: 10 connections default

#### REDIS_URL
- **Type**: String (Redis connection, optional)
- **Required**: No
- **Default**: Empty string
- **Format**: `redis://[user:password@]host:port[/database]`
- **Purpose**: Redis for credential refresh notifications
- **Example**: `REDIS_URL=redis://redis:6379/0`

### Security Configuration

#### MODULE_SECRET_KEY
- **Type**: String (cryptographic key)
- **Required**: Yes (for production)
- **Minimum Length**: 32 characters
- **Default**: `youtube_action_secret_key_change_me_in_production`
- **Purpose**: Secret for JWT token signing/verification
- **Example**: `MODULE_SECRET_KEY=your-super-secret-key-change-this`
- **Notes**:
  - Must be same across all instances
  - Generate with: `openssl rand -base64 32`
  - Default value triggers warning in logs

### Performance Configuration

#### MAX_WORKERS
- **Type**: Integer
- **Required**: No
- **Default**: `20`
- **Range**: 1-100
- **Purpose**: Maximum concurrent worker threads
- **Example**: `MAX_WORKERS=50`

#### REQUEST_TIMEOUT
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `30`
- **Range**: 5-300
- **Purpose**: HTTP request timeout
- **Example**: `REQUEST_TIMEOUT=45`

#### MAX_RETRIES
- **Type**: Integer
- **Required**: No
- **Default**: `3`
- **Range**: 1-10
- **Purpose**: Maximum retry attempts for failed requests
- **Example**: `MAX_RETRIES=5`

#### RATE_LIMIT_REQUESTS
- **Type**: Integer
- **Required**: No
- **Default**: `100`
- **Range**: 10-10000
- **Purpose**: Max requests per rate limit window
- **Example**: `RATE_LIMIT_REQUESTS=200`

#### RATE_LIMIT_WINDOW
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `60`
- **Range**: 10-3600
- **Purpose**: Rate limit window in seconds
- **Example**: `RATE_LIMIT_WINDOW=60`

### Feature Flags

#### ENABLE_CHAT_ACTIONS
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Purpose**: Enable live chat operations
- **Example**: `ENABLE_CHAT_ACTIONS=true`

#### ENABLE_VIDEO_ACTIONS
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Purpose**: Enable video metadata operations
- **Example**: `ENABLE_VIDEO_ACTIONS=true`

#### ENABLE_PLAYLIST_ACTIONS
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Purpose**: Enable playlist operations
- **Example**: `ENABLE_PLAYLIST_ACTIONS=true`

#### ENABLE_BROADCAST_ACTIONS
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Purpose**: Enable broadcast control operations
- **Example**: `ENABLE_BROADCAST_ACTIONS=true`

#### ENABLE_COMMENT_ACTIONS
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Purpose**: Enable comment operations
- **Example**: `ENABLE_COMMENT_ACTIONS=true`

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
- **Purpose**: Directory for log files
- **Example**: `LOG_DIR=/var/log/youtube-action`

#### ENABLE_SYSLOG
- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Purpose**: Enable syslog integration
- **Example**: `ENABLE_SYSLOG=true`

#### SYSLOG_HOST
- **Type**: String
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

## Example .env File

```bash
# ============================================================
# YouTube Action Module - Environment Configuration
# ============================================================

# YouTube OAuth Configuration
YOUTUBE_CLIENT_ID=123456789.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-secret-here
YOUTUBE_REDIRECT_URI=http://localhost:8073/oauth/callback
YOUTUBE_API_VERSION=v3

# Server Ports
REST_PORT=8073
GRPC_PORT=50054

# Database
DATABASE_URL=postgresql://mod_action_youtube:secure_password_here@postgres:5432/waddlebot
REDIS_URL=redis://redis:6379/0

# Security
MODULE_SECRET_KEY=your-super-secret-key-with-at-least-32-characters-here

# Performance
MAX_WORKERS=20
REQUEST_TIMEOUT=30
MAX_RETRIES=3
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Feature Flags
ENABLE_CHAT_ACTIONS=true
ENABLE_VIDEO_ACTIONS=true
ENABLE_PLAYLIST_ACTIONS=true
ENABLE_BROADCAST_ACTIONS=true
ENABLE_COMMENT_ACTIONS=true

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
  youtube-action-module:
    image: waddlebot/youtube-action-module:1.0.0
    container_name: youtube-action-module
    ports:
      - "8073:8073"
      - "50054:50054"
    environment:
      # YouTube OAuth
      YOUTUBE_CLIENT_ID: ${YOUTUBE_CLIENT_ID}
      YOUTUBE_CLIENT_SECRET: ${YOUTUBE_CLIENT_SECRET}
      YOUTUBE_REDIRECT_URI: http://localhost:8073/oauth/callback

      # Ports
      REST_PORT: 8073
      GRPC_PORT: 50054

      # Database
      DATABASE_URL: postgresql://mod_action_youtube:${DB_PASSWORD}@postgres:5432/waddlebot
      REDIS_URL: redis://redis:6379/0

      # Security
      MODULE_SECRET_KEY: ${MODULE_SECRET_KEY}

      # Performance
      MAX_WORKERS: 20
      REQUEST_TIMEOUT: 30
      MAX_RETRIES: 3
      RATE_LIMIT_REQUESTS: 100
      RATE_LIMIT_WINDOW: 60

      # Features
      ENABLE_CHAT_ACTIONS: "true"
      ENABLE_VIDEO_ACTIONS: "true"
      ENABLE_PLAYLIST_ACTIONS: "true"
      ENABLE_BROADCAST_ACTIONS: "true"
      ENABLE_COMMENT_ACTIONS: "true"

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
      test: ["CMD", "curl", "-f", "http://localhost:8073/health"]
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
      POSTGRES_USER: mod_action_youtube
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
if not YOUTUBE_CLIENT_ID:
    warnings.append("YOUTUBE_CLIENT_ID not configured")

if not YOUTUBE_CLIENT_SECRET:
    warnings.append("YOUTUBE_CLIENT_SECRET not configured")

if MODULE_SECRET_KEY == "youtube_action_secret_key_change_me_in_production":
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

### High Throughput
```bash
MAX_WORKERS=50
REQUEST_TIMEOUT=60
MAX_RETRIES=5
RATE_LIMIT_REQUESTS=500
```

### Low Resource Usage
```bash
MAX_WORKERS=5
REQUEST_TIMEOUT=15
MAX_RETRIES=1
RATE_LIMIT_REQUESTS=50
LOG_LEVEL=WARNING
```

### Debugging
```bash
LOG_LEVEL=DEBUG
ENABLE_SYSLOG=true
SYSLOG_HOST=localhost
```
