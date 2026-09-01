# Alias Interaction Module — Configuration

## Overview

The Alias Interaction Module uses environment variables for all runtime configuration. This enables secure credential management and easy deployment across different environments (development, staging, production).

---

## Environment Variables

### Core Configuration

#### MODULE_PORT
- **Type:** Integer
- **Default:** `8010`
- **Description:** HTTP port the service listens on
- **Example:** `export MODULE_PORT=8010`
- **Notes:** Must be unused on the host; typically 8010 for this module per port allocation standards

#### MODULE_NAME
- **Type:** String
- **Default:** `alias_interaction_module` (hardcoded)
- **Description:** Internal module identifier
- **Notes:** Auto-configured, not typically changed

#### MODULE_VERSION
- **Type:** String
- **Default:** `2.0.0` (hardcoded)
- **Description:** Semantic version of the module
- **Notes:** Updated during releases; auto-configured

#### LOG_LEVEL
- **Type:** String
- **Default:** `INFO`
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description:** Logging output verbosity
- **Example:** `export LOG_LEVEL=DEBUG`
- **Recommendation:** Use `DEBUG` in development, `INFO` in production

#### SECRET_KEY
- **Type:** String
- **Default:** `change-me-in-production` (insecure default)
- **Description:** Secret key for session/token signing
- **Example:** `export SECRET_KEY="your-secure-random-key-min-32-chars"`
- **Security:** MUST be changed in production; use strong random value
- **Generation:** `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

### Database Configuration

#### DATABASE_URL
- **Type:** String (PostgreSQL connection string)
- **Default:** `postgresql://waddlebot:password@localhost:5432/waddlebot`
- **Description:** PostgreSQL database connection string
- **Format:** `postgresql://[user]:[password]@[host]:[port]/[database]`
- **Example (Local):** `postgresql://waddlebot:dev_password@localhost:5432/waddlebot`
- **Example (Remote):** `postgresql://user:pass@db.example.com:5432/waddlebot_prod`
- **Example (With SSL):** `postgresql://user:pass@db.example.com:5432/waddlebot?sslmode=require`
- **Required:** Yes
- **Notes:**
  - Use environment variable in all environments
  - Never hardcode in code
  - Supports PyDAL connection parameters

### Router Service Configuration

#### CORE_API_URL
- **Type:** String (HTTP URL)
- **Default:** `http://router-service:8000`
- **Description:** Base URL of the WaddleBot Router Service
- **Example (Local):** `http://localhost:8000`
- **Example (Docker):** `http://router-service:8000`
- **Example (Kubernetes):** `http://router-service.waddlebot.svc.cluster.local:8000`
- **Usage:** Optional; used for advanced routing scenarios

#### ROUTER_API_URL
- **Type:** String (HTTP URL)
- **Default:** `http://router-service:8000/api/v1/router`
- **Description:** Router service API endpoint for complex routing
- **Example:** `http://router-service:8000/api/v1/router`
- **Usage:** Optional; used when delegating to Router Service

### Redis Configuration (Optional)

#### REDIS_URL
- **Type:** String (Redis connection string)
- **Default:** Empty string (disabled)
- **Description:** Redis connection for credential refresh notifications
- **Format:** `redis://[user]:[password]@[host]:[port]/[db]`
- **Example (Local):** `redis://localhost:6379/0`
- **Example (Docker):** `redis://redis:6379/0`
- **Example (With Auth):** `redis://default:password@redis:6379/0`
- **Required:** No (optional feature)
- **Notes:**
  - If empty, credential listener is disabled
  - Used for pub/sub credential refresh events
  - Channel: `credentials:alias_interaction:bot:refreshed`

---

## Environment Variable Examples

### Development Environment (.env)

```bash
# Core
MODULE_PORT=8010
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key-change-in-production

# Database (Local PostgreSQL)
DATABASE_URL=postgresql://waddlebot:dev_password@localhost:5432/waddlebot

# Router Service
CORE_API_URL=http://localhost:8000
ROUTER_API_URL=http://localhost:8000/api/v1/router

# Redis (optional, for development)
REDIS_URL=redis://localhost:6379/0
```

### Docker Compose Environment

