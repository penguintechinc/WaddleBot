# YouTube Music Interaction Module - Architecture

## System Architecture

The YouTube Music Interaction Module is designed as a microservice following event-driven asynchronous patterns within the WaddleBot ecosystem.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Discord Communities                       │
└─────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│              WaddleBot Router Service (Port 8000)                 │
│  Routes requests to appropriate modules based on action type     │
└──────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
┌────────▼─────────┐  ┌────────▼──────────┐  ┌──────▼──────┐
│ YouTube Music    │  │ Twitch Engagement │  │ Lambda      │
│ (Port 8025)      │  │ (Port 8024)       │  │ (Port 8026) │
│                  │  │                   │  │             │
│ - OAuth 2.0      │  │                   │  │             │
│ - Token mgmt     │  │                   │  │             │
│ - Playlist API   │  │                   │  │             │
│ - Track search   │  │                   │  │             │
└────────┬─────────┘  └───────────────────┘  └─────────────┘
         │
         ├──────────────────────────────┬──────────────────┐
         │                              │                  │
┌────────▼──────────┐  ┌───────────────▼─┐  ┌─────────────▼─┐
│   PostgreSQL      │  │    Redis        │  │   YouTube    │
│   (Credentials)   │  │   (Messaging)   │  │   Music API  │
└───────────────────┘  └─────────────────┘  └──────────────┘
```

## Component Architecture

The module is organized into logical components:

### 1. Application Core (app.py)

**Responsibility**: HTTP request handling, Quart application setup, blueprint registration

**Key Functions**:
- Initialize Quart application
- Register health check blueprint
- Register API blueprint with v1 routes
- Handle startup/shutdown lifecycle
- Database connection initialization

**Flow**:
```
Request → Quart → Route Matching → Handler → Response
   ↓                                   ↓
Logging                            Validation
   ↓                                   ↓
AAA Audit                          Processing
```

### 2. Configuration Manager (config.py)

**Responsibility**: Environment configuration, credential loading, state management

**Key Classes**:
- `Config`: Main configuration class with environment variables
- Credential loading from `platform_integrations` table
- Redis listener for credential refresh notifications
- Thread-safe credential locking mechanism

**Configuration Sources** (in order):
1. Environment variables (.env file or system)
2. Fallback defaults
3. Database lookups (for credentials)

**Key Methods**:
- `Config.load_credentials_from_db()`: Loads YouTube credentials from DB
- `Config.start_credential_listener()`: Starts background Redis listener for credential updates

**State Management**:
```
┌─────────────────────────────────────────┐
│ Configuration Manager (config.py)        │
│                                          │
│ ┌──────────────────────────────────┐   │
│ │ Environment Variables             │   │
│ │ ├─ MODULE_PORT: 8025             │   │
│ │ ├─ DATABASE_URL                  │   │
│ │ ├─ REDIS_URL (optional)          │   │
│ │ └─ OAuth credentials             │   │
│ └──────────────────────────────────┘   │
│              │                          │
│              ▼                          │
│ ┌──────────────────────────────────┐   │
│ │ Credential Loader                │   │
│ │ ├─ Load from DB on startup       │   │
│ │ ├─ Fall back to env vars         │   │
│ │ └─ Thread-safe caching           │   │
│ └──────────────────────────────────┘   │
│              │                          │
│              ▼                          │
│ ┌──────────────────────────────────┐   │
│ │ Redis Listener (optional)         │   │
│ │ ├─ Monitor credentials channel   │   │
│ │ ├─ Refresh on notify events      │   │
│ │ └─ Daemon thread execution       │   │
│ └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 3. Database Layer

**Responsibility**: Persistent storage of OAuth credentials and metadata

**Database Tables**:

#### platform_integrations
```sql
CREATE TABLE platform_integrations (
  id SERIAL PRIMARY KEY,
  platform VARCHAR(50) NOT NULL,        -- 'youtube'
  integration_type VARCHAR(50) NOT NULL, -- 'bot', 'user'
  community_id VARCHAR(255),
  user_id VARCHAR(255),
  client_id VARCHAR(255),
  client_secret VARCHAR(255),
  access_token TEXT,                    -- Encrypted
  refresh_token TEXT,                   -- Encrypted
  token_expires_at TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(platform, integration_type, community_id)
);
```

**Access Pattern**:
```
Config.load_credentials_from_db(db_connection)
  │
  ├─ Query: SELECT client_id, client_secret, access_token 
  │         FROM platform_integrations
  │         WHERE platform = 'youtube'
  │           AND integration_type = 'bot'
  │           AND is_active = TRUE
  │
  └─ Returns: First matching row or None
```

### 4. OAuth 2.0 Handler

**Responsibility**: Manage YouTube Music OAuth authentication flow

