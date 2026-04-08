# Credential Manager Module - Deployment Guide

Complete deployment guide for the Credential Manager microservice.

## Overview

The Credential Manager is a critical infrastructure component that automatically refreshes OAuth2 tokens across all streaming platforms. It runs as a standalone microservice with:

- Async token refresh polling
- Per-platform OAuth handlers
- Exponential backoff retry logic
- Redis pub/sub integration
- Comprehensive health checks

## Prerequisites

### System Requirements
- Python 3.13+
- PostgreSQL 13+
- Redis 6.0+
- Network access to OAuth endpoints (Twitch, Discord, Slack, Google, Spotify, Kick)

### Dependencies

All dependencies specified in `requirements.txt`:
```
quart>=0.19.0
hypercorn>=0.15.0
asyncpg>=0.29.0
psycopg[binary]>=3.1.0
redis>=5.0.0
httpx>=0.26.0
python-json-logger>=2.0.0
cryptography>=41.0.0
typing-extensions>=4.8.0
```

## Docker Deployment

### Building the Image

```bash
docker build -f core/credential_manager_module/Dockerfile \
  -t waddlebot/credential-manager:latest .
```

Multi-architecture build (for ARM64 and AMD64):
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f core/credential_manager_module/Dockerfile \
  -t waddlebot/credential-manager:latest \
  --push .
```

### Running Container

Development:
```bash
docker run -it --rm \
  -e DATABASE_URL=postgresql://user:pass@db:5432/waddlebot \
  -e REDIS_URL=redis://redis:6379/0 \
  -e LOG_LEVEL=DEBUG \
  -p 8095:8095 \
  waddlebot/credential-manager:latest
```

Production:
```bash
docker run -d \
  --restart unless-stopped \
  --name credential-manager \
  -e DATABASE_URL=postgresql://mod_credential_manager:${DB_PASS}@db:5432/waddlebot \
  -e REDIS_URL=redis://redis:6379/0 \
  -e TOKEN_REFRESH_BUFFER=300 \
  -e POLL_INTERVAL=60 \
  -e LOG_LEVEL=INFO \
  -p 8095:8095 \
  --health-cmd='curl -f http://localhost:8095/health' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  waddlebot/credential-manager:latest
```

### Docker Compose Integration

Add to `docker-compose.yml`:

```yaml
credential-manager:
  image: waddlebot/credential-manager:latest
  container_name: credential-manager
  environment:
    DATABASE_URL: ${DATABASE_URL}
    REDIS_URL: ${REDIS_URL}
    TOKEN_REFRESH_BUFFER: 300
    POLL_INTERVAL: 60
    MAX_REFRESH_RETRIES: 3
    RETRY_BACKOFF_BASE: 5
    LOG_LEVEL: INFO
  ports:
    - "8095:8095"
  depends_on:
    - postgres
    - redis
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8095/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  networks:
    - waddlebot-network
  restart: unless-stopped
```

## Kubernetes Deployment

### Service Manifest

```yaml
apiVersion: v1
kind: Service
metadata:
  name: credential-manager
  namespace: waddlebot
spec:
  selector:
    app: credential-manager
  ports:
    - name: http
      port: 8095
      targetPort: 8095
  type: ClusterIP
```

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: credential-manager
  namespace: waddlebot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: credential-manager
  template:
    metadata:
      labels:
        app: credential-manager
    spec:
      containers:
        - name: credential-manager
          image: waddlebot/credential-manager:latest
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8095
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: database-credentials
                  key: url
            - name: REDIS_URL
              valueFrom:
                configMapKeyRef:
                  name: redis-config
                  key: url
            - name: TOKEN_REFRESH_BUFFER
              value: "300"
            - name: POLL_INTERVAL
              value: "60"
            - name: LOG_LEVEL
              value: "INFO"
          livenessProbe:
            httpGet:
              path: /health
              port: 8095
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
          readinessProbe:
            httpGet:
              path: /health
              port: 8095
            initialDelaySeconds: 10
            periodSeconds: 5
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

### ConfigMap for Redis

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
  namespace: waddlebot
data:
  url: redis://redis-service:6379/0
```

### Database Secret

```bash
kubectl create secret generic database-credentials \
  --from-literal=url="postgresql://mod_credential_manager:${PASSWORD}@postgres:5432/waddlebot" \
  -n waddlebot
```

## Environment Configuration

### Required Variables

```bash
# Database connection
DATABASE_URL=postgresql://mod_credential_manager:password@localhost:5432/waddlebot

# Redis for pub/sub
REDIS_URL=redis://localhost:6379/0
```

### Optional Variables

```bash
# Refresh behavior
TOKEN_REFRESH_BUFFER=300          # Seconds before expiry to refresh (default: 300)
POLL_INTERVAL=60                  # Check interval in seconds (default: 60)
MAX_REFRESH_RETRIES=3             # Max retry attempts (default: 3)
RETRY_BACKOFF_BASE=5              # Backoff multiplier (default: 5)

# Server
MODULE_PORT=8095                  # REST API port (default: 8095)

# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR (default: INFO)

# Redis
REDIS_KEY_PREFIX=credentials:     # Pub/sub channel prefix (default: credentials:)
```

## Database Setup

### Create Scoped User

```sql
CREATE USER mod_credential_manager WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE waddlebot TO mod_credential_manager;
GRANT USAGE ON SCHEMA public TO mod_credential_manager;
GRANT SELECT, UPDATE ON TABLE platform_integrations TO mod_credential_manager;
```

