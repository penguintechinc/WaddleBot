# OpenWhisk Action Module - Usage Guide

## Getting Started

This guide walks you through setting up and using the OpenWhisk Action Module.

## Prerequisites

- Docker & Docker Compose
- OpenWhisk instance (local, IBM Cloud, or self-hosted)
- PostgreSQL database
- Python 3.13+ (for local development)
- OpenWhisk API key with action invocation permissions

## Quick Start (Docker)

### 1. Clone and Navigate

```bash
cd /home/penguin/code/waddlebot/action/pushing/openwhisk_action_module/
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your OpenWhisk details:

```env
OPENWHISK_API_HOST=https://openwhisk.example.com
OPENWHISK_AUTH_KEY=namespace:your-api-key-here
OPENWHISK_NAMESPACE=guest
DATABASE_URL=postgres://waddlebot:password@localhost:5432/waddlebot
MODULE_SECRET_KEY=your-64-character-secret-key-must-be-64-chars-or-longer
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

Verify services are running:

```bash
docker-compose ps
```

Expected output:
```
NAME                          STATUS
openwhisk_action_module       Up 2 seconds
postgres_openwhisk            Up 3 seconds (health: healthy)
```

### 4. Verify Module is Running

```bash
curl http://localhost:8082/health
```

Expected response:
```json
{
  "status": "healthy",
  "module": "openwhisk_action_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T21:30:45.123456",
  "database": "connected",
  "grpc_port": 50062,
  "rest_port": 8082,
  "openwhisk_api_host": "https://openwhisk.example.com",
  "namespace": "guest"
}
```

## OpenWhisk Configuration

### Setting Up OpenWhisk Credentials

The module uses `OPENWHISK_AUTH_KEY` in `namespace:key` format.

#### Get Your API Key

**For IBM Cloud Functions**:

```bash
# Login to IBM Cloud
ibmcloud login

# Get API key
ibmcloud fn property get --auth

# Format: namespace:key
# Example: waddlebot@example.com_dev:3a2e4c8f9d1b5e7a...
```

**For Local OpenWhisk**:

```bash
# With Docker installation
docker exec -it openwhisk_controller cat /data/wskdata/guest.whitelist

# Or if using standalone
wsk property get --auth
```

**For Self-Hosted OpenWhisk**:

```bash
# Contact your OpenWhisk administrator for:
# 1. API host URL
# 2. Namespace
# 3. API key
```

### Configure in .env

```env
OPENWHISK_API_HOST=https://openwhisk.cloud.ibm.com
OPENWHISK_AUTH_KEY=waddlebot@example.com_dev:3a2e4c8f9d1b5e7a...
OPENWHISK_NAMESPACE=guest
```

### Test Connection

```bash
curl -X GET http://localhost:8082/health | jq '.status'
# Should return: "healthy"
```

## Namespace Configuration

The module supports working with different OpenWhisk namespaces:

### Default Namespace

```env
OPENWHISK_NAMESPACE=guest
```

All invocations default to this namespace.

### Per-Request Namespace Override

When invoking actions, optionally specify a different namespace:

```bash
curl -X POST http://localhost:8082/api/v1/actions/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_name": "my-action",
    "namespace": "my-custom-namespace",
    "payload": {}
  }'
```

## Database Setup

### Using Docker Compose (Automatic)

The provided `docker-compose.yml` includes PostgreSQL:

```yaml
postgres_openwhisk:
  image: postgres:15
  environment:
    POSTGRES_USER: waddlebot
    POSTGRES_PASSWORD: password
    POSTGRES_DB: waddlebot
  ports:
    - "5432:5432"
```

### Using External Database

Update `DATABASE_URL` in `.env`:

```env
DATABASE_URL=postgres://user:password@your-db-host:5432/your-database
```

### Create Required Tables

```bash
psql postgres://waddlebot:password@localhost:5432/waddlebot

-- Create openwhisk_action_executions table
CREATE TABLE openwhisk_action_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) UNIQUE,
    namespace VARCHAR(255) NOT NULL,
    action_name VARCHAR(255) NOT NULL,
    action_type VARCHAR(50),
    payload TEXT,
    blocking BOOLEAN,
    timeout INTEGER,
    activation_id VARCHAR(255),
    result TEXT,
    duration_ms INTEGER,
    status VARCHAR(50),
    success BOOLEAN,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_namespace ON openwhisk_action_executions(namespace);
CREATE INDEX idx_action_name ON openwhisk_action_executions(action_name);
CREATE INDEX idx_activation_id ON openwhisk_action_executions(activation_id);
CREATE INDEX idx_success ON openwhisk_action_executions(success);
```

## Health Check

The health endpoint verifies module status:

```bash
curl -X GET http://localhost:8082/health | jq '.'
```

Check these indicators:

- `status`: Should be `healthy`
- `database`: Should be `connected`
- `openwhisk_api_host`: Should match your configuration

## First Invocation

### Step 1: Generate API Token

```bash
TOKEN=$(curl -s -X POST http://localhost:8082/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"my-api-key"}' | jq -r '.token')

echo "Token: $TOKEN"
```

**Note**: Replace `my-api-key` with your API key.

### Step 2: List Available Actions

```bash
curl -X GET http://localhost:8082/api/v1/actions \
  -H "Authorization: Bearer $TOKEN" | jq '.actions'
```

Expected response:
```json
[
  {
    "name": "my-action",
    "namespace": "guest",
    "kind": "nodejs:14",
    "updated": 1645123456789
  }
]
```

