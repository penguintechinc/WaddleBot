# Identity Core Module - Architecture Documentation

## Overview

The Identity Core Module is a dual-protocol microservice that provides unified cross-platform identity management for Waddles. It bridges multiple streaming and social platforms (Twitch, Discord, YouTube, etc.) to a unified hub user system, supporting both REST and gRPC interfaces.

**Version:** 2.0.0
**Framework:** Quart (async Python) + gRPC
**Database:** PostgreSQL
**Language:** Python 3.13

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Identity Core Module                      │
│                         (v2.0.0)                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────┐         ┌──────────────────────┐    │
│  │   REST API Layer   │         │   gRPC Server Layer  │    │
│  │   (Quart/Hypercorn)│         │   (grpc.aio)         │    │
│  │   Port: 8050       │         │   Port: 50030        │    │
│  └─────────┬──────────┘         └──────────┬───────────┘    │
│            │                                │                │
│            └────────────┬───────────────────┘                │
│                         │                                    │
│            ┌────────────▼────────────┐                      │
│            │   Service Layer         │                      │
│            │  - Identity Linking     │                      │
│            │  - User Authentication  │                      │
│            │  - Platform Management  │                      │
│            └────────────┬────────────┘                      │
│                         │                                    │
│            ┌────────────▼────────────┐                      │
│            │   Data Access Layer     │                      │
│            │   (flask_core DAL)      │                      │
│            └────────────┬────────────┘                      │
└─────────────────────────┼────────────────────────────────────┘
                          │
                 ┌────────▼─────────┐
                 │   PostgreSQL     │
                 │   Database       │
                 └──────────────────┘
```

---

## Component Architecture

### 1. Application Layer (app.py)

**Responsibility:** Application initialization, server lifecycle, and routing

**Key Components:**

#### Quart Application
```python
app = Quart(__name__)
```
- Async web framework (Flask-compatible)
- Handles HTTP/REST requests
- Manages blueprints and middleware

#### Blueprint Registration
```python
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
app.register_blueprint(api_bp)
```

#### Lifecycle Hooks

**Startup:**
```python
@app.before_serving
async def startup():
    # Initialize database
    dal = init_database(Config.DATABASE_URL)

    # Start gRPC server
    grpc_server = aio.server()
    servicer = IdentityServiceServicer(dal=dal, logger=logger)
    asyncio.create_task(_start_grpc_server(grpc_server, logger))
```

**Shutdown:**
```python
@app.before_server_shutdown
async def shutdown():
    if grpc_server:
        await grpc_server.stop(0)
```

---

### 2. Configuration Layer (config.py)

**Responsibility:** Centralized configuration management

```python
class Config:
    MODULE_NAME = 'identity_core_module'
    MODULE_VERSION = '2.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8050'))
    GRPC_PORT = int(os.getenv('GRPC_PORT', '50030'))
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://...')
    CORE_API_URL = os.getenv('CORE_API_URL', 'http://router-service:8000')
    ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://router-service:8000/api/v1/router')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
```

**Features:**
- Environment variable loading (python-dotenv)
- Type conversion (int, bool)
- Default value fallbacks
- Validation on import

---

### 3. Service Layer (services/)

#### gRPC Handler (services/grpc_handler.py)

**Responsibility:** gRPC service implementation and identity operations

**Class Hierarchy:**
```
IdentityServiceServicer
├── verify_token()           # JWT authentication
├── LookupIdentity()         # Platform → Hub user lookup
└── GetLinkedPlatforms()     # Hub user → Platforms lookup
```

**Data Classes:**
```python
@dataclass
class PlatformIdentity:
    platform: str
    platform_user_id: str
    platform_username: str

@dataclass
class LookupIdentityRequest:
    token: str
    platform: Optional[str]
    platform_user_id: Optional[str]

@dataclass
class LookupIdentityResponse:
    success: bool
    hub_user_id: Optional[int]
    username: Optional[str]
    linked_platforms: List[PlatformIdentity]
    error: Optional[str]
