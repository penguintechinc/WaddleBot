# OpenWhisk Action Module - Overview

## Purpose

The OpenWhisk Action Module is a stateless, clusterable microservice that enables WaddleBot to invoke Apache OpenWhisk actions. This module receives task instructions from the processor/router via gRPC protocol and pushes actions to OpenWhisk for execution. The module provides both gRPC and REST API interfaces for maximum flexibility.

### Key Capabilities

- **Action Invocation**: Invoke OpenWhisk actions (synchronous and asynchronous)
- **Sequence Invocation**: Execute OpenWhisk sequences (chained actions)
- **Web Action Support**: Invoke web-enabled actions with custom headers
- **Trigger Management**: Fire OpenWhisk triggers for event-driven workflows
- **Activation Tracking**: Query activation details and logs
- **Namespace Support**: Work with multiple OpenWhisk namespaces
- **JWT Authentication**: Secure REST API endpoints with JWT tokens
- **gRPC Streaming**: High-performance communication with processor/router
- **Database Logging**: All executions logged to PostgreSQL for audit
- **Credential Management**: Load OpenWhisk credentials from environment or database

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.13+ |
| Web Framework | Quart | Async |
| gRPC | gRPC Python | Latest |
| OpenWhisk SDK | apache-openwhisk | Latest |
| HTTP Client | aiohttp | Async |
| Database | PyDAL/PostgreSQL | - |
| Container | Docker | Latest |
| Authentication | JWT (HS256) | Standard |

## Module Information

- **Module Name**: openwhisk_action_module
- **Repository Location**: `/action/pushing/openwhisk_action_module/`
- **Language**: Python
- **gRPC Port**: 50062 (verified in GRPC_PORT_VISUAL_REFERENCE.txt)
- **REST API Port**: 8082
- **Database**: PostgreSQL (via PyDAL)

## Documentation Index

| Document | Purpose |
|----------|---------|
| [OVERVIEW.md](OVERVIEW.md) | Module overview, capabilities, and quick reference |
| [USAGE.md](USAGE.md) | Getting started guide, Docker setup, OpenWhisk configuration |
| [API.md](API.md) | Complete REST and gRPC API endpoint documentation |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, authentication patterns |
| [CONFIGURATION.md](CONFIGURATION.md) | Environment variables, configuration options, example .env file |
| [TESTING.md](TESTING.md) | Unit testing with mock clients, test data, execution guide |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common errors, auth issues, namespace problems |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history and release information |

## Quick Reference

### Starting the Module

```bash
# Development
docker-compose -f docker-compose.yml up -d

# Production
docker run -e OPENWHISK_API_HOST=https://openwhisk.example.com \
  -e OPENWHISK_AUTH_KEY=namespace:key \
  -e OPENWHISK_NAMESPACE=guest \
  -e DATABASE_URL=postgres://user:pass@host/db \
  -p 50062:50062 -p 8082:8082 \
  openwhisk_action_module:latest
```

### Health Check

```bash
curl -X GET http://localhost:8082/health
```

### Generate Authentication Token

```bash
curl -X POST http://localhost:8082/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"your-api-key"}'
```

### Invoke OpenWhisk Action (REST)

```bash
# Get token first
TOKEN=$(curl -s -X POST http://localhost:8082/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"your-key"}' | jq -r '.token')

# Invoke action
curl -X POST http://localhost:8082/api/v1/actions/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_name": "my-action",
    "payload": {"input": "value"},
    "blocking": true
  }'
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    WaddleBot Platform                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐         ┌──────────────────┐   │
│  │  Processor       │        │OpenWhisk Action  │   │
│  │  Router          │────────│  Module          │   │
│  └──────────────────┘ gRPC   └──────────────────┘   │
│                                     │                │
│                        ┌────────────┴────────────┐  │
│                        │                         │  │
│                   ┌─────────┐           ┌──────────┐│
│                   │ REST    │           │OpenWhisk ││
│                   │ API     │──────────│REST API  ││
│                   └─────────┘ HTTP     └──────────┘│
│                        │                           │
│                   ┌─────────┐                      │
│                   │Database │                      │
│                   │(PyDAL)  │                      │
│                   └─────────┘                      │
└─────────────────────────────────────────────────────┘
```

## Communication Patterns

### Blocking Invocation (Synchronous)

