# Lambda Action Module - Architecture

## System Architecture

The Lambda Action Module is designed as a stateless, horizontally scalable microservice that bridges WaddleBot with AWS Lambda.

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    WaddleBot Platform                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────┐                                 │
│  │ Processor / Router   │                                 │
│  │ (Task Distribution)  │                                 │
│  └──────────┬───────────┘                                 │
│             │ gRPC                                        │
│    ┌────────┴─────────────────────────┐                  │
│    │ Load Balancer / Service Mesh     │                  │
│    └────────┬─────────────────────────┘                  │
│             │                                             │
│  ┌──────────┴──────────────────────────────────────────┐ │
│  │  Lambda Action Module (Stateless Replicas)         │ │
│  │  ┌─────────────────────────────────────────────┐   │ │
│  │  │ Replica 1           Replica 2   Replica N  │   │ │
│  │  │ ┌─────────┐      ┌─────────┐  ┌──────────┐ │   │ │
│  │  │ │REST API │      │REST API │  │REST API  │ │   │ │
│  │  │ │(8080)   │      │(8080)   │  │(8080)    │ │   │ │
│  │  │ ├─────────┤      ├─────────┤  ├──────────┤ │   │ │
│  │  │ │gRPC     │      │gRPC     │  │gRPC      │ │   │ │
│  │  │ │(50060)  │      │(50060)  │  │(50060)   │ │   │ │
│  │  │ └────┬────┘      └────┬────┘  └────┬─────┘ │   │ │
│  │  └──────┼───────────────┼────────────┼──────┘ │   │ │
│  │         │               │            │         │   │ │
│  └─────────┼───────────────┼────────────┼─────────┘   │
│            │               │            │             │
│    ┌───────┴───────┬───────┴─┬───────┬──┴──────┐     │
│    │               │         │       │         │     │
│  ┌─▼──────────┐ ┌─▼─┐  ┌────▼──┐ ┌──▼─┐ ┌─────▼──┐ │
│  │AWS Lambda  │ │DB │  │Redis  │ │Log │ │Metrics │ │
│  │API         │ │   │  │ Cache │ │    │ │        │ │
│  └────────────┘ └───┘  └───────┘ └────┘ └────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Component Details

### 1. REST API Server (Quart)

**Location**: `app.py` - REST endpoints

**Responsibilities**:
- Listen on port 8080
- Handle HTTP requests from external clients
- JWT token generation and validation
- Request/response serialization (JSON)
- Error handling and responses

**Key Routes**:
- `GET /health` - Health check
- `POST /api/v1/token` - Token generation
- `POST /api/v1/invoke` - Synchronous invocation
- `POST /api/v1/invoke-async` - Asynchronous invocation
- `POST /api/v1/batch` - Batch invocation
- `GET /api/v1/functions` - List functions
- `GET /api/v1/functions/<name>` - Get function config

**Technology**: Hypercorn ASGI server (production) / Quart development server

### 2. gRPC Server

**Location**: `services/grpc_handler.py`

**Responsibilities**:
- Listen on port 50060
- Handle gRPC requests from processor/router
- Protocol buffer serialization
- Streaming support for batch operations
- Connection management

**gRPC Services**:
- `LambdaActionService.InvokeFunction()`
- `LambdaActionService.InvokeAsync()`
- `LambdaActionService.BatchInvoke()`
- `LambdaActionService.ListFunctions()`
- `LambdaActionService.GetFunctionConfig()`

### 3. Lambda Service

**Location**: `services/lambda_service.py`

**Core Responsibilities**:
- AWS Lambda invocation logic
- Credential management
- boto3 client initialization
- Request/response transformation
- Database logging

**Methods**:
- `invoke_function()` - Synchronous invocation
- `invoke_async()` - Asynchronous invocation
- `invoke_with_alias()` - Alias-specific invocation
- `invoke_with_version()` - Version-specific invocation
- `list_functions()` - Function discovery
- `get_function_config()` - Function configuration retrieval

**Execution Context**:
- Runs in asyncio event loop
- Blocks on boto3 calls using `run_in_executor()`
- Maintains database connection pool

### 4. Configuration Management

**Location**: `config.py`

**Responsibilities**:
- Load configuration from environment
- Validate required settings
- Manage AWS credentials
- Support credentials from database
- Redis credential listener setup

**Key Components**:
- `Config.validate()` - Validate all required settings
- `Config.load_credentials_from_db()` - Load from database
- `Config.start_credential_listener()` - Listen for updates

### 5. Database Layer

**Location**: `app.py` - PyDAL initialization

**Responsibilities**:
- Connection pool management
- Table definition
- Invocation logging
- Query execution

**Tables**:
- `lambda_invocations` - Logs all invocation attempts

**Connection Pool**: 10 connections (configurable)

## Data Flow

### Synchronous Invocation Flow

