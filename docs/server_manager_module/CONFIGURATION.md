# Server Manager Interaction Module - Configuration

## Environment Variables

All configuration is managed through environment variables. No configuration files are written to disk.

---

### Required Variables

#### `DATABASE_URL`

**Type:** String

PostgreSQL connection string.

**Format:** `postgresql://[user]:[password]@[host]:[port]/[database]`

```bash
DATABASE_URL=postgresql://waddlebot:secure_password@db.example.com:5432/waddlebot
```

---

#### `MODULE_PORT`

**Type:** Integer
**Default:** `8098`

Port on which the Quart application listens.

```bash
MODULE_PORT=8098
```

---

#### `RCON_ENCRYPTION_KEY`

**Type:** String (64-character hexadecimal)
**Required:** Yes — module cannot decrypt server credentials without it

AES-256-GCM key used to decrypt RCON/voice server credentials stored in the database. Must be identical to the value configured in the hub backend (`rconController.js`).

**Generate a key:**
```bash
openssl rand -hex 32
# Example output: a3f1c2e4...  (64 hex chars = 32 bytes = 256 bits)
```

```bash
RCON_ENCRYPTION_KEY=a3f1c2e4b5d6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2
```

**Important:** Rotating this key invalidates all stored encrypted credentials. After rotation, all server passwords must be re-entered via the hub frontend.

---

### Recommended Variables

#### `SECURITY_CORE_URL`

**Type:** String
**Default:** `http://security-core:8090`

Base URL of the `security_core_module`. Used when syncing bans to the global security layer.

```bash
SECURITY_CORE_URL=http://security-core:8090
```

---

#### `RCON_CONNECTION_TTL`

**Type:** Integer (seconds)
**Default:** `60`

Time-to-live for idle RCON connections in the connection pool. Connections idle longer than this value are dropped and re-established on next use.

```bash
RCON_CONNECTION_TTL=60
```

---

#### `LOG_LEVEL`

**Type:** String
**Default:** `INFO`
**Valid Values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

```bash
LOG_LEVEL=INFO
```

---

### Optional Variables

#### `REDIS_URL`

**Type:** String
**Default:** `` (empty — Redis disabled)

Redis connection string for credential refresh notifications from the hub backend.

```bash
REDIS_URL=redis://localhost:6379/0
```

---

#### `SERVER_MANAGER_URL`

**Type:** String
**Default:** `http://server-manager-interaction:8098`

Used by the hub backend to locate this module. Set in the hub backend's environment, not in this module.

```bash
# In hub backend .env:
SERVER_MANAGER_URL=http://server-manager-interaction:8098
```

---

#### `SECRET_KEY`

**Type:** String
**Default:** `change-me-in-production`

Secret key for Quart session management.

**Generate:**
```python
import secrets; print(secrets.token_urlsafe(32))
```

```bash
SECRET_KEY=your-randomly-generated-key-here
```

---

#### `CORE_API_URL`

**Type:** String
**Default:** `http://router-service:8000`

URL of the WaddleBot core API/router service.

```bash
CORE_API_URL=http://router-service:8000
```

---

## Configuration Examples

### Local Development `.env`

```bash
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
MODULE_PORT=8098
RCON_ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000
RCON_CONNECTION_TTL=60
SECURITY_CORE_URL=http://localhost:8090
LOG_LEVEL=DEBUG
SECRET_KEY=dev-key-insecure-local-only
REDIS_URL=redis://localhost:6379/0
CORE_API_URL=http://localhost:8000
```

### Docker Compose Environment

```yaml
services:
  server-manager-interaction:
    environment:
      DATABASE_URL: postgresql://waddlebot:${DB_PASSWORD}@postgres:5432/waddlebot
      MODULE_PORT: 8098
      RCON_ENCRYPTION_KEY: ${RCON_ENCRYPTION_KEY}
      RCON_CONNECTION_TTL: 60
      SECURITY_CORE_URL: http://security-core:8090
      LOG_LEVEL: INFO
      SECRET_KEY: ${SECRET_KEY}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      CORE_API_URL: http://router-service:8000
```

### Production Environment

```bash
DATABASE_URL=postgresql://waddlebot_prod:${SECURE_DB_PASSWORD}@db.prod.example.com:5432/waddlebot_prod
MODULE_PORT=8098
RCON_ENCRYPTION_KEY=${RCON_ENCRYPTION_KEY}
RCON_CONNECTION_TTL=120
SECURITY_CORE_URL=https://security-core.internal.example.com:8090
LOG_LEVEL=WARNING
SECRET_KEY=${SECURE_SECRET_KEY}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis.prod.example.com:6379/2
CORE_API_URL=https://api.waddlebot.example.com
```

