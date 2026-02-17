# OpenWhisk Action Module - Configuration Reference

## Overview

The OpenWhisk Action Module uses environment variables for configuration.

## Environment Variables

### OpenWhisk Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `OPENWHISK_API_HOST` | https://openwhisk.example.com | YES | OpenWhisk API endpoint URL |
| `OPENWHISK_AUTH_KEY` | - | YES | API key in `namespace:key` format |
| `OPENWHISK_NAMESPACE` | guest | NO | Default namespace |
| `OPENWHISK_INSECURE` | false | NO | Skip HTTPS verification |

**Example**:
```env
OPENWHISK_API_HOST=https://openwhisk.cloud.ibm.com
OPENWHISK_AUTH_KEY=waddlebot@example.com_dev:abcdef123456...
OPENWHISK_NAMESPACE=guest
OPENWHISK_INSECURE=false
```

### Database Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `DATABASE_URL` | - | YES | PostgreSQL connection URL |

**Format**: `postgres://username:password@host:port/database`

### Server Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `HOST` | 0.0.0.0 | NO | Bind address |
| `GRPC_PORT` | 50062 | NO | gRPC server port |
| `REST_PORT` | 8082 | NO | REST API port |
| `MODULE_PORT` | 8082 | NO | Alias for REST_PORT |

### Security Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `MODULE_SECRET_KEY` | - | YES | JWT signing secret (64+ chars) |
| `JWT_ALGORITHM` | HS256 | NO | JWT algorithm |
| `JWT_EXPIRATION_SECONDS` | 3600 | NO | Token lifetime |

### Module Information

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `MODULE_NAME` | openwhisk_action_module | NO | Module identifier |
| `MODULE_VERSION` | 1.0.0 | NO | Module version |

### Performance Settings

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `MAX_WORKERS` | 20 | NO | Concurrent workers |
| `REQUEST_TIMEOUT` | 30 | NO | Request timeout in seconds |
| `MAX_BATCH_SIZE` | 100 | NO | Max batch invocations |
| `DEFAULT_ACTION_TIMEOUT` | 60000 | NO | Default action timeout (ms) |
| `MAX_ACTION_TIMEOUT` | 600000 | NO | Maximum action timeout (ms) |

### Logging Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `LOG_LEVEL` | INFO | NO | Logging level |
| `LOG_DIR` | /var/log/waddlebotlog | NO | Log directory |
| `ENABLE_SYSLOG` | false | NO | Enable syslog |
| `SYSLOG_HOST` | localhost | NO | Syslog host |
| `SYSLOG_PORT` | 514 | NO | Syslog port |
| `SYSLOG_FACILITY` | LOCAL0 | NO | Syslog facility |

### Redis Configuration (Optional)

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `REDIS_URL` | - | NO | Redis connection for credential updates |

### Testing Mode

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `TESTING_MODE` | true | NO | Lenient validation for development |

## Example .env Files

### Development

```env
# OpenWhisk Configuration
OPENWHISK_API_HOST=https://openwhisk.cloud.ibm.com
OPENWHISK_AUTH_KEY=waddlebot@example.com_dev:abcdef123456...
OPENWHISK_NAMESPACE=guest
OPENWHISK_INSECURE=false

# Database
DATABASE_URL=postgres://waddlebot:password@localhost:5432/waddlebot

# Server
HOST=0.0.0.0
GRPC_PORT=50062
REST_PORT=8082

# Security
MODULE_SECRET_KEY=change-me-64-character-secret-key-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Performance
MAX_WORKERS=20
REQUEST_TIMEOUT=30

# Logging
LOG_LEVEL=DEBUG
LOG_DIR=/var/log/waddlebotlog

# Testing Mode
TESTING_MODE=true
```

### Production

```env
# OpenWhisk Configuration
OPENWHISK_API_HOST=https://openwhisk.cloud.ibm.com
OPENWHISK_AUTH_KEY=production_key_from_secure_vault
OPENWHISK_NAMESPACE=production

# Database (RDS)
DATABASE_URL=postgres://waddlebot:SECURE_PASSWORD@mydb.rds.amazonaws.com:5432/waddlebot

# Server
HOST=0.0.0.0
GRPC_PORT=50062
REST_PORT=8082

# Security (MUST change)
MODULE_SECRET_KEY=your-actual-secure-64-character-key-generated-securely

# Performance
MAX_WORKERS=50
REQUEST_TIMEOUT=30
MAX_BATCH_SIZE=100

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=true
SYSLOG_HOST=syslog.example.com
SYSLOG_PORT=514

# Redis for credential updates
REDIS_URL=redis://redis.example.com:6379/0

# Testing Mode OFF for production
TESTING_MODE=false
```

### Docker Compose

