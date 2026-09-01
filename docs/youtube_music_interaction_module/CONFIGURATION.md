# YouTube Music Interaction Module - Configuration

## Environment Variables

The YouTube Music Interaction Module is configured entirely through environment variables. These can be set via `.env` file, Docker environment, Kubernetes ConfigMaps, or system environment.

### Core Module Configuration

#### MODULE_PORT
- **Type**: Integer
- **Default**: `8025`
- **Required**: No
- **Description**: The port on which the Quart application listens for HTTP requests
- **Example**: `MODULE_PORT=8025`
- **Notes**: gRPC port (50054) is not configurable in current version

#### MODULE_NAME
- **Type**: String
- **Default**: `youtube_music_interaction_module`
- **Required**: No
- **Description**: Internal module identifier
- **Example**: `MODULE_NAME=youtube_music_interaction_module`
- **Notes**: Used in logging and metrics

#### MODULE_VERSION
- **Type**: String
- **Default**: `2.0.0`
- **Required**: No
- **Description**: Module version
- **Example**: `MODULE_VERSION=2.0.0`
- **Notes**: Read-only, set in config.py

### Database Configuration

#### DATABASE_URL
- **Type**: String (PostgreSQL connection string)
- **Default**: `postgresql://waddlebot:password@localhost:5432/waddlebot`
- **Required**: Yes
- **Description**: PostgreSQL database connection string
- **Format**: `postgresql://user:password@host:port/database`
- **Example**: 
  ```
  DATABASE_URL=postgresql://waddlebot:secure-password@postgres:5432/waddlebot
  ```
- **Security Notes**:
  - Never commit to version control
  - Use strong passwords in production
  - Ensure host is on private network
  - Consider connection pooling for scale

**Connection String Breakdown**:
```
postgresql://username:password@host:port/database
             │        │        │   │    │
             │        │        │   │    └─ Database name
             │        │        │   └────── Port (default 5432)
             │        │        └────────── Hostname/IP
             │        └────────────────── Password
             └────────────────────────── Username
```

**Alternative Formats**:
```
# Using environment variable substitution
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Using postgresql:// or postgres:// (both valid)
DATABASE_URL=postgres://user:pass@localhost:5432/waddlebot

# With connection parameters
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot?sslmode=require
```

### Router Service Configuration

#### CORE_API_URL
- **Type**: String (HTTP URL)
- **Default**: `http://router-service:8000`
- **Required**: No
- **Description**: Base URL for WaddleBot core API and router service
- **Example**: `CORE_API_URL=http://router-service:8000`
- **Notes**: Used for inter-service communication

#### ROUTER_API_URL
- **Type**: String (HTTP URL)
- **Default**: `http://router-service:8000/api/v1/router`
- **Required**: No
- **Description**: Full URL for router API endpoints
- **Example**: `ROUTER_API_URL=http://router-service:8000/api/v1/router`
- **Notes**: Endpoint path may vary by deployment

### Logging Configuration

#### LOG_LEVEL
- **Type**: String
- **Default**: `INFO`
- **Required**: No
- **Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Sets the logging verbosity level
- **Examples**:
  - `LOG_LEVEL=DEBUG` - Very verbose, includes function calls
  - `LOG_LEVEL=INFO` - Standard, operational messages
  - `LOG_LEVEL=WARNING` - Issues only
  - `LOG_LEVEL=ERROR` - Errors only
  - `LOG_LEVEL=CRITICAL` - Critical errors only
- **Notes**: AAA logging framework handles structured logging

### Security Configuration

#### SECRET_KEY
- **Type**: String
- **Default**: `change-me-in-production`
- **Required**: Yes (production)
- **Description**: Secret key for JWT tokens and session encryption
- **Security Notes**:
  - MUST change from default in production
  - Should be cryptographically random
  - Minimum 32 characters recommended
  - Never commit to version control
- **Example**: 
  ```bash
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  ```

### YouTube OAuth Configuration