**Flow Diagram**:
```
User Action (e.g., "play song")
        │
        ▼
┌──────────────────────────────┐
│ Check Credentials Exist?      │
└──────────────────────────────┘
        │
    ┌───┴───┐
    │       │
   YES     NO
    │       │
    ▼       ▼
Refresh?  Redirect to
    │      OAuth Consent
    ├─────────┬────────┐
    │         │        │
VALID    INVALID    User
    │      │        Authorizes
    ▼      ▼        │
Use    Redirect    ▼
Token  to Auth   Exchange Code
    │      │      for Token
    │      │      │
    │      └──────┴────────────┐
    │                          │
    └──────────────┬───────────┘
                   │
                   ▼
        Store in Database
                   │
                   ▼
        Return Access Token
```

**Key Operations**:
1. **Authorization Code Exchange** (POST /api/v1/oauth/token)
   - Client sends authorization code
   - Module calls YouTube OAuth token endpoint
   - Receives access_token, refresh_token, expires_in
   - Stores credentials in database
   - Returns tokens to client

2. **Token Refresh** (POST /api/v1/oauth/refresh)
   - Client provides refresh_token
   - Module calls YouTube OAuth refresh endpoint
   - Receives new access_token
   - Updates database record
   - Returns new access_token

3. **Credential Validation**
   - Check token expiration
   - Verify token still valid with YouTube API
   - Automatically refresh if expired

### 5. Health Check System

**Responsibility**: Monitor service health and dependencies

**Health Check Levels**:

**Level 1: Basic Health** (GET /health)
- Application is running
- Simple response without external checks
- Status: healthy/unhealthy
- Response time: <100ms

**Level 2: Extended Health** (GET /healthz)
- Application is running
- Database connectivity verified
- Redis connectivity verified (if enabled)
- Returns granular status for each component
- Status: healthy/degraded/unhealthy

**Dependency Checks**:
```
┌──────────────────────────────────────┐
│ Health Check Endpoint (/healthz)     │
│                                      │
│ ┌────────────────────────────────┐  │
│ │ Database Connectivity Check    │  │
│ │ ├─ Execute SELECT 1            │  │
│ │ ├─ Measure response time       │  │
│ │ └─ Status: connected/failed    │  │
│ └────────────────────────────────┘  │
│                                      │
│ ┌────────────────────────────────┐  │
│ │ Redis Connectivity Check       │  │
│ │ ├─ Ping Redis server           │  │
│ │ ├─ Measure response time       │  │
│ │ └─ Status: connected/failed    │  │
│ └────────────────────────────────┘  │
│                                      │
│ ┌────────────────────────────────┐  │
│ │ Aggregate Status               │  │
│ │ ├─ All ok → healthy (200)      │  │
│ │ ├─ Some fail → degraded (503)  │  │
│ │ └─ All fail → unhealthy (503)  │  │
│ └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

## Request/Response Flow

### Complete Request Lifecycle

```
1. CLIENT REQUEST
   │
   ├─ HTTP POST /api/v1/oauth/token
   ├─ Headers: Content-Type: application/json
   └─ Body: { "code": "...", "redirect_uri": "..." }
   
2. QUART RECEIVES REQUEST
   │
   ├─ Route matching
   ├─ Validation
   └─ Logging (entry point)
   
3. HANDLER PROCESSING
   │
   ├─ Parse JSON body
   ├─ Validate parameters
   ├─ Check authentication
   └─ Load configuration
   
4. OAUTH PROCESSING
   │
   ├─ Call YouTube OAuth endpoint
   │  │
   │  └─ POST https://oauth2.googleapis.com/token
   │     ├─ client_id
   │     ├─ client_secret
   │     ├─ code
   │     ├─ grant_type
   │     └─ redirect_uri
   │
   ├─ Receive tokens
   │  └─ access_token, refresh_token, expires_in
   │
   └─ Store in database
      │
      └─ INSERT/UPDATE platform_integrations
         ├─ client_id
         ├─ client_secret
         ├─ access_token (encrypted)
         ├─ refresh_token (encrypted)
         └─ token_expires_at
   
5. RESPONSE BUILDING
   │
   ├─ Prepare response JSON
   ├─ Add timestamp
   ├─ Set HTTP status (200)
   └─ Set Content-Type: application/json
   
6. CLIENT RECEIVES RESPONSE
   │
   └─ HTTP 200 OK
      └─ Body: { "status": "success", "data": {...} }
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Discord Bot                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ User: !play youtube:tracks
                     │ 
┌────────────────────▼────────────────────────────────────┐
│                  Router Service                         │
│              (Request Dispatcher)                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Route to: youtube-music-interaction
                     │
