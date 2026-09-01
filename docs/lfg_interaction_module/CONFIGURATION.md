# LFG Interaction Module - Configuration Guide

## Environment Variables

All configuration is managed via environment variables. This section lists all available variables, their defaults, and tuning guidance.

### Required Variables

#### Module Port
```bash
MODULE_PORT=8096
```
- **Type**: Integer
- **Default**: 8096
- **Description**: The port on which the Quart web server listens
- **Notes**: Must not conflict with other services

#### Database Connection
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/waddlebot
```
- **Type**: String (PostgreSQL connection string)
- **Default**: None (required)
- **Description**: PostgreSQL connection string for persistent storage
- **Format**: `postgresql://[user[:password]@][netloc][:port][/dbname][?param=value]`
- **Example**: `postgresql://postgres:secret@db.example.com:5432/lfg_db`
- **Notes**:
  - User must have CREATE/DROP/SELECT/INSERT/UPDATE/DELETE permissions
  - Connection pooling handled internally (min: 5, max: 20 connections)

#### API Endpoints
```bash
CORE_API_URL=http://core-api:5000
ROUTER_API_URL=http://router-api:8080
```
- **Type**: String (HTTP URLs)
- **Default**: None (required)
- **Description**: Internal API endpoints for license validation and routing
- **Notes**:
  - Used for user context validation
  - Used for router integration

#### Logging
```bash
LOG_LEVEL=INFO
```
- **Type**: String
- **Default**: INFO
- **Options**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Description**: Controls verbosity of module logs
- **Recommendations**:
  - `DEBUG`: Development only (very verbose)
  - `INFO`: Production (recommended)
  - `WARNING`: Quiet mode (errors and warnings only)

#### Security
```bash
SECRET_KEY=your-secret-key-here-minimum-32-chars
```
- **Type**: String
- **Default**: None (required)
- **Description**: Secret key for session/JWT signing and encryption
- **Requirements**:
  - Minimum 32 characters
  - Use cryptographically random string (e.g., `openssl rand -hex 32`)
  - Never share or commit to version control
  - Rotate periodically (existing sessions will invalidate)

### Optional Variables

#### Redis Cache
```bash
REDIS_URL=redis://localhost:6379/0
```
- **Type**: String (Redis connection URL)
- **Default**: None (optional)
- **Description**: Redis endpoint for caching and rate-limiting
- **Format**: `redis://[:password]@[host]:[port]/[db]`
- **Notes**:
  - If not set, in-memory caching is used (less efficient)
  - Recommended for production and multi-instance deployments
  - Used for session caching, rate-limiting, and temporary locks

#### Post Expiry Configuration
```bash
LFG_DEFAULT_EXPIRY_MINUTES=120
```
- **Type**: Integer
- **Default**: 120 (2 hours)
- **Description**: How long LFG posts remain open before auto-expiry
- **Range**: 10-1440 (10 minutes to 24 hours)
- **Recommendations**:
  - Fast-moving communities: 30-60 minutes
  - Casual communities: 120-180 minutes
  - RP/sandbox games: 300-480 minutes
- **Notes**: Expiry is checked hourly; actual expiry may be up to 60 minutes delayed

#### Per-User Post Limits
```bash
LFG_MAX_ACTIVE_POSTS_PER_USER=3
```
- **Type**: Integer
- **Default**: 3
- **Description**: Maximum number of active (open/filled) posts a user can create
- **Range**: 1-10
- **Recommendations**:
  - Single-game communities: 1-2
  - Multi-game communities: 3-5
  - High-activity communities: 5-10
- **Notes**: Prevents spam; users can still create more posts after previous ones expire/are cancelled

### Advanced Variables (Optional)

#### Connection Pooling
```bash
DB_POOL_MIN=5
DB_POOL_MAX=20
DB_POOL_TIMEOUT=30
```
- **Type**: Integer
- **Default**: min=5, max=20, timeout=30 seconds
- **Description**: PostgreSQL connection pool settings
- **Tuning**:
  - `DB_POOL_MIN`: Minimum idle connections (increase for high traffic)
  - `DB_POOL_MAX`: Maximum connections (limit per deployment; sum across all instances should not exceed DB max_connections)
  - `DB_POOL_TIMEOUT`: Connection acquisition timeout

#### Request Timeouts
```bash
REQUEST_TIMEOUT=30
BACKGROUND_JOB_TIMEOUT=60
```
- **Type**: Integer (seconds)
- **Default**: 30 and 60
- **Description**: HTTP request and background job timeouts