```

**Service Methods:**

1. **LookupIdentity**
   - Input: Token, platform, platform_user_id
   - Process: Token verification → Database query
   - Output: Hub user info + linked platforms

2. **GetLinkedPlatforms**
   - Input: Token, hub_user_id
   - Process: Token verification → Platform list query
   - Output: List of linked platform identities

**Error Handling:**
```python
try:
    # Verify token
    if not await self.verify_token(request.token):
        return LookupIdentityResponse(
            success=False,
            error="Invalid authentication token"
        )

    # Perform lookup
    # ...

except Exception as e:
    logger.error(f"Error in LookupIdentity: {str(e)}")
    return LookupIdentityResponse(
        success=False,
        error=f"Internal server error: {str(e)}"
    )
```

---

### 4. Data Access Layer (flask_core)

**Source:** Shared library at `/home/penguin/code/Waddles/libs/flask_core`

**Responsibility:** Database abstraction and ORM

**Initialization:**
```python
from flask_core import init_database

dal = init_database(Config.DATABASE_URL)
```

**Features:**
- Connection pooling
- Query builder
- Transaction management
- Database migrations support

**Usage Pattern:**
```python
# Query users
user = dal.hub_users.get(id=user_id)

# Query identities
identities = dal.hub_user_identities.where(
    hub_user_id=user_id
).select()

# Insert new identity
dal.hub_user_identities.insert(
    hub_user_id=user_id,
    platform='twitch',
    platform_user_id='123456'
)

# Update identity
dal.hub_user_identities.update(
    {'last_used': datetime.now()},
    id=identity_id
)
```

---

## Identity Linking Flow

### Cross-Platform Identity Association

```
┌──────────────┐
│ User on      │
│ Platform A   │
│ (Twitch)     │
└──────┬───────┘
       │
       │ 1. Initiate Link
       ▼
┌──────────────────────┐
│ POST /identity/link  │
│ - platform: twitch   │
│ - platform_id: 123   │
│ - username: user     │
└──────┬───────────────┘
       │
       │ 2. Generate Verification Code
       ▼
┌────────────────────────┐
│ Database:              │
│ - Create verification  │
│ - Set expiry (1 hour)  │
│ - Return code          │
└──────┬─────────────────┘
       │
       │ 3. User Receives Code
       ▼
┌──────────────────────────┐
│ Verification Code:       │
│ ABCD-1234                │
│ Expires: 2025-12-16 11:00│
└──────┬───────────────────┘
       │
       │ 4. User Verifies
       ▼
┌────────────────────────────┐
│ POST /identity/verify      │
│ - verification_code: ABCD  │
│ - platform: twitch         │
└──────┬─────────────────────┘
       │
       │ 5. Link Identity
       ▼
┌─────────────────────────────┐
│ hub_user_identities         │
│ - hub_user_id: 42           │
│ - platform: twitch          │
│ - platform_user_id: 123     │
│ - linked_at: NOW()          │
└─────────────────────────────┘
```

### Multi-Platform User Graph

```
         ┌─────────────────────────┐
         │  Hub User (ID: 42)      │
         │  Email: user@email.com  │
         │  Username: waddle_user  │
         └───────────┬─────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Twitch   │  │ Discord  │  │ YouTube  │
│ ID: 123  │  │ ID: 789  │  │ ID: 456  │
│ streamer │  │ user#123 │  │ channel  │
└──────────┘  └──────────┘  └──────────┘
```

---

## OAuth Flow Architecture

### OAuth State Management

```
┌──────────────┐
│ User clicks  │
│ "Login with  │
│  Twitch"     │
└──────┬───────┘
       │
       │ 1. Generate OAuth State
       ▼
┌─────────────────────────────┐
│ hub_oauth_states            │
│ - state: random_uuid        │
│ - platform: twitch          │
│ - mode: login               │
│ - expires_at: +15 minutes   │
└──────┬──────────────────────┘
       │
       │ 2. Redirect to Platform
       ▼
┌────────────────────────────────┐
│ https://id.twitch.tv/oauth2/   │
│ authorize?                     │
│   client_id=...                │
│   redirect_uri=...             │
│   state=random_uuid            │
│   scope=user:read:email        │
└──────┬─────────────────────────┘
       │
       │ 3. User Authorizes
       ▼
┌────────────────────────────────┐
│ Platform Callback:             │
│ /oauth/callback/twitch?        │
│   code=auth_code               │
│   state=random_uuid            │
└──────┬─────────────────────────┘
       │
       │ 4. Verify State (CSRF Protection)
       ▼
