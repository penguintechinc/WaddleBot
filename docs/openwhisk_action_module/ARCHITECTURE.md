# OpenWhisk Action Module - Architecture

## System Architecture

The OpenWhisk Action Module is a stateless, horizontally scalable bridge between WaddleBot and Apache OpenWhisk.

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
│    ┌────────┴──────────────────────────┐                 │
│    │ Load Balancer / Service Mesh      │                 │
│    └────────┬──────────────────────────┘                 │
│             │                                             │
│  ┌──────────┴────────────────────────────────────────┐   │
│  │  OpenWhisk Action Module (Stateless Replicas)   │   │
│  │  ┌─────────────────────────────────────────────┐ │   │
│  │  │ Replica 1     Replica 2      Replica N    │ │   │
│  │  │ ┌──────────┐ ┌──────────┐  ┌───────────┐ │ │   │
│  │  │ │REST API  │ │REST API  │  │REST API   │ │ │   │
│  │  │ │(8082)    │ │(8082)    │  │(8082)     │ │ │   │
│  │  │ ├──────────┤ ├──────────┤  ├───────────┤ │ │   │
│  │  │ │gRPC      │ │gRPC      │  │gRPC       │ │ │   │
│  │  │ │(50062)   │ │(50062)   │  │(50062)    │ │ │   │
│  │  │ └────┬─────┘ └────┬─────┘  └────┬──────┘ │ │   │
│  │  └──────┼──────────────┼───────────┼────────┘ │   │
│  │         │              │           │          │   │
│  └─────────┼──────────────┼───────────┼──────────┘   │
│            │              │           │              │
│   ┌────────┴──┬───────────┴─┬────────┴┬──────┐      │
│   │           │             │        │      │       │
│ ┌─▼──────┐ ┌──▼───┐  ┌─────▼───┐ ┌──▼──┐ ┌─▼────┐ │
│ │OpenWhisk│ │  DB  │  │  Redis  │ │Logs │ │Stats │ │
│ │REST API │ │      │  │ (Cache) │ │     │ │      │ │
│ └─────────┘ └──────┘  └─────────┘ └─────┘ └──────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Core Components

### 1. REST API Server (Quart)

**Port**: 8082

**Responsibilities**:
- Handle HTTP requests
- JWT token validation
- JSON request/response serialization
- Error handling

**Key Routes**:
- `GET /health` - Health check
- `POST /api/v1/auth/token` - Token generation
- `POST /api/v1/actions/invoke` - Action invocation
- `POST /api/v1/actions/invoke-async` - Async invocation
- `POST /api/v1/sequences/invoke` - Sequence invocation
- `POST /api/v1/web-actions/invoke` - Web action invocation
- `POST /api/v1/triggers/fire` - Trigger firing
- `GET /api/v1/activations/<id>` - Activation details
- `GET /api/v1/actions` - List actions
- `GET /api/v1/stats` - Statistics

### 2. gRPC Server

**Port**: 50062

**Responsibilities**:
- Handle gRPC requests from processor/router
- Protocol buffer serialization
- Streaming support
- Connection management

**Services**:
- `OpenWhiskActionService.InvokeAction()`
- `OpenWhiskActionService.InvokeSequence()`
- `OpenWhiskActionService.FireTrigger()`
- `OpenWhiskActionService.GetActivation()`
- `OpenWhiskActionService.ListActions()`

### 3. OpenWhisk Service

**File**: `services/openwhisk_service.py`

**Responsibilities**:
- OpenWhisk REST API client
- Action invocation
- Sequence execution
- Trigger firing
- Activation retrieval

**Methods**:
- `invoke_action()` - Sync/async invocation
- `invoke_sequence()` - Sequence execution
- `invoke_web_action()` - Web action invocation
- `fire_trigger()` - Trigger firing
- `get_activation()` - Activation details
- `list_actions()` - List available actions

### 4. Authentication Service

**File**: `services/auth_service.py`

**Responsibilities**:
- JWT token generation
- Token validation
- API key verification

### 5. Configuration Management

**File**: `config.py`

**Responsibilities**:
- Load configuration from environment
- Validate settings
- Manage OpenWhisk credentials
- Support database integration

