# Memories Interaction Module - Configuration

## Environment Variables

The module uses environment variables for configuration. All variables are managed in `config.py` and loaded via `python-dotenv`.

### Required Variables

#### DATABASE_URL

PostgreSQL connection string for the primary database.

```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/waddlebot"
```

Format: `postgresql://[user[:password]@][netloc][:port][/dbname]`

Components:
- **user**: PostgreSQL username (default: postgres)
- **password**: Password for user
- **netloc**: Hostname or IP (default: localhost)
- **port**: PostgreSQL port (default: 5432)
- **dbname**: Database name (default: postgres)

Example configurations:
```
# Local development
postgresql://postgres:password@localhost:5432/waddlebot

# Docker Compose (using service name)
postgresql://waddlebot:password@postgres:5432/waddlebot

# Remote server
postgresql://user:pass@db.example.com:5432/waddlebot
```

### Optional Variables

#### MODULE_PORT

HTTP port for the module to listen on.

```bash
export MODULE_PORT=8031  # default
```

Used by:
- Hypercorn server binding
- Health checks
- Docker port mapping

#### LOG_LEVEL

Logging verbosity level.

```bash
export LOG_LEVEL=INFO  # default: INFO
```

Valid values:
- `DEBUG`: Verbose debug information
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages only
- `CRITICAL`: Critical errors only

#### SECRET_KEY

Secret key for cryptographic operations.

```bash
export SECRET_KEY="your-secret-key-here-change-in-production"
```

Requirements:
- Minimum 32 characters recommended
- Use strong random value in production
- Keep secure, never commit to version control

#### CORE_API_URL

Base URL for core API service.

```bash
export CORE_API_URL="http://router-service:8000"  # default
```

Used for:
- Inter-service communication
- Credential validation
- Platform integration queries

#### ROUTER_API_URL

Base URL for router API endpoints.

```bash
export ROUTER_API_URL="http://router-service:8000/api/v1/router"  # default
```

Used for:
- Routing queries
- Service discovery
- Request forwarding

#### REDIS_URL

Redis connection string for pub/sub notifications (optional).

```bash
export REDIS_URL="redis://localhost:6379"  # optional
```

Format: `redis://[password@]host[:port][/db]`

Used for:
- Credential refresh notifications
- Background job queue (future)
- Cache synchronization

Only required if using credential refresh listener.

## Configuration Methods

### Method 1: Environment Variables

Set variables before running the module:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/waddlebot"
export MODULE_PORT=8031
export LOG_LEVEL=INFO

# Run module
python app.py
```

### Method 2: .env File

Create `.env` file in module directory:

```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
MODULE_PORT=8031
LOG_LEVEL=INFO
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://redis:6379
```

Module automatically loads from `.env` via `python-dotenv`:

```bash
python app.py
```

### Method 3: Docker Environment

Pass variables to container:

```bash
docker run -d \
  -e DATABASE_URL="postgresql://user:pass@postgres:5432/waddlebot" \
  -e MODULE_PORT=8031 \
  -e LOG_LEVEL=INFO \
  -e SECRET_KEY="change-me" \
  -p 8031:8031 \
  waddlebot/memories-interaction:latest
```

### Method 4: Docker Compose

Define in `docker-compose.yml`:

```yaml
services:
  memories-interaction:
    image: waddlebot/memories-interaction:latest
    environment:
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      MODULE_PORT: 8031
      LOG_LEVEL: INFO
      CORE_API_URL: http://router-service:8000
      ROUTER_API_URL: http://router-service:8000/api/v1/router
      SECRET_KEY: ${SECRET_KEY}  # from .env
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    ports:
      - "8031:8031"
