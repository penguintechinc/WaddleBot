# Router Module Architecture

## Overview

The Router Module is Waddles's central command routing and event processing system. It receives events from action modules (Discord, Slack, Twitch, YouTube), determines the appropriate interaction module to handle each command, manages rate limiting and caching, and coordinates responses back to users.

**Version:** 2.0.0
**Framework:** Quart (async Flask)
**Language:** Python 3.13

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Component Overview](#component-overview)
3. [Request Flow](#request-flow)
4. [Service Layer](#service-layer)
5. [Data Flow](#data-flow)
6. [Caching Strategy](#caching-strategy)
7. [Integration Patterns](#integration-patterns)
8. [Scalability & Performance](#scalability--performance)
9. [Design Patterns](#design-patterns)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Waddles Ecosystem                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │  Discord   │  │   Slack    │  │   Twitch   │  │ YouTube  │ │
│  │  Action    │  │   Action   │  │   Action   │  │  Action  │ │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────┬─────┘ │
│        │               │               │              │         │
│        └───────────────┴───────────────┴──────────────┘         │
│                           │                                      │
│                           ▼                                      │
│               ┌───────────────────────┐                         │
│               │   ROUTER MODULE       │                         │
│               │   (Central Hub)       │                         │
│               └───────────┬───────────┘                         │
│                           │                                      │
│        ┌──────────────────┼──────────────────┐                 │
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐             │
│  │ Economy  │      │  Games   │      │  Polls   │             │
│  │ Module   │      │  Module  │      │  Module  │             │
│  └──────────┘      └──────────┘      └──────────┘             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Core Services                                 │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  Hub    │ Reputation │ Workflow │ Browser Source │ Identity││
│  └──────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Infrastructure                                │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  PostgreSQL  │  Redis  │  gRPC Mesh  │  Redis Streams  │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Router Module Internal Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Router Module                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Presentation Layer (Quart)                    │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │ │
│  │  │ Router        │  │ Admin         │  │ Health       │  │ │
│  │  │ Controller    │  │ Controller    │  │ Endpoints    │  │ │
│  │  └───────┬───────┘  └───────┬───────┘  └──────┬───────┘  │ │
│  │          │                  │                  │           │ │
│  │          └──────────────────┴──────────────────┘           │ │
│  └───────────────────────────────┬───────────────────────────┘ │
│                                  │                              │
│  ┌───────────────────────────────▼───────────────────────────┐ │
│  │              Service Layer                                 │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │  ┌──────────────────┐  ┌──────────────────┐               │ │
│  │  │ Command          │  │ Translation      │               │ │
│  │  │ Processor        │  │ Service          │               │ │
│  │  └────────┬─────────┘  └────────┬─────────┘               │ │
│  │           │                     │                          │ │
│  │  ┌────────▼────────┐  ┌─────────▼────────┐               │ │
│  │  │ Command         │  │ Translation      │               │ │
│  │  │ Registry        │  │ Preprocessor     │               │ │
│  │  └─────────────────┘  └──────────────────┘               │ │
│  │                                                            │ │
│  │  ┌──────────────────┐  ┌──────────────────┐              │ │
│  │  │ Rate Limiter     │  │ Cache Manager    │              │ │
│  │  └──────────────────┘  └──────────────────┘              │ │
│  │                                                            │ │
│  │  ┌──────────────────┐  ┌──────────────────┐              │ │
│  │  │ Session Manager  │  │ gRPC Client      │              │ │
│  │  └──────────────────┘  │ Manager          │              │ │
│  │                        └──────────────────┘              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                  │                              │
│  ┌───────────────────────────────▼───────────────────────────┐ │
│  │              Data Layer                                    │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │ │
│  │  │ PostgreSQL   │  │ Redis Cache  │  │ Redis Streams   │ │ │
│  │  │ (DAL)        │  │              │  │ (Optional)      │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Overview

### Presentation Layer

#### Controllers

| Controller | Route Prefix | Purpose |
|------------|-------------|---------|
| `router_bp` | `/api/v1/router` | Main routing endpoints |
| `admin_bp` | `/api/v1/admin` | Administrative endpoints |
| `health_bp` | `/` | Health checks and metrics |

**File Locations:**
- `controllers/router.py` - Main router controller
- `controllers/admin.py` - Admin controller
- `app.py` - Health/metrics blueprints

### Service Layer

#### CommandProcessor

**File:** `services/command_processor.py`

Central orchestrator for event processing.

**Responsibilities:**
- Process incoming events (messages, commands, interactions)
- Route commands to appropriate modules
- Handle responses from modules
- Coordinate with other services (Hub, Reputation, Workflow, Browser Source)
- Manage translation pipeline
- Trigger workflows

**Key Methods:**
```python
async def process_event(event_data: Dict) -> Dict
async def execute_command(command: str, ...) -> Dict
async def _translate_message(event_data: Dict, entity_id: str) -> Optional[Dict]
async def _record_message_activity(event_data: Dict)
async def _record_reputation_event(event_data: Dict)
async def _check_and_trigger_workflows(...)
async def handle_module_response(response_data: Dict)
async def get_response(session_id: str) -> Optional[Dict]
```

**Dependencies:**
- `CommandRegistry` - Command lookup
- `CacheManager` - Caching
- `RateLimiter` - Rate limiting
- `SessionManager` - Session management
- `TranslationService` - Message translation
- `GrpcClientManager` - gRPC communication

#### CommandRegistry

**File:** `services/command_registry.py`

Dynamic command registration and routing system.

**Responsibilities:**
- Load commands from database
- Cache command definitions
- Manage community-specific and global commands
- Handle command registration/updates
- Enable/disable commands

**Data Structure:**
```python
@dataclass
class CommandInfo:
    command: str                    # e.g., "!help"
    module_name: str                # e.g., "core_commands"
    module_url: str                 # e.g., "http://core-commands:8000"
    description: str
    usage: str
    category: str                   # e.g., "fun", "moderation"
    permission_level: str           # "everyone", "member", "moderator", "admin", "owner"
    is_enabled: bool
    cooldown_seconds: int
    community_id: Optional[int]     # None = global command
```

**Key Methods:**
```python
async def get_command(command: str, community_id: Optional[int]) -> Optional[CommandInfo]
async def list_commands(...) -> List[Dict]
async def register_command(...) -> bool
async def update_command(...) -> bool
async def unregister_command(...) -> bool
async def enable_command(...) -> bool
async def disable_command(...) -> bool
async def reload_commands()
```

#### TranslationService

**File:** `services/translation_service.py`

Multi-level caching translation service with provider fallback.

**Responsibilities:**
- Translate messages with 3-tier caching (memory, Redis, database)
- Preserve tokens (@mentions, !commands, emotes, URLs)
- Manage provider fallback chain
- Handle skip conditions (too short, already in target language)
- Send captions to browser source overlay

**Caching Layers:**
1. **Memory:** LRU cache (1000 entries, 1 hour TTL)
2. **Redis:** 24 hour TTL
3. **Database:** Persistent with access tracking

**Provider Chain:**
1. Google Cloud Translation API (if configured)
2. GoogleTrans (free, always available)
3. WaddleAI (fallback)

**Key Methods:**
```python
async def translate(
    text: str,
    target_lang: str,
    community_id: int,
    config: Dict,
    platform: str = "unknown",
    channel_id: Optional[str] = None
) -> Optional[Dict]
```

#### TranslationPreprocessor

**File:** `services/translation_preprocessor.py`

Token preservation system for translations.

**Preserved Patterns:**
- `@mentions` - User mentions
- `!commands` - Bot commands
- `emails` - Email addresses
- `URLs` - Web links
- `emotes` - Platform-specific emotes (Twitch/BTTV/FFZ/7TV, Discord, Slack)

**Process:**
1. Detect tokens in source text
2. Replace with placeholders (`__TOKEN_0__`, `__TOKEN_1__`, etc.)
3. Translate preprocessed text
4. Restore original tokens in translated text

**AI Decision Service:**
For uncertain patterns, can optionally use AI to decide if a token should be preserved.

#### EmoteService

**File:** `services/emote_service.py`

Platform emote lookup and caching.

**Supported Platforms:**
- Twitch (native + BTTV + FFZ + 7TV)
- Discord (guild emojis)
- Slack (workspace emojis)

**Caching:**
- Global emotes: 30 days TTL
- Channel-specific emotes: 1 day TTL

#### RateLimiter

**File:** `services/rate_limiter.py`

Distributed Redis-backed rate limiting.

**Features:**
- Sliding window algorithm
- Distributed across multiple router instances
- Configurable limits and windows
- Automatic fallback to in-memory if Redis unavailable

**Usage:**
```python
# Check rate limit (60 requests per 60 seconds)
allowed = await rate_limiter.check_rate_limit(
    key=f"{user_id}:{command}",
    limit=60,
    window=60
)
```

#### CacheManager

**File:** `services/cache_manager.py`

Redis caching wrapper.

**Methods:**
```python
async def get(key: str) -> Optional[str]
async def set(key: str, value: str, ttl: int = 300)
async def delete(key: str)
```

#### SessionManager

**File:** `services/session_manager.py`

Session ID generation and management.

**Session ID Format:** `sess_{32-char-hex}`

**Methods:**
```python
async def create_session(entity_id: str, user_id: str) -> str
async def get_session(session_id: str) -> Dict
async def delete_session(session_id: str)
```

#### GrpcClientManager

**File:** `services/grpc_clients.py`

Centralized gRPC connection management.

**Features:**
- Connection pooling
- Automatic retry with exponential backoff
- JWT token generation
- Keepalive configuration
- Health checking

**Supported Modules:**
- Action modules: Discord, Slack, Twitch, YouTube, Lambda, GCP Functions, OpenWhisk
- Core modules: Hub, Reputation, Workflow, Browser Source, Identity

**Key Methods:**
```python
async def get_channel(module_name: str) -> grpc.aio.Channel
async def call_with_retry(method, request, ...) -> Any
async def check_health(module_name: str) -> bool
def generate_token(payload: Optional[Dict]) -> str
```

---

## Request Flow

### Event Processing Flow

```
1. Event Received
   ↓
2. Validate Request (Pydantic)
   ↓
3. Generate Session ID
   ↓
4. Check Message Type
   ├─ chatMessage → Parse command
   ├─ slashCommand → Convert to !command
   ├─ interaction → Route to module
   └─ stream_event → Record activity
   ↓
5. Rate Limit Check
   ↓
6. Translation (if enabled)
   ├─ Detect language
   ├─ Preprocess (preserve tokens)
   ├─ Translate
   ├─ Postprocess (restore tokens)
   └─ Send caption to overlay
   ↓
7. Command Lookup (CommandRegistry)
   ↓
8. Module Enabled Check
   ↓
9. Command Cooldown Check
   ↓
10. Execute Command
    ├─ HTTP Request to module
    └─ gRPC Call to module (if enabled)
    ↓
11. Store Response (Redis cache)
    ↓
12. Activity Tracking (Hub module)
    ├─ Message activity (leaderboards)
    └─ Stream events (subs, follows, raids)
    ↓
13. Reputation Tracking (Reputation module)
    ↓
14. Workflow Triggers (Workflow module)
    ├─ Check for matching triggers
    └─ Execute workflows
    ↓
15. Return Response to Caller
```

### Command Execution Flow

```
CommandProcessor.execute_command()
  ↓
Get community ID
  ↓
Look up command in CommandRegistry
  ↓
Check module enabled
  ↓
Check command enabled
  ↓
Check cooldown
  ↓
Parse arguments
  ↓
Build payload
  ↓
Call module via HTTP/gRPC
  ├─ HTTP: POST /api/v1/execute
  └─ gRPC: ExecuteCommand RPC
  ↓
Retry on failure (exponential backoff)
  ↓
Store response in cache
  ↓
Return result
```

### Translation Flow

```
CommandProcessor._translate_message()
  ↓
Get translation config
  ↓
Check skip conditions
  ├─ Translation disabled?
  ├─ Message too short?
  └─ Already in target language?
  ↓
Initialize TranslationService
  ↓
Preprocess message
  ├─ Detect @mentions, !commands, emails, URLs
  ├─ Detect platform emotes (EmoteService)
  ├─ Replace with placeholders
  └─ AI decision for uncertain tokens (optional)
  ↓
Check cache (3-tier)
  ├─ Memory cache (LRU, 1 hour)
  ├─ Redis cache (24 hours)
  └─ Database cache (persistent)
  ↓
Translate (if cache miss)
  ├─ Try Google Cloud API
  ├─ Try GoogleTrans (free)
  └─ Try WaddleAI (fallback)
  ↓
Postprocess
  ├─ Restore original tokens
  └─ Replace placeholders
  ↓
Store in cache (all 3 tiers)
  ↓
Send caption to Browser Source
  ├─ gRPC: SendCaption RPC
  └─ HTTP fallback: POST /api/v1/internal/captions
  ↓
Return translation result
```

---

## Service Layer

### Service Dependencies

```
CommandProcessor
  ├─ DAL (database access)
  ├─ CacheManager (Redis)
  ├─ RateLimiter (Redis)
  ├─ SessionManager
  ├─ CommandRegistry
  │   ├─ DAL
  │   └─ CacheManager
  ├─ TranslationService
  │   ├─ DAL
  │   ├─ CacheManager
  │   ├─ EmoteService
  │   │   ├─ DAL
  │   │   └─ CacheManager
  │   ├─ TranslationPreprocessor
  │   │   ├─ EmoteService
  │   │   └─ AIDecisionService (optional)
  │   └─ Translation Providers
  │       ├─ GoogleCloudProvider
  │       ├─ GoogleTransProvider
  │       └─ WaddleAIProvider
  └─ GrpcClientManager
```

### Initialization Order

```python
# app.py - startup sequence

1. Initialize DAL (database)
   ↓
2. Create CacheManager (Redis)
   ↓
3. Create RateLimiter (Redis)
   ↓
4. Create SessionManager
   ↓
5. Create CommandRegistry
   └─ Load commands from database
   ↓
6. Create CommandProcessor
   └─ Initialize TranslationService (lazy)
   └─ Initialize gRPC manager (if enabled)
   ↓
7. Initialize StreamPipeline (if enabled)
   ↓
8. Start stream consumers (background tasks)
```

---

## Data Flow

### Database Schema (Key Tables)

#### commands
```sql
CREATE TABLE commands (
  id SERIAL PRIMARY KEY,
  command VARCHAR(255) NOT NULL,
  module_name VARCHAR(255) NOT NULL,
  description TEXT,
  usage TEXT,
  category VARCHAR(100) DEFAULT 'general',
  permission_level VARCHAR(50) DEFAULT 'everyone',
  is_enabled BOOLEAN DEFAULT TRUE,
  is_active BOOLEAN DEFAULT TRUE,
  cooldown_seconds INTEGER DEFAULT 0,
  community_id INTEGER REFERENCES communities(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_commands_lookup ON commands(command, community_id, is_active);
```

#### translation_cache
```sql
CREATE TABLE translation_cache (
  source_text_hash VARCHAR(64) PRIMARY KEY,
  source_lang VARCHAR(10) NOT NULL,
  target_lang VARCHAR(10) NOT NULL,
  translated_text TEXT NOT NULL,
  provider VARCHAR(50) NOT NULL,
  confidence_score FLOAT DEFAULT 0.0,
  created_at TIMESTAMP DEFAULT NOW(),
  access_count INTEGER DEFAULT 1,
  last_accessed TIMESTAMP DEFAULT NOW(),
  UNIQUE(source_text_hash, source_lang, target_lang)
);

CREATE INDEX idx_translation_cache_langs ON translation_cache(source_lang, target_lang);
CREATE INDEX idx_translation_cache_access ON translation_cache(last_accessed, access_count);
```

#### community_servers
```sql
CREATE TABLE community_servers (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL REFERENCES communities(id),
  platform VARCHAR(50) NOT NULL,
  platform_server_id VARCHAR(255) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_community_servers_lookup ON community_servers(platform_server_id, is_active);
```

### Redis Key Patterns

| Pattern | Purpose | TTL |
|---------|---------|-----|
| `waddlebot:session:{session_id}` | Session data | 3600s |
| `entity:community:{entity_id}` | Entity → Community mapping | 600s |
| `module_enabled:{community_id}:{module_name}` | Module status | 300s |
| `cooldown:{user_id}:{command}` | Command cooldown | Variable |
| `translation:{cache_key}` | Translation cache | 86400s |
| `emotes:global:{platform}:{provider}` | Global emotes | 2592000s |
| `emotes:channel:{platform}:{channel_id}` | Channel emotes | 86400s |
| `response:{session_id}` | Module response | 3600s |

### gRPC Message Flow

```
Router → Hub (RecordMessage)
  ↓
Router → Reputation (RecordEvent)
  ↓
Router → Workflow (TriggerWorkflow)
  ↓
Router → Browser Source (SendCaption)
```

---

## Caching Strategy

### Multi-Tier Caching

```
Request
  ↓
Check Memory Cache (LRU)
  ├─ HIT → Return
  └─ MISS
      ↓
  Check Redis Cache
      ├─ HIT → Promote to Memory → Return
      └─ MISS
          ↓
      Check Database Cache
          ├─ HIT → Promote to Redis & Memory → Return
          └─ MISS
              ↓
          Query/Compute
              ↓
          Store in All Caches
              ↓
          Return
```

### Cache Invalidation

**Time-Based:**
- Memory cache: 1 hour TTL (LRU eviction)
- Redis cache: Variable TTL (5 min to 30 days)
- Database cache: Persistent (manual cleanup)

**Event-Based:**
- Command updates → Clear command cache
- Module status change → Clear module_enabled cache
- Community settings change → Clear entity cache

---

## Integration Patterns

### HTTP Integration

**Pattern:** REST API calls with retry

```python
async def _call_module_with_retry(module_url: str, payload: Dict) -> Optional[Dict]:
    for attempt in range(max_retries):
        try:
            async with session.post(
                f"{module_url}/api/v1/execute",
                json=payload,
                headers={'X-Service-Key': SERVICE_API_KEY},
                timeout=timeout
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
```

### gRPC Integration

**Pattern:** gRPC with automatic REST fallback

```python
async def _record_message_activity(event_data: Dict):
    # Try gRPC first
    if grpc_manager and GRPC_ENABLED:
        try:
            channel = await grpc_manager.get_channel('hub_internal')
            stub = HubInternalServiceStub(channel)
            request = RecordMessageRequest(...)
            await grpc_manager.call_with_retry(stub.RecordMessage, request)
            return
        except Exception as e:
            logger.warning(f"gRPC failed, falling back to REST: {e}")

    # Fallback to REST
    await session.post(f"{HUB_API_URL}/api/v1/internal/activity/message", ...)
```

### Redis Streams Integration

**Pattern:** Consumer group with DLQ

```python
async def _stream_consumer_worker(pipeline, consumer_group, consumer_name):
    while True:
        # Consume events from inbound stream
        events = await pipeline.consume_events(
            'events:inbound',
            consumer_group,
            consumer_name
        )

        for event in events:
            try:
                # Process event
                await process_event(event['data'])

                # Acknowledge success
                await pipeline.acknowledge_event(
                    'events:inbound',
                    consumer_group,
                    event['id']
                )
            except Exception as e:
                # Move to DLQ if max retries exceeded
                if event.get('retry_count', 0) >= max_retries:
                    await pipeline.move_to_dlq(
                        'events:inbound',
                        event['id'],
                        str(e),
                        event_data=event['data']
                    )
                    await pipeline.acknowledge_event(...)
```

---

## Scalability & Performance

### Horizontal Scaling

**Router instances can be scaled independently:**

```yaml
# Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: router-module
spec:
  replicas: 5  # Scale to 5 instances
  selector:
    matchLabels:
      app: router-module
  template:
    spec:
      containers:
      - name: router
        image: waddlebot/router:latest
        env:
        - name: ROUTER_MAX_WORKERS
          value: "20"
        - name: ROUTER_MAX_CONCURRENT
          value: "100"
```

**Benefits:**
- Redis-backed rate limiting (shared state)
- Redis caching (shared cache)
- Stateless design (no local state)
- Database connection pooling per instance

### Performance Optimizations

#### 1. Connection Pooling

```python
# Database connection pool
dal = init_database(
    Config.DATABASE_URL,
    pool_size=Config.ROUTER_MAX_WORKERS,  # 20 connections
    read_replica_uri=Config.READ_REPLICA_URL
)
```

#### 2. Async Processing

```python
# Fire-and-forget activity tracking
asyncio.create_task(self._record_message_activity(event_data))
asyncio.create_task(self._record_reputation_event(event_data))
```

#### 3. Batch Processing

```python
# Process up to 100 events concurrently
results = await asyncio.gather(*[
    processor.process_event(e) for e in events_list
])
```

#### 4. Read Replicas

```python
# Query read replica for non-critical reads
result = dal.executesql(
    query,
    params,
    use_replica=True  # Route to read replica
)
```

### Performance Metrics

| Operation | Typical Latency | Max Throughput |
|-----------|----------------|----------------|
| Event processing (cached) | 5-10ms | 10,000 req/s |
| Event processing (uncached) | 50-100ms | 2,000 req/s |
| Command execution | 100-500ms | 1,000 req/s |
| Translation (cached) | 5ms | 20,000 req/s |
| Translation (uncached) | 200-500ms | 500 req/s |
| gRPC call | 10-50ms | 5,000 req/s |

---

## Design Patterns

### 1. Facade Pattern

`CommandProcessor` acts as a facade, simplifying interactions with multiple services.

### 2. Strategy Pattern

Translation providers implement `TranslationProvider` interface, allowing runtime selection.

### 3. Chain of Responsibility

Provider fallback chain: Google Cloud → GoogleTrans → WaddleAI

### 4. Repository Pattern

`CommandRegistry` abstracts command storage and retrieval.

### 5. Circuit Breaker Pattern

gRPC calls with automatic REST fallback on repeated failures.

### 6. Observer Pattern

Event-driven activity tracking (Hub, Reputation, Workflow notifications).

### 7. Factory Pattern

`get_grpc_manager()` singleton factory for gRPC client creation.

### 8. Decorator Pattern

`@validate_json` decorator for request validation.

---

## Error Handling

### Error Propagation

```
Controller (HTTP 200/400/500)
  ↓
Service (success/error dict)
  ↓
External Module (HTTP/gRPC status)
```

### Graceful Degradation

```python
# Translation failure → Skip translation
if not translation_result:
    return None  # Continue without translation

# gRPC failure → Fallback to REST
except grpc.aio.AioRpcError:
    await rest_call()

# Redis failure → Continue without cache
except redis.exceptions.ConnectionError:
    return None  # Skip cache, query database
```

---

## Testing Strategy

### Unit Tests

- Test each service in isolation
- Mock external dependencies (database, Redis, HTTP, gRPC)
- Test error handling and edge cases

### Integration Tests

- Test controller → service → database flow
- Test gRPC communication
- Test Redis caching

### End-to-End Tests

- Test complete event processing flow
- Test translation pipeline
- Test workflow triggers

**Test File:** `test_validation.py` - Pydantic model validation tests

---

## See Also

- [API.md](./API.md) - API endpoints and request/response formats
- [CONFIGURATION.md](./CONFIGURATION.md) - Configuration options
- [USAGE.md](./USAGE.md) - Usage examples and workflows
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues and solutions