---

## Docker Compose Full Example

```yaml
version: '3.8'

services:
  server-manager-interaction:
    build:
      context: .
      dockerfile: action/interactive/server_manager_interaction_module/Dockerfile
    container_name: server-manager-interaction
    restart: unless-stopped
    ports:
      - "8098:8098"
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      MODULE_PORT: 8098
      RCON_ENCRYPTION_KEY: ${RCON_ENCRYPTION_KEY}
      RCON_CONNECTION_TTL: ${RCON_CONNECTION_TTL:-60}
      SECURITY_CORE_URL: http://security-core:8090
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      SECRET_KEY: ${SECRET_KEY}
      REDIS_URL: ${REDIS_URL:-}
      CORE_API_URL: http://router-service:8000
    volumes:
      - /var/log/waddlebotlog:/var/log/waddlebotlog
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8098/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - waddlebot

  postgres:
    image: postgres:15-alpine
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
    networks:
      - waddlebot

volumes:
  postgres_data:

networks:
  waddlebot:
    driver: bridge
```

---

## Kubernetes Deployment

### ConfigMap (Non-Sensitive)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: server-manager-config
  namespace: waddlebot
data:
  MODULE_PORT: "8098"
  LOG_LEVEL: "INFO"
  RCON_CONNECTION_TTL: "60"
  SECURITY_CORE_URL: "http://security-core:8090"
  CORE_API_URL: "http://router-service:8000"
```

### Secret (Sensitive)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: server-manager-secrets
  namespace: waddlebot
type: Opaque
stringData:
  DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
  RCON_ENCRYPTION_KEY: "your-64-char-hex-key"
  SECRET_KEY: "your-random-secret"
  REDIS_URL: redis://:password@redis:6379/0
```

---

## Variable Summary Table

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `MODULE_PORT` | No | `8098` | Quart listen port |
| `RCON_ENCRYPTION_KEY` | Yes | — | 64-char hex AES-256-GCM key |
| `SECURITY_CORE_URL` | Recommended | `http://security-core:8090` | Ban sync target |
| `RCON_CONNECTION_TTL` | No | `60` | Connection pool idle TTL (seconds) |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `SECRET_KEY` | No | `change-me-in-production` | Quart session key |
| `REDIS_URL` | No | `` (disabled) | Redis for credential notifications |
| `CORE_API_URL` | No | `http://router-service:8000` | Core API / router URL |
| `SERVER_MANAGER_URL` | No (hub only) | `http://server-manager-interaction:8098` | Set in hub backend, not this module |

---

## Security Best Practices

### Credentials Management

- Never hardcode `RCON_ENCRYPTION_KEY` or `DATABASE_URL` in source files
- Use Kubernetes Secrets or a secrets manager (AWS Secrets Manager, HashiCorp Vault)
- Add `.env` to `.gitignore`

### RCON_ENCRYPTION_KEY Handling

- Store in a secrets manager, not plaintext in CI/CD variables
- The same key must be set in both this module and the hub backend
- Key rotation requires re-saving all server credentials afterward

### Production Checklist

- [ ] `RCON_ENCRYPTION_KEY` is a cryptographically random 64-char hex value
- [ ] `SECRET_KEY` changed from default
- [ ] Strong database password in use
- [ ] `LOG_LEVEL` set to `WARNING` or `ERROR` (not `DEBUG`)
- [ ] Redis authentication enabled
- [ ] TLS used for all service-to-service URLs
- [ ] `SECURITY_CORE_URL` is reachable from this container

---

## Logging Configuration

| Level | Usage |
|-------|-------|
| `DEBUG` | Development — verbose, includes RCON request/response |
| `INFO` | Normal operations — startup, connections, commands |
| `WARNING` | Degraded operation — connection retries, slow commands |
| `ERROR` | Command failures, decrypt errors, ban sync failures |
| `CRITICAL` | Module cannot start — missing key, DB unreachable |

Log file inside container: `/var/log/waddlebotlog/server_manager_interaction_module.log`

Docker volume mapping: `-v /var/log/waddlebotlog:/var/log/waddlebotlog`

---

**Module**: server_manager_interaction_module
**Version**: 1.0.0
**Last Updated**: 2026-02-24
