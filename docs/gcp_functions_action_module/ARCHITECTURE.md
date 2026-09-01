# GCP Functions Action Module - Architecture

## System Overview

The GCP Functions Action Module is a stateless, horizontally scalable microservice built with Python 3.13 that processes Cloud Function invocation tasks from the WaddleBot router and executes them against Google Cloud Platform Cloud Functions.

## Component Architecture

### 1. REST API Server (Quart)

The Quart ASGI server provides REST endpoints on port 8081:

- Handles HTTP requests from third-party integrations
- JWT token generation and validation
- Request routing to GCP Functions Service
- Error handling and response formatting
- Logging of all requests

Key endpoints:
- /health - Health check with GCP connectivity
- /api/v1/auth/token - JWT token generation
- /api/v1/functions/invoke - Invoke Cloud Functions
- /api/v1/functions/invoke-http - HTTP function invocation
- /api/v1/functions/batch - Batch invocation
- /api/v1/functions/list - List functions
- /api/v1/stats - Invocation statistics

### 2. gRPC Server

The gRPC server on port 50061 handles task processing from the router:

- Receives GCPFunctionActionRequest messages
- Processes Cloud Function invocation tasks
- Returns GCPFunctionActionResponse with results
- Streaming support for batch operations

Protocol Buffers define the message format:
- GCPFunctionActionRequest
- GCPFunctionActionResponse
- GCPFunctionAction enum

### 3. GCP Functions Service

Core business logic for Cloud Function invocations:

```python
class GCPFunctionsService:
    - _load_credentials() - Load service account credentials
    - _ensure_session() - HTTP session management
    - _get_id_token() - Generate ID tokens for auth
    - invoke_function() - Invoke Cloud Function
    - invoke_http_function() - HTTP function invocation
    - list_functions() - List all functions
    - get_function_details() - Get function metadata
    - close() - Cleanup resources
```

All methods are async using aiohttp for HTTP requests to GCP.

### 4. Authentication Service

JWT token management for API access:

```python
class AuthService:
    - create_service_token() - Generate JWT tokens
    - verify_token() - Validate JWT tokens
    - validate_api_key() - Check API keys
```

Supports both API key validation and JWT tokens.

### 5. gRPC Handler

Implements the GCPFunctionsActionServicer from protobuf:

```python
class GCPFunctionsActionServicer:
    - ExecuteAction(request, context) - Execute single invocation
    - BatchExecuteActions(request_iterator) - Batch operations

class GrpcServer:
    - start() - Start gRPC server
    - stop() - Stop gRPC server
```

Bridges between gRPC messages and GCP Functions Service.

### 6. Configuration Management

The Config class centralizes environment configuration:

- GCP settings (project ID, region, credentials)
- Database connection (PyDAL)
- Server settings (ports, host)
- Security settings (JWT secret, algorithm)
- Performance tuning (workers, timeouts)
- Logging configuration
- Testing mode flags

Supports:
- Environment variable loading
- Database credential loading
- Credential refresh via Redis
- Validation with error/warning reporting

### 7. Database Layer

PyDAL (Python Data Abstraction Layer) handles database operations:

**Tables:**
- gcp_function_invocations: Audit log of all invocations
  - execution_id: Unique invocation identifier
  - project_id, region: GCP location
  - function_name: Cloud Function name
  - payload: JSON input data
  - status_code: HTTP response code
  - success: Boolean result
  - response: Function output
  - error: Error message if failed
  - execution_time_ms: Duration
  - created_at: Timestamp

Connection pooling with 10 connections for performance.

## GCP Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│         GCP Service Account Authentication                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Module Startup                                            │
│     └─> Load credentials from:                              │
│        a) GCP_SERVICE_ACCOUNT_KEY (JSON string/file path)   │
│        b) Default credentials (GCE/GKE environment)         │
│                                                               │
│  2. Function Invocation                                      │
│     └─> Get ID token for Cloud Function                     │
│        Using service account credentials                    │
│                                                               │
│  3. HTTP Request to Cloud Function                           │
│     ├─> URL: https://region-project.cloudfunctions.net/fn  │
│     ├─> Header: Authorization: Bearer ID_TOKEN             │
│     └─> Payload: JSON with function input                  │
│                                                               │
│  4. Response Handling                                        │
│     ├─> Parse HTTP response                                 │
│     ├─> Log to database                                     │
│     └─> Return to requester                                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Request Flow

### REST API Invocation Flow

```
1. Client Request (REST)
   |
   ├─> Quart Router
   |   |
   |   ├─> require_auth decorator
   |   |   └─> JWT validation
   |   |
   |   ├─> Request parsing
   |   |   └─> Parameter validation
   |   |
   |   └─> GCP Functions Service method call
   |       |
   |       ├─> _ensure_session()
   |       ├─> _get_id_token()
   |       ├─> aiohttp.ClientSession.post()
   |       │   └─> GCP Cloud Functions API
   |       ├─> Parse response
   |       ├─> Log to database
   |       └─> Return result
   |
   └─> Response (JSON or error)
```

### gRPC Batch Processing Flow

```
1. Router sends GCPFunctionActionRequest[] (gRPC)
   |
   ├─> gRPC Server receives request
   |   |
   |   ├─> GCPFunctionsActionServicer.BatchExecuteActions()
   |   |
   |   ├─> Create async tasks for each invocation
   |   |   └─> GCP Functions Service method calls
   |   |
   |   ├─> asyncio.gather() for concurrent execution
   |   |
   |   └─> Aggregate results
   |
   └─> Return GCPFunctionActionResponse[] (gRPC)
       with success status and details for each
```

