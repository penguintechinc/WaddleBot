# Module RTC — Configuration Guide

Complete reference for all configuration options, environment variables, and deployment settings for Module RTC.

## Configuration Methods

Module RTC supports configuration through environment variables. All settings have sensible defaults for development.

**Priority Order** (highest to lowest):
1. Environment variables
2. Hardcoded defaults in `internal/config/config.go`

## Environment Variables

### Module Configuration

#### MODULE_PORT
- **Type**: Integer
- **Default**: `8093`
- **Description**: HTTP REST API listen port
- **Example**: `export MODULE_PORT=8093`
- **Usage**: Public-facing port for clients

#### GRPC_PORT
- **Type**: Integer
- **Default**: `50067`
- **Description**: gRPC service listen port
- **Example**: `export GRPC_PORT=50067`
- **Usage**: Internal gRPC communication (future expansion)
- **Note**: From GRPC_PORT_VISUAL_REFERENCE.txt, port 50067 is reserved for module_rtc

#### MODULE_NAME
- **Type**: String
- **Default**: `module_rtc`
- **Description**: Module identifier
- **Example**: `export MODULE_NAME=module_rtc`
- **Usage**: Appears in health check responses, logging

#### MODULE_VERSION
- **Type**: String
- **Default**: `1.0.0`
- **Description**: Semantic version string
- **Example**: `export MODULE_VERSION=1.0.0`
- **Usage**: Version in health check, logging, compatibility

### LiveKit Configuration

#### LIVEKIT_HOST
- **Type**: String
- **Default**: `localhost:7880`
- **Description**: LiveKit server address with port
- **Example**: `export LIVEKIT_HOST=livekit.example.com:7880`
- **Usage**: Connect to LiveKit SFU
- **Required**: Yes (module starts with warning if missing)
- **Note**: Must be accessible from Module RTC container

#### LIVEKIT_API_KEY
- **Type**: String
- **Default**: Empty string
- **Description**: LiveKit API key for authentication
- **Example**: `export LIVEKIT_API_KEY=devkey123456`
- **Usage**: Authenticate to LiveKit room/participant APIs
- **Required**: Yes for production
- **Security**: Never commit to version control, use secrets management
- **Obtaining**: Generated in LiveKit admin panel

#### LIVEKIT_API_SECRET
- **Type**: String
- **Default**: Empty string
- **Description**: LiveKit API secret (private key)
- **Example**: `export LIVEKIT_API_SECRET=devsecret789xyz`
- **Usage**: HMAC signing for token generation
- **Required**: Yes for production
- **Security**: Highly sensitive, use secrets vault
- **Note**: Used to sign JWT tokens for client authentication

### Database Configuration

#### DATABASE_URL
- **Type**: PostgreSQL connection string
- **Default**: `postgres://waddlebot:password@localhost:5432/waddlebot`
- **Example**: `export DATABASE_URL=postgres://user:pass@db.example.com:5432/waddlebot_prod`
- **Format**: `postgres://username:password@host:port/database`
- **Usage**: Persist room and participant data
- **Required**: No (optional for future database-backed features)
- **Connection Pooling**: Implement at reverse proxy level

**Connection String Components**:
- **username**: PostgreSQL user (default: waddlebot)
- **password**: PostgreSQL password
- **host**: Database server hostname
- **port**: PostgreSQL port (default: 5432)
- **database**: Database name (default: waddlebot)

**Connection Pool Settings** (for production):
- Min connections: 5
- Max connections: 20
- Connection timeout: 30s
- Idle timeout: 5m

### Logging Configuration

#### LOG_LEVEL
- **Type**: String
- **Default**: `INFO`
- **Valid Values**: `DEBUG`, `INFO`, `WARN`, `ERROR`
- **Example**: `export LOG_LEVEL=DEBUG`
- **Usage**: Control logging verbosity
- **Recommended**:
  - **Development**: `DEBUG`
  - **Staging**: `INFO`
  - **Production**: `WARN` or `ERROR`

**Log Output**:
- Sent to stdout
- Structured JSON (one per line)
- Includes timestamp, level, module, message

### API Configuration

#### HUB_API_URL
- **Type**: String
- **Default**: `http://hub-api:8060`
- **Example**: `export HUB_API_URL=https://hub.example.com`
- **Usage**: Community metadata and event notifications
- **Required**: No (optional for hub integration)
- **Note**: Used by event webhooks

## Configuration Examples

### Development Environment

Create `.env.development`:

```bash
# Module
MODULE_PORT=8093
GRPC_PORT=50067
MODULE_NAME=module_rtc
MODULE_VERSION=1.0.0
LOG_LEVEL=DEBUG

# LiveKit (development server)
LIVEKIT_HOST=localhost:7880
LIVEKIT_API_KEY=devkey123
LIVEKIT_API_SECRET=devsecret456

# Database (local PostgreSQL)
DATABASE_URL=postgres://waddlebot:waddlebot@localhost:5432/waddlebot

# Hub
HUB_API_URL=http://localhost:8060
```

Load with:
```bash
export $(cat .env.development | xargs)
go run ./cmd/server/main.go
```

