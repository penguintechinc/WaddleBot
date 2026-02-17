# Engagement Module — Configuration Guide

## Environment Variables

The Engagement Module is configured via environment variables. All variables are optional with sensible defaults. For production deployments, override all defaults.

---

## Database Configuration

### DATABASE_URL
**Type**: String
**Default**: `postgres://waddlebot:password@localhost:5432/waddlebot`
**Format**: PostgreSQL connection string

Sets the complete database connection string. If set, individual `DB_*` variables are ignored.

```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

**Note**: The module normalizes `postgresql://` to `postgres://` for PyDAL compatibility.

### DB_HOST
**Type**: String
**Default**: `localhost`

PostgreSQL server hostname or IP address.

```bash
DB_HOST=db.example.com
```

### DB_PORT
**Type**: Integer
**Default**: `5432`

PostgreSQL server port.

```bash
DB_PORT=5432
```

### DB_NAME
**Type**: String
**Default**: `waddlebot`

Database name.

```bash
DB_NAME=waddlebot
```

### DB_USER
**Type**: String
**Default**: `waddlebot`

Database user account.

```bash
DB_USER=waddlebot
```

### DB_PASS
**Type**: String
**Default**: `password`
**⚠️ Important**: Change in production

Database user password.

```bash
DB_PASS=your-secure-password-here
```

### DB_POOL_SIZE
**Type**: Integer
**Default**: `10`

Connection pool size. Increase if seeing "pool exhausted" errors under load.

```bash
DB_POOL_SIZE=20  # For high-traffic deployments
```

---

## Module Configuration

### MODULE_PORT
**Type**: Integer
**Default**: `8091`

HTTP REST API port.

```bash
MODULE_PORT=8091
```

### MODULE_HOST
**Type**: String
**Default**: `0.0.0.0`

Bind address for HTTP server. Use `0.0.0.0` for all interfaces (Docker) or `127.0.0.1` for localhost only.

```bash
MODULE_HOST=0.0.0.0
```

### MODULE_VERSION
**Type**: String
**Default**: `1.0.0`

Module version string. Returned in health check responses.

```bash
MODULE_VERSION=1.0.0
```

### MODULE_SECRET_KEY
**Type**: String
**Default**: `change-me-in-production`
**⚠️ Important**: Required for production

Secret key for module-level security operations. Must be unique and secure.

```bash
MODULE_SECRET_KEY=your-random-secret-key-min-32-chars
```

Generate a secure key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## gRPC Configuration

### GRPC_PORT
**Type**: Integer
**Default**: `50061`

gRPC server port. See docs/GRPC_PORT_VISUAL_REFERENCE.txt for port allocations.

```bash
GRPC_PORT=50061
```

### GRPC_HOST
**Type**: String
**Default**: `0.0.0.0`

Bind address for gRPC server.

```bash
GRPC_HOST=0.0.0.0
```

---

## JWT Configuration

### JWT_SECRET
**Type**: String
**Default**: `jwt-secret-key-change-in-prod`
**⚠️ Important**: Must be changed in production

Secret key for JWT token signing and verification. Tokens signed with this key will be invalid if secret changes.

```bash
JWT_SECRET=your-random-jwt-secret-min-32-chars
```

### JWT_ALGORITHM
**Type**: String
**Default**: `HS256`

JWT signing algorithm. Recommended algorithms: `HS256`, `HS512`, `RS256`.

```bash
JWT_ALGORITHM=HS256
```

### JWT_EXPIRATION_HOURS
**Type**: Integer
**Default**: `24`

JWT token expiration time in hours. Tokens expire after this duration.

```bash
JWT_EXPIRATION_HOURS=24  # 24 hours = 1 day
```

---

## Logging Configuration

### LOG_LEVEL
**Type**: String
**Default**: `INFO`
**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

Minimum logging level. Lower levels (DEBUG) produce more verbose output.

```bash
LOG_LEVEL=DEBUG      # Development: Very verbose
LOG_LEVEL=INFO       # Default: General information
LOG_LEVEL=WARNING    # Production: Warnings and errors only
```

### LOG_FORMAT
**Type**: String
**Default**: `text`
**Options**: `text`, `json`

Log output format. JSON format recommended for log aggregation systems.

```bash
LOG_FORMAT=text      # Human-readable format
LOG_FORMAT=json      # Structured JSON for log aggregation
```

---

## Environment Configuration

### ENVIRONMENT
**Type**: String
**Default**: `development`
**Options**: `development`, `production`

Deployment environment. Affects validation strictness and default settings.

```bash
ENVIRONMENT=development  # Relaxed validation
ENVIRONMENT=production   # Strict validation
```

In production mode, the module validates that all required secrets are properly configured.

### RELEASE_MODE
**Type**: Boolean
**Default**: `false`

Enable license key validation. Set to `true` for production deployments with license gating.

```bash
RELEASE_MODE=false   # Development: License not required
RELEASE_MODE=true    # Production: License key required
```

---

## License Configuration

### LICENSE_KEY
**Type**: String
**Default**: (empty)

License key from Penguin Tech License Server. Required when `RELEASE_MODE=true`.

```bash
LICENSE_KEY=PT-ENGAGEMENT-MODULE-XXXXXXXXXXXX
```

### LICENSE_SERVER
**Type**: String
**Default**: `https://license.penguintech.io`

Penguin Tech License Server endpoint for license validation.

```bash
LICENSE_SERVER=https://license.penguintech.io
```

---

## Redis Configuration (Optional)

