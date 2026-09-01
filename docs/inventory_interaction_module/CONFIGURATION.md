# Inventory Interaction Module - Configuration

## Environment Variables

All configuration for the Inventory Interaction Module is managed through environment variables.

### Required Variables

#### DATABASE_URL

**Type:** String  
**Default:** `postgresql://waddlebot:password@localhost:5432/waddlebot`  

PostgreSQL connection string for database access.

**Format:** `postgresql://[user]:[password]@[host]:[port]/[database]`

**Example:**
```bash
DATABASE_URL=postgresql://waddlebot:secure_password@db.example.com:5432/waddlebot
```

#### MODULE_PORT

**Type:** Integer  
**Default:** 8024

Port on which the Quart application listens.

**Example:**
```bash
MODULE_PORT=8024
```

### Optional Variables

#### CORE_API_URL

**Type:** String  
**Default:** `http://router-service:8000`

URL of the core API service for integration.

#### ROUTER_API_URL

**Type:** String  
**Default:** `http://router-service:8000/api/v1/router`

URL of the router service API.

#### LOG_LEVEL

**Type:** String  
**Default:** `INFO`  
**Valid Values:** DEBUG, INFO, WARNING, ERROR, CRITICAL

Logging level for application logs.

#### SECRET_KEY

**Type:** String  
**Default:** `change-me-in-production`

Secret key for session management and CSRF protection.

**Production Requirements:**
- Must be randomly generated
- Should be at least 32 characters
- Must be kept secure
- Should be rotated periodically

**Generate with Python:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

#### REDIS_URL

**Type:** String  
**Default:** `` (empty, Redis disabled)

Redis connection string for credential refresh notifications.

**Format:** `redis://[user]:[password]@[host]:[port]/[db]`

**Examples:**
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_URL=redis://user:password@redis.example.com:6379/0
```

## Configuration Examples

### Local Development .env

```bash
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
MODULE_PORT=8024
LOG_LEVEL=DEBUG
CORE_API_URL=http://localhost:8000
ROUTER_API_URL=http://localhost:8000/api/v1/router
SECRET_KEY=dev-key-only-insecure-changeme
REDIS_URL=redis://localhost:6379/0
```

### Docker Compose Environment

```yaml
services:
  inventory-interaction:
    environment:
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      MODULE_PORT: 8024
      LOG_LEVEL: INFO
      CORE_API_URL: http://router-service:8000
      ROUTER_API_URL: http://router-service:8000/api/v1/router
      SECRET_KEY: dev-secret-key
```

### Production Environment

```bash
DATABASE_URL=postgresql://waddlebot_prod:${SECURE_DB_PASSWORD}@db.prod.example.com:5432/waddlebot_prod
MODULE_PORT=8024
LOG_LEVEL=WARNING
CORE_API_URL=https://api.waddlebot.example.com
ROUTER_API_URL=https://api.waddlebot.example.com/api/v1/router
SECRET_KEY=${SECURE_SECRET_KEY}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis.prod.example.com:6379/1
```

## Docker Compose Full Example

```yaml
version: '3.8'

services:
  inventory-interaction:
    build:
      context: .
      dockerfile: action/interactive/inventory_interaction_module/Dockerfile
    container_name: inventory-interaction
    restart: unless-stopped
    ports:
      - "8024:8024"
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      MODULE_PORT: 8024
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      CORE_API_URL: http://router-service:8000
      ROUTER_API_URL: http://router-service:8000/api/v1/router
      SECRET_KEY: ${SECRET_KEY}
      REDIS_URL: ${REDIS_URL:-}
    volumes:
      - /var/log/waddlebotlog:/var/log/waddlebotlog
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8024/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - waddlebot

  postgres:
    image: postgres:15-alpine
    container_name: waddlebot-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-waddlebot}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-password}
      POSTGRES_DB: ${DB_NAME:-waddlebot}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - waddlebot

  redis:
    image: redis:7-alpine
    container_name: waddlebot-redis
    restart: unless-stopped
    networks:
      - waddlebot

volumes:
  postgres_data:

networks:
  waddlebot:
    driver: bridge
```

## Kubernetes Deployment

### ConfigMap for Non-Sensitive Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: inventory-config
  namespace: waddlebot
data:
  MODULE_PORT: "8024"
  LOG_LEVEL: "INFO"
  CORE_API_URL: "http://router-service:8000"
  ROUTER_API_URL: "http://router-service:8000/api/v1/router"
```

### Secret for Sensitive Configuration

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: inventory-secrets
  namespace: waddlebot
type: Opaque
stringData:
  DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
  SECRET_KEY: $(openssl rand -hex 32)
  REDIS_URL: redis://:password@redis:6379/0
```

## Load Order

Environment variables are loaded in this order:
1. .env file (if present)
2. System environment variables (override .env)
3. Hardcoded defaults in config.py

## Security Best Practices

### Credentials Management

Do NOT hardcode credentials. Use environment variables instead.

### Using Secrets Management

- Kubernetes Secrets
- AWS Secrets Manager
- HashiCorp Vault
- Environment-specific .env files (add to .gitignore)

### .env File Safety

Add to .gitignore:
```bash
.env
.env.local
*.env
```

### Production Checklist

- [ ] Change SECRET_KEY from default
- [ ] Use strong database password
- [ ] Use HTTPS for API URLs
- [ ] Enable Redis authentication
- [ ] Set LOG_LEVEL=WARNING (not DEBUG)
- [ ] Use environment-specific secrets
- [ ] Rotate credentials regularly
- [ ] Monitor error logs for security

## Database Configuration

### Connection Pool Settings

AsyncDAL connection pooling is configured with:
- Staging: pool_size=10
- Production: pool_size=20-30

### PostgreSQL Requirements

- Version: 13 or higher
- Max connections: >= 200
- Migration 014 applied

## Logging Configuration

### Log Levels

| Level | Usage | Output |
|-------|-------|--------|
| DEBUG | Development/detailed tracing | Verbose |
| INFO | Normal operations | Important events |
| WARNING | Degraded operation | Issues to monitor |
| ERROR | Failures | Error conditions |
| CRITICAL | System failures | Severe issues |

### Log File Location

Inside container: `/var/log/waddlebotlog/inventory_interaction_module.log`

Docker volume mapping: `-v /var/log/waddlebotlog:/var/log/waddlebotlog`

## Verification

### Check Configuration on Startup

```bash
# View Docker logs
docker logs inventory-interaction | head -20

# Check environment variables
docker exec inventory-interaction env | grep -E "^(DATABASE|MODULE|LOG)"

# Health check
curl http://localhost:8024/health
```

### Validate Database Connection

```bash
# From container
docker exec inventory-interaction psql $DATABASE_URL -c "SELECT version();"

# From host (if psql installed)
psql $DATABASE_URL -c "SELECT version();"
```

---

**Module**: inventory_interaction_module  
**Version**: 2.0.0  
**Last Updated**: 2026-02-16