### Staging Environment

Create `.env.staging`:

```bash
# Module
MODULE_PORT=8093
GRPC_PORT=50067
MODULE_NAME=module_rtc
MODULE_VERSION=1.0.0
LOG_LEVEL=INFO

# LiveKit (staging server)
LIVEKIT_HOST=livekit-staging.penguintech.cloud:7880
LIVEKIT_API_KEY=${LIVEKIT_API_KEY_STAGING}  # From CI/CD secrets
LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET_STAGING}

# Database (staging PostgreSQL)
DATABASE_URL=${DATABASE_URL_STAGING}

# Hub
HUB_API_URL=https://hub-staging.penguintech.cloud
```

### Production Environment

Create `.env.production`:

```bash
# Module
MODULE_PORT=8093
GRPC_PORT=50067
MODULE_NAME=module_rtc
MODULE_VERSION=1.0.0
LOG_LEVEL=WARN

# LiveKit (production cluster)
LIVEKIT_HOST=livekit-prod.penguintech.cloud:7880
LIVEKIT_API_KEY=${LIVEKIT_API_KEY_PROD}  # From secure vault
LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET_PROD}

# Database (production PostgreSQL with replication)
DATABASE_URL=${DATABASE_URL_PROD}

# Hub
HUB_API_URL=https://hub.penguintech.cloud
```

## Docker Configuration

### Docker Run

```bash
docker run \
  -p 8093:8093 \
  -p 50067:50067 \
  -e MODULE_PORT=8093 \
  -e GRPC_PORT=50067 \
  -e LIVEKIT_HOST=livekit:7880 \
  -e LIVEKIT_API_KEY=key123 \
  -e LIVEKIT_API_SECRET=secret456 \
  -e DATABASE_URL=postgres://user:pass@postgres:5432/waddlebot \
  -e LOG_LEVEL=INFO \
  waddlebot/module-rtc:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  module-rtc:
    image: waddlebot/module-rtc:latest
    container_name: module-rtc
    ports:
      - "${MODULE_PORT:-8093}:8093"
      - "${GRPC_PORT:-50067}:50067"
    environment:
      # Module configuration
      MODULE_PORT: ${MODULE_PORT:-8093}
      GRPC_PORT: ${GRPC_PORT:-50067}
      MODULE_NAME: module_rtc
      MODULE_VERSION: ${MODULE_VERSION:-1.0.0}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}

      # LiveKit
      LIVEKIT_HOST: ${LIVEKIT_HOST:-livekit:7880}
      LIVEKIT_API_KEY: ${LIVEKIT_API_KEY}
      LIVEKIT_API_SECRET: ${LIVEKIT_API_SECRET}

      # Database
      DATABASE_URL: ${DATABASE_URL:-postgres://waddlebot:password@postgres:5432/waddlebot}

      # Hub API
      HUB_API_URL: ${HUB_API_URL:-http://hub-api:8060}

    depends_on:
      - postgres
      - livekit

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8093/health"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 5s

    networks:
      - waddlebot

    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: module-rtc-postgres
    environment:
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      POSTGRES_DB: waddlebot
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./config/postgres/migrations:/docker-entrypoint-initdb.d
    networks:
      - waddlebot
    restart: unless-stopped

  livekit:
    image: livekit/livekit-server:latest
    container_name: module-rtc-livekit
    command: --dev --ip=0.0.0.0
    ports:
      - "7880:7880"
      - "7881:7881"
      - "7882:7882/udp"
    networks:
      - waddlebot
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  waddlebot:
    driver: bridge
```

Load environment from `.env` file:
```bash
docker-compose --env-file .env.staging up -d
```

## Kubernetes Configuration

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: module-rtc-config
  namespace: waddlebot
data:
  MODULE_PORT: "8093"
  GRPC_PORT: "50067"
  MODULE_NAME: "module_rtc"
  MODULE_VERSION: "1.0.0"
  LOG_LEVEL: "INFO"
  LIVEKIT_HOST: "livekit.waddlebot.svc.cluster.local:7880"
  HUB_API_URL: "http://hub-api.waddlebot.svc.cluster.local:8060"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: module-rtc-secrets
  namespace: waddlebot
type: Opaque
stringData:
  LIVEKIT_API_KEY: "your-api-key"
  LIVEKIT_API_SECRET: "your-api-secret"
  DATABASE_URL: "postgres://user:pass@postgres:5432/waddlebot"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: module-rtc
  namespace: waddlebot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: module-rtc
  template:
    metadata:
      labels:
        app: module-rtc
    spec:
      containers:
      - name: module-rtc
        image: registry.example.com/waddlebot/module-rtc:1.0.0
        ports:
        - containerPort: 8093
          name: http
        - containerPort: 50067
          name: grpc

        # Load from ConfigMap
        envFrom:
        - configMapRef:
            name: module-rtc-config

        # Load sensitive from Secret
        env:
        - name: LIVEKIT_API_KEY
          valueFrom:
            secretKeyRef:
              name: module-rtc-secrets
              key: LIVEKIT_API_KEY
        - name: LIVEKIT_API_SECRET
          valueFrom:
            secretKeyRef:
              name: module-rtc-secrets
              key: LIVEKIT_API_SECRET
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: module-rtc-secrets
              key: DATABASE_URL

        livenessProbe:
          httpGet:
            path: /health
            port: 8093
          initialDelaySeconds: 10
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /health
            port: 8093
          initialDelaySeconds: 5
          periodSeconds: 5

        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Configuration Validation

