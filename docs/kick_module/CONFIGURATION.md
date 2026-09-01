# Kick Module Configuration Guide

## Environment Variables

All configuration is provided via environment variables. The module loads from `.env` file during development and from orchestration platform (Kubernetes, Docker) in production.

### Core Service Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MODULE_PORT` | int | 8007 | Yes | HTTP server listen port |
| `LOG_LEVEL` | string | INFO | No | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `SECRET_KEY` | string | (none) | Yes | Session encryption key (min 32 chars, use `openssl rand -base64 32`) |

### Database Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATABASE_URL` | string | (none) | Yes | PostgreSQL connection string: `postgresql://user:pass@host:5432/dbname` |
| `DB_POOL_SIZE` | int | 10 | No | Connection pool size |
| `DB_POOL_OVERFLOW` | int | 5 | No | Additional overflow connections |
| `DB_POOL_TIMEOUT` | int | 30 | No | Connection timeout (seconds) |

### API Integration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CORE_API_URL` | string | (none) | Yes | Core API endpoint (e.g., `http://core-api:8000`) |
| `ROUTER_API_URL` | string | (none) | Yes | Router API endpoint (e.g., `http://router-api:8001`) |
| `ROUTER_TIMEOUT` | int | 10 | No | Router API request timeout (seconds) |
| `API_REQUEST_TIMEOUT` | int | 10 | No | Default HTTP request timeout (seconds) |

### Kick Platform Integration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `KICK_WEBHOOK_SECRET` | string | (none) | Yes | Webhook HMAC secret from Kick dashboard (min 32 chars) |
| `KICK_PUSHER_KEY` | string | eb1d5f283081a78b932c | No | Pusher application key (usually fixed by Kick) |
| `KICK_PUSHER_CLUSTER` | string | us2 | No | Pusher cluster region (us2 is default for Kick) |

### Cache & Session Storage

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `REDIS_URL` | string | (none) | No | Redis connection string (e.g., `redis://localhost:6379/0`) |
| `CACHE_TTL` | int | 3600 | No | Cache time-to-live (seconds) |
| `SESSION_TIMEOUT` | int | 86400 | No | Session timeout (seconds) |

### Performance & Limits

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MAX_CONNECTIONS` | int | 100 | No | Max concurrent HTTP connections |
| `MAX_BATCH_SIZE` | int | 50 | No | Max events per batch to Router |
| `BATCH_TIMEOUT` | float | 0.5 | No | Max wait time for batch (seconds) |
| `WEBHOOK_TIMEOUT` | int | 5 | No | Webhook processing timeout (seconds) |

### Debugging & Development

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DEBUG` | bool | false | No | Enable debug mode (detailed errors) |
| `KICK_DEBUG_SIGNATURES` | bool | false | No | Log signature verification details |
| `MOCK_MODE` | bool | false | No | Use mock data instead of real API calls |
| `SKIP_ROUTER` | bool | false | No | Don't forward events to Router (testing) |

## Configuration Examples

### Development Environment (.env)

```bash
# Server
MODULE_PORT=8007
LOG_LEVEL=DEBUG
SECRET_KEY=$(openssl rand -base64 32)
DEBUG=true

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/waddlebot_dev
DB_POOL_SIZE=5
DB_POOL_OVERFLOW=2

# APIs
CORE_API_URL=http://localhost:8000
ROUTER_API_URL=http://localhost:8001
ROUTER_TIMEOUT=10

# Kick Platform
KICK_WEBHOOK_SECRET=$(openssl rand -base64 32)
KICK_PUSHER_KEY=eb1d5f283081a78b932c
KICK_PUSHER_CLUSTER=us2

# Cache
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Development
KICK_DEBUG_SIGNATURES=true
SKIP_ROUTER=false
```

### Production Environment

