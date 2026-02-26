# Clip Interaction Module - Architecture Guide

Design patterns, data flow, service interactions, and system architecture for the Clip Interaction Module.

## System Architecture

### Layered Architecture

The module follows a classic layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│           HTTP Request Layer                    │
│  (Quart routing, request/response handling)    │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│         Middleware Layer                        │
│  (Authentication, validation, CORS, logging)   │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│         Service Layer                           │
│  (Business logic, data transformation)         │
│  - ClipService                                 │
│  - TwitchClipService                           │
└──────────┬──────────────────────────┬───────────┘
           │                          │
    ┌──────▼──────┐            ┌──────▼──────┐
    │  PyDAL ORM  │            │ Redis Cache │
    └──────┬──────┘            └──────┬──────┘
           │                          │
    ┌──────▼──────────────────────────▼──────┐
│         Persistence Layer                   │
│  (PostgreSQL, Redis clients)               │
└────────────────────────────────────────────┘
```

## Service Layer Design

### ClipService

Primary business logic for clip management. All CRUD operations on clips and reels.

```python
class ClipService:
    """Manages clip bookmarks, highlights, and reels"""

    async def bookmark_clip(
        community_id: UUID,
        clip_id: str,
        clip_url: str,
        title: str,
        game: Optional[str],
        tags: List[str],
        user_id: UUID
    ) -> ClipBookmark:
        """Create a new bookmark or raise conflict if exists"""

    async def get_clips(
        community_id: UUID,
        filters: ClipFilters,
        limit: int,
        offset: int
    ) -> Tuple[List[ClipBookmark], int]:
        """Query clips with filtering and pagination"""

    async def update_tags(
        community_id: UUID,
        clip_id: UUID,
        tags: List[str]
    ) -> ClipBookmark:
        """Update clip tags atomically"""

    async def mark_highlight(
        community_id: UUID,
        clip_id: UUID
    ) -> ClipBookmark:
        """Flag clip for reel inclusion"""

    async def create_reel(
        community_id: UUID,
        name: str,
        description: Optional[str],
        clip_ids: List[UUID],
        user_id: UUID
    ) -> HighlightReel:
        """Create highlight reel (validates all clips exist)"""

    async def get_reel(
        community_id: UUID,
        reel_id: UUID
    ) -> HighlightReel:
        """Retrieve reel with populated clip data"""

    async def publish_reel(
        community_id: UUID,
        reel_id: UUID
    ) -> HighlightReel:
        """Mark reel as published"""

    async def get_overlay_data(
        community_id: UUID
    ) -> OverlayData:
        """Get 5 latest highlights for OBS"""
```

### TwitchClipService

HTTP proxy layer for clip creation via action-twitch module.

```python
class TwitchClipService:
    """Proxies clip creation to action-twitch"""

    async def create_clip(
        broadcast_id: str,
        title: str,
        language: Optional[str],
        has_delay: bool
    ) -> dict:
        """HTTP POST to action-twitch, returns clip metadata"""
```

## Data Flow Diagrams

### Creating a Clip

```
User Request (POST /api/v1/clips/{cid}/create)
    │
    ├─> Auth Middleware
    │    └─> Validate JWT token
    │
    ├─> Route Handler
    │    └─> Validate request body
    │
    ├─> TwitchClipService.create_clip()
    │    └─> HTTP POST to action-twitch:8010/clips
    │        └─> Twitch API creates clip
    │
    ├─> Log event
    │    └─> Send "clip.created" to Router
    │
    └─> Response (201 Created)
```

### Bookmarking a Clip

```
User Request (POST /api/v1/clips/{cid}/bookmark)
    │
    ├─> Auth Middleware
    │    └─> Validate JWT token
    │
    ├─> Route Handler
    │    ├─> Validate request body
    │    └─> Validate community exists (via Core API)
    │
    ├─> ClipService.bookmark_clip()
    │    ├─> Check for duplicate (community_id + clip_id)
    │    ├─> Insert into clip_bookmarks table
    │    └─> Invalidate cache
    │
    ├─> Log event
    │    └─> Send "clip.bookmarked" to Router
    │
    └─> Response (201 Created)
```

### Creating a Highlight Reel

```
User Request (POST /api/v1/reels/{cid})
    │
    ├─> Auth Middleware
    │    └─> Validate JWT token
    │
    ├─> Route Handler
    │    ├─> Validate request body
    │    └─> Validate community exists
    │
    ├─> ClipService.create_reel()
    │    ├─> Verify all clip_ids exist in community
    │    ├─> Check reel count < MAX_REELS_PER_COMMUNITY
    │    ├─> Check clip count < MAX_CLIPS_PER_REEL
    │    ├─> Insert into clip_highlight_reels table
    │    └─> Cache reel metadata
    │
    ├─> Log event
    │    └─> Send "reel.created" to Router
    │
    └─> Response (201 Created)