## Data Flow

### Action Invocation (Blocking)

```
1. Client REST Request
   POST /api/v1/actions/invoke
   │
2. JWT Validation
   verify_token() -> valid
   │
3. Service Call
   openwhisk_service.invoke_action(
     namespace, action_name, payload, blocking=True
   )
   │
4. OpenWhisk REST API Call
   POST /api/v1/namespaces/{ns}/actions/{name}
   │
5. OpenWhisk Execution
   (External to module)
   │
6. Response Processing
   - Extract result
   - Extract status
   - Extract logs
   │
7. Database Logging
   INSERT INTO openwhisk_action_executions
   │
8. Return Response
   {
     execution_id: "...",
     success: true,
     activation_id: "...",
     result: {...}
   }
```

### Async Invocation

```
1. Client Request
   blocking=false
   │
2. OpenWhisk REST API
   PUT /api/v1/namespaces/{ns}/triggers/{name}
   │
3. Immediate Return
   activation_id: "..."
   │
4. Action Executes Independently
   (Asynchronous in OpenWhisk)
```

## OpenWhisk Integration

### REST API Communication

The module uses aiohttp for async HTTP communication with OpenWhisk:

```python
async with aiohttp.ClientSession() as session:
    response = await session.post(
        f"{OPENWHISK_API_HOST}/api/v1/namespaces/{namespace}/actions/{action}",
        headers={
            "Authorization": f"Basic {base64(auth_key)}"
        },
        json=payload
    )
```

### Authentication

OpenWhisk uses HTTP Basic Auth with `namespace:key` format:

```python
import base64
auth_header = base64.b64encode(
    f"{namespace}:{key}".encode()
).decode()
# Result: "Basic <base64-encoded>"
```

### API Endpoints

OpenWhisk REST API endpoints:

```
GET    /api/v1/namespaces               # List namespaces
POST   /api/v1/namespaces/{ns}/actions  # Invoke action
GET    /api/v1/namespaces/{ns}/actions  # List actions
GET    /api/v1/namespaces/{ns}/activations/{id} # Get activation
POST   /api/v1/namespaces/{ns}/triggers/{name} # Fire trigger
GET    /api/v1/namespaces/{ns}/packages # List packages
```

## Invocation Types

### Blocking Invocation

- Client waits for completion
- Maximum timeout: 5-10 minutes (configurable)
- Returns full result and logs
- Suitable for: Request-response workflows

### Non-Blocking Invocation

- Action queued immediately
- Returns activation ID
- Result available via activation query
- Suitable for: Long-running actions, notifications

### Web Action

- Invokes web-enabled action
- HTTP context available to action
- Can return HTTP response
- Useful for: APIs, webhooks

## Credential Management

### Credential Sources (Priority Order)

```
1. Environment Variables (Highest)
   OPENWHISK_API_HOST
   OPENWHISK_AUTH_KEY
   OPENWHISK_NAMESPACE
   ↓ (if not set)

2. Database platform_integrations
   WHERE platform='openwhisk'
   ↓ (if not found)

3. Redis Credential Listener
   Channel: credentials:openwhisk:bot:refreshed
```

### Credential Refresh

```
External Service → Updates DB → Redis publish
                                   ↓
                         Module listener thread
                                   ↓
                         Reloads credentials
```

## Error Handling

```
OpenWhisk Request
       │
    ┌──┴──┐
    │     │
Success  Error
    │       │
   ✓     └──┬──────────┐
    │       │          │
    │   ┌───┴─────┐    │
    │   │ Log Error│    │
    │   └───┬─────┘    │
    │       │          │
    │   ┌───▼────────────────┐
    │   │ Database Insert    │
    │   │ (failure record)   │
    │   └────────────────────┘
    │       │
    └───┬───┘
        │
    Response
```

## Database Schema

### openwhisk_action_executions