### Step 3: Invoke an Action

First, create a test action in OpenWhisk:

```bash
# Create simple action
echo 'exports.main = async (params) => ({ message: "Hello from OpenWhisk" })' > hello.js

# Deploy to OpenWhisk
wsk action create my-test-action hello.js
```

Then invoke it:

```bash
curl -X POST http://localhost:8082/api/v1/actions/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_name": "my-test-action",
    "payload": {"name": "WaddleBot"},
    "blocking": true
  }' | jq '.'
```

Expected response:
```json
{
  "execution_id": "exec_1645123456789",
  "success": true,
  "activation_id": "3e27a4f0b4d94fcb27a4f0b4d94fcb2",
  "result": {
    "message": "Hello from OpenWhisk"
  },
  "duration": 125
}
```

## Local Development Setup

### 1. Create Virtual Environment

```bash
python3.13 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create .env File

```env
OPENWHISK_API_HOST=https://openwhisk.cloud.ibm.com
OPENWHISK_AUTH_KEY=namespace:key
OPENWHISK_NAMESPACE=guest
DATABASE_URL=postgres://waddlebot:password@localhost:5432/waddlebot
MODULE_SECRET_KEY=change-me-to-64-character-secret-key-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GRPC_PORT=50062
REST_PORT=8082
LOG_LEVEL=DEBUG
```

### 4. Run Tests

```bash
pytest tests/ -v
```

### 5. Start Module

```bash
python app.py
```

Expected startup output:
```
[2026-02-16 21:30:00] INFO root - Starting openwhisk_action_module v1.0.0
[2026-02-16 21:30:01] INFO services - OpenWhisk service initialized
[2026-02-16 21:30:01] INFO grpc - Starting gRPC server on 0.0.0.0:50062
[2026-02-16 21:30:01] INFO app - Hypercorn starting on 0.0.0.0:8082
```

## Working with Different Action Types

### Regular Actions

```bash
curl -X POST http://localhost:8082/api/v1/actions/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_name": "my-action",
    "payload": {"data": "value"},
    "blocking": true
  }'
```

### Web Actions

Web actions are invoked with HTTP context:

```bash
curl -X POST http://localhost:8082/api/v1/web-actions/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "package_name": "default",
    "action_name": "hello",
    "method": "POST",
    "headers": {"X-Custom": "value"},
    "payload": {}
  }'
```

### Sequences

Invoke a sequence (multiple actions chained):

```bash
curl -X POST http://localhost:8082/api/v1/sequences/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sequence_name": "action1->action2->action3",
    "payload": {"initial": "data"}
  }'
```

### Triggers

Fire a trigger to start rules:

```bash
curl -X POST http://localhost:8082/api/v1/triggers/fire \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "my-trigger",
    "payload": {"event": "data"}
  }'
```

## Async vs Blocking

### Blocking (Wait for Result)

```env
blocking: true
```

- Client waits for action completion
- Returns result and logs
- Maximum timeout: 5-10 minutes (configurable)

### Non-Blocking (Fire and Forget)

```env
blocking: false
```

- Action queued immediately
- Returns activation ID
- Client can poll for results
- Useful for long-running actions

## Troubleshooting Setup Issues

### Cannot Connect to OpenWhisk

Error:
```
Connection refused or timeout
```

Solution:
1. Verify `OPENWHISK_API_HOST` is correct
2. Ensure OpenWhisk instance is running
3. Check network connectivity: `curl -X GET $OPENWHISK_API_HOST/api/v1/namespaces`
4. Verify API key: `curl -u YOUR_NAMESPACE:This15TotallyAnExampleKey! -X GET $OPENWHISK_API_HOST/api/v1/namespaces`

### Invalid API Key

Error:
```
{"error": "Unauthorized"}
```

Solution:
1. Get correct API key from OpenWhisk
2. Verify format: `namespace:key` (must have colon)
3. Test with wsk CLI: `wsk action list`

### Actions Not Found

Error:
```
{"error": "action not found"}
```

Solution:
1. Verify action exists: `wsk action list`
2. Check namespace is correct
3. Create test action: `wsk action create test-action test.js`

## Stopping the Module

```bash
# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop local Python
# Press Ctrl+C in terminal
```

## Environment Variables Summary

| Variable | Default | Purpose | Required |
|----------|---------|---------|----------|
| OPENWHISK_API_HOST | https://openwhisk.example.com | OpenWhisk API URL | Yes |
| OPENWHISK_AUTH_KEY | - | namespace:key format | Yes |
| OPENWHISK_NAMESPACE | guest | Default namespace | No |
| OPENWHISK_INSECURE | false | Skip HTTPS verify | No |
| DATABASE_URL | - | PostgreSQL connection | Yes |
| GRPC_PORT | 50062 | gRPC port | No |
| REST_PORT | 8082 | REST port | No |
| MODULE_SECRET_KEY | - | JWT secret (64+ chars) | Yes |
| JWT_EXPIRATION_SECONDS | 3600 | Token lifetime | No |
| MAX_WORKERS | 20 | Concurrent workers | No |
| REQUEST_TIMEOUT | 30 | Request timeout | No |
| LOG_LEVEL | INFO | Logging level | No |

See [CONFIGURATION.md](CONFIGURATION.md) for complete details.

## Next Steps

- [API Reference](API.md) - Learn all endpoints
- [Architecture](ARCHITECTURE.md) - Understand system design
- [Testing Guide](TESTING.md) - Run tests
- [Troubleshooting](TROUBLESHOOTING.md) - Common errors
