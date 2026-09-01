# Action Serverless Service

Combined microservice that merges 3 serverless action modules into a single Quart application on port 8103.

## Modules Included

1. **AWS Lambda Module** (port 8103 → `/api/v1/lambda`)
   - Lambda function invocation
   - JWT-based authentication
   - Support for aliases and versions
   - Execution logging and error handling
   - gRPC service on port 50051

2. **Apache OpenWhisk Module** (port 8103 → `/api/v1/openwhisk`)
   - OpenWhisk action invocation
   - Blocking and non-blocking execution modes
   - API key validation
   - JWT token generation
   - gRPC service on port 50052

3. **GCP Cloud Functions Module** (port 8103 → `/api/v1/gcp`)
   - GCP Cloud Function invocation
   - Service account authentication
   - Region-specific deployment support
   - Custom header support
   - gRPC service on port 50053

## Architecture

```
/app/
  app.py                        # Combined Quart entry point
  config.py                     # Unified configuration
  requirements.txt              # Merged dependencies
  Dockerfile                    # Multi-stage build
  lambda_action_module/         # AWS Lambda service code
  openwhisk_action_module/      # Apache OpenWhisk service code
  gcp_functions_action_module/  # GCP Cloud Functions service code
  libs/                         # Shared Quart utilities
```

## API Endpoints

### Health & Status
- `GET /healthz` - Liveness probe
- `GET /health` - Health with timestamp
- `GET /api/v1/health` - Unified service status

### AWS Lambda
- `GET /api/v1/lambda/health` - Lambda module health check
- `POST /api/v1/lambda/token` - Generate JWT token (requires `client_id` + `client_secret`)
- `POST /api/v1/lambda/invoke` - Invoke Lambda function (requires function name and payload)

### Apache OpenWhisk
- `GET /api/v1/openwhisk/health` - OpenWhisk module health check
- `POST /api/v1/openwhisk/token` - Generate JWT token (requires valid `api_key`)
- `POST /api/v1/openwhisk/invoke` - Invoke OpenWhisk action (requires action name and optional namespace)

### GCP Cloud Functions
- `GET /api/v1/gcp/health` - GCP module health check
- `POST /api/v1/gcp/token` - Generate JWT token (requires valid `api_key`)
- `POST /api/v1/gcp/invoke` - Invoke GCP Cloud Function (requires function name, optional project/region)

## Environment Variables

### AWS Lambda
```bash
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
LAMBDA_MODULE_SECRET_KEY=your-lambda-secret
LAMBDA_JWT_EXPIRATION_SECONDS=3600
LAMBDA_JWT_ALGORITHM=HS256
LAMBDA_DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
```

### Apache OpenWhisk
```bash
OPENWHISK_API_HOST=https://api.openwhisk.ng.bluemix.net
OPENWHISK_NAMESPACE=your-namespace
OPENWHISK_API_KEY=your-openwhisk-api-key
OPENWHISK_JWT_EXPIRATION_SECONDS=3600
OPENWHISK_JWT_ALGORITHM=HS256
```

### GCP Cloud Functions
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GCP_PROJECT_ID=your-gcp-project
GCP_REGION=us-central1
GCP_JWT_EXPIRATION_SECONDS=3600
GCP_JWT_ALGORITHM=HS256
GCP_API_KEY=your-gcp-api-key
```

### Common
```bash
# Service
MODULE_NAME=action-serverless
MODULE_VERSION=1.0.0
MODULE_PORT=8103
MODULE_HOST=0.0.0.0

# Logging
LOG_DIR=/var/log/waddlebot
LOG_LEVEL=INFO

# gRPC Ports
GRPC_LAMBDA_PORT=50051
GRPC_OPENWHISK_PORT=50052
GRPC_GCP_PORT=50053
```

## Building

### Local Build
```bash
docker build -t action-serverless:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8103:8103 \
  -p 50051:50051 \
  -p 50052:50052 \
  -p 50053:50053 \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e OPENWHISK_API_HOST=https://api.openwhisk.ng.bluemix.net \
  -e OPENWHISK_API_KEY=your-key \
  -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-creds.json \
  -e GCP_PROJECT_ID=your-project \
  -v /path/to/gcp-creds.json:/path/to/gcp-creds.json \
  action-serverless:latest
