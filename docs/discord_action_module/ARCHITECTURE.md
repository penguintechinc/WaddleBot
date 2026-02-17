# Discord Action Module - Architecture

## System Overview

The Discord Action Module is a stateless, horizontally scalable microservice built with Python 3.13 that processes Discord action tasks from the WaddleBot router and executes them via the Discord Bot API.

## Component Architecture

### 1. REST API Server (Quart)

The Quart ASGI server provides REST endpoints on port 8070:

- Handles HTTP requests from third-party integrations
- JWT token generation and validation
- Request routing to Discord Service
- Error handling and response formatting
- Logging of all requests

Key endpoints:
- /health - Health check
- /api/v1/token - JWT token generation
- /api/v1/message - Message operations
- /api/v1/role - Role management
- /api/v1/moderation/* - Moderation actions
- /api/v1/webhook/* - Webhook operations

### 2. gRPC Server

The gRPC server on port 50051 handles task processing from the router:

- Receives DiscordActionRequest messages
- Processes tasks asynchronously
- Returns DiscordActionResponse with results
- Bidirectional streaming support for batch operations

Protocol Buffers define the message format:
- DiscordActionRequest
- DiscordActionResponse
- DiscordAction enum (MESSAGE, REACTION, ROLE, MODERATION)

### 3. Discord Service

Core business logic for Discord API interactions:

```python
class DiscordService:
    - _get_session() - HTTP session management
    - _check_rate_limit() - Rate limiting enforcement
    - _log_action() - Activity logging
    - send_message() - Send text messages
    - send_embed() - Send rich embeds
    - add_reaction() - Add emoji reactions
    - manage_role() - Add/remove roles
    - kick_user() - Kick users
    - ban_user() - Ban users
    - timeout_user() - Timeout users
    - create_webhook() - Create webhooks
    - send_webhook() - Send via webhooks
    - delete_message() - Delete messages
    - edit_message() - Edit messages
```

All methods are async and use aiohttp for HTTP requests to Discord API.

### 4. gRPC Handler

Implements the DiscordActionServicer from protobuf:

```python
class DiscordActionServicer(discord_action_pb2_grpc.DiscordActionServicer):
    - ExecuteAction(request, context) - Execute single action
    - BatchExecuteActions(request_iterator, context) - Batch operations
```

Bridges between gRPC messages and Discord Service methods.

### 5. Configuration Management

The Config class centralizes environment configuration:

- Discord API settings (token, API version, base URL)
- Database connection (PyDAL)
- Server settings (ports, host)
- Security settings (JWT secret, algorithm, expiration)
- Performance tuning (concurrent requests, timeouts)
- Logging configuration
- Rate limit settings

Supports:
- Environment variable loading
- Database credential loading (from platform_integrations table)
- Credential refresh via Redis Pub/Sub
- Validation with error/warning reporting

### 6. Database Layer

PyDAL (Python Data Abstraction Layer) handles database operations:

**Tables:**
- discord_actions: Audit log of all operations
  - action_type: MESSAGE, REACTION, ROLE, etc.
  - guild_id, channel_id, user_id: Discord IDs
  - success: Boolean result
  - error_message: Error details
  - request_data: JSON of request
  - response_data: JSON of Discord response
  - created_at: Timestamp

Connection pooling with 10 connections for performance.

### 7. Authentication & Authorization

JWT-based token authentication:

```
1. Client calls /api/v1/token with credentials
2. Token endpoint validates client_id and client_secret
3. Creates JWT with payload: {client_id, exp, iat}
4. Returns token with expiration time
5. Client uses token in Authorization: Bearer header
6. require_auth decorator validates token on each request
7. Token verified with MODULE_SECRET_KEY
8. Expired tokens rejected with 401 Unauthorized
```

## Request Flow

### REST API Request Flow

```
1. Client Request (REST)
   |
   ├─> Quart Router
   |   |
   |   ├─> @require_auth decorator
   |   |   └─> JWT validation
   |   |
   |   ├─> Request parsing
   |   |   └─> Parameter validation
   |   |
   |   └─> Discord Service method call
   |       |
   |       ├─> _check_rate_limit()
   |       ├─> _get_session()
   |       ├─> aiohttp.ClientSession.post()
   |       │   └─> Discord API
   |       ├─> Parse response
   |       ├─> _log_action() to database
   |       └─> Return result
   |
   └─> Response (JSON or error)
```

### gRPC Request Flow

```
1. Router sends DiscordActionRequest (gRPC)
   |
   ├─> gRPC Server receives request
   |   |
   |   ├─> DiscordActionServicer.ExecuteAction()
   |   |
   |   ├─> Route to correct Discord Service method
   |   |   based on action_type enum
   |   |
   |   └─> Same flow as REST internally
   |
   └─> Return DiscordActionResponse (gRPC)
       with success status and details
```

## Concurrency Model

**Async I/O Architecture:**

- All external I/O is async (Discord API, database, network)
- Quart provides ASGI async runtime
- gRPC server runs in thread pool executor
- aiohttp ClientSession for HTTP requests
- PyDAL handles connection pooling

**Threading Model:**

- Main thread: Quart event loop
- gRPC thread pool: Configurable workers (default: 10)
- Credential listener: Background daemon thread (optional)

**Rate Limiting:**

- Async lock (_rate_limit_lock) protects rate limit state
- Per-endpoint tracking with reset times
- Exponential backoff on rate limit errors

## Error Handling

**Retry Logic:**

- MAX_RETRIES: 3 attempts (configurable)
- RETRY_DELAY: 1.0 second initial delay
- Exponential backoff: delay * (attempt + 1)

**Specific Error Handling:**

- Discord API errors: Log and return with details
- Rate limit errors: Wait and retry
- Database errors: Log and return error
- Network errors: Retry with backoff
- Invalid token: Return 401 Unauthorized
- Validation errors: Return 400 Bad Request

## Scaling Considerations

**Stateless Design:**

- No local state or memory
- All state in database or Discord API
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
```

**Database Considerations:**

- Connection pool per instance (10 connections default)
- Shared PostgreSQL database
- discord_actions table for audit trail
- platform_integrations for credentials

**Rate Limiting at Scale:**

- In-memory rate limit tracking per instance
- May need Redis for global rate limiting across instances
- Discord API enforces its own rate limits globally

## Security Architecture

**Credential Management:**

```
┌─────────────────────────────────────┐
│  Credential Storage Options         │
├─────────────────────────────────────┤
│                                     │
│  Option 1: Environment Variables    │
│  DISCORD_BOT_TOKEN=xxxx             │
│                                     │
│  Option 2: Database                 │
│  platform_integrations table        │
│  Loaded on startup                  │
│                                     │
│  Option 3: Redis Pub/Sub             │
│  credentials:discord:bot:refreshed  │
│  Dynamic updates without restart    │
│                                     │
└─────────────────────────────────────┘
```

**JWT Security:**

- Token signed with MODULE_SECRET_KEY
- HS256 algorithm
- Expiration enforcement
- Created/updated timestamps

**TLS/SSL:**

- gRPC server supports TLS (via environment config)
- REST API should be behind reverse proxy with TLS
- Database connections use SSL if specified in DATABASE_URL

## Dependencies

**Runtime:**

- Python 3.13
- Quart: Async ASGI web framework
- gRPC: Distributed messaging
- PyDAL: Database abstraction
- aiohttp: Async HTTP client
- pyjwt: JWT tokens
- hypercorn: ASGI server
- google-auth: (Optional) GCP credentials

**External:**

- PostgreSQL 12+ database
- Discord Bot API (v10)
- Network connectivity for Discord

## Deployment Models

### Docker Compose (Development)

```yaml
discord_action_module:
  build: .
  environment: ...
  ports:
    - "50051:50051"
    - "8070:8070"
  depends_on:
    - postgres
```

### Kubernetes (Production)

```yaml
kind: Deployment
apiVersion: apps/v1
metadata:
  name: discord-action-module
spec:
  replicas: 3
  selector:
    matchLabels:
      app: discord-action-module
  template:
    metadata:
      labels:
        app: discord-action-module
    spec:
      containers:
      - name: discord-action-module
        image: waddlebot/discord-action-module:latest
        ports:
        - containerPort: 50051
          name: grpc
        - containerPort: 8070
          name: rest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: discord-secrets
              key: database_url
        - name: DISCORD_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: discord-secrets
              key: bot_token
        livenessProbe:
          httpGet:
            path: /health
            port: 8070
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8070
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Performance Metrics

**Expected Performance:**

- Message send latency: 100-500ms (Discord API dependent)
- Embed send latency: 150-600ms
- Role management latency: 200-800ms
- Moderation actions: 300-1000ms
- Throughput: 50-100 concurrent requests per instance

**Scaling Limits:**

- Discord API rate limits: 50 requests/second globally
- Database: Connection pool (10 per instance)
- Per-instance: 100 concurrent requests
- gRPC workers: 10 threads (configurable)

**Monitoring Points:**

- HTTP request latency
- Discord API response time
- Database query time
- Rate limit hits
- Error rates
- Active connections
- Token validation time

See MONITORING.md for detailed metrics setup.
