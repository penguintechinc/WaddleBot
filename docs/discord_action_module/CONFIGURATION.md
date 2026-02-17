# Discord Action Module - Configuration

## Overview

The Discord Action Module uses environment variables for configuration, with optional fallback to database-stored credentials. All settings are centralized in the `config.py` file and loaded at startup.

## Environment Variables

### Discord API Configuration

#### DISCORD_BOT_TOKEN
**Type:** String  
**Required:** Yes (for production use)  
**Default:** "" (empty)  
**Description:** Discord Bot token for authentication with Discord API

```bash
export DISCORD_BOT_TOKEN="your-bot-token-here"
```

Get from Discord Developer Portal:
1. Go to https://discord.com/developers/applications
2. Select your application
3. Go to "Bot" section
4. Copy the token under TOKEN

#### DISCORD_API_VERSION
**Type:** String  
**Default:** "10"  
**Description:** Discord API version to use

```bash
export DISCORD_API_VERSION="10"
```

Do not change unless Discord releases new API versions and module needs updating.

### Database Configuration

#### DATABASE_URL
**Type:** String  
**Required:** Yes  
**Default:** "postgresql://user:pass@localhost:5432/waddlebot"  
**Description:** PostgreSQL connection string

```bash
# Format: postgresql://username:password@host:port/database
export DATABASE_URL="postgresql://waddlebot:password@postgres:5432/waddlebot"
```

Supports:
- Standard PostgreSQL URLs
- Unix socket connections
- Connection parameters (sslmode, etc.)

The module converts postgresql:// to postgres:// for PyDAL compatibility.

#### REDIS_URL
**Type:** String  
**Default:** "" (empty, optional)  
**Description:** Redis connection for credential refresh notifications

```bash
export REDIS_URL="redis://localhost:6379/0"
```

If set, module listens for credential refresh events on channel:
`credentials:discord:bot:refreshed`

### Server Configuration

#### HOST
**Type:** String  
**Default:** "0.0.0.0"  
**Description:** Server bind address

```bash
export HOST="0.0.0.0"  # Listen on all interfaces
```

#### GRPC_PORT
**Type:** Integer  
**Default:** 50051  
**Valid Range:** 1-65535  
**Description:** gRPC server port

```bash
export GRPC_PORT="50051"
```

Used for processor/router communication via gRPC protocol.

#### REST_PORT
**Type:** Integer  
**Default:** 8070  
**Valid Range:** 1-65535  
**Description:** REST API server port

```bash
export REST_PORT="8070"
```

Used for third-party integrations via HTTP REST API.

### Security Configuration

#### MODULE_SECRET_KEY
**Type:** String  
**Required:** Yes (for production)  
**Minimum Length:** 64 characters  
**Default:** "change_me_in_production_64_char_key_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  
**Description:** Secret key for JWT signing

```bash
# Generate a secure 64+ character key
export MODULE_SECRET_KEY="$(openssl rand -hex 32)"
```

WARNING: Change this in production! Use strong, random key.

Generate secure key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

#### JWT_ALGORITHM
**Type:** String  
**Default:** "HS256"  
**Description:** JWT signing algorithm

```bash
export JWT_ALGORITHM="HS256"
```

Do not change unless you know JWT signing algorithms.

#### JWT_EXPIRATION_SECONDS
**Type:** Integer  
**Default:** 3600 (1 hour)  
**Description:** JWT token expiration time in seconds

```bash
export JWT_EXPIRATION_SECONDS="3600"
```

Set higher for longer-lived tokens, lower for tighter security.

### Performance Settings

#### MAX_CONCURRENT_REQUESTS
**Type:** Integer  
**Default:** 100  
**Description:** Maximum concurrent REST API requests

```bash
export MAX_CONCURRENT_REQUESTS="100"
```

Limit based on available resources and Discord API rates.