┌────────────────────────────────┐
│ Validate:                      │
│ - State exists in database     │
│ - State not expired            │
│ - State matches platform       │
└──────┬─────────────────────────┘
       │
       │ 5. Exchange Code for Token
       ▼
┌────────────────────────────────┐
│ POST to Platform Token API     │
│ Receive:                       │
│ - access_token                 │
│ - refresh_token                │
│ - expires_in                   │
└──────┬─────────────────────────┘
       │
       │ 6. Fetch User Info
       ▼
┌────────────────────────────────┐
│ GET /user (with access_token)  │
│ Receive:                       │
│ - platform_user_id             │
│ - username                     │
│ - email                        │
│ - avatar                       │
└──────┬─────────────────────────┘
       │
       │ 7. Link or Create Identity
       ▼
┌────────────────────────────────┐
│ hub_user_identities            │
│ - Insert/Update identity       │
│ - Store tokens                 │
│ - Set expiration               │
└────────────────────────────────┘
```

---

## gRPC Architecture

### Proto Definition

**File:** `/home/penguin/code/Waddles/libs/grpc_protos/identity.proto`

```protobuf
syntax = "proto3";
package waddlebot.identity;
import "common.proto";

service IdentityService {
    rpc LookupIdentity(LookupIdentityRequest) returns (LookupIdentityResponse);
    rpc GetLinkedPlatforms(GetLinkedPlatformsRequest) returns (GetLinkedPlatformsResponse);
}

message LookupIdentityRequest {
    string token = 1;
    string platform = 2;
    string platform_user_id = 3;
}

message LookupIdentityResponse {
    bool success = 1;
    int32 hub_user_id = 2;
    string username = 3;
    repeated PlatformIdentity linked_platforms = 4;
    waddlebot.common.Error error = 5;
}

message PlatformIdentity {
    string platform = 1;
    string platform_user_id = 2;
    string platform_username = 3;
}
```

### gRPC Server Lifecycle

```python
# Initialization
grpc_server = aio.server()
servicer = IdentityServiceServicer(dal=dal, logger=logger)

# Server startup
grpc_server.add_insecure_port(f"0.0.0.0:{Config.GRPC_PORT}")
await grpc_server.start()
logger.system(f"gRPC server started on port {Config.GRPC_PORT}")

# Server running
await grpc_server.wait_for_termination()

# Graceful shutdown
await grpc_server.stop(grace_period=0)
```

### gRPC vs REST Decision Matrix

| Feature | gRPC | REST |
|---------|------|------|
| Speed | Fast (protobuf) | Slower (JSON) |
| Use Case | Service-to-service | Client-to-service |
| Browser Support | Limited | Full |
| Streaming | Bidirectional | HTTP/2 only |
| Schema | Strongly typed | Flexible |
| Debugging | Harder | Easier |

**When to Use gRPC:**
- High-frequency identity lookups
- Service mesh communication
- Real-time platform verification
- Low latency requirements

**When to Use REST:**
- Web UI interactions
- Public API access
- Third-party integrations
- Human-readable debugging

---

## Database Schema Architecture

### Entity Relationship Diagram

```
┌─────────────────┐
│   hub_users     │
│─────────────────│
│ id (PK)         │◄────┐
│ email           │     │
│ username        │     │
│ password_hash   │     │
│ is_active       │     │
│ created_at      │     │
└─────────────────┘     │
                        │
                        │ 1:N
                        │
        ┌───────────────┼──────────────────┐
        │               │                  │
        │               │                  │
┌───────▼──────────┐    │    ┌─────────────▼────────┐
│hub_user_identities│    │    │ hub_user_profiles    │
│──────────────────│    │    │──────────────────────│
│ id (PK)          │    │    │ id (PK)              │
│ hub_user_id (FK) │────┘    │ hub_user_id (FK)     │
│ platform         │         │ display_name         │
│ platform_user_id │         │ bio                  │
│ platform_username│         │ custom_avatar_url    │
│ access_token     │         │ visibility           │
│ refresh_token    │         │ social_links         │
│ linked_at        │         └──────────────────────┘
│ UNIQUE(platform, │
│  platform_user_id)│
└──────────────────┘