```

### OBS Overlay Query

```
OBS Browser Source (GET /api/v1/overlay/{cid})
    │
    ├─> Check Redis cache
    │    ├─> HIT: Return cached data + 304
    │    └─> MISS: Continue
    │
    ├─> Auth Middleware
    │    └─> Validate JWT token
    │
    ├─> Route Handler
    │    └─> Validate community exists
    │
    ├─> ClipService.get_overlay_data()
    │    ├─> Query latest 5 is_highlight=true clips
    │    ├─> Order by created_at DESC
    │    └─> Return minimal payload
    │
    ├─> Cache result (TTL: 300s)
    │
    └─> Response (200 OK)
```

## Database Schema Design

### clip_bookmarks Table

```sql
CREATE TABLE clip_bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES communities(id),
    clip_id VARCHAR(255) NOT NULL,
    clip_url VARCHAR(2048) NOT NULL,
    title VARCHAR(500) NOT NULL,
    game VARCHAR(255),
    tags JSONB DEFAULT '[]'::jsonb,
    bookmarked_by UUID NOT NULL REFERENCES users(id),
    is_highlight BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(community_id, clip_id),
    INDEX idx_community_highlight (community_id, is_highlight, created_at DESC),
    INDEX idx_community_game (community_id, game),
    INDEX idx_created_at (created_at DESC)
);
```

**Indexes**:

| Name | Columns | Purpose |
|------|---------|---------|
| `pk_clip_bookmarks` | `id` | Primary key |
| `uq_community_clip` | `community_id, clip_id` | Prevent duplicates |
| `idx_community_highlight` | `community_id, is_highlight, created_at DESC` | Highlight queries, OBS overlay |
| `idx_community_game` | `community_id, game` | Game filtering |
| `idx_created_at` | `created_at DESC` | Timeline queries |

### clip_highlight_reels Table

```sql
CREATE TABLE clip_highlight_reels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES communities(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    clip_ids UUID[] NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id),
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_community (community_id),
    INDEX idx_published (community_id, is_published),
    INDEX idx_created_at (created_at DESC)
);
```

**Indexes**:

| Name | Columns | Purpose |
|------|---------|---------|
| `pk_clip_highlight_reels` | `id` | Primary key |
| `idx_community` | `community_id` | Community filtering |
| `idx_published` | `community_id, is_published` | Published reel queries |
| `idx_created_at` | `created_at DESC` | Timeline queries |

## Caching Strategy

### Cache Keys

```
clip:list:{community_id}:filter={game}:{tag}:{limit}:{offset}
  └─> List of clips (5 min TTL)

clip:overlay:{community_id}
  └─> Latest 5 highlights (5 min TTL)

reel:{reel_id}
  └─> Reel metadata (10 min TTL)

community:exists:{community_id}
  └─> Community validation (1 hour TTL)
```

### Cache Invalidation

Invalidate cache on write operations:

| Operation | Cache Keys Invalidated |
|-----------|----------------------|
| `bookmark_clip()` | `clip:list:*`, `clip:overlay:*` |
| `update_tags()` | `clip:list:*` |
| `mark_highlight()` | `clip:list:*`, `clip:overlay:*` |
| `create_reel()` | `reel:*` |
| `publish_reel()` | `reel:{reel_id}` |

## Error Handling Strategy

### Error Types and Handling

| Error | HTTP Status | Description | Retry |
|-------|-------------|-------------|-------|
| InvalidRequest | 400 | Bad parameters | No |
| Unauthorized | 401 | Missing/invalid token | No |
| Forbidden | 403 | Insufficient permissions | No |
| NotFound | 404 | Resource not found | No |
| DuplicateBookmark | 409 | Clip already bookmarked | No |
| ValidationError | 422 | Validation failed | No |
| RateLimited | 429 | Too many requests | Yes |
| InternalError | 500 | Server error | Yes |
| ServiceUnavailable | 503 | External service down | Yes |

### Resilience Patterns

**Circuit Breaker** (action-twitch)

```
CLOSED → (success) → CLOSED
       → (failure) → OPEN
OPEN  → (timeout) → HALF_OPEN
HALF_OPEN → (success) → CLOSED
         → (failure) → OPEN
```

**Retry with Exponential Backoff**

```
attempt 1: immediate
attempt 2: 2 seconds
attempt 3: 4 seconds
max retries: 3
```

**Timeout Strategy**

| Service | Timeout | Rationale |
|---------|---------|-----------|
| Core API | 10s | Validation queries |
| Router | 10s | Event publishing (async in future) |
| Twitch | 30s | Clip creation can be slow |
| PostgreSQL | 30s | Large queries |
| Redis | 5s | Cache (non-critical) |

## Request/Response Model

### Request Validation

```python
@dataclass
class BookmarkClipRequest:
    clip_id: str  # Required
    clip_url: str  # Required, must be valid URL
    title: str  # Required, 1-500 chars
    game: Optional[str]  # 0-255 chars
    tags: List[str]  # 0-20 tags, each 1-50 chars

    # Validation rules:
    # - No duplicate tags (case-insensitive)
    # - No special characters in tags (alphanumeric + hyphens)
    # - URL must be HTTPS and from twitch.tv