### REDIS_URL
**Type**: String
**Default**: (empty)

Redis connection string for credential refresh notifications. Optional.

```bash
REDIS_URL=redis://localhost:6379
REDIS_URL=redis://:password@redis-host:6379
```

---

## Complete .env Example

```bash
# Database Configuration
DB_TYPE=postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=waddlebot
DB_USER=waddlebot
DB_PASS=secure-password-here
DB_POOL_SIZE=10

# Module Configuration
MODULE_PORT=8091
MODULE_HOST=0.0.0.0
MODULE_VERSION=1.0.0
MODULE_SECRET_KEY=your-random-secret-key-min-32-chars
ENVIRONMENT=development

# gRPC Configuration
GRPC_PORT=50061
GRPC_HOST=0.0.0.0

# JWT Configuration
JWT_SECRET=your-random-jwt-secret-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=text

# Release Mode (License Gating)
RELEASE_MODE=false

# License Configuration (if applicable)
LICENSE_KEY=
LICENSE_SERVER=https://license.penguintech.io

# Redis (Optional)
REDIS_URL=
```

---

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  engagement:
    image: waddlebot/engagement:latest
    container_name: engagement-module
    ports:
      - "8091:8091"
      - "50061:50061"
    environment:
      # Database
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: waddlebot
      DB_USER: waddlebot
      DB_PASS: password
      DB_POOL_SIZE: 10

      # Module
      MODULE_PORT: 8091
      MODULE_HOST: 0.0.0.0
      MODULE_VERSION: 1.0.0
      MODULE_SECRET_KEY: your-secret-key
      ENVIRONMENT: development

      # gRPC
      GRPC_PORT: 50061
      GRPC_HOST: 0.0.0.0

      # JWT
      JWT_SECRET: your-jwt-secret
      JWT_ALGORITHM: HS256
      JWT_EXPIRATION_HOURS: 24

      # Logging
      LOG_LEVEL: INFO
      LOG_FORMAT: text

      # License
      RELEASE_MODE: false

    depends_on:
      - postgres
    networks:
      - waddlebot-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8091/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      POSTGRES_DB: waddlebot
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - waddlebot-network

networks:
  waddlebot-network:

volumes:
  postgres-data:
```

---

## Kubernetes ConfigMap and Secret

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: engagement-config
data:
  MODULE_PORT: "8091"
  MODULE_HOST: "0.0.0.0"
  MODULE_VERSION: "1.0.0"
  GRPC_PORT: "50061"
  GRPC_HOST: "0.0.0.0"
  JWT_ALGORITHM: "HS256"
  JWT_EXPIRATION_HOURS: "24"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "text"
  ENVIRONMENT: "production"
  RELEASE_MODE: "false"
  LICENSE_SERVER: "https://license.penguintech.io"

---
apiVersion: v1
kind: Secret
metadata:
  name: engagement-secrets
type: Opaque
stringData:
  DB_HOST: postgres.default.svc.cluster.local
  DB_PORT: "5432"
  DB_NAME: waddlebot
  DB_USER: waddlebot
  DB_PASS: your-secure-password
  MODULE_SECRET_KEY: your-random-secret-key-32-chars
  JWT_SECRET: your-random-jwt-secret-32-chars
  LICENSE_KEY: PT-ENGAGEMENT-MODULE-XXXXXXXX

---
apiVersion: v1
kind: Pod
metadata:
  name: engagement-module
spec:
  containers:
  - name: engagement
    image: waddlebot/engagement:latest
    ports:
    - name: http
      containerPort: 8091
    - name: grpc
      containerPort: 50061
    envFrom:
    - configMapRef:
        name: engagement-config
    - secretRef:
        name: engagement-secrets
    livenessProbe:
      httpGet:
        path: /health
        port: 8091
      initialDelaySeconds: 10
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health
        port: 8091
      initialDelaySeconds: 5
      periodSeconds: 5
```

---

## Production Checklist

- [ ] Change `DB_PASS` to secure password
- [ ] Change `MODULE_SECRET_KEY` to random 32+ character string
- [ ] Change `JWT_SECRET` to random 32+ character string
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Set `DB_POOL_SIZE` appropriate to traffic (typically 20-50)
- [ ] Configure `LICENSE_KEY` if using `RELEASE_MODE=true`
- [ ] Test health check endpoint before deployment
- [ ] Verify database connectivity before deployment
- [ ] Set up monitoring and alerting on health checks

---

## Validation Rules

The module validates configuration at startup:

```python
@classmethod
def validate(cls) -> bool:
    # Check required secrets in production
    if cls.ENVIRONMENT == "production":
        if cls.MODULE_SECRET_KEY == "change-me-in-production":
            raise ValueError("MODULE_SECRET_KEY must be changed for production")
        if cls.JWT_SECRET == "jwt-secret-key-change-in-prod":
            raise ValueError("JWT_SECRET must be changed for production")

    # Validate port ranges
    if not (1 <= cls.MODULE_PORT <= 65535):
        raise ValueError(f"Invalid MODULE_PORT: {cls.MODULE_PORT}")
    if not (1 <= cls.GRPC_PORT <= 65535):
        raise ValueError(f"Invalid GRPC_PORT: {cls.GRPC_PORT}")

    return True
```

---

## Next Steps

- See [USAGE.md](USAGE.md) for deployment examples
- See [API.md](API.md) for endpoint documentation
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for configuration issues

**Company**: Penguin Tech Inc
**License**: Limited AGPL-3.0
**Last Updated**: 2026-02-16