```bash
# Server
MODULE_PORT=8007
LOG_LEVEL=INFO
SECRET_KEY=<use-secrets-manager>
DEBUG=false

# Database
DATABASE_URL=postgresql://<prod-user>:<prod-pass>@postgres-prod:5432/waddlebot
DB_POOL_SIZE=20
DB_POOL_OVERFLOW=10
DB_POOL_TIMEOUT=30

# APIs
CORE_API_URL=https://core-api.penguintech.cloud
ROUTER_API_URL=https://router-api.penguintech.cloud
ROUTER_TIMEOUT=15

# Kick Platform
KICK_WEBHOOK_SECRET=<use-secrets-manager>
KICK_PUSHER_KEY=eb1d5f283081a78b932c
KICK_PUSHER_CLUSTER=us2

# Cache
REDIS_URL=redis://:password@redis-prod:6379/0
CACHE_TTL=7200

# Performance
MAX_CONNECTIONS=200
MAX_BATCH_SIZE=100
BATCH_TIMEOUT=0.2
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  kick-module:
    image: waddlebot/kick-module:latest
    ports:
      - "8007:8007"
    environment:
      MODULE_PORT: 8007
      LOG_LEVEL: INFO
      SECRET_KEY: ${SECRET_KEY}
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/waddlebot
      CORE_API_URL: http://core-api:8000
      ROUTER_API_URL: http://router-api:8001
      KICK_WEBHOOK_SECRET: ${KICK_WEBHOOK_SECRET}
      KICK_PUSHER_KEY: eb1d5f283081a78b932c
      KICK_PUSHER_CLUSTER: us2
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      - core-api
      - router-api
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8007/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: waddlebot
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes ConfigMap Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kick-module-config
  namespace: waddlebot
data:
  MODULE_PORT: "8007"
  LOG_LEVEL: "INFO"
  CORE_API_URL: "http://core-api:8000"
  ROUTER_API_URL: "http://router-api:8001"
  KICK_PUSHER_KEY: "eb1d5f283081a78b932c"
  KICK_PUSHER_CLUSTER: "us2"
  DB_POOL_SIZE: "20"
  MAX_CONNECTIONS: "200"

---
apiVersion: v1
kind: Secret
metadata:
  name: kick-module-secrets
  namespace: waddlebot
type: Opaque
stringData:
  SECRET_KEY: "your-secret-key-here"
  KICK_WEBHOOK_SECRET: "your-webhook-secret-here"
  DATABASE_URL: "postgresql://user:pass@postgres:5432/waddlebot"
  REDIS_URL: "redis://redis:6379/0"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kick-module
  namespace: waddlebot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kick-module
  template:
    metadata:
      labels:
        app: kick-module
    spec:
      containers:
      - name: kick-module
        image: waddlebot/kick-module:latest
        ports:
        - containerPort: 8007
        envFrom:
        - configMapRef:
            name: kick-module-config
        - secretRef:
            name: kick-module-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8007
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/status
            port: 8007
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

## Secret Management

### Generating Secure Secrets

```bash
# Generate SECRET_KEY
openssl rand -base64 32

# Generate KICK_WEBHOOK_SECRET
openssl rand -base64 32

# For Kubernetes, create secret:
kubectl create secret generic kick-module-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -base64 32) \
  --from-literal=KICK_WEBHOOK_SECRET=$(openssl rand -base64 32) \
  --from-literal=DATABASE_URL="postgresql://..." \
  --from-literal=REDIS_URL="redis://..."
```

### Using AWS Secrets Manager

```bash
# Store secrets
aws secretsmanager create-secret \
  --name waddlebot/kick-module \
  --secret-string '{
    "SECRET_KEY": "...",
    "KICK_WEBHOOK_SECRET": "...",
    "DATABASE_URL": "..."
  }'

# Fetch in deployment script
SECRET=$(aws secretsmanager get-secret-value \
  --secret-id waddlebot/kick-module \
  --query SecretString --output text)
```

## Network Configuration

### Firewall Rules

For Docker/host deployments:

```bash
# Allow webhook inbound
ufw allow 8007/tcp from any to any

# Allow outbound to Kick APIs
ufw allow out to api.kick.com
ufw allow out to pusher.us2.pusher.com

# Allow outbound to internal services
ufw allow out to 10.0.0.0/8  # Internal network
```

### Load Balancer Configuration

For HTTPS/proxying:

```nginx
# Nginx upstream
upstream kick_module {
    server kick-module-1:8007;
    server kick-module-2:8007;
    server kick-module-3:8007;
}

server {
    listen 443 ssl;
    server_name webhook.waddlebot.io;

    # Webhook endpoint (accepts POST only)
    location /webhook/kick {
        proxy_pass http://kick_module;
        proxy_method POST;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;

        # Important: Don't modify X-Signature header
        proxy_pass_header X-Signature;

        # Webhook timeout
        proxy_read_timeout 10s;
        proxy_connect_timeout 5s;
    }

    # Status endpoints (read-only)
    location ~ ^/(health|api/v1/status|metrics)$ {
        proxy_pass http://kick_module;
        proxy_method GET;
        access_log off;  # Skip metrics in access logs
    }
}
```

## Validation & Testing Configuration

```bash
# Validate DATABASE_URL syntax
psql $DATABASE_URL -c "SELECT 1;"

# Validate API endpoints are reachable
curl -I $CORE_API_URL/health
curl -I $ROUTER_API_URL/health

# Test Redis connection
redis-cli -u $REDIS_URL ping

# Verify Pusher connectivity
curl https://api.pusherapp.com/apps/[app-id]/channels

# Validate webhook secret format (must be 32+ chars)
if [ ${#KICK_WEBHOOK_SECRET} -lt 32 ]; then
    echo "ERROR: KICK_WEBHOOK_SECRET must be at least 32 characters"
    exit 1
fi
```

## Configuration Migration

### Upgrading Configuration

When updating the module, check for new required variables:

```bash
# Compare current env vars with module requirements
diff <(grep -o '^[A-Z_]*=' .env | sort) \
     <(grep -o '^[A-Z_]*' trigger/receiver/kick_module_flask/config.py | sort)

# Missing variables will be listed
```

### Backward Compatibility

Configuration is backward compatible within minor versions. When upgrading:

1. Review RELEASE_NOTES.md for breaking changes
2. Add any new required environment variables
3. Preserve existing variable values
4. Test in staging before production deployment

## See Also

- [API Documentation](API.md)
- [Usage Guide](USAGE.md)
- [Architecture Details](ARCHITECTURE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