```
1. Client Request (REST)
   POST /api/v1/invoke with JWT token
   │
2. JWT Validation
   verify_jwt(token) -> valid, payload
   │
3. Service Call
   lambda_service.invoke_function(
     function_name, payload, invocation_type
   )
   │
4. AWS Credentials Load
   Config.AWS_ACCESS_KEY_ID
   Config.AWS_SECRET_ACCESS_KEY
   │
5. boto3 Client Creation
   boto3.client('lambda',
     aws_access_key_id=...,
     aws_secret_access_key=...,
     region_name=...
   )
   │
6. Lambda API Call
   client.invoke(
     FunctionName=function_name,
     InvocationType='RequestResponse',
     Payload=payload,
     LogType='Tail'
   )
   │
7. AWS Lambda Execution
   (AWS side - external)
   │
8. Response Processing
   - Extract status_code (200 = success)
   - Decode response_payload
   - Decode LogResult (base64)
   - Extract executed_version
   │
9. Database Logging
   INSERT INTO lambda_invocations (
     function_name, invocation_type, payload,
     status_code, response_payload, success, ...
   )
   │
10. Return Response
    {
      success: true,
      status_code: 200,
      payload: "...",
      executed_version: "$LATEST",
      log_result: "..."
    }
```

### Asynchronous Invocation Flow

```
1. Client Request
   POST /api/v1/invoke-async
   │
2. JWT Validation
   │
3. Service Call
   lambda_service.invoke_async(
     function_name, payload
   )
   │
4. boto3 Call (Event Type)
   client.invoke(
     FunctionName=function_name,
     InvocationType='Event',
     Payload=payload
   )
   │
5. AWS Lambda Queuing
   Function queued for execution
   │
6. Immediate Response
   status_code = 202 (Accepted)
   return activation_id
   │
7. Database Log
   INSERT (status_code=202, success=true)
   │
8. Return Response
    {
      success: true,
      status_code: 202,
      request_id: "..."
    }
```

## Credential Management

### Credential Priority

```
1. Environment Variables (Highest Priority)
   AWS_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY
   ↓ (if not set)

2. Database Integration Table
   platform_integrations WHERE
   platform='aws_lambda' AND
   integration_type='bot' AND
   is_active=TRUE
   ↓ (if not found)

3. AWS IAM Role (Production)
   EC2/ECS/EKS instance role
```

### Credential Refresh

The module supports real-time credential refresh via Redis:

```
┌─────────────────────────────────┐
│ Credential Management Service   │
│ (External to Lambda Module)     │
└────────────┬────────────────────┘
             │ Updates platform_integrations
             │
        ┌────▼────────────────────┐
        │ Redis Pub/Sub            │
        │ Channel:                 │
        │ credentials:aws_lambda:  │
        │ bot:refreshed            │
        └────┬─────────────────────┘
             │
    ┌────────▼─────────┐
    │ Lambda Module    │
    │ Credential       │
    │ Listener Thread  │
    │ (daemon)         │
    └────────┬─────────┘
             │
        ┌────▼────────────────────┐
        │ Config._credential_lock  │
        │ Set credentials_loaded   │
        │ = false                  │
        │ (reload on next request) │
        └──────────────────────────┘
```

## AWS Authentication

### boto3 Client Initialization

```python
client = boto3.client(
    'lambda',
    aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
    region_name=Config.AWS_REGION
)
```

### IAM Permissions Required