### Required Table

The service requires `platform_integrations` table with schema:

```sql
CREATE TABLE IF NOT EXISTS platform_integrations (
  id SERIAL PRIMARY KEY,
  platform VARCHAR(50) NOT NULL,
  integration_type VARCHAR(50) NOT NULL,
  community_id INTEGER,
  user_id INTEGER,
  access_token TEXT,
  refresh_token TEXT,
  client_id VARCHAR(255),
  client_secret TEXT,
  token_type VARCHAR(50),
  expires_at TIMESTAMP WITH TIME ZONE,
  scopes TEXT[],
  config_data JSONB,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(platform, integration_type, community_id, user_id)
);

CREATE INDEX idx_platform_integrations_active_expiring
  ON platform_integrations(is_active, expires_at)
  WHERE is_active = true AND expires_at IS NOT NULL;
```

## Health Checks

### Manual Health Check

```bash
curl http://localhost:8095/health
```

Expected response:
```json
{
  "status": "healthy",
  "module": "credential_manager",
  "version": "1.0.0",
  "running": true,
  "last_cycle": "2025-02-05T10:30:15.123456Z",
  "total_refreshed": 42,
  "total_errors": 2
}
```

### Monitoring Endpoints

Status check:
```bash
curl http://localhost:8095/api/v1/credentials/status
```

Force refresh:
```bash
curl -X POST http://localhost:8095/api/v1/credentials/refresh-now
```

## Performance Tuning

### Connection Pooling

Default: 2-5 PostgreSQL connections

For high-load environments, adjust in code:
```python
asyncpg.create_pool(
    url,
    min_size=5,   # Increase from 2
    max_size=10,  # Increase from 5
)
```

### Polling Interval

- **Low frequency**: POLL_INTERVAL=300 (5 minutes) - reduced load
- **Standard**: POLL_INTERVAL=60 (1 minute) - balanced
- **High frequency**: POLL_INTERVAL=10 (10 seconds) - maximum responsiveness

### Token Refresh Buffer

- **Conservative**: TOKEN_REFRESH_BUFFER=600 (10 min before expiry)
- **Standard**: TOKEN_REFRESH_BUFFER=300 (5 min before expiry)
- **Aggressive**: TOKEN_REFRESH_BUFFER=60 (1 min before expiry)

## Monitoring & Logging

### Log Levels

- **DEBUG**: All operations logged (verbose, production not recommended)
- **INFO**: Normal operations (default, recommended)
- **WARNING**: Issues that need attention
- **ERROR**: Failures

### Log Parsing

Logs include timestamps, module name, level, and message:
```
2025-02-05 10:30:15 [credential_manager.services.refresh_service] INFO: Refresh cycle: 5 tokens refreshed
```

### Metrics

Access via `/api/v1/credentials/status`:
- Total credentials by platform
- Expiring soon count
- Expired count

## Troubleshooting

### Service Won't Start

Check logs for:
```
docker logs credential-manager
```

Common issues:
1. **DATABASE_URL invalid**: Verify format and credentials
2. **REDIS_URL invalid**: Verify Redis is running
3. **Port conflict**: 8095 already in use

### Tokens Not Refreshing

Check:
1. Service is running: `curl http://localhost:8095/health`
2. Database has active credentials: `SELECT COUNT(*) FROM platform_integrations WHERE is_active=true`
3. Token expiry times are valid: `SELECT MIN(expires_at) FROM platform_integrations`
4. POLL_INTERVAL is reasonable (not 0)

### High Error Rate

Check:
1. OAuth provider endpoints reachable: `curl https://id.twitch.tv/oauth2/token -I`
2. Client credentials valid in database
3. Network connectivity from container
4. OAuth provider rate limits not exceeded

### Memory Usage High

Reduce:
- POLL_INTERVAL (less frequent checks)
- Database pool size
- Redis cache

## Security

### Best Practices

1. **Never log credentials**: Verify LOG_LEVEL != DEBUG with real credentials
2. **Use secrets backend**: Store DB and OAuth credentials securely
3. **Network isolation**: Restrict access to service to internal network only
4. **Token encryption**: Credentials stored encrypted in database
5. **HTTPS**: Use reverse proxy with HTTPS in production

### Secret Management

Store sensitive config in Kubernetes secrets or environment:

```bash
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...
docker run -e DATABASE_URL -e REDIS_URL credential-manager
```

## Backup & Recovery

### Database Backup

```bash
pg_dump -U mod_credential_manager waddlebot > credentials_backup.sql
```

### Important Notes

- Service is stateless (state in database)
- No local caching of tokens
- Safe to scale horizontally
- Redis is for pub/sub only (not state)

## Updates & Upgrades

### Pulling New Image

```bash
docker pull waddlebot/credential-manager:latest
```

### Rolling Update (Kubernetes)

```bash
kubectl set image deployment/credential-manager \
  credential-manager=waddlebot/credential-manager:v2.0.0 \
  -n waddlebot --record
```

### Rollback (if needed)

```bash
kubectl rollout undo deployment/credential-manager -n waddlebot
```

## Support & Debugging

### Enable Debug Logging

```bash
docker run -e LOG_LEVEL=DEBUG credential-manager
```

### Force Refresh Cycle

```bash
curl -X POST http://localhost:8095/api/v1/credentials/refresh-now
```

### Check Service Status

```bash
curl http://localhost:8095/health | jq .
```

For additional support, see main [README](README.md) and [Waddlebot Documentation](../../docs/).
