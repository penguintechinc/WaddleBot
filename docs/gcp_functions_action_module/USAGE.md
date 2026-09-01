# GCP Functions Action Module - Usage Guide

## Getting Started

The GCP Functions Action Module is a containerized service that invokes GCP Cloud Functions. This guide covers setup, configuration, and basic usage.

## Prerequisites

Before running the module, you need:

1. **GCP Project**
   - GCP project with billing enabled
   - Cloud Functions API enabled
   - Cloud Functions created and deployed

2. **Service Account**
   - Service Account with Cloud Functions Invoker role
   - JSON key file downloaded

3. **Cloud Functions**
   - At least one Cloud Function deployed
   - Function accessible from module network
   - Correct region configured

4. **Database**
   - PostgreSQL 12+ (included in docker-compose.yml)
   - Can use existing database with DATABASE_URL

5. **Docker & Docker Compose**
   - Docker Engine 20.10+
   - Docker Compose 2.0+

## GCP Project Setup

### 1. Enable Cloud Functions API

```bash
gcloud services enable cloudfunctions.googleapis.com
```

### 2. Create Service Account

```bash
gcloud iam service-accounts create waddlebot-functions \
  --display-name "WaddleBot Cloud Functions"
```

### 3. Grant Required Permissions

```bash
# Cloud Functions Invoker role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member "serviceAccount:waddlebot-functions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role "roles/cloudfunctions.invoker"

# Cloud Functions Viewer role (for listing functions)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member "serviceAccount:waddlebot-functions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role "roles/cloudfunctions.viewer"
```

### 4. Create and Download JSON Key

```bash
gcloud iam service-accounts keys create gcp-key.json \
  --iam-account=waddlebot-functions@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

Save the key securely - you'll use it for GCP_SERVICE_ACCOUNT_KEY.

### 5. Deploy a Test Cloud Function

```bash
gcloud functions deploy my-test-function \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --region us-central1 \
  --source . \
  --entry-point main
```

Note the function name and region for later use.

## Quick Start with Docker Compose

### 1. Clone Repository
```bash
cd /home/penguin/code/waddlebot/action/pushing/gcp_functions_action_module
```

### 2. Create Environment File
```bash
cp .env.example .env
```

Edit .env and set:
```
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1
GCP_SERVICE_ACCOUNT_KEY=/path/to/gcp-key.json
GCP_SERVICE_ACCOUNT_EMAIL=waddlebot-functions@YOUR_PROJECT_ID.iam.gserviceaccount.com
MODULE_SECRET_KEY=your_64_character_secret_key_here
```

### 3. Mount GCP Credentials

In docker-compose.yml, add volume mount:
```yaml
services:
  gcp_functions_action_module:
    volumes:
      - ./gcp-key.json:/app/gcp-key.json:ro
    environment:
      GCP_SERVICE_ACCOUNT_KEY: /app/gcp-key.json
```

### 4. Start the Service
```bash
docker-compose up -d
```

Verify it's running:
```bash
docker-compose logs -f gcp_functions_action_module
```

### 5. Check Health
```bash
curl http://localhost:8081/health
```

Expected response:
```json
{
  "status": "healthy",
  "module": "gcp_functions_action_module",
  "version": "1.0.0",
  "database": "connected",
  "gcp_project": "my-project",
  "gcp_region": "us-central1"
}
```

## First API Request

### 1. Generate Authentication Token
```bash
curl -X POST http://localhost:8081/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "any_key_in_testing",
    "service": "my_service",
    "permissions": ["invoke_functions"]
  }'
```

Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

### 2. Invoke a Cloud Function
```bash
curl -X POST http://localhost:8081/api/v1/functions/invoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "project": "my-project",
    "region": "us-central1",
    "function_name": "my-test-function",
    "payload": {"message": "Hello Cloud Function"}
  }'
```

Response:
```json
{
  "success": true,
  "status_code": 200,
  "response": "Function output here",
  "execution_id": "my-test-function_1708077045",
  "execution_time_ms": 245
}
```

## Docker Compose Configuration

The included docker-compose.yml includes:

- gcp_functions_action_module (Python service)
- PostgreSQL database
- Redis (optional credential caching)

```yaml
version: '3.8'
services:
  gcp_functions_action_module:
    build: .
    environment:
      GCP_PROJECT_ID: ${GCP_PROJECT_ID}
      GCP_REGION: ${GCP_REGION}
      GCP_SERVICE_ACCOUNT_KEY: ${GCP_SERVICE_ACCOUNT_KEY}
      MODULE_SECRET_KEY: ${MODULE_SECRET_KEY}
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      GRPC_PORT: 50061
      REST_PORT: 8081
    ports:
      - "50061:50061"
      - "8081:8081"
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: waddlebot
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Logging