1. Client sends `InvokeActionRequest` via REST/gRPC
2. Module receives request and validates credentials
3. Module invokes OpenWhisk action with blocking=true
4. OpenWhisk executes action and returns result
5. Module logs execution to database
6. Module sends response with activation ID and result

### Non-Blocking Invocation (Asynchronous)

1. Client sends `InvokeActionRequest` with blocking=false
2. Module queues action for execution
3. Module returns activation ID immediately
4. Action executes independently
5. Client can poll for results using activation ID

### Sequence Execution

1. Client invokes a sequence (multiple actions chained)
2. OpenWhisk executes first action
3. Output passed to next action in sequence
4. Final output returned to client

## OpenWhisk Configuration

The module supports multiple credential sources:

1. **Environment Variables** (highest priority)
   - `OPENWHISK_API_HOST`: OpenWhisk API endpoint
   - `OPENWHISK_AUTH_KEY`: namespace:key format
   - `OPENWHISK_NAMESPACE`: Namespace name

2. **Database Integration Table** (fallback)
   - Loads from `platform_integrations` table
   - Query: `SELECT access_token, config_data FROM platform_integrations WHERE platform='openwhisk' AND integration_type='bot' AND is_active=TRUE`

3. **Redis Credential Listener** (optional real-time refresh)
   - Listens to: `credentials:openwhisk:bot:refreshed`
   - Automatically reloads on update

## REST API Overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/auth/token` | POST | Generate JWT token |
| `/api/v1/actions/invoke` | POST | Invoke action |
| `/api/v1/actions/invoke-async` | POST | Async invocation |
| `/api/v1/sequences/invoke` | POST | Invoke sequence |
| `/api/v1/web-actions/invoke` | POST | Invoke web action |
| `/api/v1/triggers/fire` | POST | Fire trigger |
| `/api/v1/activations/<id>` | GET | Get activation details |
| `/api/v1/actions` | GET | List actions |
| `/api/v1/stats` | GET | Module statistics |

## gRPC Services

The module implements gRPC services for processor/router integration:

- `OpenWhiskActionService`: Main service for action invocation
  - `InvokeAction()`: Execute action
  - `InvokeSequence()`: Execute sequence
  - `FireTrigger()`: Fire trigger
  - `GetActivation()`: Retrieve activation
  - `ListActions()`: List available actions

## Database Schema

### openwhisk_action_executions Table

```sql
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
```

## Configuration Summary

Key environment variables:

```
OPENWHISK_API_HOST         # OpenWhisk API URL (REQUIRED)
OPENWHISK_AUTH_KEY         # namespace:key format (REQUIRED)
OPENWHISK_NAMESPACE        # Default namespace (default: guest)
OPENWHISK_INSECURE         # Skip HTTPS verification (false)
DATABASE_URL               # PostgreSQL connection (REQUIRED)
GRPC_PORT                  # gRPC port (default: 50062)
REST_PORT                  # REST port (default: 8082)
JWT_EXPIRATION_SECONDS     # Token lifetime (default: 3600)
MODULE_SECRET_KEY          # JWT secret (64+ chars, REQUIRED)
MAX_WORKERS                # Concurrent workers (default: 20)
REQUEST_TIMEOUT            # Request timeout (default: 30)
LOG_LEVEL                  # Logging level (default: INFO)
```

For complete details, see [CONFIGURATION.md](CONFIGURATION.md).

## Performance Characteristics

- **Throughput**: Up to 20 concurrent actions (configurable)
- **Latency**: Varies by action, typically 100-500ms
- **Async Latency**: Sub-100ms queue + return
- **Database Logging**: ~10-20ms per execution
- **Horizontal Scaling**: Stateless design allows multiple replicas

## Security Features

- **JWT Authentication**: All REST endpoints secured
- **OpenWhisk Key Management**: Credentials protected
- **HTTPS Support**: Full TLS/SSL support
- **Request Validation**: Input validation on all endpoints
- **Error Safety**: No credentials in error messages

## Limitations

- Maximum payload size: 1 MB (OpenWhisk limit)
- Action timeout: 5-600 seconds (configurable)
- Namespace must be pre-configured
- No multi-namespace switching per invocation

## Next Steps

- [Getting Started](USAGE.md) - Set up environment
- [API Reference](API.md) - Explore endpoints
- [Configuration](CONFIGURATION.md) - Environment setup
- [Testing](TESTING.md) - Run tests

## Support & Troubleshooting

For common issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

For deployment questions, refer to main WaddleBot documentation.