```env
# OpenWhisk Configuration
OPENWHISK_API_HOST=https://openwhisk.cloud.ibm.com
OPENWHISK_AUTH_KEY=namespace:api-key
OPENWHISK_NAMESPACE=guest

# Database (Docker network)
DATABASE_URL=postgres://waddlebot:password@postgres_openwhisk:5432/waddlebot

# Server
HOST=0.0.0.0
GRPC_PORT=50062
REST_PORT=8082

# Security
MODULE_SECRET_KEY=docker-dev-secret-64-chars-long-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
```

## Configuration Validation

The module validates configuration on startup:

```python
Config.validate()  # Raises ValueError if invalid
```

### Validation Rules

**Development/Testing Mode (TESTING_MODE=true)**:
- DATABASE_URL must be set

**Production Mode (TESTING_MODE=false)**:
- OPENWHISK_API_HOST must be set
- OPENWHISK_AUTH_KEY must be set in `namespace:key` format
- DATABASE_URL must be set
- MODULE_SECRET_KEY must not be default value

## Getting Credentials

### IBM Cloud Functions

```bash
# Login
ibmcloud login

# Get API key
ibmcloud fn property get --auth

# Output format: namespace:key
# Example: waddlebot@example.com_dev:3a2e4c8f9d1b5e7a...
```

### Local/Docker OpenWhisk

```bash
# If running in Docker
docker exec -it openwhisk_controller cat /data/wskdata/guest.whitelist

# Or get from wsk CLI
wsk property get --auth
```

### Self-Hosted OpenWhisk

Contact your OpenWhisk administrator for:
1. API host URL
2. Namespace
3. API key

## Configuration Priority

1. **Environment Variables** (highest)
   - Set in shell, .env, or container
2. **Python Defaults** (lowest)
   - Hard-coded in config.py

## Database Integration (Optional)

Store credentials in database instead of environment:

```sql
INSERT INTO platform_integrations (
  platform,
  integration_type,
  access_token,
  config_data,
  is_active
) VALUES (
  'openwhisk',
  'bot',
  'namespace:key',
  '{
    "api_host": "https://openwhisk.example.com",
    "namespace": "guest",
    "insecure": false
  }',
  true
);
```

Then call in app startup:

```python
Config.load_credentials_from_db(db)

# Optional: Listen for credential updates
listener = Config.start_credential_listener(redis_client)
```

## Secrets Management Best Practices

### Generating Secure Keys

```bash
# Linux/macOS
openssl rand -base64 48

# Python
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Development

- Store in .env (gitignored)
- Simple passwords OK
- Use testing defaults

### Production

- Use secure vault (AWS Secrets Manager, HashiCorp Vault)
- Strong passwords (64+ characters)
- Rotate periodically
- Never commit to git

### Kubernetes

Store secrets as Kubernetes Secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: openwhisk-credentials
type: Opaque
stringData:
  api-host: "https://openwhisk.example.com"
  auth-key: "namespace:key"
  jwt-secret: "your-64-char-secret-key"
```

Reference in deployment:

```yaml
env:
- name: OPENWHISK_AUTH_KEY
  valueFrom:
    secretKeyRef:
      name: openwhisk-credentials
      key: auth-key
```

## Validation Checklist

Before deploying to production:

- [ ] OPENWHISK_API_HOST is correct and accessible
- [ ] OPENWHISK_AUTH_KEY is valid (format: namespace:key)
- [ ] OPENWHISK_NAMESPACE is correct
- [ ] DATABASE_URL works and database exists
- [ ] MODULE_SECRET_KEY is 64+ characters and unique
- [ ] All passwords are strong
- [ ] Log directory exists and is writable
- [ ] Ports 50062 and 8082 are available
- [ ] TESTING_MODE is false in production

## Configuration Examples

### IBM Cloud Functions

```env
OPENWHISK_API_HOST=https://us-south.functions.cloud.ibm.com
OPENWHISK_AUTH_KEY=waddlebot@company.com_dev:abc123def456...
OPENWHISK_NAMESPACE=waddlebot@company.com_dev
```

### Local Docker

```env
OPENWHISK_API_HOST=http://localhost:3233
OPENWHISK_AUTH_KEY=guest:password
OPENWHISK_NAMESPACE=guest
```

### High Throughput

```env
MAX_WORKERS=100
REQUEST_TIMEOUT=60
DEFAULT_ACTION_TIMEOUT=120000  # 2 minutes
```

### Debug Mode

```env
LOG_LEVEL=DEBUG
TESTING_MODE=true
REQUEST_TIMEOUT=60
```

## Summary

**Required**:
- OPENWHISK_API_HOST
- OPENWHISK_AUTH_KEY (format: namespace:key)
- DATABASE_URL
- MODULE_SECRET_KEY (64+ chars)

**Recommended**:
- OPENWHISK_NAMESPACE (if not guest)
- LOG_LEVEL=INFO (production)
- ENABLE_SYSLOG=true (production)

**Optional**:
- REDIS_URL (credential updates)
- Performance tuning variables

See [USAGE.md](USAGE.md) for setup and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for issues.