View real-time logs:
```bash
docker-compose logs -f gcp_functions_action_module
```

View specific module logs:
```bash
docker-compose exec gcp_functions_action_module tail -f /var/log/waddlebotlog/gcp_functions_action.log
```

## Configuration

See CONFIGURATION.md for all environment variables and their meanings.

Key variables:
- GCP_PROJECT_ID - Your GCP project ID
- GCP_REGION - GCP region (default: us-central1)
- GCP_SERVICE_ACCOUNT_KEY - Service account JSON key (path or inline)
- DATABASE_URL - PostgreSQL connection string
- GRPC_PORT - gRPC server port (default: 50061)
- REST_PORT - REST API port (default: 8081)
- MODULE_SECRET_KEY - JWT signing key
- MAX_BATCH_SIZE - Max functions per batch (default: 100)
- FUNCTION_TIMEOUT - Per-function timeout in seconds (default: 60)

## Health Check Endpoint

Health endpoint with connection verification:
```bash
curl http://localhost:8081/health
```

Returns:
- status: "healthy" or "unhealthy"
- database: "connected" or error
- gcp_project: configured project ID
- gcp_region: configured region
- grpc_port: listening port
- rest_port: listening port

If status is "unhealthy", check:
1. Database connectivity (PostgreSQL running?)
2. GCP credentials validity
3. GCP project ID correct
4. Network connectivity to GCP
5. Logs for error details

## Common Tasks

### List Cloud Functions

```bash
curl "http://localhost:8081/api/v1/functions/list?project=my-project&region=us-central1" \
  -H "Authorization: Bearer TOKEN"
```

Response:
```json
{
  "project": "my-project",
  "region": "us-central1",
  "functions": [
    {
      "name": "my-function",
      "status": "ACTIVE",
      "runtime": "python311",
      "entryPoint": "main"
    }
  ],
  "count": 1
}
```

### Get Function Details

```bash
curl "http://localhost:8081/api/v1/functions/my-function/details?project=my-project&region=us-central1" \
  -H "Authorization: Bearer TOKEN"
```

### Invoke HTTP Function

```bash
curl -X POST http://localhost:8081/api/v1/functions/invoke-http \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "url": "https://us-central1-my-project.cloudfunctions.net/my-function",
    "payload": {"data": "test"},
    "method": "POST",
    "headers": {"X-Custom-Header": "value"},
    "timeout": 30
  }'
```

### Batch Invoke Functions

```bash
curl -X POST http://localhost:8081/api/v1/functions/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "invocations": [
      {
        "function_name": "function-1",
        "payload": {"id": 1}
      },
      {
        "function_name": "function-2",
        "payload": {"id": 2}
      },
      {
        "function_name": "function-3",
        "payload": {"id": 3}
      }
    ]
  }'
```

Response:
```json
{
  "responses": [
    {"success": true, "status_code": 200},
    {"success": true, "status_code": 200},
    {"success": false, "error": "Function not found"}
  ],
  "total_count": 3,
  "success_count": 2,
  "failure_count": 1
}
```

### Get Statistics

```bash
curl "http://localhost:8081/api/v1/stats" \
  -H "Authorization: Bearer TOKEN"
```

Response:
```json
{
  "module": "gcp_functions_action_module",
  "version": "1.0.0",
  "stats": {
    "total_invocations": 156,
    "successful_invocations": 152,
    "failed_invocations": 4,
    "average_execution_time_ms": 342,
    "grpc_port": 50061,
    "rest_port": 8081,
    "gcp_project": "my-project",
    "gcp_region": "us-central1"
  },
  "timestamp": "2026-02-16T10:30:45.123456"
}
```

## Troubleshooting

**Module fails to start:**
- Check GCP_PROJECT_ID is set
- Check GCP credentials file path
- Check DATABASE_URL is valid
- Check logs: `docker-compose logs gcp_functions_action_module`

**Health check fails:**
- Database connectivity: Check PostgreSQL is running
- GCP credentials: Verify service account key
- GCP project: Ensure project ID is correct
- Logs show permission denied: Check IAM roles

**Function invocations fail:**
- Function not found: Verify function name and region
- Permission denied: Check service account has Cloud Functions Invoker role
- Authentication failed: Verify GCP credentials
- Timeout: Increase FUNCTION_TIMEOUT if functions are slow

See TROUBLESHOOTING.md for more detailed error resolution.