## Concurrency Model

**Async I/O Architecture:**

- All external I/O is async (GCP API, database, network)
- Quart provides ASGI async runtime
- gRPC server runs in thread pool executor
- aiohttp ClientSession for HTTP requests
- PyDAL handles connection pooling

**Threading Model:**

- Main thread: Quart event loop
- gRPC thread pool: Configurable workers (default: 10)
- Max worker threads: 20 (configurable MAX_WORKERS)
- Credential listener: Background daemon thread (optional)

**Batch Processing:**

- asyncio.gather() for concurrent function invocations
- Up to 100 functions per batch (configurable)
- Each function invocation in parallel
- Results aggregated with success counts

## Error Handling

**Retry Logic:**

- MAX_RETRIES: 3 attempts (configurable)
- RETRY_DELAY: 1 second initial delay
- Exponential backoff: delay * (attempt + 1)

**Specific Error Handling:**

- GCP API errors: Log and return with details
- Authentication errors: Return 401/403
- Network errors: Retry with backoff
- Timeout errors: Return timeout error
- Invalid credentials: Return authentication error
- Database errors: Log and return error

## Scaling Considerations

**Stateless Design:**

- No local state or memory
- All state in database or GCP
- Can scale horizontally with multiple instances

**Load Balancing:**

```
        ┌─────────────────────────────────┐
        │       Load Balancer             │
        │      (nginx/HAProxy)            │
        └─────────────────────────────────┘
         │         │         │         │
         ▼         ▼         ▼         ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │Instance1│ │Instance2│ │Instance3│
    └─────────┘ └─────────┘ └─────────┘
         │         │         │
         └─────────┴─────────┘
                │
         ┌──────────────────┐
         │  PostgreSQL DB   │
         │  (Shared state)  │
         └──────────────────┘
                │
         ┌──────────────────┐
         │ GCP Cloud Fn API │
         └──────────────────┘
```

**Database Considerations:**

- Connection pool per instance (10 connections default)
- Shared PostgreSQL database
- gcp_function_invocations table for audit
- Stats queries use database aggregation

**GCP API Rate Limiting:**

- GCP enforces quotas per service account
- Per-project limits on concurrent executions
- Module retries with exponential backoff
- Monitor GCP quota usage

## Security Architecture

**Credential Management:**

```
┌─────────────────────────────────────┐
│  GCP Credential Options             │
├─────────────────────────────────────┤
│                                     │
│  Option 1: JSON Key File            │
│  GCP_SERVICE_ACCOUNT_KEY=/path/key  │
│                                     │
│  Option 2: JSON String              │
│  GCP_SERVICE_ACCOUNT_KEY='{"...'    │
│                                     │
│  Option 3: Default Credentials      │
│  GCE/GKE environment variables      │
│                                     │
│  Option 4: Database                 │
│  platform_integrations table        │
│                                     │
└─────────────────────────────────────┘
```

**JWT Security:**

- Token signed with MODULE_SECRET_KEY
- HS256 algorithm
- Expiration enforcement
- Created/updated timestamps

**GCP ID Token Security:**

- Per-function ID tokens generated
- Automatic credential refresh
- Valid for 1 hour by default
- Cached in service account credentials

## Dependencies

**Runtime:**

- Python 3.13
- Quart: Async ASGI web framework
- gRPC: Distributed messaging
- PyDAL: Database abstraction
- aiohttp: Async HTTP client
- google-cloud-functions: GCP SDK
- google-auth: GCP authentication
- pyjwt: JWT tokens
- hypercorn: ASGI server

**External:**

- PostgreSQL 12+ database
- GCP Cloud Functions API
- GCP Service Account
- Network connectivity to GCP

## Deployment Models

### Docker Compose (Development)

```yaml
gcp_functions_action_module:
  build: .
  environment: ...
  ports:
    - "50061:50061"
    - "8081:8081"
  depends_on:
    - postgres
```

### Kubernetes (Production)

```yaml
kind: Deployment
apiVersion: apps/v1
metadata:
  name: gcp-functions-action-module
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: gcp-functions-action-module
        image: waddlebot/gcp-functions-action-module:latest
        ports:
        - containerPort: 50061
          name: grpc
        - containerPort: 8081
          name: rest
        env:
        - name: GCP_PROJECT_ID
          valueFrom:
            secretKeyRef:
              name: gcp-secrets
              key: project_id
        - name: GCP_SERVICE_ACCOUNT_KEY
          valueFrom:
            secretKeyRef:
              name: gcp-secrets
              key: service_account_key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: gcp-secrets
              key: database_url
        livenessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Performance Metrics

**Expected Performance:**

- Function invocation latency: 200-1000ms (GCP dependent)
- Batch processing: Up to 100 concurrent invocations
- Throughput: 20-50 invocations/second per instance
- Average execution time: Depends on function complexity

**Scaling Limits:**

- GCP quota limits (project-specific)
- Database: Connection pool (10 per instance)
- Per-instance: 20 max workers
- Per-request: 60 second function timeout

**Monitoring Points:**

- HTTP request latency
- GCP API response time
- Batch completion time
- Database query time
- Error rates
- Success rates
- Execution time distribution