#### Async Worker Configuration
```bash
WORKER_COUNT=4
WORKER_THREADS=1
```
- **Type**: Integer
- **Default**: 4 workers, 1 thread per worker
- **Description**: Quart ASGI worker configuration
- **Tuning**:
  - `WORKER_COUNT`: CPU cores * 2-4 (e.g., 8-core CPU → 16-32 workers)
  - `WORKER_THREADS`: Usually 1 (async is thread-free)

#### Rate Limiting
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_USER=100
RATE_LIMIT_PER_IP=500
RATE_LIMIT_WINDOW=60
```
- **Type**: Boolean / Integer (seconds)
- **Default**: true, 100, 500, 60
- **Description**: Rate-limiting configuration
- **Notes**:
  - Requires Redis to be configured
  - Recommended for production
  - Returns 429 (Too Many Requests) when limits exceeded

#### Database Migrations
```bash
AUTO_MIGRATE=true
```
- **Type**: Boolean
- **Default**: true
- **Description**: Automatically run migrations on startup
- **Notes**: Set to false if using external migration tools

#### Monitoring & Observability
```bash
METRICS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_ENABLED=true
```
- **Type**: Boolean / Integer
- **Default**: true, 9090, true
- **Description**: Prometheus metrics and health check endpoints
- **Notes**:
  - Metrics available at `/metrics`
  - Health check at `/health`
  - Use for container orchestration probes

#### Debug Mode
```bash
DEBUG=false
```
- **Type**: Boolean
- **Default**: false
- **Description**: Enable debug mode (verbose logging, SQL query logging, etc.)
- **Notes**:
  - Never enable in production
  - Significantly impacts performance
  - Exposes sensitive information in logs

---

## Environment Configuration Examples

### Local Development
```bash
# .env.local
MODULE_PORT=8096
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/waddlebot_dev
REDIS_URL=redis://localhost:6379/0
CORE_API_URL=http://localhost:5000
ROUTER_API_URL=http://localhost:8080
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key-change-this-to-32-chars
LFG_DEFAULT_EXPIRY_MINUTES=30
DEBUG=true
```

### Testing
```bash
# .env.test
MODULE_PORT=8097
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/waddlebot_test
REDIS_URL=redis://localhost:6379/1
CORE_API_URL=http://localhost:5000
ROUTER_API_URL=http://localhost:8080
LOG_LEVEL=WARNING
SECRET_KEY=test-secret-key-change-this-to-32-chars
LFG_DEFAULT_EXPIRY_MINUTES=5
RATE_LIMIT_ENABLED=false
AUTO_MIGRATE=true
```

### Production (Kubernetes)
```bash
# ConfigMap: lfg-config
MODULE_PORT=8096
LOG_LEVEL=INFO
LFG_DEFAULT_EXPIRY_MINUTES=120
LFG_MAX_ACTIVE_POSTS_PER_USER=3
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_USER=100
RATE_LIMIT_PER_IP=500
METRICS_ENABLED=true
AUTO_MIGRATE=true
DEBUG=false
WORKER_COUNT=8

# Secret: lfg-secrets
DATABASE_URL=postgresql://lfg_user:$DBPASS@postgres.default.svc.cluster.local:5432/waddlebot
REDIS_URL=redis://:$REDISPASS@redis.default.svc.cluster.local:6379/0
CORE_API_URL=http://core-api:5000
ROUTER_API_URL=http://router-api:8080
SECRET_KEY=$SECRETKEY
```

### High-Traffic Environment
```bash
# .env.production-hc
MODULE_PORT=8096
DATABASE_URL=postgresql://lfg_user:$PASSWORD@postgres-replica-pool.internal:5432/waddlebot
REDIS_URL=redis-cluster://redis.internal:6379/0
CORE_API_URL=http://core-api.internal:5000
ROUTER_API_URL=http://router-api.internal:8080
LOG_LEVEL=INFO
SECRET_KEY=$SECRETKEY
LFG_DEFAULT_EXPIRY_MINUTES=120
LFG_MAX_ACTIVE_POSTS_PER_USER=5
DB_POOL_MIN=10
DB_POOL_MAX=50
WORKER_COUNT=32
RATE_LIMIT_PER_USER=200
RATE_LIMIT_PER_IP=1000
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true
```

---

## Configuration via Docker Compose

### docker-compose.yml
```yaml
version: '3.8'

services:
  lfg-module:
    image: waddlebot/lfg-interaction-module:latest
    ports:
      - "8096:8096"
    environment:
      MODULE_PORT: 8096
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/waddlebot
      REDIS_URL: redis://redis:6379/0
      CORE_API_URL: http://core-api:5000
      ROUTER_API_URL: http://router-api:8080
      LOG_LEVEL: INFO
      SECRET_KEY: your-secret-key-here-minimum-32-chars
      LFG_DEFAULT_EXPIRY_MINUTES: 120
      LFG_MAX_ACTIVE_POSTS_PER_USER: 3
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8096/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: waddlebot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## Configuration via Kubernetes

### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lfg-config
  namespace: waddlebot
data:
  MODULE_PORT: "8096"
  LOG_LEVEL: "INFO"
  LFG_DEFAULT_EXPIRY_MINUTES: "120"
  LFG_MAX_ACTIVE_POSTS_PER_USER: "3"
  RATE_LIMIT_ENABLED: "true"
  RATE_LIMIT_PER_USER: "100"
  RATE_LIMIT_PER_IP: "500"
  METRICS_ENABLED: "true"
  AUTO_MIGRATE: "true"
```

### Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: lfg-secrets
  namespace: waddlebot
type: Opaque
data:
  DATABASE_URL: cG9zdGdyZXM6Ly9sZmdfcm9vOiRQQVNTV09SREBwb3N0Z3Jlcy5kZWZhdWx0OnBnYXtZAQDQEDXRvYnlEZWZhdWx0LnN2Yy5jbHVzdGVyLmxvY2FsOjU0MzIvd2FkZGxlYm90
  REDIS_URL: cmVkaXM6Ly9yZWRpcy5kZWZhdWx0LnN2Yy5jbHVzdGVyLmxvY2FsOjYzNzkvMA==
  CORE_API_URL: aHR0cDovL2NvcmUtYXBpOjUwMDA=
  ROUTER_API_URL: aHR0cDovL3JvdXRlci1hcGk6ODA4MA==
  SECRET_KEY: <base64-encoded-secret-key>
```

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lfg-module
  namespace: waddlebot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lfg-module
  template:
    metadata:
      labels:
        app: lfg-module
    spec:
      containers:
      - name: lfg-module
        image: waddlebot/lfg-interaction-module:latest
        ports:
        - containerPort: 8096
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: lfg-config
        - secretRef:
            name: lfg-secrets
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8096
          initialDelaySeconds: 40
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8096
          initialDelaySeconds: 20
          periodSeconds: 10
```

---

## Tuning & Optimization

### For High-Traffic Communities
1. **Increase worker count**: `WORKER_COUNT=16` (or 2x CPU cores)
2. **Expand connection pool**: `DB_POOL_MAX=50`
3. **Use Redis cluster**: Multiple Redis nodes for caching
4. **Increase rate limits**: `RATE_LIMIT_PER_USER=200`
5. **Expand post expiry window**: `LFG_DEFAULT_EXPIRY_MINUTES=180`

### For Slow Networks
1. **Increase timeouts**: `REQUEST_TIMEOUT=60`
2. **Reduce connection pool**: `DB_POOL_MAX=10` (to avoid connection exhaustion)
3. **Enable caching**: `REDIS_URL` (required for efficiency)

### For Memory-Constrained Environments
1. **Reduce worker count**: `WORKER_COUNT=2`
2. **Shrink connection pool**: `DB_POOL_MAX=5`
3. **Disable metrics**: `METRICS_ENABLED=false`
4. **Use in-memory cache**: Omit `REDIS_URL` (default)

### For Security Hardening
1. **Enable rate limiting**: `RATE_LIMIT_ENABLED=true`
2. **Use strong secret**: `SECRET_KEY=$(openssl rand -hex 32)`
3. **Enable HTTPS**: Configure reverse proxy (TLS termination)
4. **Restrict CIDR**: Network policies to restrict access
5. **Rotate secrets**: Update `SECRET_KEY` periodically

---

## Health Checks & Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8096/health
```

Response (200 OK):
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "uptime_seconds": 3600
}
```

### Metrics Endpoint (Prometheus)
```bash
curl http://localhost:9090/metrics
```

Key metrics:
- `lfg_posts_created_total` — Total posts created
- `lfg_posts_active` — Currently active posts
- `lfg_joins_total` — Total joins across all posts
- `http_requests_total` — HTTP request count by method/status
- `http_request_duration_seconds` — Request latency

### Log Levels
- `DEBUG`: Development; every operation logged
- `INFO`: Production; key events logged
- `WARNING`: Issues and deprecations
- `ERROR`: Failures requiring attention
- `CRITICAL`: System failures

---

## Configuration Validation

The module validates configuration on startup:
```bash
docker-compose up interactive-lfg
```

If configuration is invalid:
```
ERROR: Invalid LFG_DEFAULT_EXPIRY_MINUTES=5. Must be 10-1440 minutes.
```

Always check startup logs for configuration errors before assuming service is healthy.
