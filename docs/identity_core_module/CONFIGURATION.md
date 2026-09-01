# Identity Core Module - Configuration Guide

## Overview

This document describes all configuration options for the Identity Core Module, including environment variables, database settings, Docker configuration, and deployment options.

---

## Environment Variables

### Core Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MODULE_NAME` | string | identity_core_module | No | Module identifier for logging |
| `MODULE_VERSION` | string | 2.0.0 | No | Module version for tracking |
| `MODULE_PORT` | integer | 8050 | No | REST API server port |
| `GRPC_PORT` | integer | 50030 | No | gRPC server port |

**Example:**
```bash
MODULE_NAME=identity_core_module
MODULE_VERSION=2.0.0
MODULE_PORT=8050
GRPC_PORT=50030
```

---

### Database Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATABASE_URL` | string | postgresql://... | Yes | PostgreSQL connection string |

**Format:**
```bash
DATABASE_URL=postgresql://username:password@host:port/database
```

**Example:**
```bash
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
```

**Connection Pool Settings (from flask_core):**
- Default pool size: 10 connections
- Max overflow: 20 connections
- Pool timeout: 30 seconds
- Pool recycle: 3600 seconds (1 hour)

---

### Service URLs

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CORE_API_URL` | string | http://router-service:8000 | No | Core API base URL |
| `ROUTER_API_URL` | string | http://router-service:8000/api/v1/router | No | Router service URL |

**Example:**
```bash
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router
```

---

### Security Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SECRET_KEY` | string | change-me-in-production | Yes | JWT signing key and session encryption |

**Example:**
```bash
SECRET_KEY=your-very-secure-random-key-here-min-32-chars
```

**Security Best Practices:**
- Use a cryptographically secure random string
- Minimum 32 characters recommended
- Rotate keys periodically
- Never commit to version control
- Use secrets management in production

**Generate Secure Key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### Logging Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LOG_LEVEL` | string | INFO | No | Logging verbosity level |

**Valid Values:**
- `DEBUG` - Detailed debugging information
- `INFO` - General informational messages
- `WARNING` - Warning messages for potential issues
- `ERROR` - Error messages for failures
- `CRITICAL` - Critical failures requiring immediate attention

**Example:**
```bash
LOG_LEVEL=INFO
```

---

## Configuration File (.env)

The module uses `python-dotenv` to load environment variables from a `.env` file.

### Sample .env File

```bash
# Identity Core Module Configuration
# Copy this to .env and customize for your environment

# Module Settings
MODULE_NAME=identity_core_module
MODULE_VERSION=2.0.0
MODULE_PORT=8050
GRPC_PORT=50030

# Database Connection
DATABASE_URL=postgresql://waddlebot:secure_password@postgres:5432/waddlebot

# Service URLs
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Security
SECRET_KEY=change-me-to-a-secure-random-key-minimum-32-characters

# Logging
LOG_LEVEL=INFO
```

### File Location

Place `.env` file in the module root:
```
/home/penguin/code/Waddles/core/identity_core_module/.env
```

### Loading Order

1. Environment variables (highest priority)
2. `.env` file
3. Default values in `config.py` (lowest priority)

---

## Docker Configuration

### Dockerfile

Location: `/home/penguin/code/Waddles/core/identity_core_module/Dockerfile`

**Key Configuration:**

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Copy shared library
COPY libs/flask_core /app/libs/flask_core

# Install shared library
RUN cd /app/libs/flask_core && pip install --no-cache-dir .

# Copy module files
COPY identity_core_module_flask/requirements.txt /app/
COPY identity_core_module_flask /app/

# Install module dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8050", "--workers", "4"]
```

### Build Configuration

**Build Context:** Parent directory (to access shared libs)

**Build Command:**
```bash
cd /home/penguin/code/Waddles
docker build -f core/identity_core_module/Dockerfile \
  -t waddlebot/identity-core:latest .
```

**Multi-stage Build Tags:**
```bash
# Development
docker build -t waddlebot/identity-core:dev .

# Production
docker build -t waddlebot/identity-core:2.0.0 .
docker tag waddlebot/identity-core:2.0.0 waddlebot/identity-core:latest
```

---

### Docker Compose Configuration

#### Service Definition

```yaml
services:
  identity-core:
    image: waddlebot/identity-core:latest
    container_name: waddlebot-identity-core
    restart: unless-stopped
    ports:
      - "8050:8050"
      - "50030:50030"
    environment:
      - MODULE_PORT=8050
      - GRPC_PORT=50030
      - DATABASE_URL=postgresql://waddlebot:${DB_PASSWORD}@postgres:5432/waddlebot
      - CORE_API_URL=http://router-service:8000
      - ROUTER_API_URL=http://router-service:8000/api/v1/router
      - SECRET_KEY=${SECRET_KEY}
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - waddlebot-network
    volumes:
      - identity-logs:/var/log/waddlebotlog
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8050/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:16-alpine
    container_name: waddlebot-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=waddlebot
      - POSTGRES_USER=waddlebot
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./config/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./config/postgres/migrations:/docker-entrypoint-initdb.d/migrations
    networks:
      - waddlebot-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U waddlebot"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  identity-logs:
  postgres-data:

networks:
  waddlebot-network:
    driver: bridge
```

#### Environment Variables File

Create `docker-compose.env`:
```bash
# Database
DB_PASSWORD=your_secure_database_password

# Identity Core
SECRET_KEY=your_secure_secret_key_min_32_chars
```

**Load with:**
```bash
docker-compose --env-file docker-compose.env up -d
```

---

## Database Schema

### Required Tables

The Identity Core Module uses these database tables:

#### hub_users

```sql
CREATE TABLE hub_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    username VARCHAR(100),
    password_hash VARCHAR(255),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_super_admin BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(100),
    email_verification_expires TIMESTAMP,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### hub_user_identities

```sql
CREATE TABLE hub_user_identities (
    id SERIAL PRIMARY KEY,
    hub_user_id INTEGER REFERENCES hub_users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(100) NOT NULL,
    platform_username VARCHAR(100),
    platform_email VARCHAR(255),
    avatar_url TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, platform_user_id)
);
```

#### hub_user_profiles

```sql
CREATE TABLE hub_user_profiles (
    id SERIAL PRIMARY KEY,
    hub_user_id INTEGER REFERENCES hub_users(id) ON DELETE CASCADE UNIQUE,
    display_name VARCHAR(100),
    bio TEXT,
    location VARCHAR(100),
    website_url VARCHAR(255),
    custom_avatar_url TEXT,
    banner_url TEXT,
    social_links JSONB DEFAULT '{}',
    visibility VARCHAR(30) DEFAULT 'shared_communities',
    show_activity BOOLEAN DEFAULT TRUE,
    show_communities BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### hub_oauth_states

```sql
CREATE TABLE hub_oauth_states (
    id SERIAL PRIMARY KEY,
    state VARCHAR(100) UNIQUE NOT NULL,
    mode VARCHAR(20) DEFAULT 'login',
    platform VARCHAR(50),
    user_id INTEGER REFERENCES hub_users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### hub_sessions

```sql
CREATE TABLE hub_sessions (
    id SERIAL PRIMARY KEY,
    hub_user_id INTEGER REFERENCES hub_users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Database Indexes

Performance indexes (from migration 001):

```sql
-- Session lookups
CREATE INDEX idx_hub_sessions_token
  ON hub_sessions(session_token) WHERE is_active = true;

-- Identity platform lookups
CREATE INDEX idx_hub_user_identities_platform_lookup
  ON hub_user_identities(platform, platform_user_id);

CREATE INDEX idx_hub_user_identities_hub_user
  ON hub_user_identities(hub_user_id);

-- User lookups
CREATE INDEX idx_hub_users_email ON hub_users(email);
CREATE INDEX idx_hub_users_username ON hub_users(username);
CREATE INDEX idx_hub_users_active
  ON hub_users(id) WHERE is_active = true;
```

### Database Migration

Apply migrations using:
```bash
psql -U waddlebot -d waddlebot -f /home/penguin/code/Waddles/config/postgres/init.sql
psql -U waddlebot -d waddlebot -f /home/penguin/code/Waddles/config/postgres/migrations/001_add_performance_indexes.sql
```

---

## Hypercorn Server Configuration

The module uses Hypercorn as the ASGI server for Quart.

### Runtime Configuration

**Default Settings:**
```python
config = HyperConfig()
config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
config.workers = 4
```

### Advanced Configuration

Create `hypercorn-config.toml`:

```toml
# Hypercorn Configuration for Identity Core Module

bind = ["0.0.0.0:8050"]
workers = 4
worker_class = "asyncio"

# Timeouts
graceful_timeout = 30
keep_alive_timeout = 5

# SSL/TLS (production)
# certfile = "/path/to/cert.pem"
# keyfile = "/path/to/key.pem"

# Logging
accesslog = "/var/log/waddlebotlog/identity-access.log"
errorlog = "/var/log/waddlebotlog/identity-error.log"
loglevel = "info"

# Performance
backlog = 2048
max_app_queue_size = 10

# Server Headers
server_names = ["identity-core"]
```

**Run with config file:**
```bash
hypercorn app:app --config hypercorn-config.toml
```

---

## gRPC Server Configuration

### Port Configuration

```python
GRPC_PORT = int(os.getenv('GRPC_PORT', '50030'))
```

### Server Initialization

```python
grpc_server = aio.server()
grpc_server.add_insecure_port(f"0.0.0.0:{Config.GRPC_PORT}")
await grpc_server.start()
```

### TLS Configuration (Production)

For production, use TLS:

```python
# Load credentials
with open('server.key', 'rb') as f:
    private_key = f.read()
with open('server.crt', 'rb') as f:
    certificate = f.read()

# Create credentials
credentials = grpc.ssl_server_credentials(
    [(private_key, certificate)]
)

# Add secure port
grpc_server.add_secure_port(
    f"0.0.0.0:{Config.GRPC_PORT}",
    credentials
)
```

---

## Production Configuration Checklist

### Security
- [ ] Change `SECRET_KEY` to secure random value
- [ ] Use strong database password
- [ ] Enable HTTPS/TLS for REST API
- [ ] Enable TLS for gRPC
- [ ] Set `LOG_LEVEL` to `INFO` or `WARNING`
- [ ] Disable debug mode
- [ ] Configure firewall rules
- [ ] Use environment-specific secrets management

### Performance
- [ ] Tune database connection pool
- [ ] Configure Hypercorn workers (CPU cores × 2-4)
- [ ] Enable database query caching
- [ ] Configure reverse proxy (nginx/traefik)
- [ ] Enable gzip compression
- [ ] Set up CDN for static assets

### Monitoring
- [ ] Configure Prometheus metrics scraping
- [ ] Set up health check monitoring
- [ ] Configure log aggregation
- [ ] Enable database slow query logging
- [ ] Set up alerts for errors

### Database
- [ ] Run all migrations
- [ ] Configure database backups
- [ ] Set up replication (if needed)
- [ ] Optimize indexes
- [ ] Configure connection pooling

### Deployment
- [ ] Use container orchestration (Kubernetes/Docker Swarm)
- [ ] Configure auto-scaling
- [ ] Set up load balancing
- [ ] Configure rolling updates
- [ ] Set resource limits

---

## Configuration Validation

### Startup Validation

The module validates configuration on startup:

```python
# Required variables check
assert Config.DATABASE_URL, "DATABASE_URL must be set"
assert Config.SECRET_KEY != "change-me-in-production", \
    "SECRET_KEY must be changed for production"
```

### Manual Validation

Validate configuration:

```bash
# Test database connection
python3 -c "from config import Config; print(Config.DATABASE_URL)"

# Test module startup
python3 app.py
```

---

## Troubleshooting Configuration

### Common Issues

#### Database Connection Failed
```
Error: could not connect to database
```

**Solutions:**
- Verify `DATABASE_URL` format
- Check database is running
- Verify network connectivity
- Check credentials
- Ensure database exists

#### Port Already in Use
```
Error: Address already in use: 0.0.0.0:8050
```

**Solutions:**
- Change `MODULE_PORT` or `GRPC_PORT`
- Stop conflicting service
- Check for zombie processes

#### Module Won't Start
```
Error: No module named 'flask_core'
```

**Solutions:**
- Install shared library: `cd libs/flask_core && pip install .`
- Verify PYTHONPATH includes libs directory
- Check Docker build includes shared libs

---

## Environment-Specific Configurations

### Development

```bash
# .env.development
MODULE_PORT=8050
GRPC_PORT=50030
DATABASE_URL=postgresql://waddlebot:dev123@localhost:5432/waddlebot_dev
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key-not-for-production
```

### Staging

```bash
# .env.staging
MODULE_PORT=8050
GRPC_PORT=50030
DATABASE_URL=postgresql://waddlebot:${DB_PASSWORD}@postgres-staging:5432/waddlebot_staging
LOG_LEVEL=INFO
SECRET_KEY=${SECRET_KEY_STAGING}
```

### Production

```bash
# .env.production
MODULE_PORT=8050
GRPC_PORT=50030
DATABASE_URL=postgresql://waddlebot:${DB_PASSWORD}@postgres-prod:5432/waddlebot
LOG_LEVEL=WARNING
SECRET_KEY=${SECRET_KEY_PROD}
```

**Load environment-specific config:**
```bash
export ENV=production
python3 app.py
```

---

## Configuration Reference Summary

| Category | Variables | Required | Default |
|----------|-----------|----------|---------|
| Core | MODULE_NAME, MODULE_VERSION, MODULE_PORT, GRPC_PORT | No | See defaults |
| Database | DATABASE_URL | Yes | localhost |
| Services | CORE_API_URL, ROUTER_API_URL | No | router-service |
| Security | SECRET_KEY | Yes | change-me |
| Logging | LOG_LEVEL | No | INFO |

---

## Additional Resources

- [Flask Core Library Documentation](../../libs/flask_core/README.md)
- [Database Schema Documentation](../../config/postgres/README.md)
- [Docker Deployment Guide](../../docs/deployment/docker.md)
- [Hypercorn Documentation](https://hypercorn.readthedocs.io/)
- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
