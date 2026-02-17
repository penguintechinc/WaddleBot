# Analytics Core Module — Configuration

**Version:** 1.0.0
**Last Updated:** 2026-02-16

---

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Configuration Hierarchy](#configuration-hierarchy)
3. [Database Configuration](#database-configuration)
4. [Redis Configuration](#redis-configuration)
5. [Service URLs](#service-urls)
6. [Analytics Settings](#analytics-settings)
7. [Security Settings](#security-settings)
8. [Logging Configuration](#logging-configuration)
9. [Example Configurations](#example-configurations)
10. [Validation & Defaults](#validation--defaults)

---

## Environment Variables

All configuration is controlled via environment variables. Load from `.env` file or system environment.

### Module Identity Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MODULE_NAME` | str | `analytics-core` | No | Module identifier for logs |
| `MODULE_VERSION` | str | `1.0.0` | No | Module version for health check |
| `MODULE_PORT` | int | `8040` | No | REST API port |

**Example:**
```bash
MODULE_NAME=analytics-core
MODULE_VERSION=1.0.0
MODULE_PORT=8040
```

### Database Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATABASE_URL` | str | `postgresql://waddlebot:waddlebot123@localhost:5432/waddlebot` | Yes | PostgreSQL connection string |
| `DB_TYPE` | str | `postgresql` | No | Database type (postgresql, mysql, mariadb) |

**Format:**
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Example:**
```bash
# Local development
DATABASE_URL=postgresql://waddlebot:waddlebot123@localhost:5432/waddlebot

# Production with SSL
DATABASE_URL=postgresql://waddlebot:secure_pass@postgres.example.com:5432/waddlebot?sslmode=require

# Cloud deployment
DATABASE_URL=postgresql://user:pass@cloud-db.example.com/waddlebot
```

**Validation:**
- Must be valid PostgreSQL connection string
- User must have SELECT, INSERT, UPDATE, DELETE on analytics_* tables
- Connection pool size: Managed by PyDAL (default 20 connections)

### Redis Configuration (Optional)

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `REDIS_HOST` | str | `localhost` | No | Redis host address |
| `REDIS_PORT` | int | `6379` | No | Redis port |
| `REDIS_PASSWORD` | str | `` (empty) | No | Redis password |
| `REDIS_DB` | int | `0` | No | Redis database number (0-15) |
| `REDIS_URL` | str | `` (empty) | No | Full Redis URL (overrides above) |

**Format:**
```
redis://[password@][host]:[port]/[database]
```

**Example:**
```bash
# Local Redis (no auth)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Redis with password
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_PASSWORD=secure_password
REDIS_DB=1

# Full URL (takes precedence)
REDIS_URL=redis://:password@redis.example.com:6379/1
```

**Validation:**
- Optional, but improves performance when available
- If not configured, caching is disabled
- Connection failure is non-blocking (module still works)

### Service URLs

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ROUTER_API_URL` | str | `http://router:8000/api/v1/router` | No | Router service URL |
| `REPUTATION_API_URL` | str | `http://reputation:8021/api/v1/reputation` | No | Reputation service URL |

**Example:**
```bash
# Development (local services)
ROUTER_API_URL=http://router:8000/api/v1/router
REPUTATION_API_URL=http://reputation:8021/api/v1/reputation

# Production (fully qualified)
ROUTER_API_URL=https://router.penguintech.io/api/v1/router
REPUTATION_API_URL=https://reputation.penguintech.io/api/v1/reputation

# Custom deployment
ROUTER_API_URL=http://internal-router.local/api/v1/router
REPUTATION_API_URL=http://internal-reputation.local/api/v1/reputation
```

**Validation:**
- Must be accessible from analytics-core container
- Should use HTTP/HTTPS
- Timeouts: Default 30 seconds per request

### Security Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SECRET_KEY` | str | `change-me-in-production` | Yes (prod) | Flask session key |
| `SERVICE_API_KEY` | str | `` (empty) | Yes (prod) | Service-to-service auth key |

**Example:**
```bash
# Development
SECRET_KEY=dev-secret-key-insecure
SERVICE_API_KEY=dev-service-key

# Production (use strong random values)
SECRET_KEY=abcdef123456789012345678901234567890
SERVICE_API_KEY=xyz987654321abcdefghijklmnopqrst
```

**Generation:**
```bash
# Generate strong random keys
python -c "import secrets; print(secrets.token_hex(32))"
# Output: 8f6b4c2e9a1d7f5b3c8e0a2d4f6b8c1e

# Or use openssl
openssl rand -hex 32
```

**Validation:**
- SECRET_KEY: Minimum 16 characters (recommended 32+)
- SERVICE_API_KEY: Minimum 16 characters
- Must be unique per deployment
- Rotate periodically (e.g., quarterly)

### Logging Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LOG_LEVEL` | str | `INFO` | No | Python logging level |

**Valid Values:**
- `DEBUG` - Verbose output, all events logged
- `INFO` - Standard logging, application events
- `WARNING` - Warnings and errors only
- `ERROR` - Errors only, silent otherwise
- `CRITICAL` - Critical errors only

**Example:**
```bash
# Development
LOG_LEVEL=DEBUG

# Production
LOG_LEVEL=INFO

# High-security or performance-critical
LOG_LEVEL=WARNING
```

---

## Configuration Hierarchy

Configurations are loaded in this order (later overrides earlier):

```
1. Code defaults (in config.py)
        ↓
2. .env file (in working directory)
        ↓
3. System environment variables
        ↓
4. Kubernetes ConfigMap (if deployed)
        ↓
5. Database platform_integrations table (credentials only)
```

**Example Flow:**

```bash
# config.py (code defaults)
DEFAULT_POLLING_INTERVAL = 30

# .env file
DEFAULT_POLLING_INTERVAL=60

# System env var (highest priority)
export DEFAULT_POLLING_INTERVAL=45

# Result: 45 is used
```

---

## Database Configuration

### Connection Pool Settings

**Via PyDAL (automatic):**
```python
# Default settings
pool_size = 20          # Connection pool size
max_overflow = 40       # Additional connections allowed
pool_recycle = 3600     # Recycle connections after 1 hour
pool_pre_ping = True    # Test connections before use
```

**Adjust for deployment:**

Small deployment (< 10 communities):
```python
pool_size = 5
max_overflow = 10
```

Large deployment (> 1000 communities):
```python
pool_size = 50
max_overflow = 100
pool_recycle = 1800
```

### Required Tables

The module requires these tables to exist in PostgreSQL:

**Configuration:**
- `analytics_config` - Per-community settings
- `analytics_aggregation_state` - Last aggregation timestamp

**Metrics:**
- `analytics_metrics_timeseries` - Time-series metrics

**Bot Detection:**
- `analytics_bot_scores` - Cached bot scores
- `analytics_suspected_bots` - Suspected bot users
- `analytics_bad_actor_alerts` - Bad actor flags

**Community Health:**
- `analytics_community_health` - Health metrics

**Source Data:**
- `activity_message_events` - Message activity
- `activity_watch_sessions` - Watch session data
- `hub_users` - User information

**Create table if missing:**

The module will auto-create tables if they don't exist (requires migration to be run first).

### Database User Permissions

Minimum required permissions:

```sql
-- Create analytics user
CREATE USER analytics WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT USAGE ON SCHEMA public TO analytics;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO analytics;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO analytics;
GRANT CREATE ON SCHEMA public TO analytics;

-- For connection pooling
GRANT CONNECT ON DATABASE waddlebot TO analytics;
```

---

## Redis Configuration

### Cache Keys

Bot scores are cached with these keys:

```
analytics:bot-score:{community_id}
analytics:suspected-bots:{community_id}
```

### Pub/Sub Channels

For credential refresh notifications:

```
credentials:analytics_core:bot:refreshed
```

### Memory Requirements

Typical Redis memory usage:

- 1000 communities: ~5MB (bot scores only)
- With metrics caching: ~50MB
- Production recommendation: 256MB - 1GB

### Eviction Policy

Recommended Redis configuration:

```
maxmemory-policy allkeys-lru    # Evict least recently used keys
maxmemory 256mb                 # Max memory allocation
```

---

## Service URLs

### Router Service

Analytics depends on Router service for event ingestion.

**Required endpoints:**
- None (Router pushes events to Analytics)

**Default URL:**
```
http://router:8000/api/v1/router
```

**Override for different environments:**

```bash
# Development (Docker Compose)
ROUTER_API_URL=http://router:8000/api/v1/router

# Kubernetes staging
ROUTER_API_URL=http://router-staging.default.svc.cluster.local:8000/api/v1/router

# Production
ROUTER_API_URL=https://router.penguintech.io/api/v1/router
```

### Reputation Service

Analytics queries Reputation service for reputation scores.

**Default URL:**
```
http://reputation:8021/api/v1/reputation
```

**Override for different environments:**

```bash
# Development
REPUTATION_API_URL=http://reputation:8021/api/v1/reputation

# Kubernetes
REPUTATION_API_URL=http://reputation.default.svc.cluster.local:8021/api/v1/reputation

# Production
REPUTATION_API_URL=https://reputation.penguintech.io/api/v1/reputation
```

---

## Analytics Settings

### Time Windows & Retention

| Variable | Type | Default | Unit | Description |
|----------|------|---------|------|-------------|
| `DEFAULT_POLLING_INTERVAL` | int | `30` | seconds | Client polling interval |
| `DEFAULT_RAW_RETENTION_DAYS` | int | `30` | days | Keep raw events |
| `DEFAULT_AGGREGATED_RETENTION_DAYS` | int | `365` | days | Keep aggregated metrics |

**Example:**
```bash
# Short retention for testing
DEFAULT_RAW_RETENTION_DAYS=7
DEFAULT_AGGREGATED_RETENTION_DAYS=90

# Long retention for compliance
DEFAULT_RAW_RETENTION_DAYS=90
DEFAULT_AGGREGATED_RETENTION_DAYS=1825  # 5 years
```

### Bucket Sizes

**Available bucket sizes** (read-only in config):
```python
BUCKET_SIZES = ['1h', '1d', '1w', '1m']
```

All bucket sizes are always available. Cannot be disabled.

### Premium Features

**Features requiring premium subscription:**
```python
PREMIUM_FEATURES = [
    'community_health',
    'bad_actor_detection',
    'user_journey',
    'retention_cohorts',
    'engagement_funnels'
]
```

Configuration per community is done via API, not env vars:
```bash
curl -X PUT http://localhost:8040/api/v1/analytics/123/config \
  -d '{"is_premium": true}'
```

### Health Grade Thresholds

**Grading scale** (read-only in config):
```python
HEALTH_GRADES = {
    'A+': {'min': 95, 'max': 100},
    'A': {'min': 90, 'max': 94},
    'B+': {'min': 85, 'max': 89},
    'B': {'min': 80, 'max': 84},
    'C+': {'min': 75, 'max': 79},
    'C': {'min': 70, 'max': 74},
    'D': {'min': 60, 'max': 69},
    'F': {'min': 0, 'max': 59}
}
```

Cannot be changed without code modification.

---

## Logging Configuration

### Log Format

Standard structured logging format:

```
TIMESTAMP | LEVEL | MODULE | MESSAGE | CONTEXT

Example:
2026-02-16 10:30:00 | INFO | analytics-core | Database initialized | result=SUCCESS
```

### Audit Logging

Special audit logs for compliance:

```
{
  "timestamp": "2026-02-16T10:30:00Z",
  "event_type": "analytics_config_updated",
  "community_id": 123,
  "action": "update_config",
  "user_id": 456,
  "changes": {
    "is_premium": false -> true,
    "polling_interval_seconds": 30 -> 15
  },
  "result": "SUCCESS"
}
```

### Log Destinations

- **Console**: Quart development mode
- **File**: Production deployment (via Docker)
- **Structured**: Elasticsearch/CloudWatch integration (custom)

---

## Example Configurations

### Development (Local)

```bash
# .env.development
MODULE_NAME=analytics-core
MODULE_VERSION=1.0.0
MODULE_PORT=8040
LOG_LEVEL=DEBUG

# Database (local PostgreSQL)
DATABASE_URL=postgresql://waddlebot:waddlebot123@localhost:5432/waddlebot
DB_TYPE=postgresql

# Redis (local)
REDIS_HOST=localhost
REDIS_PORT=6379

# Services (Docker Compose)
ROUTER_API_URL=http://router:8000/api/v1/router
REPUTATION_API_URL=http://reputation:8021/api/v1/reputation

# Security (development keys)
SECRET_KEY=dev-secret-key-change-in-production
SERVICE_API_KEY=dev-service-key-change-in-production

# Analytics
DEFAULT_POLLING_INTERVAL=30
DEFAULT_RAW_RETENTION_DAYS=30
DEFAULT_AGGREGATED_RETENTION_DAYS=365
```

**Start:**
```bash
python app.py
```

### Staging (Docker Compose)

```bash
# .env.staging
MODULE_NAME=analytics-core-staging
MODULE_VERSION=1.0.0
MODULE_PORT=8040
LOG_LEVEL=INFO

# Database (staging PostgreSQL)
DATABASE_URL=postgresql://analytics:secure_pass@postgres-staging.internal:5432/waddlebot_staging
DB_TYPE=postgresql

# Redis (staging)
REDIS_HOST=redis-staging.internal
REDIS_PORT=6379
REDIS_PASSWORD=staging_password

# Services
ROUTER_API_URL=http://router-staging.internal:8000/api/v1/router
REPUTATION_API_URL=http://reputation-staging.internal:8021/api/v1/reputation

# Security (staging keys - rotate monthly)
SECRET_KEY=staging_secret_abcdef123456789...
SERVICE_API_KEY=staging_service_xyz987654321...

# Analytics
DEFAULT_RAW_RETENTION_DAYS=60
DEFAULT_AGGREGATED_RETENTION_DAYS=365
```

**Docker Compose:**
```yaml
services:
  analytics-core:
    image: waddlebot/analytics-core:latest
    ports:
      - "8040:8040"
    environment:
      - MODULE_PORT=8040
      - DATABASE_URL=postgresql://...
      - REDIS_HOST=redis
      - LOG_LEVEL=INFO
    depends_on:
      - postgres
      - redis
```

**Start:**
```bash
docker-compose -f docker-compose.staging.yml up
```

### Production (Kubernetes)

```bash
# .env.production
MODULE_NAME=analytics-core
MODULE_VERSION=1.0.0
MODULE_PORT=8040
LOG_LEVEL=INFO

# Database (production RDS/Cloud SQL)
DATABASE_URL=postgresql://analytics:${DB_PASSWORD}@postgres.c.example.com:5432/waddlebot_prod
DB_TYPE=postgresql

# Redis (production Redis cluster)
REDIS_URL=redis://:${REDIS_PASSWORD}@redis-cluster.c.example.com:6379/1

# Services (production URLs)
ROUTER_API_URL=https://router.penguintech.io/api/v1/router
REPUTATION_API_URL=https://reputation.penguintech.io/api/v1/reputation

# Security (production keys from secrets)
SECRET_KEY=${SECRET_KEY}         # From Kubernetes Secret
SERVICE_API_KEY=${SERVICE_API_KEY} # From Kubernetes Secret

# Analytics (production settings)
DEFAULT_POLLING_INTERVAL=30
DEFAULT_RAW_RETENTION_DAYS=30
DEFAULT_AGGREGATED_RETENTION_DAYS=365
```

**Kubernetes ConfigMap:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: analytics-core-config
  namespace: production
data:
  MODULE_PORT: "8040"
  LOG_LEVEL: "INFO"
  DATABASE_URL: "postgresql://..."
  ROUTER_API_URL: "https://..."
  REPUTATION_API_URL: "https://..."
```

**Kubernetes Secret:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: analytics-core-secrets
  namespace: production
type: Opaque
data:
  SECRET_KEY: base64_encoded_value
  SERVICE_API_KEY: base64_encoded_value
  REDIS_PASSWORD: base64_encoded_value
```

**Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analytics-core
  namespace: production
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: analytics-core
        image: registry.penguintech.io/waddlebot/analytics-core:v1.0.0
        ports:
        - containerPort: 8040
        envFrom:
        - configMapRef:
            name: analytics-core-config
        - secretRef:
            name: analytics-core-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

---

## Validation & Defaults

### Validation at Startup

The module validates configuration at startup:

```python
def validate_config():
    # Check required vars
    assert DATABASE_URL, "DATABASE_URL required"
    assert MODULE_PORT > 1024, "MODULE_PORT must be > 1024"

    # Check connections
    try:
        dal = init_database(DATABASE_URL)
        logger.info("Database connection OK")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

    # Check Redis if configured
    if REDIS_URL:
        try:
            redis_client = redis.from_url(REDIS_URL)
            redis_client.ping()
            logger.info("Redis connection OK")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")

    # Warn about insecure production settings
    if is_production():
        if SECRET_KEY == 'change-me-in-production':
            logger.error("SECRET_KEY not changed!")
            raise ValueError("Insecure SECRET_KEY in production")
```

### Default Values

If environment variable is not set:

| Variable | Default Value |
|----------|---------------|
| `MODULE_NAME` | `analytics-core` |
| `MODULE_VERSION` | `1.0.0` |
| `MODULE_PORT` | `8040` |
| `DATABASE_URL` | `postgresql://waddlebot:waddlebot123@localhost:5432/waddlebot` |
| `DB_TYPE` | `postgresql` |
| `REDIS_HOST` | `localhost` |
| `REDIS_PORT` | `6379` |
| `REDIS_PASSWORD` | `` (empty) |
| `REDIS_DB` | `0` |
| `REDIS_URL` | `` (empty, uses REDIS_HOST/PORT) |
| `ROUTER_API_URL` | `http://router:8000/api/v1/router` |
| `REPUTATION_API_URL` | `http://reputation:8021/api/v1/reputation` |
| `SECRET_KEY` | `change-me-in-production` |
| `SERVICE_API_KEY` | `` (empty) |
| `LOG_LEVEL` | `INFO` |
| `DEFAULT_POLLING_INTERVAL` | `30` |
| `DEFAULT_RAW_RETENTION_DAYS` | `30` |
| `DEFAULT_AGGREGATED_RETENTION_DAYS` | `365` |

---

**Last Updated:** 2026-02-16
**Maintained By:** Penguin Tech Inc