#### REQUEST_TIMEOUT
**Type:** Integer (seconds)  
**Default:** 30  
**Description:** HTTP request timeout for Discord API calls

```bash
export REQUEST_TIMEOUT="30"
```

Increase if Discord API is slow, decrease for faster timeouts.

### Discord Rate Limiting

#### DISCORD_RATE_LIMIT_GLOBAL
**Type:** Integer  
**Default:** 50 (requests/second)  
**Description:** Global rate limit enforcement

```bash
export DISCORD_RATE_LIMIT_GLOBAL="50"
```

Limits overall requests to Discord API.

#### DISCORD_RATE_LIMIT_PER_CHANNEL
**Type:** Integer  
**Default:** 5 (requests/second)  
**Description:** Per-channel rate limit

```bash
export DISCORD_RATE_LIMIT_PER_CHANNEL="5"
```

Limits requests to individual channels.

### Retry Configuration

#### MAX_RETRIES
**Type:** Integer  
**Default:** 3  
**Description:** Maximum retry attempts for failed requests

```bash
export MAX_RETRIES="3"
```

Number of times to retry Discord API calls on failure.

#### RETRY_DELAY
**Type:** Float (seconds)  
**Default:** 1.0  
**Description:** Initial retry delay

```bash
export RETRY_DELAY="1.0"
```

Delay is multiplied by (attempt + 1) for exponential backoff.

### Logging Configuration

#### LOG_LEVEL
**Type:** String  
**Default:** "INFO"  
**Valid Values:** DEBUG, INFO, WARNING, ERROR, CRITICAL  
**Description:** Logging level

```bash
export LOG_LEVEL="INFO"
```

Set to DEBUG for verbose logging during development.

#### LOG_DIR
**Type:** String (path)  
**Default:** "/var/log/waddlebotlog"  
**Description:** Directory for log files

```bash
export LOG_DIR="/var/log/waddlebotlog"
```

Directory must be writable by the application.

#### ENABLE_SYSLOG
**Type:** Boolean  
**Default:** "false"  
**Valid Values:** "true", "false"  
**Description:** Enable syslog logging

```bash
export ENABLE_SYSLOG="false"  # or "true"
```

Send logs to syslog in addition to file.

#### SYSLOG_HOST
**Type:** String  
**Default:** "localhost"  
**Description:** Syslog server hostname

```bash
export SYSLOG_HOST="localhost"
```

Used if ENABLE_SYSLOG is true.

#### SYSLOG_PORT
**Type:** Integer  
**Default:** 514  
**Description:** Syslog server port

```bash
export SYSLOG_PORT="514"
```

Standard syslog port is 514 (UDP) or 601 (TCP).

#### SYSLOG_FACILITY
**Type:** String  
**Default:** "LOCAL0"  
**Valid Values:** LOCAL0-LOCAL7, USER, DAEMON, etc.  
**Description:** Syslog facility

```bash
export SYSLOG_FACILITY="LOCAL0"
```

### Module Information

#### MODULE_NAME
**Type:** String  
**Default:** "discord_action_module"  
**Description:** Module identifier

```bash
export MODULE_NAME="discord_action_module"
```

Used in logging and health endpoints.

#### MODULE_VERSION
**Type:** String  
**Default:** "1.0.0"  
**Description:** Module version

```bash
export MODULE_VERSION="1.0.0"
```

Returned in health check endpoint.

## Example .env File

Create a `.env` file with all required settings:

```bash
# Discord Configuration
DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN

# Database
DATABASE_URL=postgresql://waddlebot:secure_password@postgres:5432/waddlebot

# Server
HOST=0.0.0.0
GRPC_PORT=50051
REST_PORT=8070

# Security
MODULE_SECRET_KEY=e8c3d4e7c1a9b2f5e8c3d4e7c1a9b2f5e8c3d4e7c1a9b2f5e8c3d4e7c1a9b2f5

# Performance
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30

# Rate Limiting
DISCORD_RATE_LIMIT_GLOBAL=50
DISCORD_RATE_LIMIT_PER_CHANNEL=5

# Retries
MAX_RETRIES=3
RETRY_DELAY=1.0

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false

# Module Info
MODULE_VERSION=1.0.0
```