```bash
# Core
MODULE_PORT=8010
LOG_LEVEL=INFO
SECRET_KEY=docker-secret-key-min-32-chars-long

# Database (Docker hostname)
DATABASE_URL=postgresql://waddlebot:docker_password@postgres:5432/waddlebot

# Router Service (Docker hostname)
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Redis (Docker hostname)
REDIS_URL=redis://redis:6379/0
```

### Kubernetes Environment

```bash
# Core
MODULE_PORT=8010
LOG_LEVEL=INFO
SECRET_KEY=${SECRET_KEY_FROM_SECRET}

# Database (Kubernetes service DNS)
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres.waddlebot.svc.cluster.local:5432/waddlebot

# Router Service (Kubernetes service DNS)
CORE_API_URL=http://router-service.waddlebot.svc.cluster.local:8000
ROUTER_API_URL=http://router-service.waddlebot.svc.cluster.local:8000/api/v1/router

# Redis (Kubernetes service DNS)
REDIS_URL=redis://redis.waddlebot.svc.cluster.local:6379/0
```

### Production Environment

```bash
# Core
MODULE_PORT=8010
LOG_LEVEL=WARNING
SECRET_KEY=<STRONG_RANDOM_VALUE_FROM_SECRET_MANAGER>

# Database (Production RDS/Cloud SQL)
DATABASE_URL=postgresql://<USER>:<PASS>@<PROD_HOST>:5432/waddlebot_prod?sslmode=require

# Router Service (Production)
CORE_API_URL=https://router.production.internal:8000
ROUTER_API_URL=https://router.production.internal:8000/api/v1/router

# Redis (Production Cache)
REDIS_URL=redis://<USER>:<PASS>@<PROD_CACHE_HOST>:6379/0?ssl=true
```

---

## Configuration Files

### .env File (Local Development)

Create a `.env` file in the module root directory:

```bash
# action/interactive/alias_interaction_module/.env
MODULE_PORT=8010
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key-1234567890abcdefghijklmnop
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
CORE_API_URL=http://localhost:8000
ROUTER_API_URL=http://localhost:8000/api/v1/router
REDIS_URL=redis://localhost:6379/0
```

**Important:** Never commit .env to version control. Use .gitignore:

```
# .gitignore
.env
.env.local
.env.*.local
```

### .env.example (Template)

Commit this template to version control:

```bash
# action/interactive/alias_interaction_module/.env.example
MODULE_PORT=8010
LOG_LEVEL=INFO
SECRET_KEY=CHANGE_ME_IN_PRODUCTION
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router
REDIS_URL=redis://redis:6379/0
```

---

## Docker Configuration

### Dockerfile Environment

The Dockerfile sets the default command but uses environment variables:

```dockerfile
# Snippet from Dockerfile
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8010", "--workers", "4"]
```

### Docker Run Command

```bash
docker run -d \
  -e MODULE_PORT=8010 \
  -e LOG_LEVEL=INFO \
  -e SECRET_KEY="production-secret-key" \
  -e DATABASE_URL="postgresql://user:pass@postgres:5432/waddlebot" \
  -e CORE_API_URL="http://router-service:8000" \
  -e REDIS_URL="redis://redis:6379/0" \
  -p 8010:8010 \
  --name alias-interaction \
  waddlebot/alias-interaction:latest
```

### Docker Compose Services

```yaml
version: '3.8'
services:
  alias-interaction:
    image: waddlebot/alias-interaction:2.0.0
    container_name: alias-interaction
    environment:
      MODULE_PORT: "8010"
      LOG_LEVEL: "INFO"
      SECRET_KEY: "docker-compose-secret-key"
      DATABASE_URL: "postgresql://waddlebot:password@postgres:5432/waddlebot"
      CORE_API_URL: "http://router-service:8000"
      ROUTER_API_URL: "http://router-service:8000/api/v1/router"
      REDIS_URL: "redis://redis:6379/0"
    ports:
      - "8010:8010"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Kubernetes Configuration

### ConfigMap (Non-sensitive Configuration)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alias-interaction-config
  namespace: waddlebot
data:
  MODULE_PORT: "8010"
  LOG_LEVEL: "INFO"
  CORE_API_URL: "http://router-service.waddlebot.svc.cluster.local:8000"
  ROUTER_API_URL: "http://router-service.waddlebot.svc.cluster.local:8000/api/v1/router"
  REDIS_URL: "redis://redis.waddlebot.svc.cluster.local:6379/0"
```