```

## Ports

- **8103** - HTTP REST API (all 3 modules)
- **50051** - gRPC service (AWS Lambda module)
- **50052** - gRPC service (Apache OpenWhisk module)
- **50053** - gRPC service (GCP Cloud Functions module)

## Service Authentication

### AWS Lambda
Requires JWT token obtained from `/api/v1/lambda/token` endpoint:

```bash
# 1. Generate token
curl -X POST http://localhost:8103/api/v1/lambda/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"your-id","client_secret":"your-secret"}'

# 2. Use token in Authorization header
curl -X POST http://localhost:8103/api/v1/lambda/invoke \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name":"my-function",
    "payload":{"key":"value"},
    "invocation_type":"RequestResponse",
    "alias":"live",
    "version":"$LATEST"
  }'
```

### Apache OpenWhisk
Requires API key validation and JWT token:

```bash
# 1. Generate token
curl -X POST http://localhost:8103/api/v1/openwhisk/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"your-openwhisk-api-key","service":"my-service"}'

# 2. Use token for action invocation
curl -X POST http://localhost:8103/api/v1/openwhisk/invoke \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace":"my-namespace",
    "action_name":"my-action",
    "payload":{"key":"value"},
    "blocking":true,
    "timeout":30000
  }'
```

### GCP Cloud Functions
Requires API key validation and service token:

```bash
# 1. Generate token
curl -X POST http://localhost:8103/api/v1/gcp/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"your-gcp-api-key","service":"my-service","permissions":["invoke_functions"]}'

# 2. Use token for function invocation
curl -X POST http://localhost:8103/api/v1/gcp/invoke \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project":"my-gcp-project",
    "region":"us-central1",
    "function_name":"my-function",
    "payload":{"key":"value"},
    "headers":{"X-Custom-Header":"value"}
  }'
```

Health endpoints are exempt from authentication:
```bash
curl http://localhost:8103/health
curl http://localhost:8103/api/v1/lambda/health
curl http://localhost:8103/api/v1/openwhisk/health
curl http://localhost:8103/api/v1/gcp/health
```

## Database Schema

The AWS Lambda module uses penguin-dal with `migrate=False` for runtime queries:

- Lambda: invocations, execution logs, function metadata
- Database initialization via Alembic only

## Module Loading

Each module initializes independently. If a module fails to initialize, it is disabled and health checks report `disabled` status (HTTP 503). This allows the service to continue operating with available modules:

- Lambda disabled → Lambda endpoints return 503, other modules work
- OpenWhisk disabled → OpenWhisk endpoints return 503, other modules work
- GCP disabled → GCP endpoints return 503, other modules work

All disabled modules are logged at startup with detailed error messages.

## Logging

Uses structured logging with file rotation:
- Log file: `/var/log/waddlebot/action_serverless.log`
- Max file size: 10 MB
- Backup count: 5 rotated files
- Console and file output simultaneously
- Per-module initialization and invocation logging

## Request/Response Examples

### AWS Lambda Invocation
**Request:**
```json
{
  "function_name": "my-lambda-function",
  "payload": {"event": "data"},
  "invocation_type": "RequestResponse",
  "alias": "prod",
  "version": "$LATEST"
}
```

**Response (Success):**
```json
{
  "success": true,
  "status_code": 200,
  "payload": {"result": "success"},
  "executed_version": "$1",
  "log_result": "[execution logs]"
}
```

### OpenWhisk Action Invocation
**Request:**
```json
{
  "namespace": "production",
  "action_name": "my-action",
  "payload": {"input": "data"},
  "blocking": true,
  "timeout": 30000
}
```

**Response (Success):**
```json
{
  "success": true,
  "activationId": "activation-id",
  "result": {"output": "data"}
}
```

### GCP Cloud Function Invocation
**Request:**
```json
{
  "project": "my-gcp-project",
  "region": "us-central1",
  "function_name": "my-function",
  "payload": {"input": "data"},
  "headers": {"X-Custom": "header"}
}
```

**Response (Success):**
```json
{
  "success": true,
  "executionId": "execution-id",
  "result": {"output": "data"}
}
```
