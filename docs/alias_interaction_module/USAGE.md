# Alias Interaction Module — Usage Guide

## Overview

This guide covers practical scenarios for using the Alias Interaction Module, from local development to production deployment.

**Current Version:** 2.0.0

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Running Locally](#running-locally)
3. [Docker Deployment](#docker-deployment)
4. [Health Checks](#health-checks)
5. [Common Workflows](#common-workflows)
6. [Variable Substitution Examples](#variable-substitution-examples)
7. [Integration Examples](#integration-examples)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 12+
- Docker & Docker Compose (for containerized deployment)
- pip package manager

### Quick Installation

```bash
# Navigate to project root
cd /home/penguin/code/waddlebot

# Install module dependencies
cd action/interactive/alias_interaction_module
pip install -r requirements.txt

# Set up environment variables (see CONFIGURATION.md)
cp .env.example .env
# Edit .env with your database credentials
```

---

## Running Locally

### Option 1: Direct Python Execution

```bash
# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/waddlebot"
export MODULE_PORT="8010"
export LOG_LEVEL="DEBUG"

# Run the application
cd action/interactive/alias_interaction_module
python3 app.py
```

The service will start on `http://localhost:8010`

### Option 2: Using Hypercorn (Production-like)

```bash
# Install hypercorn if not already installed
pip install hypercorn

# Run with Hypercorn
cd action/interactive/alias_interaction_module
hypercorn app:app --bind 0.0.0.0:8010 --workers 4
```

This simulates production configuration with 4 worker processes.

### Option 3: Docker Compose

```bash
# Build the image
docker build -f action/interactive/alias_interaction_module/Dockerfile \
  -t waddlebot/alias-interaction:latest .

# Run the container
docker run -d \
  -e DATABASE_URL="postgresql://user:pass@postgres:5432/waddlebot" \
  -e MODULE_PORT="8010" \
  -e LOG_LEVEL="INFO" \
  -p 8010:8010 \
  --name alias-interaction \
  waddlebot/alias-interaction:latest
```

---

## Docker Deployment

### Building the Image

```bash
# From project root
docker build -f action/interactive/alias_interaction_module/Dockerfile \
  -t waddlebot/alias-interaction:2.0.0 .

# Tag for registry
docker tag waddlebot/alias-interaction:2.0.0 registry.io/waddlebot/alias-interaction:2.0.0

# Push to registry
docker push registry.io/waddlebot/alias-interaction:2.0.0
```

### Docker Compose Integration

```yaml
# docker-compose.yml snippet
services:
  alias-interaction:
    image: waddlebot/alias-interaction:2.0.0
    container_name: alias-interaction
    environment:
      DATABASE_URL: "postgresql://waddlebot:password@postgres:5432/waddlebot"
      MODULE_PORT: "8010"
      CORE_API_URL: "http://router-service:8000"
      ROUTER_API_URL: "http://router-service:8000/api/v1/router"
      LOG_LEVEL: "INFO"
      REDIS_URL: "redis://redis:6379"
    ports:
      - "8010:8010"
    depends_on:
      - postgres
      - redis
    volumes:
      - /var/log/waddlebotlog:/var/log/waddlebotlog
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alias-interaction
spec:
  replicas: 3
  selector:
    matchLabels:
      app: alias-interaction
  template:
    metadata:
      labels:
        app: alias-interaction
    spec:
      containers:
      - name: alias-interaction
        image: waddlebot/alias-interaction:2.0.0
        ports:
        - containerPort: 8010
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: alias-secrets
              key: database-url
        - name: MODULE_PORT
          value: "8010"
        livenessProbe:
          httpGet:
            path: /health
            port: 8010
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8010
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Health Checks

### Health Check Endpoint

The module provides a standard health check endpoint:

```bash
# Check service health
curl http://localhost:8010/health

# Expected response (200 OK)
{
  "status": "healthy",
  "timestamp": "2026-02-16T10:30:00Z",
  "service": "alias_interaction_module",
  "version": "2.0.0"
}
```

### Metrics Endpoint

```bash
# Get service metrics
curl http://localhost:8010/metrics

# Returns Prometheus-format metrics including:
# - Request count and latency
# - Database connection status
# - Service uptime
```

### Startup Verification

```bash
# Check logs after startup
docker logs alias-interaction

# Expected startup output:
# [INFO] Starting alias_interaction_module
# [INFO] Database connection established
# [INFO] alias_interaction_module started - result: SUCCESS
```

---

## Common Workflows

### Creating an Alias

```bash
# Create a new alias for a community
curl -X POST http://localhost:8010/api/v1/aliases \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "community-123",
    "alias_name": "diagnose",
    "command": "check_system_status --user {user} --verbose",
    "created_by": "admin-user-456"
  }'

# Response (201 Created)
{
  "data": {
    "id": "alias-789",
    "alias_name": "diagnose",
    "command": "check_system_status --user {user} --verbose"
  }
}
```

### Listing Community Aliases

```bash
# Get all active aliases for a community
curl "http://localhost:8010/api/v1/aliases?community_id=community-123"

# Response (200 OK)
{
  "data": [
    {
      "id": "alias-789",
      "community_id": "community-123",
      "alias_name": "diagnose",
      "command": "check_system_status --user {user} --verbose",
      "usage_count": 5,
      "is_active": true
    },
    {
      "id": "alias-790",
      "community_id": "community-123",
      "alias_name": "report",
      "command": "create_incident --title {arg1} --body {all_args}",
      "usage_count": 12,
      "is_active": true
    }
  ]
}
```

### Executing an Alias with Variables

```bash
# Execute an alias with user and arguments
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -H "Content-Type: application/json" \
  -d '{
    "alias_name": "diagnose",
    "user": "john_doe",
    "args": []
  }'

# Response (200 OK)
{
  "data": {
    "command": "check_system_status --user john_doe --verbose"
  }
}
```

### Executing with Arguments

```bash
# Execute alias with positional arguments
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -H "Content-Type: application/json" \
  -d '{
    "alias_name": "report",
    "user": "jane_smith",
    "args": ["Server down", "Production", "Critical"]
  }'

# Response expands variables:
{
  "data": {
    "command": "create_incident --title Server down --body Server down Production Critical"
  }
}
```

### Deleting an Alias

```bash
# Soft delete an alias
curl -X DELETE http://localhost:8010/api/v1/aliases/alias-789

# Response (200 OK)
{
  "data": {
    "message": "Alias deleted"
  }
}
```

---

## Variable Substitution Examples

The module supports the following variable placeholders:

| Variable | Description | Example |
|---|---|---|
| `{user}` | Current user identifier | `john_doe` |
| `{args}` | All arguments space-separated | `Server down Production` |
| `{arg1}` | First argument | `Server` |
| `{arg2}` | Second argument | `down` |
| `{all_args}` | All arguments (same as {args}) | `Server down Production` |

### Example 1: User-Aware Command

```json
{
  "alias_name": "check_email",
  "command": "send_notification {user}@company.com status_report"
}
```

Execution:
```bash
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -d '{
    "alias_name": "check_email",
    "user": "alice",
    "args": []
  }'
```

Results in: `send_notification alice@company.com status_report`

### Example 2: Positional Arguments

```json
{
  "alias_name": "schedule",
  "command": "book_meeting --attendees {arg1} --duration {arg2} --organizer {user}"
}
```

Execution with `["team-engineering", "30"]`:

Results in: `book_meeting --attendees team-engineering --duration 30 --organizer bob`

### Example 3: Dynamic Commands

```json
{
  "alias_name": "search",
  "command": "elasticsearch --index logs --query {all_args}"
}
```

Execution with `["status:error", "host:production-1", "last:24h"]`:

Results in: `elasticsearch --index logs --query status:error host:production-1 last:24h`

---

## Integration Examples

### Slack Integration

Create aliases to interact with Slack workflows:

```bash
# Create alias for posting to Slack
curl -X POST http://localhost:8010/api/v1/aliases \
  -d '{
    "community_id": "slack-community-1",
    "alias_name": "alert",
    "command": "slack.post_message --channel {arg1} --severity {arg2} --message {all_args}",
    "created_by": "bot-manager"
  }'

# Use it
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -d '{
    "alias_name": "alert",
    "user": "monitoring-bot",
    "args": ["#alerts", "CRITICAL", "Database replication lag detected"]
  }'
