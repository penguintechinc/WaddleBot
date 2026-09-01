# Shoutout Interaction Module — Configuration

## Environment Variables

All configuration is managed through environment variables. The module loads variables in this order:

1. **Runtime Environment** (highest priority)
2. **`.env` file** in module directory
3. **Database** (platform_integrations table, if available)
4. **Hardcoded defaults** (lowest priority)

### Required Variables

These variables MUST be set before the module starts:

#### TWITCH_CLIENT_ID
```
TWITCH_CLIENT_ID=your_twitch_application_client_id
```

Twitch application client ID for Helix API authentication.

- **Type:** String
- **Required:** Yes
- **Where to get:** [Twitch Developer Console](https://dev.twitch.tv/console/apps)
- **Example:** `TWITCH_CLIENT_ID=This15TotallyAnExampleClientId!`

#### TWITCH_CLIENT_SECRET
```
TWITCH_CLIENT_SECRET=your_twitch_application_secret
```

Twitch application secret for OAuth token generation.

- **Type:** String
- **Required:** Yes
- **Where to get:** [Twitch Developer Console](https://dev.twitch.tv/console/apps)
- **Security:** Never commit to version control
- **Example:** `TWITCH_CLIENT_SECRET=abcdefghijklmnopqrstuvwxyz123456`

#### DATABASE_URL
```
DATABASE_URL=postgresql://user:password@host:port/database
```

PostgreSQL connection string for storing shoutout history, templates, and config.

- **Type:** String (connection URL)
- **Required:** Yes
- **Default:** `postgresql://waddlebot:password@localhost:5432/waddlebot`
- **Format:** `postgresql://[user[:password]@][netloc][:port][/dbname]`
- **Example:** `DATABASE_URL=postgresql://waddlebot:securepass@db.penguintech.cloud:5432/waddlebot`

### Optional Variables

#### YOUTUBE_API_KEY
```
YOUTUBE_API_KEY=your_youtube_api_key
```

YouTube Data API key for cross-platform video shoutout fallback.

- **Type:** String
- **Required:** No (video shoutout falls back gracefully if missing)
- **Where to get:** [Google Cloud Console](https://console.cloud.google.com/)
- **Security:** Never commit to version control
- **Note:** Only needed if you want YouTube fallback when Twitch clips unavailable

#### MODULE_PORT
```
MODULE_PORT=8011
```

HTTP port the module listens on.

- **Type:** Integer
- **Default:** `8011`
- **Valid range:** 1024-65535
- **Example:** `MODULE_PORT=8011`

#### IDENTITY_URL
```
IDENTITY_URL=http://identity-core:8050
```

Base URL for identity core service (cross-platform identity resolution).

- **Type:** String (URL)
- **Default:** `http://identity-core:8050`
- **Docker Compose:** `http://identity-core:8050`
- **Local Development:** `http://localhost:8050`
- **Example:** `IDENTITY_URL=http://identity-service.default.svc.cluster.local:8050`

#### CORE_API_URL
```
CORE_API_URL=http://router-service:8000
```

Base URL for core API/router service.

- **Type:** String (URL)
- **Default:** `http://router-service:8000`
- **Used for:** Internal service-to-service communication
- **Example:** `CORE_API_URL=http://api.penguintech.cloud`

#### ROUTER_API_URL
```
ROUTER_API_URL=http://router-service:8000/api/v1/router
```

Full router API endpoint URL.

- **Type:** String (URL)
- **Default:** `http://router-service:8000/api/v1/router`
- **Example:** `ROUTER_API_URL=http://router.svc.cluster.local:8000/api/v1/router`

#### LOG_LEVEL
```
LOG_LEVEL=INFO
```

Logging verbosity level.

- **Type:** String
- **Default:** `INFO`
- **Valid values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Recommendation:** Use `INFO` in production, `DEBUG` during development/troubleshooting
- **Example:** `LOG_LEVEL=DEBUG`

#### SECRET_KEY
```
SECRET_KEY=change-me-in-production
```

Flask secret key for session management (change in production).

- **Type:** String
- **Default:** `change-me-in-production`
- **Security:** MUST change in production
- **Recommendation:** Use cryptographically secure random string
- **Generation:** `python -c "import secrets; print(secrets.token_hex(32))"`

#### REDIS_URL
```
REDIS_URL=redis://localhost:6379
```

Redis connection URL for credential refresh notifications (optional).

- **Type:** String (connection URL)
- **Default:** Empty (disabled)
- **Format:** `redis://[user[:password]@][host][:port][/db]`
- **Purpose:** Listen for credential refresh events on channels:
  - `credentials:twitch:bot:refreshed`
  - `credentials:youtube:bot:refreshed`
- **Example:** `REDIS_URL=redis://:password@redis.cluster.local:6379/0`

#### VIDEO_SHOUTOUT_DEFAULT_DURATION
```
VIDEO_SHOUTOUT_DEFAULT_DURATION=30
```

Default duration (in seconds) to display video shoutout widget.

- **Type:** Integer
- **Default:** `30`
- **Valid range:** 5-120
- **Example:** `VIDEO_SHOUTOUT_DEFAULT_DURATION=45`

#### VIDEO_SHOUTOUT_DEFAULT_COOLDOWN
```
VIDEO_SHOUTOUT_DEFAULT_COOLDOWN=60
```

Default cooldown (in minutes) between video shoutouts.

- **Type:** Integer
- **Default:** `60`
- **Valid range:** 1-1440 (up to 24 hours)
- **Example:** `VIDEO_SHOUTOUT_DEFAULT_COOLDOWN=120`

## Complete .env Template

```bash
# Required: Twitch API Credentials
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret

# Required: Database Connection
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot

# Optional: YouTube API for Video Fallback
YOUTUBE_API_KEY=your_youtube_api_key

# Service URLs
MODULE_PORT=8011
IDENTITY_URL=http://identity-core:8050
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Logging
LOG_LEVEL=INFO

# Security (CHANGE IN PRODUCTION)
SECRET_KEY=change-me-in-production

# Optional: Redis for Credential Refresh Events
REDIS_URL=redis://localhost:6379

# Video Shoutout Defaults
VIDEO_SHOUTOUT_DEFAULT_DURATION=30
VIDEO_SHOUTOUT_DEFAULT_COOLDOWN=60
```

## Docker Compose Example

```yaml
services:
  shoutout-module:
    image: shoutout-interaction-module:2.0.0
    container_name: shoutout-module
    ports:
      - "8011:8011"
    environment:
      MODULE_PORT: 8011
      DATABASE_URL: postgresql://waddlebot:secure_password@postgres:5432/waddlebot
      TWITCH_CLIENT_ID: ${TWITCH_CLIENT_ID}
      TWITCH_CLIENT_SECRET: ${TWITCH_CLIENT_SECRET}
      YOUTUBE_API_KEY: ${YOUTUBE_API_KEY}
      IDENTITY_URL: http://identity-core:8050
      CORE_API_URL: http://router-service:8000
      ROUTER_API_URL: http://router-service:8000/api/v1/router
      LOG_LEVEL: INFO
      SECRET_KEY: ${SECRET_KEY}
      REDIS_URL: redis://redis:6379
      VIDEO_SHOUTOUT_DEFAULT_DURATION: 30
      VIDEO_SHOUTOUT_DEFAULT_COOLDOWN: 60
    depends_on:
      - postgres
      - redis
      - identity-core
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8011/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - waddlebot-network
    restart: unless-stopped
```

## Kubernetes ConfigMap Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: shoutout-config
  namespace: waddlebot
data:
  MODULE_PORT: "8011"
  DATABASE_URL: "postgresql://waddlebot:$(DB_PASSWORD)@postgres.waddlebot.svc:5432/waddlebot"
  IDENTITY_URL: "http://identity-core.waddlebot.svc:8050"
  CORE_API_URL: "http://router-service.waddlebot.svc:8000"
  ROUTER_API_URL: "http://router-service.waddlebot.svc:8000/api/v1/router"
  LOG_LEVEL: "INFO"
  VIDEO_SHOUTOUT_DEFAULT_DURATION: "30"
  VIDEO_SHOUTOUT_DEFAULT_COOLDOWN: "60"
---
apiVersion: v1
kind: Secret
metadata:
  name: shoutout-secrets
  namespace: waddlebot
type: Opaque
stringData:
  TWITCH_CLIENT_ID: "your_twitch_client_id"
  TWITCH_CLIENT_SECRET: "your_twitch_client_secret"
  YOUTUBE_API_KEY: "your_youtube_api_key"
  SECRET_KEY: "your_secret_key_here"
```

## Database Credentials from platform_integrations

The module can load Twitch and YouTube credentials from the database instead of environment variables. This enables runtime credential updates without restart.

**Table:** `platform_integrations`

```sql
CREATE TABLE platform_integrations (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50),  -- 'twitch', 'youtube'
    integration_type VARCHAR(50),  -- 'bot', 'user'
    client_id VARCHAR(255),  -- Twitch Client ID
    client_secret VARCHAR(255),  -- Twitch Client Secret
    access_token VARCHAR(1024),  -- YouTube API Key or access token
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Load Priority:**
1. Database credentials (if available)
2. Environment variables
3. Hardcoded defaults (empty string)

To enable database credential loading:

```python
# In startup code:
Config.load_credentials_from_db(dal)
```

## Redis Credential Refresh Listener

When Redis is configured, the module listens for credential refresh notifications:

```python
Config.start_credential_listener(redis_client)
```

**Monitored Channels:**
- `credentials:twitch:bot:refreshed` - Twitch credentials updated
- `credentials:youtube:bot:refreshed` - YouTube credentials updated

**Behavior:**
When message received on either channel, the module resets its cached credentials and reloads from database on next API call.

## Configuration Validation

The module validates configuration at startup:

```
✓ DATABASE_URL valid and reachable
✓ TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET set
✓ MODULE_PORT is integer between 1024-65535
✓ IDENTITY_URL is valid URL
✓ LOG_LEVEL is valid (DEBUG/INFO/WARNING/ERROR/CRITICAL)
```

If validation fails, the module logs error and exits with code 1.

## Development Configuration

For local development with `make dev`:

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env

# Run development server
make dev
```

**Typical development .env:**

```bash
MODULE_PORT=8011
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
TWITCH_CLIENT_ID=your_dev_client_id
TWITCH_CLIENT_SECRET=your_dev_client_secret
YOUTUBE_API_KEY=your_dev_youtube_key
IDENTITY_URL=http://localhost:8050
CORE_API_URL=http://localhost:8000
LOG_LEVEL=DEBUG
SECRET_KEY=dev-key-not-for-production
```

## Feature Flags & Behavior

### Text Shoutouts
Controlled by `ShoutoutConfig`:
- `so_enabled` (boolean) - Enable/disable text shoutouts
- `so_permission` (string) - Who can trigger (!so command)

### Video Shoutouts
Controlled by `ShoutoutConfig`:
- `vso_enabled` (boolean) - Enable/disable video shoutouts (!vso)
- `vso_permission` (string) - Who can trigger (!vso command)

### Auto-Shoutouts
Configured per community:
- `auto_shoutout_mode` - 'disabled', 'enabled', 'vips_only'
- `trigger_first_message` - Auto-shoutout on first chat message
- `trigger_raid_host` - Auto-shoutout on raid/host events

These are stored in `video_shoutout_config` table and retrieved via:

```
GET /api/v1/video-shoutout/config/{community_id}
PUT /api/v1/video-shoutout/config/{community_id}
```

## Production Recommendations

1. **Use strong SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Store secrets in environment/vault, not version control:**
   - Use `.env` locally only (never commit)
   - Use K8s Secrets in production
   - Use HashiCorp Vault for multi-environment

3. **Enable Redis for credential refresh:**
   - Allows updating Twitch/YouTube tokens without restart

4. **Set LOG_LEVEL=INFO (not DEBUG) in production**

5. **Monitor circuit breaker metrics:**
   - Check `GET /api/v1/circuit-breaker/metrics` regularly
   - Alert if circuit breaker trips

6. **Database backups:**
   - Regular PostgreSQL backups (at least daily)
   - Covers shoutout history and community configs