```

### Method 5: Kubernetes ConfigMap/Secrets

Create Kubernetes resources:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: memories-config
data:
  MODULE_PORT: "8031"
  LOG_LEVEL: "INFO"
  CORE_API_URL: "http://router-service:8000"
  ROUTER_API_URL: "http://router-service:8000/api/v1/router"
---
apiVersion: v1
kind: Secret
metadata:
  name: memories-secrets
type: Opaque
stringData:
  DATABASE_URL: postgresql://user:pass@postgres:5432/waddlebot
  SECRET_KEY: your-secret-key-here
  REDIS_URL: redis://redis:6379
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memories-interaction
spec:
  template:
    spec:
      containers:
      - name: memories-interaction
        image: waddlebot/memories-interaction:latest
        envFrom:
        - configMapRef:
            name: memories-config
        - secretRef:
            name: memories-secrets
        ports:
        - containerPort: 8031
```

## Default Configuration

If environment variables are not set, defaults are used:

```python
MODULE_NAME = 'memories_interaction_module'
MODULE_VERSION = '2.0.0'
MODULE_PORT = 8031
DATABASE_URL = 'postgresql://waddlebot:password@localhost:5432/waddlebot'
CORE_API_URL = 'http://router-service:8000'
ROUTER_API_URL = 'http://router-service:8000/api/v1/router'
LOG_LEVEL = 'INFO'
SECRET_KEY = 'change-me-in-production'
REDIS_URL = ''  # empty = disabled
```

## Credential Management

### Database Credentials Loading

Module can load credentials from platform_integrations table:

```python
Config.load_credentials_from_db(db_connection)
```

Looks for:
- platform = 'memories_interaction'
- integration_type = 'bot'
- is_active = TRUE

Falls back to environment variables if DB lookup fails.

### Redis Listener

Background thread listens for credential refresh notifications:

```bash
Channel: credentials:memories_interaction:bot:refreshed
```

When notified, module invalidates cached credentials and reloads.

Start listener:

```python
if redis_url:
    Config.start_credential_listener(redis_client)
```

## Configuration Validation

Module validates configuration on startup:

```python
# Validation checks
- DATABASE_URL is valid PostgreSQL URL
- MODULE_PORT is valid integer (1-65535)
- LOG_LEVEL is valid level (DEBUG, INFO, etc.)
- SECRET_KEY is set to non-default value in production
```

If validation fails, module logs warnings but continues with defaults.

## Example .env File

```bash
# Database
DATABASE_URL=postgresql://waddlebot:waddlebot123@postgres:5432/waddlebot

# Module
MODULE_PORT=8031
LOG_LEVEL=INFO
SECRET_KEY=secure-random-key-min-32-chars-required

# APIs
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Cache (optional)
REDIS_URL=redis://redis:6379/0
```

## Example Production Configuration

For production deployments:

```bash
# Database with connection pooling
DATABASE_URL=postgresql://prod_user:STRONG_PASSWORD@db-prod.example.com:5432/waddlebot

# Module
MODULE_PORT=8031
LOG_LEVEL=WARNING  # Reduce verbosity in production

# Security
SECRET_KEY=$(openssl rand -base64 32)

# APIs
CORE_API_URL=https://api.example.com
ROUTER_API_URL=https://api.example.com/api/v1/router

# Caching
REDIS_URL=redis://redis-prod:6379/0
```

## Troubleshooting Configuration

### Database Connection Failed

Check:
1. DATABASE_URL is correctly formatted
2. PostgreSQL server is running and accessible
3. Credentials are correct
4. Network connectivity to database host

```bash
# Test connection
psql postgresql://user:pass@host:5432/dbname
```

### Module Not Starting

Check:
1. All required variables are set
2. MODULE_PORT is not in use by another process
3. Log files for error messages

```bash
# View logs
docker logs memories-module

# Check port
netstat -tulpn | grep 8031
```

### Credential Loading Fails

Check:
1. platform_integrations table exists
2. Credentials record exists with correct platform name
3. is_active = TRUE
4. Environment variable fallback works

---

Last Updated: February 16, 2026
Module Version: 2.0.0