#### YOUTUBE_CLIENT_ID
- **Type**: String (Google OAuth 2.0 Client ID)
- **Default**: (empty)
- **Required**: Yes
- **Description**: OAuth 2.0 Client ID from Google Cloud Console
- **Format**: `xxx.apps.googleusercontent.com`
- **Example**: `YOUTUBE_CLIENT_ID=123456789.apps.googleusercontent.com`
- **Where to Get**:
  1. Go to [Google Cloud Console](https://console.cloud.google.com/)
  2. Create project or select existing
  3. Enable YouTube Data API v3
  4. Go to Credentials > Create Credentials > OAuth 2.0 Client ID
  5. Choose Web Application
  6. Copy Client ID value

#### YOUTUBE_CLIENT_SECRET
- **Type**: String (Google OAuth 2.0 Client Secret)
- **Default**: (empty)
- **Required**: Yes
- **Description**: OAuth 2.0 Client Secret from Google Cloud Console
- **Format**: Long alphanumeric string
- **Example**: `YOUTUBE_CLIENT_SECRET=GOCSPX-ABC123XYZ...`
- **Security Notes**:
  - Never commit to version control
  - Treat as sensitive as a password
  - Rotate regularly
  - Store in secret management system

### Redis Configuration (Optional)

#### REDIS_URL
- **Type**: String (Redis connection URL)
- **Default**: (empty - Redis disabled)
- **Required**: No
- **Description**: Redis connection URL for credential refresh notifications
- **Format**: `redis://[username:password@]host:port[/database]`
- **Examples**:
  ```
  # Local Redis
  REDIS_URL=redis://localhost:6379/0

  # Redis with password
  REDIS_URL=redis://:password@redis-server:6379/0

  # Redis Cluster
  REDIS_URL=redis://redis-node1:6379,redis-node2:6379

  # Redis Sentinel
  REDIS_URL=redis://sentinel1:26379/0?sentinel=mymaster
  ```
- **Notes**:
  - If empty, Redis features are disabled
  - Credential refresh notifications require Redis
  - Connection tested on startup
  - Optional for small deployments

## Example Configuration Files

### Development Environment (.env)

```bash
# Core Configuration
MODULE_PORT=8025
MODULE_NAME=youtube_music_interaction_module
MODULE_VERSION=2.0.0

# Database
DATABASE_URL=postgresql://waddlebot:dev-password@localhost:5432/waddlebot

# API URLs
CORE_API_URL=http://localhost:8000
ROUTER_API_URL=http://localhost:8000/api/v1/router

# Logging
LOG_LEVEL=DEBUG

# Security
SECRET_KEY=dev-secret-key-change-in-production

# YouTube OAuth
YOUTUBE_CLIENT_ID=123456789.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-ABC123XYZ...

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

### Docker Compose Environment

```yaml
services:
  youtube-music-interaction:
    environment:
      MODULE_PORT: 8025
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      CORE_API_URL: http://router-service:8000
      ROUTER_API_URL: http://router-service:8000/api/v1/router
      LOG_LEVEL: INFO
      SECRET_KEY: ${SECRET_KEY}
      YOUTUBE_CLIENT_ID: ${YOUTUBE_CLIENT_ID}
      YOUTUBE_CLIENT_SECRET: ${YOUTUBE_CLIENT_SECRET}
      REDIS_URL: redis://redis:6379/0
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: youtube-music-interaction
  namespace: waddlebot
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: youtube-music-interaction
        image: waddlebot/youtube-music-interaction:latest
        ports:
        - containerPort: 8025
          name: http
        - containerPort: 50054
          name: grpc
        env:
        - name: MODULE_PORT
          value: "8025"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: waddlebot-secrets
              key: database-url
        - name: YOUTUBE_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: youtube-oauth
              key: client-id
        - name: YOUTUBE_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: youtube-oauth
              key: client-secret
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: waddlebot-secrets
              key: secret-key
        - name: REDIS_URL
          value: redis://redis-service:6379/0
```

### Production Environment

```bash
# Core Configuration
MODULE_PORT=8025
MODULE_NAME=youtube_music_interaction_module
MODULE_VERSION=2.0.0

# Database - Use RDS or managed database
DATABASE_URL=postgresql://waddlebot:$(cat /run/secrets/db_password)@postgres-prod.example.com:5432/waddlebot

# API URLs
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Logging
LOG_LEVEL=INFO

# Security - Use secrets management
SECRET_KEY=$(cat /run/secrets/secret_key)
YOUTUBE_CLIENT_ID=$(cat /run/secrets/youtube_client_id)
YOUTUBE_CLIENT_SECRET=$(cat /run/secrets/youtube_client_secret)

# Redis - Use Redis Cluster or ElastiCache
REDIS_URL=redis://redis-cluster.example.com:6379/0
```

## Configuration Loading Order

The module loads configuration in the following order (first match wins):

1. Environment variables (from system or .env file)
2. Default values in config.py
3. Database lookups for credentials
4. Fallback to environment variables if DB fails

```
┌─────────────────────────────────────────────┐
│ Configuration Loading Process               │
└─────────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │ Import .env file      │
        │ (if exists)           │
        └────────┬──────────────┘
                 │
                 ▼
        ┌───────────────────────┐
        │ Read env variables    │
        │ from system           │
        └────────┬──────────────┘
                 │
                 ▼
        ┌───────────────────────┐
        │ Apply defaults from   │
        │ Config class          │
        └────────┬──────────────┘
                 │
                 ▼
        ┌───────────────────────┐
        │ On startup:           │
        │ Load credentials      │
        │ from database         │
        └────────┬──────────────┘
                 │
                 ├─ Success ──► Use DB credentials
                 │
                 └─ Failure ──► Fall back to env vars
                 │
                 ▼
        ┌───────────────────────┐
        │ Start Redis listener  │
        │ (if REDIS_URL set)    │
        └───────────────────────┘
```

## Validation & Requirements

### Required Variables Checklist

The following variables MUST be set for production deployment:

- [ ] `DATABASE_URL` - Valid PostgreSQL connection string
- [ ] `YOUTUBE_CLIENT_ID` - Valid Google OAuth Client ID
- [ ] `YOUTUBE_CLIENT_SECRET` - Valid Google OAuth Client Secret
- [ ] `SECRET_KEY` - Strong, unique key (never use default)
- [ ] `CORE_API_URL` - Reachable router service URL
- [ ] `ROUTER_API_URL` - Reachable router API endpoint

### Optional but Recommended

- [ ] `REDIS_URL` - For credential refresh notifications
- [ ] `LOG_LEVEL` - Set to INFO or WARNING in production
- [ ] Kubernetes secrets for all sensitive values

## Secret Management Best Practices

### Development

```bash
# Use .env file (DO NOT commit)
echo ".env" >> .gitignore

# Generate strong keys
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Load into environment
export $(cat .env | xargs)
```

### Production - Docker

Use Docker secrets:

```bash
# Store secrets
echo "your-db-password" | docker secret create db_password -
echo "your-secret-key" | docker secret create secret_key -

# Reference in compose
environment:
  DATABASE_URL: postgresql://user:FILE__db_password@host/db
  SECRET_KEY: FILE__secret_key
```

### Production - Kubernetes

Use Kubernetes Secrets:

```bash
# Create secret
kubectl create secret generic youtube-oauth \
  --from-literal=client-id=... \
  --from-literal=client-secret=... \
  -n waddlebot

# Reference in deployment
env:
- name: YOUTUBE_CLIENT_ID
  valueFrom:
    secretKeyRef:
      name: youtube-oauth
      key: client-id
```

### Production - Vault/AWS Secrets Manager

```bash
# Load from external secret manager
eval "$(vault kv get -format=json secret/waddlebot | \
  jq -r '.data.data | to_entries[] | "export \(.key)=\(.value)"')"

# Or with AWS Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id waddlebot/youtube-music \
  --region us-east-1 \
  | jq -r '.SecretString | fromjson | to_entries[] | "export \(.key)=\(.value)"'
```

## Troubleshooting Configuration Issues

### Variable Not Being Loaded

Check in this order:

1. **Is it in .env file?**
   ```bash
   grep YOUTUBE_CLIENT_ID .env
   ```

2. **Is it in environment?**
   ```bash
   echo $YOUTUBE_CLIENT_ID
   ```

3. **Is it in container/pod?**
   ```bash
   docker-compose exec youtube-music-interaction env | grep YOUTUBE
   # or
   kubectl exec -it deployment/youtube-music-interaction -- env | grep YOUTUBE
   ```

4. **Check application logs for loading message**
   ```bash
   docker-compose logs youtube-music-interaction | grep -i config
   ```

### Database Connection Failures

Test connection manually:

```bash
# Use psql
psql "$DATABASE_URL"

# Or from inside container
docker-compose exec youtube-music-interaction \
  python3 -c "from sqlalchemy import create_engine; \
              engine = create_engine('$DATABASE_URL'); \
              print(engine.execute('SELECT 1'))"
```

### Credential Loading Issues

Check database for stored credentials:

```bash
psql "$DATABASE_URL"

SELECT * FROM platform_integrations 
WHERE platform = 'youtube' 
  AND is_active = TRUE;
```

---

**Last Updated**: 2026-02-16
