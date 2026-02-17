# Lambda Action Module - Overview

## Purpose

The Lambda Action Module is a stateless, clusterable microservice that enables WaddleBot to invoke AWS Lambda functions. This module receives task instructions from the processor/router via gRPC protocol and pushes actions to AWS Lambda for execution. The module provides both gRPC and REST API interfaces for maximum flexibility.

### Key Capabilities

- **Synchronous Lambda Invocation**: Invoke Lambda functions and wait for response using `RequestResponse` invocation type
- **Asynchronous Lambda Invocation**: Fire-and-forget Lambda invocations using `Event` invocation type
- **Batch Invocations**: Submit multiple Lambda function invocations in a single batch request
- **Alias & Version Support**: Invoke specific Lambda function aliases or versions
- **Function Discovery**: List all available Lambda functions in the AWS region
- **Function Introspection**: Retrieve detailed configuration for specific Lambda functions
- **JWT Authentication**: Secure REST API endpoints with JWT token-based authentication
- **gRPC Streaming**: High-performance communication with the processor/router
- **Database Logging**: All invocations are logged to PostgreSQL for audit and analytics
- **Credential Management**: Load AWS credentials from environment variables or database integration table

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.13+ |
| Web Framework | Quart | Async |
| gRPC | gRPC Python | Latest |
| AWS SDK | boto3 | Latest |
| Database | PyDAL/PostgreSQL | - |
| Container | Docker | Latest |
| Authentication | JWT (HS256) | Standard |

## Module Information

- **Module Name**: lambda_action_module
- **Repository Location**: `/action/pushing/lambda_action_module/`
- **Language**: Python
- **gRPC Port**: 50060 (verified in GRPC_PORT_VISUAL_REFERENCE.txt)
- **REST API Port**: 8080
- **Database**: PostgreSQL (via PyDAL)

## Documentation Index

| Document | Purpose |
|----------|---------|
| [OVERVIEW.md](OVERVIEW.md) | Module overview, capabilities, and quick reference |
| [USAGE.md](USAGE.md) | Getting started guide, Docker setup, AWS credential configuration |
| [API.md](API.md) | Complete REST and gRPC API endpoint documentation |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, authentication patterns |
| [CONFIGURATION.md](CONFIGURATION.md) | Environment variables, configuration options, example .env file |
| [TESTING.md](TESTING.md) | Unit testing with moto mock, test data, execution guide |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common errors, auth issues, throttling, timeouts, IAM problems |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history and release information |

## Quick Reference

### Starting the Module

```bash
# Development
docker-compose -f docker-compose.yml up -d

# Production
docker run -e AWS_ACCESS_KEY_ID=<key> \
  -e AWS_SECRET_ACCESS_KEY=<secret> \
  -e AWS_REGION=us-east-1 \
  -e DATABASE_URL=postgres://user:pass@host/db \
  -p 50060:50060 -p 8080:8080 \
  lambda_action_module:latest
```

### Health Check

```bash
curl -X GET http://localhost:8080/health
```

### Generate Authentication Token

```bash
curl -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"test","client_secret":"secret"}'
```

### Invoke Lambda Function (REST)

```bash
# Get token first
TOKEN=\$(curl -s -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"test","client_secret":"secret"}' | jq -r '.token')

# Invoke function
curl -X POST http://localhost:8080/api/v1/invoke \
  -H "Authorization: Bearer \$TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "my-function",
    "payload": "{\\"input\\": \\"value\\"}",
    "invocation_type": "RequestResponse"
  }'
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    WaddleBot Platform                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐         ┌──────────────────┐   │
│  │  Processor       │        │  Lambda Action   │   │
│  │  Router          │────────│  Module          │   │
│  └──────────────────┘ gRPC   └──────────────────┘   │
│                                     │                │
│                        ┌────────────┴────────────┐  │
│                        │                         │  │
│                   ┌─────────┐              ┌──────┐ │
│                   │ REST    │              │ AWS  │ │
│                   │ API     │─────────────│Lambda│ │
│                   └─────────┘ boto3 API   └──────┘ │
│                        │                           │
│                   ┌─────────┐                      │
│                   │Database │                      │
│                   │(PyDAL)  │                      │
│                   └─────────┘                      │
└─────────────────────────────────────────────────────────┘
```

## Communication Patterns

### Synchronous Invocation
1. Processor sends `InvokeFunctionRequest` via gRPC
2. Lambda module receives request and validates credentials
3. Module invokes AWS Lambda function with `RequestResponse` type
4. AWS Lambda executes function and returns results
5. Module logs results to database
6. Module sends `InvokeFunctionResponse` with results back to processor

### Asynchronous Invocation
1. Processor sends `InvokeAsyncRequest` via gRPC
2. Lambda module receives request
3. Module invokes AWS Lambda function with `Event` type (fire-and-forget)
4. AWS Lambda returns activation ID immediately
5. Module logs to database and returns activation ID
6. Function executes independently in AWS Lambda