### Secret (Sensitive Configuration)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alias-interaction-secrets
  namespace: waddlebot
type: Opaque
stringData:
  SECRET_KEY: "your-secret-key-from-vault"
  DATABASE_URL: "postgresql://user:password@postgres.waddlebot.svc.cluster.local:5432/waddlebot"
```

### Deployment (Using ConfigMap and Secret)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alias-interaction
  namespace: waddlebot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: alias-interaction
  template:
    metadata:
      labels:
        app: alias-interaction
    spec:
      containers:
      - name: alias-interaction
        image: waddlebot/alias-interaction:2.0.0
        ports:
        - containerPort: 8010
        envFrom:
        - configMapRef:
            name: alias-interaction-config
        - secretRef:
            name: alias-interaction-secrets
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: alias-interaction-secrets
              key: DATABASE_URL
        livenessProbe:
          httpGet:
            path: /health
            port: 8010
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8010
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Configuration Validation

### Check Current Configuration

```bash
# View loaded configuration
python3 -c "from config import Config; import pprint; pprint.pprint({
    'MODULE_NAME': Config.MODULE_NAME,
    'MODULE_VERSION': Config.MODULE_VERSION,
    'MODULE_PORT': Config.MODULE_PORT,
    'DATABASE_URL': Config.DATABASE_URL[:20] + '***',
    'LOG_LEVEL': Config.LOG_LEVEL,
})"
```

### Validate Database Connection

```bash
# Test PostgreSQL connection
export DATABASE_URL="postgresql://user:pass@localhost:5432/waddlebot"
python3 -c "
from config import Config
import psycopg2
try:
    conn = psycopg2.connect(Config.DATABASE_URL)
    print('Database connection: OK')
    conn.close()
except Exception as e:
    print(f'Database connection: FAILED - {e}')
"
```

### Validate Redis Connection

```bash
# Test Redis connection (if configured)
export REDIS_URL="redis://localhost:6379/0"
python3 -c "
from config import Config
import redis
if Config.REDIS_URL:
    try:
        r = redis.from_url(Config.REDIS_URL)
        r.ping()
        print('Redis connection: OK')
    except Exception as e:
        print(f'Redis connection: FAILED - {e}')
else:
    print('Redis: Not configured')
"
```

---

## Security Best Practices

1. **SECRET_KEY**
   - Generate cryptographically secure random value
   - Minimum 32 characters
   - Rotate regularly
   - Store in secret manager (HashiCorp Vault, AWS Secrets Manager, etc.)

2. **DATABASE_URL**
   - Use SSL/TLS for remote databases
   - Store credentials in secret manager
   - Use read-only database users where possible
   - Implement connection pooling limits

3. **REDIS_URL**
   - Use authentication if available
   - Enable TLS for remote Redis
   - Restrict network access to localhost or private network

4. **LOG_LEVEL**
   - Use WARNING or ERROR in production
   - Avoid DEBUG which may log sensitive data
   - Implement centralized logging

5. **General**
   - Never commit secrets to version control
   - Use environment variable files (.env) only in development
   - Implement secret rotation policies
   - Audit configuration changes

---

## Troubleshooting Configuration

### Database Connection Fails

```bash
# 1. Verify DATABASE_URL format
echo $DATABASE_URL

# 2. Test PostgreSQL connectivity
psql $(echo $DATABASE_URL | sed 's/postgresql:\/\///')

# 3. Check network access
ping <database_host>

# 4. View logs for detailed error
LOG_LEVEL=DEBUG python3 app.py
```

### Module Won't Start

```bash
# 1. Check all required env vars are set
env | grep -E "MODULE|DATABASE|REDIS"

# 2. Verify port is not in use
lsof -i :8010

# 3. Check logs
docker logs alias-interaction 2>&1 | tail -50
```

### Redis Listener Not Starting

```bash
# 1. Verify REDIS_URL format
echo $REDIS_URL

# 2. Test Redis connectivity
redis-cli -u $REDIS_URL ping

# 3. Check if Redis is optional
# If Redis is optional and unavailable, credential listener simply won't start
```

---

## Feature Flags

Currently, no feature flags are implemented. Future versions may add:

- Alias caching (enable/disable via env var)
- Rate limiting (enable/disable via env var)
- Advanced substitution (enable/disable via env var)

Check release notes for new feature flags.