## Loading Configuration

### Priority Order

1. Environment variables (highest priority)
2. .env file in working directory
3. default values in config.py (lowest priority)

### Docker Compose

Pass environment variables via docker-compose.yml:

```yaml
services:
  discord_action_module:
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - DATABASE_URL=${DATABASE_URL}
      - GRPC_PORT=50051
      - REST_PORT=8070
      - MODULE_SECRET_KEY=${MODULE_SECRET_KEY}
```

### Kubernetes

Use Secrets for sensitive values:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: discord-secrets
type: Opaque
stringData:
  DISCORD_BOT_TOKEN: your-token-here
  MODULE_SECRET_KEY: your-secret-key-here
  DATABASE_URL: postgresql://...
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: discord-action-module
spec:
  template:
    spec:
      containers:
      - name: discord-action-module
        env:
        - name: DISCORD_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: discord-secrets
              key: DISCORD_BOT_TOKEN
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: discord-secrets
              key: DATABASE_URL
```

## Credential Management

### Option 1: Environment Variables (Default)

Set DISCORD_BOT_TOKEN as environment variable:

```bash
export DISCORD_BOT_TOKEN="your-token"
```

Simplest, but less flexible for credential rotation.

### Option 2: Database Storage

Store credentials in `platform_integrations` table:

```sql
INSERT INTO platform_integrations 
  (platform, integration_type, access_token, is_active, created_at)
VALUES 
  ('discord', 'bot', 'bot-token-here', true, NOW());
```

Module loads from database on startup via `Config.load_credentials_from_db()`.

### Option 3: Redis Pub/Sub (Dynamic Updates)

If REDIS_URL is configured, module listens for credential updates:

```bash
# In another process/service
REDIS_URL="redis://localhost:6379"
redis-cli PUBLISH credentials:discord:bot:refreshed "update"
```

Module reloads credentials without restart.

## Validation

Configuration is validated on startup. Errors stop the application:

```bash
docker-compose logs
# Configuration errors: DATABASE_URL is required
```

Warnings are logged but don't stop application:

```
WARNING DISCORD_BOT_TOKEN not configured - Discord API calls will fail
WARNING MODULE_SECRET_KEY less than 64 chars - consider setting for production
```

Run validation:

```python
from config import Config
errors, warnings = Config.validate()
print(f"Errors: {errors}")
print(f"Warnings: {warnings}")
```

## Configuration Summary Endpoint

Get current configuration (without secrets):

```bash
curl http://localhost:8070/health | jq .config
```

Returns:

```json
{
  "module_name": "discord_action_module",
  "module_version": "1.0.0",
  "grpc_port": 50051,
  "rest_port": 8070,
  "database_configured": true,
  "discord_token_configured": true,
  "max_concurrent_requests": 100,
  "request_timeout": 30,
  "log_level": "INFO",
  "credentials_from_db": false
}
```

## Troubleshooting Configuration

**Module won't start:**
- Check DATABASE_URL is valid: `psql $DATABASE_URL`
- Check DISCORD_BOT_TOKEN is valid
- Check logs for validation errors

**API calls fail with 503:**
- Check DISCORD_BOT_TOKEN is set and valid
- Verify bot token in Discord Developer Portal

**Rate limiting issues:**
- Increase DISCORD_RATE_LIMIT_GLOBAL
- Increase DISCORD_RATE_LIMIT_PER_CHANNEL
- Check Discord API status

**Logging not working:**
- Check LOG_DIR is writable: `ls -la /var/log/waddlebotlog`
- Check LOG_LEVEL is valid
- Check disk space: `df -h`

See TROUBLESHOOTING.md for more solutions.