## AWS Credentials Flow

The module supports multiple credential sources with the following priority:

1. **Environment Variables** (highest priority)
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`

2. **Database Integration Table** (fallback)
   - Loads from `platform_integrations` table
   - Query: `SELECT client_id, client_secret, config_data FROM platform_integrations WHERE platform = 'aws_lambda' AND integration_type = 'bot' AND is_active = TRUE`

3. **Redis Credential Listener** (optional real-time refresh)
   - Listens to Redis channel: `credentials:aws_lambda:bot:refreshed`
   - Automatically reloads credentials when notified

## REST API Overview

| Endpoint | Method | Authentication | Purpose |
|----------|--------|----------------|---------|
| `/health` | GET | None | Health check |
| `/api/v1/token` | POST | None | Generate JWT token |
| `/api/v1/invoke` | POST | JWT | Synchronous invocation |
| `/api/v1/invoke-async` | POST | JWT | Asynchronous invocation |
| `/api/v1/batch` | POST | JWT | Batch invocation |
| `/api/v1/functions` | GET | JWT | List functions |
| `/api/v1/functions/<name>` | GET | JWT | Get function config |

## gRPC Services

The module implements the following gRPC services (defined in `grpc_proto/`):

- `LambdaActionService`: Main service for Lambda function invocations
  - `InvokeFunction()`: Synchronous invocation
  - `InvokeAsync()`: Asynchronous invocation
  - `BatchInvoke()`: Batch invocation
  - `ListFunctions()`: List available functions
  - `GetFunctionConfig()`: Get function details

## Database Schema

### lambda_invocations Table

```sql
CREATE TABLE lambda_invocations (
    id INTEGER PRIMARY KEY,
    function_name VARCHAR(255) NOT NULL,
    invocation_type VARCHAR(50) NOT NULL,
    payload TEXT,
    alias VARCHAR(255),
    version VARCHAR(50),
    status_code INTEGER,
    response_payload TEXT,
    function_error VARCHAR(255),
    executed_version VARCHAR(50),
    request_id VARCHAR(255),
    success BOOLEAN,
    error_message TEXT,
    invoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

## Configuration Summary

The module requires these key environment variables:

```
AWS_ACCESS_KEY_ID          # AWS IAM access key (REQUIRED)
AWS_SECRET_ACCESS_KEY      # AWS IAM secret key (REQUIRED)
AWS_REGION                 # AWS region (default: us-east-1)
DATABASE_URL               # PostgreSQL connection URL (REQUIRED)
GRPC_PORT                  # gRPC server port (default: 50060)
REST_PORT                  # REST API port (default: 8080)
JWT_EXPIRATION_SECONDS     # JWT token lifetime (default: 3600)
MODULE_SECRET_KEY          # Secret key for JWT signing (64+ chars, REQUIRED)
MAX_CONCURRENT_REQUESTS    # Max concurrent requests (default: 100)
REQUEST_TIMEOUT            # Request timeout in seconds (default: 30)
LAMBDA_TIMEOUT             # Lambda timeout in seconds (default: 300)
LAMBDA_MEMORY_SIZE         # Lambda memory in MB (default: 512)
LAMBDA_MAX_RETRIES         # Max invocation retries (default: 3)
LOG_LEVEL                  # Logging level (default: INFO)
```

For complete details, see [CONFIGURATION.md](CONFIGURATION.md).

## Performance Characteristics

- **Throughput**: Up to 100 concurrent requests (configurable)
- **Latency**: Synchronous invocations typically 100-500ms (depends on Lambda function)
- **Asynchronous Latency**: Sub-100ms fire-and-forget
- **Database Logging**: ~10-20ms per invocation record
- **Horizontal Scaling**: Stateless design allows unlimited replicas

## Security Features

- **JWT Authentication**: All REST endpoints require Bearer token
- **AWS IAM Integration**: Uses AWS credentials with proper IAM roles
- **HTTPS Support**: Fully compatible with HTTPS/TLS
- **Credential Isolation**: Secrets never logged or exposed
- **Request Validation**: Input validation on all endpoints
- **Error Handling**: Safe error messages without credential leakage

## Limitations

- Maximum synchronous request timeout: 15 minutes (AWS Lambda maximum)
- Maximum payload size: 6 MB (AWS Lambda limit)
- No local state - all state stored in database
- AWS region must be pre-configured (no multi-region support in this version)

## Next Steps

- [Getting Started](USAGE.md) - Set up your development environment
- [API Reference](API.md) - Explore all available endpoints
- [Configuration](CONFIGURATION.md) - Learn about environment variables
- [Testing](TESTING.md) - Run tests with moto mock

## Support & Troubleshooting

For common issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

For deployment questions, refer to the main WaddleBot documentation.