┌──────────────────┐
│ hub_oauth_states │
│──────────────────│
│ id (PK)          │
│ state (UNIQUE)   │
│ mode             │
│ platform         │
│ user_id (FK)     │
│ expires_at       │
└──────────────────┘

┌──────────────────┐
│  hub_sessions    │
│──────────────────│
│ id (PK)          │
│ hub_user_id (FK) │
│ session_token    │
│ expires_at       │
│ is_active        │
└──────────────────┘
```

### Index Strategy

**Hot Path Queries:**
```sql
-- Most frequent: Platform identity lookup
SELECT hub_user_id FROM hub_user_identities
WHERE platform = 'twitch' AND platform_user_id = '123456';

-- Index: idx_hub_user_identities_platform_lookup
CREATE INDEX ON hub_user_identities(platform, platform_user_id);

-- Session authentication
SELECT * FROM hub_sessions
WHERE session_token = 'token' AND is_active = true;

-- Index: idx_hub_sessions_token
CREATE INDEX ON hub_sessions(session_token) WHERE is_active = true;

-- User identity retrieval
SELECT * FROM hub_user_identities
WHERE hub_user_id = 42;

-- Index: idx_hub_user_identities_hub_user
CREATE INDEX ON hub_user_identities(hub_user_id);
```

---

## Security Architecture

### Authentication Flow

```
┌──────────────┐
│ API Request  │
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│ Check X-API-Key or  │
│ Authorization Header│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐      No      ┌──────────────┐
│ Token Present?      │─────────────►│ 401 Unauthorized│
└──────┬──────────────┘              └──────────────┘
       │ Yes
       ▼
┌─────────────────────┐
│ Validate Token:     │
│ - Format check      │
│ - Signature verify  │
│ - Expiry check      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐      Invalid  ┌──────────────┐
│ Token Valid?        │──────────────►│ 401 Invalid  │
└──────┬──────────────┘               └──────────────┘
       │ Valid
       ▼
┌─────────────────────┐
│ Extract user_id     │
│ Load user context   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Process Request     │
└─────────────────────┘
```

### Token Security

**JWT Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": 42,
    "username": "waddle_user",
    "exp": 1734348000,
    "iat": 1734344400,
    "iss": "identity_core_module"
  },
  "signature": "HMACSHA256(...)"
}
```

**Token Validation:**
1. Decode token
2. Verify signature using SECRET_KEY
3. Check expiration timestamp
4. Validate issuer
5. Extract user claims

### OAuth Security

**CSRF Protection:**
- Random state parameter generation
- State stored in database with expiration
- State validated on callback
- One-time use (deleted after validation)

**Token Storage:**
- Access tokens encrypted at rest
- Refresh tokens encrypted at rest
- Tokens never logged
- Token rotation on refresh

---

## Logging Architecture

### Structured Logging (AAA Format)

**From flask_core library:**

```python
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

# Authentication logs
logger.auth(
    user_id=42,
    action="login",
    platform="twitch",
    result="SUCCESS"
)

# Authorization logs
logger.authz(
    user_id=42,
    action="link_identity",
    resource="platform:twitch",
    result="ALLOWED"
)

# System logs
logger.system(
    action="startup",
    message="gRPC server started",
    port=50030
)

# Error logs
logger.error(
    message="Database connection failed",
    error=str(e),
    context={"attempt": retry_count}
)
```

**Log Output Format:**
```json
{
  "timestamp": "2025-12-16T10:30:00.123Z",
  "level": "INFO",
  "module": "identity_core_module",
  "version": "2.0.0",
  "type": "AUTH",
  "user_id": 42,
  "action": "login",
  "platform": "twitch",
  "result": "SUCCESS",
  "duration_ms": 45
}
```

---

## Deployment Architecture

### Container Architecture

```
┌─────────────────────────────────────────┐
│   Docker Container                       │
│   waddlebot/identity-core:2.0.0         │
├─────────────────────────────────────────┤
│                                          │
│   ┌──────────────────────────────────┐  │
│   │   Hypercorn (4 workers)          │  │
│   │   - Worker 1 (Quart + gRPC)      │  │
│   │   - Worker 2 (Quart + gRPC)      │  │
│   │   - Worker 3 (Quart + gRPC)      │  │
│   │   - Worker 4 (Quart + gRPC)      │  │
│   └──────────────────────────────────┘  │
│                                          │
│   Ports:                                 │
│   - 8050 (REST API)                     │
│   - 50030 (gRPC)                        │
│                                          │
│   Volumes:                               │
│   - /var/log/waddlebotlog (logs)        │
│                                          │
│   User: waddlebot (non-root)            │
└─────────────────────────────────────────┘
```