### Required vs Optional

**Required for Production**:
- `LIVEKIT_HOST`: Must be set and accessible
- `LIVEKIT_API_KEY`: Cannot be empty
- `LIVEKIT_API_SECRET`: Cannot be empty

**Recommended for Production**:
- `LOG_LEVEL`: Set to `WARN` or `ERROR`
- `DATABASE_URL`: For persistent storage

**Optional**:
- `MODULE_PORT`: Use default (8093) unless port conflict
- `GRPC_PORT`: Use default (50067) unless port conflict
- `HUB_API_URL`: Only if using event notifications

### Startup Validation

Module RTC performs these checks on startup:

```go
if cfg.LiveKitAPIKey == "" || cfg.LiveKitAPISecret == "" {
    log.Println("WARNING: LiveKit API credentials not configured")
}
```

If credentials are missing, module still starts but cannot create rooms.

## Secrets Management

### Development (Local)

Use `.env` file (add to `.gitignore`):
```bash
echo ".env.local" >> .gitignore
echo "LIVEKIT_API_SECRET=dev_secret_123" > .env.local
source .env.local
```

### Docker (Development)

Use `docker-compose.override.yml`:
```yaml
services:
  module-rtc:
    environment:
      LIVEKIT_API_KEY: dev_key
      LIVEKIT_API_SECRET: dev_secret
      DATABASE_URL: postgres://waddlebot:password@postgres:5432/waddlebot
```

### Kubernetes (Production)

Use sealed secrets or HashiCorp Vault:

```bash
# Using kubectl secrets
kubectl create secret generic module-rtc-secrets \
  --from-literal=LIVEKIT_API_KEY=$LIVEKIT_API_KEY \
  --from-literal=LIVEKIT_API_SECRET=$LIVEKIT_API_SECRET \
  -n waddlebot

# Using sealed-secrets
kubeseal -f secret.yaml -w sealed-secret.yaml
```

## Port Mapping

### Standard Ports

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Module RTC HTTP | 8093 | HTTP | REST API |
| Module RTC gRPC | 50067 | gRPC | Internal services |
| LiveKit WS | 7880 | WebSocket | WebRTC signaling |
| LiveKit RTC | 7881 | TCP | WebRTC control |
| LiveKit Media | 7882 | UDP | WebRTC media |
| PostgreSQL | 5432 | TCP | Database |
| Redis | 6379 | TCP | Cache |

### Port Forwarding (Development)

```bash
# Forward local port to remote container
kubectl port-forward -n waddlebot svc/module-rtc 8093:8093 &

# Access: http://localhost:8093
```

## Monitoring Configuration

### Prometheus Metrics (Future)

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'module-rtc'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
```

### Health Check Integration

```bash
# HAProxy
backend module_rtc
    balance roundrobin
    option httpchk GET /health HTTP/1.1
    server rtc1 10.0.0.1:8093 check inter 10s
    server rtc2 10.0.0.2:8093 check inter 10s
    server rtc3 10.0.0.3:8093 check inter 10s
```

## Troubleshooting Configuration

### Check Active Configuration

```bash
# View environment in running container
docker exec module-rtc env | grep -E "^(MODULE|GRPC|LIVEKIT|DATABASE|LOG)"

# Check logs for config loading
docker logs module-rtc | head -20
```

### Validate LiveKit Connection

```bash
# Test LiveKit connectivity from container
docker exec module-rtc \
  curl -s http://livekit:7880/twirp/livekit.RoomService/ListRooms

# Or test from host
curl -v http://livekit.example.com:7880
```

### Test API

```bash
# Health check
curl http://localhost:8093/health

# Create room (will fail if LiveKit misconfigured)
curl -X POST http://localhost:8093/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{"community_id":1,"room_name":"test"}'
```

## Performance Tuning

### Recommended Settings for Load

**Light Load** (100s of participants):
```bash
MODULE_PORT=8093
LOG_LEVEL=INFO
# Single instance sufficient
```

**Medium Load** (1000+ participants):
```bash
MODULE_PORT=8093
LOG_LEVEL=WARN
# 2-3 instances behind load balancer
# Increase PostgreSQL pool to 10-15
```

**High Load** (10000+ participants):
```bash
MODULE_PORT=8093
LOG_LEVEL=ERROR
# 5-10 instances behind load balancer
# PostgreSQL read replicas
# Redis for state distribution
# Consider dedicated LiveKit cluster
```

## Upgrading Configuration

When upgrading versions:
1. Review `.env` against new defaults
2. Check for new environment variables in release notes
3. Test in staging first
4. Perform rolling update (K8s) or blue-green (Docker)
5. Verify health check passes
6. Monitor logs for warnings