```

### Discord Integration

```bash
# Create alias for Discord commands
curl -X POST http://localhost:8010/api/v1/aliases \
  -d '{
    "community_id": "discord-guild-1",
    "alias_name": "announce",
    "command": "discord.send --channel {arg1} --embed.author {user}",
    "created_by": "admin"
  }'
```

### Router Module Integration

The module can integrate with the Router Service for complex routing:

```bash
# Create alias that calls router
curl -X POST http://localhost:8010/api/v1/aliases \
  -d '{
    "community_id": "community-1",
    "alias_name": "route_action",
    "command": "router.execute --action {arg1} --context {all_args}",
    "created_by": "admin"
  }'
```

---

## Troubleshooting

### Module Fails to Start

**Problem:** Service won't start, getting connection errors

**Solution:**
```bash
# Check database connection
export DATABASE_URL="postgresql://user:pass@localhost:5432/waddlebot"
python3 -c "from config import Config; print(Config.DATABASE_URL)"

# Verify PostgreSQL is running
psql -U user -d waddlebot -c "SELECT 1"

# Check logs
docker logs alias-interaction
```

### Alias Execution Returns None

**Problem:** `execute_alias` returns None even though alias exists

**Solution:**
```bash
# Verify alias exists and is_active=true
curl "http://localhost:8010/api/v1/aliases?community_id=your-community-id" \
  | grep -i "alias_name"

# Check for typos in alias_name request parameter
# Verify is_active flag is true in database
```

### Variable Substitution Not Working

**Problem:** Variables like {user} not being replaced in command

**Solution:**
```bash
# Verify proper JSON format in request
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -H "Content-Type: application/json" \
  -d '{"alias_name": "test", "user": "username", "args": ["arg1"]}'

# Check for typos in variable names (case-sensitive)
# Ensure args array is properly formatted
```

### Database Connection Timeout

**Problem:** Getting timeout errors on database operations

**Solution:**
```bash
# Increase connection timeout
export DATABASE_URL="postgresql://user:pass@localhost:5432/waddlebot?connect_timeout=10"

# Check PostgreSQL logs
tail -f /var/log/postgresql/postgresql.log

# Verify network connectivity
ping postgres-server
```

---

## Performance Tuning

### Increasing Worker Count

For high-traffic deployments, increase Hypercorn workers:

```bash
# In docker-compose or dockerfile
hypercorn app:app --bind 0.0.0.0:8010 --workers 8
```

### Connection Pooling

Configure database connection pooling in environment:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/waddlebot?pool_size=20&max_overflow=40"
```

### Caching Aliases

For frequently accessed aliases, consider implementing Redis caching by extending the AliasService class.

---

## Security Considerations

- Always use environment variables for sensitive credentials
- Rotate SECRET_KEY regularly in production
- Use HTTPS/TLS for all API communications
- Validate alias commands before execution
- Implement rate limiting on execute endpoint
- Use strong database credentials
- Enable PostgreSQL SSL connections

See [CONFIGURATION.md](CONFIGURATION.md) for detailed security setup.
