# YouTube Live Module Configuration

Comprehensive reference for all environment variables and configuration options.

## Environment Variables

All configuration is managed via environment variables. Set them before starting the module or in a `.env` file.

### Server Configuration

#### MODULE_PORT
- **Type**: integer
- **Default**: `8006`
- **Description**: Port the module listens on
- **Example**: `MODULE_PORT=8006`

#### LOG_LEVEL
- **Type**: string (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- **Default**: `INFO`
- **Description**: Logging verbosity level
- **Values**:
  - `DEBUG`: All messages including API calls and internal state
  - `INFO`: Standard operational messages (recommended for production)
  - `WARNING`: Warnings and errors only
  - `ERROR`: Errors only
  - `CRITICAL`: Critical issues only
- **Example**: `LOG_LEVEL=DEBUG`

#### SECRET_KEY
- **Type**: string
- **Required**: Yes (for session security)
- **Description**: Flask/Quart secret key for session encryption
- **Generate**: `python -c "import secrets; print(secrets.token_hex(32))"`
- **Example**: `SECRET_KEY=abc123def456...`

#### LOG_FORMAT
- **Type**: string (text|json)
- **Default**: `text`
- **Description**: Log output format
- **Values**:
  - `text`: Human-readable text format
  - `json`: JSON structured logging
- **Example**: `LOG_FORMAT=json`

### YouTube API Configuration

#### YOUTUBE_API_KEY
- **Type**: string
- **Required**: Yes
- **Description**: YouTube Data API v3 API key for public data access
- **Obtain**: [Google Cloud Console](https://console.cloud.google.com/)
- **Quota**: 10,000 units/day free tier
- **Unit Cost**: ~1 unit per chat poll request
- **Example**: `YOUTUBE_API_KEY=AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### YOUTUBE_CLIENT_ID
- **Type**: string
- **Required**: For OAuth 2.0 flows
- **Description**: OAuth 2.0 client ID for user authentication
- **Obtain**: Google Cloud Console → Credentials → OAuth 2.0 Client ID
- **Example**: `YOUTUBE_CLIENT_ID=123456789-xxx.apps.googleusercontent.com`

#### YOUTUBE_CLIENT_SECRET
- **Type**: string
- **Required**: For OAuth 2.0 flows
- **Description**: OAuth 2.0 client secret
- **Important**: Keep secret! Never commit to version control
- **Example**: `YOUTUBE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxx`

#### YOUTUBE_WEBHOOK_CALLBACK_URL
- **Type**: string (URL)
- **Required**: For webhook integration
- **Description**: Public URL where YouTube sends PubSubHubbub notifications
- **Format**: `https://yourdomain.com/api/v1/webhook`
- **Requirements**:
  - Must be HTTPS
  - Must be publicly accessible
  - Must match registered webhook URL
- **Example**: `YOUTUBE_WEBHOOK_CALLBACK_URL=https://waddlebot.io/youtube/webhook`

### Database Configuration

#### DATABASE_URL
- **Type**: string (connection string)
- **Required**: Yes
- **Description**: PostgreSQL database connection string
- **Format**: `postgresql://[user[:password]@][host][:port][/dbname][?param=value]`
- **Examples**:
  - Local dev: `postgresql://localhost/waddlebot`
  - With auth: `postgresql://user:password@db.example.com:5432/waddlebot`
  - With SSL: `postgresql://user:password@db.example.com/waddlebot?sslmode=require`

#### DB_POOL_SIZE
- **Type**: integer
- **Default**: `10`
- **Description**: Maximum number of persistent database connections
- **Tuning**: Increase for high-throughput deployments
- **Example**: `DB_POOL_SIZE=20`

#### DB_MAX_OVERFLOW
- **Type**: integer
- **Default**: `5`
- **Description**: Maximum overflow connections above pool size
- **Tuning**: Increase for burst traffic
- **Example**: `DB_MAX_OVERFLOW=10`

#### DB_POOL_TIMEOUT
- **Type**: integer (seconds)
- **Default**: `30`
- **Description**: Timeout for acquiring a connection from the pool
- **Example**: `DB_POOL_TIMEOUT=60`

### Router API Configuration

#### ROUTER_API_URL
- **Type**: string (URL)
- **Required**: Yes
- **Description**: Base URL of the core router service for event routing
- **Format**: `http://[host][:port]`
- **Examples**:
  - Local dev: `http://localhost:8000`
  - Docker: `http://router:8000`
  - Remote: `https://router.example.com`

#### ROUTER_API_TIMEOUT
- **Type**: integer (seconds)
- **Default**: `10`
- **Description**: Timeout for requests to router service
- **Example**: `ROUTER_API_TIMEOUT=30`

#### ROUTER_API_RETRIES
- **Type**: integer
- **Default**: `3`
- **Description**: Number of retries on router API request failure
- **Example**: `ROUTER_API_RETRIES=5`

### Redis Configuration (Optional)

#### REDIS_URL
- **Type**: string (connection string)
- **Default**: None (in-memory cache if not set)
- **Description**: Redis connection URL for credential caching and rate limiting
- **Format**: `redis://[password@][host][:port][/db]`
- **Examples**:
  - Local: `redis://localhost:6379/0`
  - With auth: `redis://:password@redis.example.com:6379/0`
  - Cluster: `rediss://redis-cluster.example.com:6379`

#### REDIS_CACHE_TTL
- **Type**: integer (seconds)
- **Default**: `3600`
- **Description**: Time-to-live for cached credentials
- **Example**: `REDIS_CACHE_TTL=7200`

### Chat Polling Configuration

#### CHAT_POLL_INTERVAL
- **Type**: integer (seconds)
- **Default**: `5`
- **Description**: Interval between chat polling requests per channel
- **Guidance**:
  - Smaller = more real-time but higher API quota usage
  - Larger = saves quota but higher latency
- **API Quota Impact**: 1 unit per request
  - At 5s interval: ~17,280 units/day per channel
  - At 10s interval: ~8,640 units/day per channel
  - 100 channels at 5s: Exceeds 10K daily quota
- **Example**: `CHAT_POLL_INTERVAL=10`

#### CHAT_MAX_RESULTS
- **Type**: integer (1-200)
- **Default**: `200`
- **Description**: Maximum messages per polling request
- **Guidance**:
  - Higher = fewer requests but larger payloads
  - Lower = more requests but less data processing
  - Optimal: Balance between API calls and message throughput
- **Example**: `CHAT_MAX_RESULTS=100`

#### CHAT_POLL_TIMEOUT
- **Type**: integer (seconds)
- **Default**: `30`
- **Description**: Timeout for individual chat polling requests
- **Example**: `CHAT_POLL_TIMEOUT=45`

#### CHAT_ERROR_THRESHOLD
- **Type**: integer
- **Default**: `10`
- **Description**: Number of consecutive errors before removing a channel
- **Guidance**: Keep at 10 to auto-recover from transient failures
- **Example**: `CHAT_ERROR_THRESHOLD=15`

### Feature Flags

#### ENABLE_WEBHOOK_HANDLER
- **Type**: boolean (true|false)
- **Default**: `true`
- **Description**: Enable PubSubHubbub webhook handler for stream events
- **Example**: `ENABLE_WEBHOOK_HANDLER=true`

#### ENABLE_CREDENTIAL_CACHING
- **Type**: boolean (true|false)
- **Default**: `true`
- **Description**: Enable Redis caching of OAuth credentials
- **Example**: `ENABLE_CREDENTIAL_CACHING=true`

#### ENABLE_METRICS
- **Type**: boolean (true|false)
- **Default**: `true`
- **Description**: Enable Prometheus metrics endpoint
- **Example**: `ENABLE_METRICS=true`

#### ENABLE_AUTO_SUBSCRIBE
- **Type**: boolean (true|false)
- **Default**: `true`
- **Description**: Auto-subscribe channels to PubSubHubbub on registration
- **Example**: `ENABLE_AUTO_SUBSCRIBE=true`

### Security Configuration

#### ALLOWED_ORIGINS
- **Type**: string (comma-separated URLs)
- **Default**: `http://localhost:3000,http://localhost:8000`
- **Description**: Allowed CORS origins for API requests
- **Example**: `ALLOWED_ORIGINS=https://waddlebot.io,https://admin.waddlebot.io`

#### USE_HTTPS
- **Type**: boolean (true|false)
- **Default**: `false` (development), `true` (production)
- **Description**: Enforce HTTPS for all connections
- **Example**: `USE_HTTPS=true`

#### WEBHOOK_VERIFY_SIGNATURE
- **Type**: boolean (true|false)
- **Default**: `true`
- **Description**: Verify PubSubHubbub webhook signatures
- **Example**: `WEBHOOK_VERIFY_SIGNATURE=true`

#### WEBHOOK_SECRET
- **Type**: string
- **Description**: Secret key for webhook signature verification
- **Generate**: Same as SECRET_KEY if not set
- **Example**: `WEBHOOK_SECRET=webhook-secret-key`

### Monitoring & Observability

#### METRICS_PORT
- **Type**: integer
- **Default**: `9090`
- **Description**: Port for Prometheus metrics endpoint
- **Example**: `METRICS_PORT=9090`

#### ENABLE_REQUEST_LOGGING
- **Type**: boolean (true|false)
- **Default**: `true`
- **Description**: Log all HTTP requests and responses
- **Example**: `ENABLE_REQUEST_LOGGING=false` (disable for high traffic)

#### SLOW_REQUEST_THRESHOLD
- **Type**: float (seconds)
- **Default**: `1.0`
- **Description**: Log requests slower than threshold
- **Example**: `SLOW_REQUEST_THRESHOLD=2.0`

### Development Configuration

#### DEBUG_MODE
- **Type**: boolean (true|false)
- **Default**: `false`
- **Description**: Enable debug mode with auto-reload and verbose output
- **Example**: `DEBUG_MODE=true`

#### MOCK_API_RESPONSES
- **Type**: boolean (true|false)
- **Default**: `false`
- **Description**: Use mock API responses for testing without YouTube API
- **Example**: `MOCK_API_RESPONSES=true`

#### MOCK_CHAT_DATA_FILE
- **Type**: string (file path)
- **Description**: JSON file with mock chat data for testing
- **Example**: `MOCK_CHAT_DATA_FILE=tests/fixtures/mock_chat.json`

## Configuration Examples

### Local Development

```bash
# .env
MODULE_PORT=8006
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key-12345678
YOUTUBE_API_KEY=AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxx
DATABASE_URL=postgresql://localhost/waddlebot
ROUTER_API_URL=http://localhost:8000
CHAT_POLL_INTERVAL=5
CHAT_MAX_RESULTS=200
DEBUG_MODE=true
```

### Production (AWS/GCP)

```bash
# Production config
MODULE_PORT=8006
LOG_LEVEL=INFO
LOG_FORMAT=json
SECRET_KEY=<secure-random-key>
YOUTUBE_API_KEY=<api-key>
YOUTUBE_CLIENT_ID=<client-id>
YOUTUBE_CLIENT_SECRET=<client-secret>
YOUTUBE_WEBHOOK_CALLBACK_URL=https://waddlebot.io/youtube/webhook
DATABASE_URL=postgresql://user:pass@db.rds.amazonaws.com:5432/waddlebot?sslmode=require
ROUTER_API_URL=https://router.internal.example.com
REDIS_URL=redis://:password@redis.example.com:6379/0
CHAT_POLL_INTERVAL=10
CHAT_MAX_RESULTS=100
ALLOWED_ORIGINS=https://waddlebot.io
USE_HTTPS=true
WEBHOOK_VERIFY_SIGNATURE=true
ENABLE_REQUEST_LOGGING=false
DB_POOL_SIZE=20
```

### High-Throughput Setup (100+ channels)

```bash
# Optimized for throughput
MODULE_PORT=8006
LOG_LEVEL=INFO
YOUTUBE_API_KEY=<api-key>
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
ROUTER_API_URL=http://router:8000
REDIS_URL=redis://redis:6379/0

# Reduce API quota usage
CHAT_POLL_INTERVAL=10
CHAT_MAX_RESULTS=50

# Database tuning
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=10

# Monitoring
ENABLE_REQUEST_LOGGING=false
SLOW_REQUEST_THRESHOLD=2.0
```

### Testing Setup

```bash
# .env.test
MODULE_PORT=8007
LOG_LEVEL=DEBUG
SECRET_KEY=test-secret-key
YOUTUBE_API_KEY=test-key
DATABASE_URL=postgresql://localhost/waddlebot_test
ROUTER_API_URL=http://localhost:8001
MOCK_API_RESPONSES=true
MOCK_CHAT_DATA_FILE=tests/fixtures/mock_chat.json
```

## Configuration Validation

The module validates configuration on startup. Common validation errors:

### Missing Required Variables

```
ERROR: Missing required environment variable: YOUTUBE_API_KEY
```

**Solution**: Set `YOUTUBE_API_KEY` before starting.

### Invalid Values

```
ERROR: DATABASE_URL is invalid: postgresql://... (connection refused)
```

**Solution**: Verify database is running and connection string is correct.

### Invalid Port

```
ERROR: MODULE_PORT must be between 1 and 65535, got: 99999
```

**Solution**: Use valid port number (typically 8000-9000 for services).

## Database Migrations

Configuration changes may require database schema updates:

```bash
# Automatic on startup (PyDAL)
python main.py  # Creates tables if missing

# Manual migration (if needed)
python -m alembic upgrade head
```

## Security Best Practices

1. **API Keys**:
   - Never commit to version control
   - Use secret management (AWS Secrets, HashiCorp Vault)
   - Rotate regularly
   - Restrict to necessary scopes

2. **Database**:
   - Use strong passwords
   - Enable SSL/TLS connections
   - Restrict access to authorized IPs
   - Enable audit logging

3. **OAuth Tokens**:
   - Store encrypted in database
   - Refresh automatically before expiry
   - Never log tokens
   - Rotate refresh tokens periodically

4. **Webhook URLs**:
   - Must be HTTPS in production
   - Verify signatures
   - Use secret keys for HMAC validation

## Performance Tuning

See [USAGE.md](USAGE.md) Performance Tuning section for guidance on:
- API quota optimization
- Database connection pooling
- Concurrent polling
- Memory usage optimization

## Configuration Reload

Most configurations take effect immediately:

- Log level: Runtime update
- Polling interval: Takes effect after current cycle
- API limits: Immediate

To apply some changes, restart the module:

```bash
docker-compose restart trigger-youtube
```

## Related Documentation

- [API.md](API.md) - API endpoints and responses
- [USAGE.md](USAGE.md) - Setup and operational procedures
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Error resolution