┌────────────────────▼────────────────────────────────────┐
│       YouTube Music Interaction Module                  │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ 1. Request Handler                             │   │
│  │    └─ Parse action: "play"                     │   │
│  └────────────────────────────────────────────────┘   │
│                     │                                   │
│  ┌────────────────────────────────────────────────┐   │
│  │ 2. Check Credentials                           │   │
│  │    ├─ Query: Config.load_credentials_from_db()│   │
│  │    └─ Load: access_token, refresh_token       │   │
│  └────────────────────────────────────────────────┘   │
│                     │                                   │
│  ┌────────────────────────────────────────────────┐   │
│  │ 3. Validate Token                              │   │
│  │    ├─ Check: token_expires_at > now            │   │
│  │    ├─ If expired: Refresh                      │   │
│  │    └─ Return: valid access_token               │   │
│  └────────────────────────────────────────────────┘   │
│                     │                                   │
│  ┌────────────────────────────────────────────────┐   │
│  │ 4. Query YouTube Music API                     │   │
│  │    └─ GET /youtube/v3/search                   │   │
│  │       └─ Query: q=tracks, part=snippet         │   │
│  └────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Response: Track results
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Router Service                         │
│            (Response to Discord Bot)                    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Discord Bot                           │
│        (Display results to user)                        │
└─────────────────────────────────────────────────────────┘
```

## Threading Model

The module uses async/await for non-blocking I/O:

```
┌──────────────────────────────────────────────────────┐
│ Hypercorn Server (4 workers)                         │
│                                                      │
│ Worker 1                Worker 2    Worker 3/4      │
│ ┌────────────┐        ┌────────────┐               │
│ │ Event Loop │        │ Event Loop │ ...           │
│ │            │        │            │               │
│ │ ┌────────┐ │        │ ┌────────┐ │               │
│ │ │Task:   │ │        │ │Task:   │ │               │
│ │ │Request │ │        │ │Request │ │               │
│ │ │Handler │ │        │ │Handler │ │               │
│ │ └────────┘ │        │ └────────┘ │               │
│ │     │      │        │     │      │               │
│ │     ├─async await   │     ├─async await          │
│ │     │   DB query    │     │   YouTube API call   │
│ │     │      │        │     │      │               │
│ │     └──────┘        │     └──────┘               │
│ │ (non-blocking)      │ (non-blocking)             │
│ └────────────┘        └────────────┘               │
└──────────────────────────────────────────────────────┘
```

**Key Advantages**:
- Thousands of concurrent connections
- Non-blocking I/O operations
- Efficient resource utilization
- Can handle long-running operations (OAuth, API calls)

## Redis Integration (Optional)

When Redis is configured, the module listens for credential refresh notifications:

```
┌────────────────────────────────┐
│  OAuth Credential Management   │
│  System                        │
└────────┬───────────────────────┘
         │
         │ Credential refresh
         │ (external system)
         │
         ▼
┌────────────────────────────────┐
│ Redis Pub/Sub                  │
│                                │
│ Channel:                       │
│ credentials:youtube:bot:...    │
└────────┬───────────────────────┘
         │
         │ Publish message
         │
         ▼
┌─────────────────────────────────┐
│ YouTube Music Module            │
│                                 │
│ Background Thread:              │
│ Config.start_credential_listener│
│   │                             │
│   ├─ Listen on channel          │
│   ├─ Receive notification       │
│   ├─ Reload credentials         │
│   └─ Update Config state        │
└─────────────────────────────────┘
```

## Security Architecture

### Credential Storage

```
User OAuth Token
       │
       ▼
Encryption Layer (AES-256)
       │
       ▼
Database Storage (Encrypted)
┌────────────────────────────┐
│ platform_integrations      │
│                            │
│ access_token: [encrypted]  │
│ refresh_token: [encrypted] │
└────────────────────────────┘
       │
       ▼
Decrypt on Load
       │
       ▼
Use in API Calls (in-memory)
```

### Authentication Flow

```
Request with Authorization Header
       │
       ├─ Extract: "Bearer <token>"
       │
       ▼
Validate Token
       │
       ├─ Check signature
       ├─ Check expiration
       ├─ Check scope
       │
       ▼
Verify Permissions
       │
       ├─ Check user role
       ├─ Check community access
       │
       ▼
Allow/Deny Request
```

## Scalability Considerations

The module is designed to scale horizontally:

1. **Stateless Design**: No server-side state (except transient memory cache)
2. **Shared Database**: All instances read/write to same PostgreSQL DB
3. **Distributed Credentials**: Credentials stored centrally, refreshed via Redis
4. **Load Balancing**: Can run multiple instances behind load balancer
5. **Async I/O**: Thousands of concurrent connections per instance

---

**Last Updated**: 2026-02-16