```sql
CREATE TABLE openwhisk_action_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    namespace VARCHAR(255) NOT NULL,
    action_name VARCHAR(255) NOT NULL,
    action_type VARCHAR(50),  -- action, sequence, web_action, trigger
    payload TEXT,
    blocking BOOLEAN,
    timeout INTEGER,
    activation_id VARCHAR(255),
    result TEXT,
    duration_ms INTEGER,
    status VARCHAR(50),        -- success, failure, timeout
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

## Scaling Considerations

### Horizontal Scaling

Module is fully stateless:
- No in-memory state
- No session affinity
- No shared state between replicas

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openwhisk-action-module
spec:
  replicas: 5  # Scale to N replicas
  template:
    spec:
      containers:
      - name: openwhisk-action-module
        ports:
        - containerPort: 8082  # REST
        - containerPort: 50062 # gRPC
```

### Worker Pool Configuration

```env
MAX_WORKERS=20          # Concurrent workers (default)
REQUEST_TIMEOUT=30      # Request timeout (default)
```

Total capacity = `replicas × MAX_WORKERS`

## Security Architecture

### Authentication Flow

```
Client Request
     ↓
Check Authorization Header
     ↓
Extract JWT Token
     ↓
Verify Token (secret key)
     ↓
Extract Payload
     ↓ (valid)
Process Request
     ↓ (invalid)
401 Unauthorized
```

### Credential Protection

- OpenWhisk API key never logged
- JWT secret never transmitted
- Credentials not in error messages
- Database logs don't expose secrets

### Network Security

- REST API: HTTP (TLS in production)
- OpenWhisk: HTTPS always
- gRPC: Insecure (TLS in production)

## Monitoring & Observability

### Key Metrics

```
- Action invocation success rate
- Average invocation latency
- Error distribution
- Database query performance
- gRPC connection count
- JWT token generation rate
```

### Database Queries for Monitoring

```sql
-- Success rate (last hour)
SELECT COUNT(*) FILTER (WHERE success=true) as successes,
       COUNT(*) as total,
       ROUND(100.0 * COUNT(*) FILTER (WHERE success=true) / 
             COUNT(*), 2) as success_rate
FROM openwhisk_action_executions
WHERE created_at > NOW() - INTERVAL '1 hour';

-- Slowest actions (last 24h)
SELECT action_name,
       COUNT(*) as invocations,
       ROUND(AVG(duration_ms), 0) as avg_duration_ms,
       MAX(duration_ms) as max_duration_ms
FROM openwhisk_action_executions
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY action_name
ORDER BY avg_duration_ms DESC
LIMIT 20;

-- Error analysis
SELECT error,
       COUNT(*) as count
FROM openwhisk_action_executions
WHERE success=false 
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY error
ORDER BY count DESC;
```

## Kubernetes Deployment

```yaml
apiVersion: v1
kind: Service
metadata:
  name: openwhisk-action-module
spec:
  type: ClusterIP
  ports:
  - name: rest
    port: 8082
    targetPort: 8082
  - name: grpc
    port: 50062
    targetPort: 50062
  selector:
    app: openwhisk-action-module
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openwhisk-action-module
spec:
  replicas: 3
  selector:
    matchLabels:
      app: openwhisk-action-module
  template:
    metadata:
      labels:
        app: openwhisk-action-module
    spec:
      containers:
      - name: openwhisk-action-module
        image: openwhisk_action_module:1.0.0
        ports:
        - name: rest
          containerPort: 8082
        - name: grpc
          containerPort: 50062
        env:
        - name: OPENWHISK_API_HOST
          valueFrom:
            secretKeyRef:
              name: openwhisk
              key: api-host
        - name: OPENWHISK_AUTH_KEY
          valueFrom:
            secretKeyRef:
              name: openwhisk
              key: auth-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database
              key: url
        livenessProbe:
          httpGet:
            path: /health
            port: 8082
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8082
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Docker Compose

```yaml
version: '3.8'
services:
  openwhisk_action_module:
    build: .
    ports:
    - "8082:8082"
    - "50062:50062"
    environment:
      OPENWHISK_API_HOST: ${OPENWHISK_API_HOST}
      OPENWHISK_AUTH_KEY: ${OPENWHISK_AUTH_KEY}
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

See also:
- [CONFIGURATION.md](CONFIGURATION.md)
- [API.md](API.md)
- [TESTING.md](TESTING.md)