Minimum permissions for invocation:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function/*"
    }
  ]
}
```

Additional permissions for discovery:

```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:ListFunctions",
    "lambda:GetFunction",
    "lambda:GetFunctionConfiguration"
  ],
  "Resource": "*"
}
```

## Invocation Patterns

### RequestResponse (Synchronous)

- Client waits for function completion
- Maximum timeout: 15 minutes (AWS Lambda)
- Returns function output
- Suitable for: Request-response workflows

**Timing**:
```
Request sent → AWS processes → Response received
Time: ~100ms-1s (variable based on function)
```

### Event (Asynchronous)

- AWS queues function for execution
- Immediate return (202 status)
- No results available to caller
- Suitable for: Background jobs, notifications

**Timing**:
```
Request sent → Immediate return (202)
Function processes independently
```

### DryRun

- Validates function exists and permissions correct
- No actual execution
- Useful for pre-flight checks

## Error Handling Strategy

```
┌─────────────────────────────┐
│ Request to invoke_function() │
└────────────┬────────────────┘
             │
      ┌──────▼──────┐
      │ boto3 Call  │
      └──────┬──────┘
             │
      ┌──────┴──────────┬────────────┐
      │                 │            │
   Success         ClientError  Exception
      │                 │            │
      ▼                 ▼            ▼
   ✓ Extract      ✓ Log error   ✓ Log error
   - Status      ✓ Save to DB  ✓ Save to DB
   - Payload     ✓ Return      ✓ Return
   - Logs        (False, err)  (False, err)
      │                 │            │
      └─────────┬───────┴────────────┘
                │
         ┌──────▼──────────┐
         │ Log to Database │
         │ lambda_invoca   │
         │ tions table     │
         └─────────────────┘
```

### Error Types and Handling

| Error Type | Example | Handling | Logging |
|-----------|---------|----------|---------|
| Missing Credentials | AWS_ACCESS_KEY_ID not set | Fail at startup | stdout |
| Invalid Credentials | Expired AWS key | Return 500 error | DB + stdout |
| Function Not Found | Wrong function name | Return 500 error | DB + stdout |
| Lambda Timeout | Function exceeds timeout | Return timeout error | DB + stdout |
| Throttling | Too many concurrent invokes | Return 429 error | DB + stdout |
| Invalid Payload | Payload > 6MB | Return 400 error | stdout |
| Service Error | AWS API unavailable | Return 503 error | DB + stdout |
| Database Error | DB connection fails | Return 500 error | stdout |

## Scaling Considerations

### Horizontal Scaling

The module is completely stateless:
- No in-memory state
- No session affinity required
- No shared state between replicas

Deployment:
```yaml
kind: Deployment
metadata:
  name: lambda-action-module
spec:
  replicas: 3  # Scale to N replicas
  template:
    spec:
      containers:
      - name: lambda-action-module
        image: lambda_action_module:latest
        ports:
        - containerPort: 8080  # REST
        - containerPort: 50060 # gRPC
```

### Connection Pooling

- **Database Pool**: 10 connections (configurable)
- **boto3 Clients**: One per replica (created on startup)
- **gRPC Workers**: 10 thread pool workers

### Rate Limiting

- `MAX_CONCURRENT_REQUESTS`: 100 (default)
- Enforced per replica
- Total capacity = replicas × MAX_CONCURRENT_REQUESTS

## Security Architecture

### Authentication

```
Client Request → JWT Token → verify_jwt() → Payload extracted → Request processed
                    ↓
                  Invalid → 401 Unauthorized
```

### Credential Protection

- AWS credentials never logged (safe printing)
- JWT secret never transmitted
- No credentials in error messages
- Database logs don't include raw credentials

### Network Security

- REST API: HTTP (TLS in production)
- gRPC: Insecure (TLS in production)
- Database: Encrypted connection string
- AWS: HTTPS/TLS always

## Monitoring & Observability

### Logging Levels

```
DEBUG   - Detailed execution flow
INFO    - Key operations (invoke, list, etc.)
WARNING - Configuration issues, credential problems
ERROR   - Failures (AWS errors, DB errors)
```

### Key Metrics to Monitor

```
- Invocation success rate
- Average invocation latency
- Error rate by type
- Database connection pool usage
- gRPC connection count
- JWT token generation rate
```

### Database Queries for Monitoring

```sql
-- Success rate (last hour)
SELECT COUNT(*) FILTER (WHERE success=true) as successes,
       COUNT(*) as total,
       100.0 * COUNT(*) FILTER (WHERE success=true) / COUNT(*) as success_rate
FROM lambda_invocations
WHERE invoked_at > NOW() - INTERVAL '1 hour';

-- Slowest functions (last 24 hours)
SELECT function_name,
       COUNT(*) as invocations,
       AVG(EXTRACT(EPOCH FROM (completed_at - invoked_at))) as avg_duration_s,
       MAX(EXTRACT(EPOCH FROM (completed_at - invoked_at))) as max_duration_s
FROM lambda_invocations
WHERE invoked_at > NOW() - INTERVAL '24 hours'
GROUP BY function_name
ORDER BY avg_duration_s DESC
LIMIT 20;

-- Error analysis
SELECT error_message,
       COUNT(*) as count
FROM lambda_invocations
WHERE success=false AND invoked_at > NOW() - INTERVAL '1 hour'
GROUP BY error_message
ORDER BY count DESC;
```

## Deployment Architecture

### Kubernetes

```yaml
apiVersion: v1
kind: Service
metadata:
  name: lambda-action-module
spec:
  type: ClusterIP
  ports:
  - name: rest
    port: 8080
    targetPort: 8080
  - name: grpc
    port: 50060
    targetPort: 50060
  selector:
    app: lambda-action-module
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lambda-action-module
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lambda-action-module
  template:
    metadata:
      labels:
        app: lambda-action-module
    spec:
      containers:
      - name: lambda-action-module
        image: lambda_action_module:1.0.0
        ports:
        - name: rest
          containerPort: 8080
        - name: grpc
          containerPort: 50060
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: access-key-id
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database
              key: url
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Docker Compose

```yaml
version: '3.8'
services:
  lambda_action_module:
    build: .
    ports:
    - "8080:8080"
    - "50060:50060"
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      DATABASE_URL: postgres://waddlebot:password@postgres:5432/waddlebot
    depends_on:
      postgres:
        condition: service_healthy
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: password
      POSTGRES_DB: waddlebot
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U waddlebot"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## Next Steps

- See [CONFIGURATION.md](CONFIGURATION.md) for environment variables
- See [API.md](API.md) for endpoint details
- See [TESTING.md](TESTING.md) for test strategy