### Service Mesh Integration

```
┌───────────────┐       ┌───────────────┐
│  Web UI       │       │  Action       │
│  (REST)       │       │  Modules      │
└───────┬───────┘       │  (gRPC)       │
        │               └───────┬───────┘
        │ HTTP/JSON             │ gRPC
        │                       │
        ▼                       ▼
    ┌───────────────────────────────┐
    │    Identity Core Module       │
    │    - REST API (8050)          │
    │    - gRPC API (50030)         │
    └───────────────┬───────────────┘
                    │
                    │ PostgreSQL
                    ▼
            ┌───────────────┐
            │   Database    │
            └───────────────┘
```

---

## Performance Considerations

### Connection Pooling

**Database:**
- Pool size: 10 connections
- Max overflow: 20 connections
- Pool recycle: 3600 seconds
- Timeout: 30 seconds

**Hypercorn Workers:**
- Worker count: 4 (configurable)
- Worker class: asyncio
- Keep-alive: 5 seconds

### Caching Strategy

**Identity Lookups:**
- Cache frequently accessed identities in memory
- TTL: 5 minutes
- Invalidate on identity update/unlink

**Session Tokens:**
- Database-backed (no in-memory cache)
- Indexed for fast lookup
- Cleanup of expired sessions via cron

---

## Error Handling Architecture

### Error Propagation

```
┌──────────────┐
│ gRPC/REST    │
│ Request      │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Service Layer    │
│ try/catch block  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ DAL Layer        │
│ Database errors  │
└──────┬───────────┘
       │
       ▼
┌──────────────────────────┐
│ Structured Error Response│
│ - Error code             │
│ - Message                │
│ - Context                │
└──────────────────────────┘
```

### Error Types

| Layer | Error Type | Handling |
|-------|-----------|----------|
| Request | Validation | 400 Bad Request |
| Auth | Token invalid | 401 Unauthorized |
| Authz | Permission denied | 403 Forbidden |
| Service | Not found | 404 Not Found |
| Service | Conflict | 409 Conflict |
| Database | Connection | Retry + 503 |
| Internal | Exception | Log + 500 |

---

## Future Architecture Enhancements

### Planned Improvements

1. **Caching Layer**
   - Redis for identity cache
   - Session cache
   - Rate limiting

2. **Message Queue**
   - Async identity verification
   - Platform sync events
   - Audit log streaming

3. **Service Mesh**
   - Istio/Linkerd integration
   - mTLS between services
   - Traffic shaping

4. **Observability**
   - OpenTelemetry traces
   - Distributed tracing
   - Custom metrics

5. **High Availability**
   - Multi-region deployment
   - Database replication
   - Failover automation

---

## Architecture Decision Records

### ADR-001: Dual Protocol Support (REST + gRPC)

**Decision:** Support both REST and gRPC protocols

**Rationale:**
- REST for web UI and external integrations
- gRPC for high-performance service-to-service
- Shared business logic via service layer

### ADR-002: Async Framework (Quart)

**Decision:** Use Quart instead of Flask

**Rationale:**
- Native async/await support
- Better performance for I/O-bound operations
- Flask-compatible API
- Required for concurrent gRPC server

### ADR-003: Centralized Identity Store

**Decision:** Single source of truth in PostgreSQL

**Rationale:**
- Consistent identity across platforms
- ACID transactions for linking
- Relational model fits identity graph
- Proven scalability

### ADR-004: Token-based Authentication

**Decision:** JWT tokens for authentication

**Rationale:**
- Stateless authentication
- Easy to validate across services
- Standard format (RFC 7519)
- Contains user claims

---

## References

- [Quart Documentation](https://quart.palletsprojects.com/)
- [gRPC Python Guide](https://grpc.io/docs/languages/python/)
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/performance-tips.html)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OAuth 2.0 Security](https://datatracker.ietf.org/doc/html/rfc6749)