```

### Response Envelope

```json
{
  "data": {...},
  "error": null,
  "request_id": "uuid",
  "timestamp": "ISO8601"
}
```

## Async Architecture

### Quart Async Features

- Async route handlers
- Async database connections (via PyDAL)
- Async HTTP client (httpx)
- Async Redis client

### Concurrency Model

```
Incoming Request
    │
    ├─> Quart Worker (async)
    │    ├─> Auth check (blocking)
    │    ├─> Validate request (blocking)
    │    ├─> Database query (async, non-blocking)
    │    ├─> Cache check (async, non-blocking)
    │    └─> External service call (async, non-blocking)
    │
    └─> Response
```

**Max concurrent requests**: Configurable, default 100 (hypercorn workers × threads)

## Performance Considerations

### Query Optimization

**Avoid N+1 queries**:

```python
# BAD: N+1
clips = db(db.clip_bookmarks).select()
for clip in clips:
    reel = db(db.clip_highlight_reels).select()  # N queries!

# GOOD: Batch load
clip_ids = [c.id for c in clips]
reels = db(db.clip_highlight_reels).select(
    db.clip_highlight_reels.id.belongs(clip_ids)
)
reel_map = {r.id: r for r in reels}
```

**Index utilization**:

All list queries use indexed columns:

```
GET /api/v1/clips?game=Valorant
  └─> Uses idx_community_game

GET /api/v1/clips?highlights_only=true
  └─> Uses idx_community_highlight
```

### Memory Management

- Connection pooling (5-20 connections)
- Redis cache limits (TTL-based eviction)
- Pagination (max 100 items per request)
- Streaming responses for large datasets (future)

## Security Architecture

### Authentication & Authorization

```
User → Auth Middleware → JWT Validation → Community Check
                              │
                              └─> Is user member of community?
                                  ├─> YES: Allow
                                  └─> NO: Forbidden (403)
```

### Input Validation

All user inputs validated before database access:

- String length limits (255-2048 chars)
- UUID format validation
- URL validation (HTTPS + twitch.tv)
- Tag character restrictions
- Rate limiting (100 req/min per user)

### Data Protection

- Secrets never logged
- Sensitive headers stripped from logs
- SQL injection prevented (PyDAL parameterization)
- XSS prevention (no HTML in responses)
- CSRF token for state-changing requests (future)

## Integration Points

### Core API Integration

```python
async def validate_community(community_id: UUID, token: str) -> bool:
    """Check community exists and user has access"""
    response = await httpx_client.get(
        f"{CORE_API_URL}/api/v1/communities/{community_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.status_code == 200
```

### Router Integration

```python
async def publish_event(event_type: str, data: dict) -> None:
    """Publish event to router for distribution"""
    await httpx_client.post(
        f"{ROUTER_API_URL}/api/v1/events",
        json={"type": event_type, "payload": data},
        headers={"Authorization": f"Bearer {SERVICE_TOKEN}"}
    )
```

### Twitch Module Proxy

```python
async def create_clip_via_twitch(broadcast_id: str, title: str) -> dict:
    """Proxy clip creation to action-twitch"""
    response = await httpx_client.post(
        f"{TWITCH_MODULE_URL}/api/v1/clips",
        json={"broadcast_id": broadcast_id, "title": title},
        timeout=30.0
    )
    return response.json()
```

## Deployment Topology

### Development (Single Container)

```
Docker Container (8098)
├─> Python 3.12
├─> Quart + Hypercorn
├─> PyDAL + PostgreSQL Driver
├─> httpx (HTTP client)
└─> Redis Client (optional)
```

### Production (Kubernetes)

```
Kubernetes Namespace: waddlebot
├─> clip-interaction Deployment
│    ├─> 3 replicas
│    ├─> Liveness probe: /health
│    ├─> Readiness probe: /health?check=db
│    └─> Resource limits: 512Mi RAM, 250m CPU
│
├─> PostgreSQL StatefulSet (shared)
├─> Redis StatefulSet (shared)
└─> Service (internal)
     └─> Port 8098
```

## Monitoring & Observability

### Metrics

```
clip_interaction_http_requests_total
clip_interaction_http_request_duration_seconds
clip_interaction_db_queries_total
clip_interaction_db_query_duration_seconds
clip_interaction_cache_hits_total
clip_interaction_cache_misses_total
```

### Logs

```json
{
  "timestamp": "2026-02-24T15:30:00Z",
  "level": "INFO",
  "request_id": "req-uuid-1234",
  "user_id": "user-uuid",
  "community_id": "community-uuid",
  "action": "clip_bookmarked",
  "clip_id": "twitch-clip-123",
  "duration_ms": 42
}
```
