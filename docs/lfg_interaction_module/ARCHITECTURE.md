# LFG Interaction Module - Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Applications                          │
│                  (Discord Bots, Web Dashboards, etc)                │
└──────────────────────────────┬──────────────────────────────────────┘
                                │
                   HTTP/HTTPS (Port 8096)
                                │
┌──────────────────────────────▼──────────────────────────────────────┐
│              LFG Interaction Module (Quart/Python 3.12)              │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     HTTP Request Handler                    │   │
│  │        (ASGI application with async/await support)         │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────────┐   │
│  │                    Route Dispatcher                         │   │
│  │  /api/v1/lfg/posts        (POST, GET)                      │   │
│  │  /api/v1/lfg/posts/:id    (DELETE)                         │   │
│  │  /api/v1/lfg/posts/:id/join (POST, DELETE)                 │   │
│  │  /api/v1/lfg/expire       (POST - cron)                    │   │
│  │  /health, /metrics        (monitoring)                     │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────────┐   │
│  │              Controller Layer (Business Logic)              │   │
│  │  - Post creation/validation                                │   │
│  │  - Join/leave management                                  │   │
│  │  - Status transitions (open → filled → expired)           │   │
│  │  - Per-user post limit enforcement                        │   │
│  │  - Auto-fill detection                                    │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────────┐   │
│  │                  LfgService (Data Layer)                    │   │
│  │  - create_post()                                           │   │
│  │  - list_posts(filters)                                    │   │
│  │  - join_post(post_id, user_id)                            │   │
│  │  - leave_post(post_id, user_id)                           │   │
│  │  - cancel_post(post_id, creator_id)                       │   │
│  │  - expire_posts()                                         │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │                                                        │
│  ┌──────────┴────────────────┬────────────────┬──────────────────┐ │
│  │                           │                │                  │ │
│  ▼                           ▼                ▼                  ▼ │
│ ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│ │   Database Abstraction Layer (PyDAL) │  │ In-Memory Cache  │   │
│ │                                      │  │ (Optional Redis) │   │
│ │ lfg_posts table                     │  │                  │   │
│ │ lfg_joins table                     │  │ Session cache    │   │
│ └─────────────────┘  └──────────────────┘  │ Rate limits      │   │
└─────────────────────────────────────────────┴──────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
        ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
        │ PostgreSQL   │ │   Redis     │ │ External APIs│
        │ (lfg_posts,  │ │  (optional) │ │ (CORE, RTR) │
        │  lfg_joins)  │ │             │ │              │
        └──────────────┘ └─────────────┘ └──────────────┘
```

## Component Details

### 1. HTTP Request Handler (ASGI)
- **Framework**: Quart (async Python web framework)
- **Purpose**: Receives incoming HTTP requests, routes to appropriate handlers
- **Key Features**:
  - Full async/await support (non-blocking I/O)
  - Automatic JSON serialization/deserialization
  - Built-in error handling and status code mapping
  - Middleware support (logging, auth, CORS)

### 2. Route Dispatcher
Maps incoming HTTP requests to controller methods:

| Endpoint | Method | Controller | Handler |
|----------|--------|------------|---------|
| `/lfg/posts` | POST | LfgController | create_post() |
| `/lfg/posts/{id}` | GET | LfgController | get_post() |
| `/lfg/posts` | GET | LfgController | list_posts() |
| `/lfg/posts/{id}/join` | POST | LfgController | join_post() |
| `/lfg/posts/{id}/join` | DELETE | LfgController | leave_post() |
| `/lfg/posts/{id}` | DELETE | LfgController | cancel_post() |
| `/lfg/expire` | POST | LfgController | expire_posts() |
| `/health` | GET | HealthController | health_check() |
| `/metrics` | GET | MetricsController | prometheus_metrics() |

### 3. Controller Layer (Business Logic)

**LfgController** handles request validation and orchestrates service calls:

```
POST /lfg/posts Request
    ↓
Validate request body
    ↓
Validate platform + game values
    ↓
Call: LfgService.create_post()
    ↓
Check: Count active posts for user (< 3)
    ↓
Insert: lfg_posts record (status='open', expires_at=now+120min)
    ↓
Response: 201 Created with post details
```

**Key validations**:
- user_id and community_id exist (via Core API)
- player_count_needed > 0
- Unique constraint: post_id + user_id in lfg_joins
- Per-user limit: max 3 active posts
- Platform value in [discord, twitch, youtube, slack, kick]
- Activity value in [raid, pvp, pve, coop, casual, ranked]

### 4. LfgService (Data Layer)

Core service methods:

#### create_post(payload)
1. Validate input and check per-user limits
2. Insert new record into `lfg_posts` table
3. Return new post with status='open'

#### list_posts(community_id, filters)
1. Query `lfg_posts` WHERE community_id=? AND status IN (?, ?, ...)
2. Apply optional filters (game, activity, status)
3. Order by created_at DESC
4. Return paginated results (limit, offset)

#### join_post(post_id, user_id, platform, display_name)
1. Fetch post by ID, validate status='open'
2. Check unique constraint (post_id, user_id not in lfg_joins)
3. Insert join record into `lfg_joins` table
4. Increment `current_player_count` (in-memory, or via VIEW)
5. Check if `current_player_count >= player_count_needed`
6. If filled, update post status to 'filled'
7. Return success with updated counts

#### leave_post(post_id, user_id)
1. Fetch post by ID
2. Delete join record from `lfg_joins`
3. Recalculate current_player_count
4. If post is 'filled' and count < needed, revert to 'open'
5. Return success with updated counts

#### cancel_post(post_id, user_id)
1. Fetch post by ID, verify user_id is creator
2. Delete all join records for post_id
3. Update post status to 'cancelled'
4. Return success

#### expire_posts()
1. Query posts WHERE status IN ('open', 'filled') AND expires_at < now()
2. Update status to 'expired' for each
3. Delete all associated join records
4. Return count of expired posts

### 5. Database Layer (PyDAL)

**Tables**:

#### lfg_posts
```sql
CREATE TABLE lfg_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL,
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    game VARCHAR(255) NOT NULL,
    activity VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    rank_or_level VARCHAR(255),
    player_count_needed INT NOT NULL CHECK (player_count_needed > 0),
    message TEXT,
    platform_message_id VARCHAR(255),
    status ENUM('open', 'filled', 'expired', 'cancelled') DEFAULT 'open',
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (community_id) REFERENCES communities(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_community_status (community_id, status),
    INDEX idx_expires_at (expires_at),
    INDEX idx_created_at (created_at DESC)
);
```

#### lfg_joins
```sql
CREATE TABLE lfg_joins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL,
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    joined_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (post_id) REFERENCES lfg_posts(id) ON DELETE CASCADE,
    UNIQUE(post_id, user_id),
    INDEX idx_post_id (post_id)
);
```

**Indexes for Performance**:
- `idx_community_status`: Fast listing by community + status
- `idx_expires_at`: Efficient expiry job queries
- `idx_created_at`: Recent posts retrieval
- `UNIQUE(post_id, user_id)`: Prevents duplicate joins

### 6. Caching Strategy (Optional Redis)

**Cache Keys**:
```
lfg:posts:{community_id}:{filter_hash} → list results (TTL: 30s)
lfg:post:{post_id} → post details (TTL: 10s)
lfg:user_posts:{user_id} → user's posts (TTL: 30s)
rate_limit:{user_id}:{window} → request count
```

**Write-Through Pattern**:
- Create post → Cache invalidated
- Join post → Post cache invalidated
- Leave post → Post cache invalidated
- Expire posts → All post caches invalidated

**Benefits**:
- Reduced database load for frequent list operations
- Faster response times for read-heavy workloads
- Rate-limiting support

---

## Data Flow Examples

### Flow 1: Creating an LFG Post

```
Client Request
    ↓
POST /api/v1/lfg/posts
{
  "community_id": "...",
  "user_id": "...",
  "game": "Valorant",
  "player_count_needed": 4,
  ...
}
    ↓
LfgController.create_post()
    - Validate input
    - Check user's active post count
    - Call LfgService.create_post()
    ↓
LfgService.create_post()
    - Insert into lfg_posts (status='open')
    - expires_at = now + 120 minutes
    - Invalidate community posts cache
    ↓
Database Write
    - PostgreSQL INSERT returns new post ID
    ↓
Controller
    - Fetch created post details
    - Return 201 Created response
    ↓
Client Response
{
  "status": "success",
  "data": {
    "id": "post-uuid",
    "status": "open",
    "current_player_count": 1,
    "player_count_needed": 4,
    "expires_at": "2026-02-24T12:00:00Z"
  }
}
```

### Flow 2: Joining a Post (Auto-Fill Detection)

```
Client Request
    ↓
POST /api/v1/lfg/posts/{post_id}/join
{
  "user_id": "...",
  "platform": "discord",
  "display_name": "User#1234"
}
    ↓
LfgController.join_post()
    - Fetch post from cache/DB
    - Validate post status == 'open'
    - Call LfgService.join_post()
    ↓
LfgService.join_post()
    - Check unique constraint (post_id, user_id)
    - Insert into lfg_joins
    - Query current join count
    ↓
Database Operations
    - INSERT lfg_joins (new participant)
    - SELECT COUNT(*) FROM lfg_joins WHERE post_id=?
    ↓
Auto-Fill Detection
    IF count >= player_count_needed THEN
        - UPDATE lfg_posts SET status='filled'
        - Invalidate post cache
    END IF
    ↓
Controller
    - Return 200 OK with updated post details
    - status: 'filled' (if applicable)
    ↓
Client Response
{
  "status": "success",
  "data": {
    "post_id": "...",
    "current_player_count": 4,
    "player_count_needed": 4,
    "status": "filled",  ← Auto-filled
    "joined_at": "..."
  }
}
```

### Flow 3: Leaving a Post (Revert from Filled to Open)

```
Client Request
    ↓
DELETE /api/v1/lfg/posts/{post_id}/join
{
  "user_id": "..."
}
    ↓
LfgController.leave_post()
    - Fetch post from cache/DB
    - Call LfgService.leave_post()
    ↓
LfgService.leave_post()
    - Delete from lfg_joins (user_id, post_id)
    - Query current join count
    ↓
Database Operations
    - DELETE lfg_joins WHERE post_id=? AND user_id=?
    - SELECT COUNT(*) FROM lfg_joins WHERE post_id=?
    ↓
Status Revert Check
    IF post.status == 'filled' AND count < player_count_needed THEN
        - UPDATE lfg_posts SET status='open'
        - Invalidate post cache
    END IF
    ↓
Controller
    - Return 200 OK with updated post details
    - status: 'open' (if applicable)
    ↓
Client Response
{
  "status": "success",
  "data": {
    "post_id": "...",
    "current_player_count": 3,
    "player_count_needed": 4,
    "status": "open",  ← Reverted
    "left_at": "..."
  }
}
```

### Flow 4: Background Expiry Job

```
Scheduled Cron Event (Hourly)
    ↓
POST /api/v1/lfg/expire
{
  "cron_token": "internal-secret"
}
    ↓
LfgController.expire_posts()
    - Validate cron_token
    - Call LfgService.expire_posts()
    ↓
LfgService.expire_posts()
    - Query posts WHERE expires_at < NOW()
    - AND status IN ('open', 'filled')
    ↓
Database Cleanup
    - FOR each post_id:
        - DELETE FROM lfg_joins WHERE post_id=?
        - UPDATE lfg_posts SET status='expired'
    ↓
Cache Invalidation
    - Invalidate all affected post caches
    ↓
Controller
    - Return 200 OK with expiry count
    ↓
Response
{
  "status": "success",
  "data": {
    "expired_count": 24,
    "timestamp": "2026-02-24T11:00:00Z"
  }
}
```

---

## Concurrency & Safety

### Database Constraints
1. **Primary Keys**: All tables use UUID PKs (collision-free)
2. **Unique Constraints**: `UNIQUE(post_id, user_id)` on lfg_joins prevents duplicate joins
3. **Foreign Keys**: lfg_joins.post_id references lfg_posts (with CASCADE DELETE)
4. **Check Constraints**: player_count_needed > 0

### Optimistic Locking
- Current player count is derived (SELECT COUNT) not cached
- Reduces race conditions on fill detection
- Small performance cost acceptable for correctness

### Transaction Isolation
- Quart/PyDAL use PostgreSQL's default isolation level (READ COMMITTED)
- Most operations are single-row (safe under RC)
- Expiry job may use SERIALIZABLE for consistency

---

## Scalability Considerations

### Horizontal Scaling
- Stateless design: all instances can handle any request
- Shared PostgreSQL backend (read replicas optional for list queries)
- Redis cluster for distributed caching
- Load balancer (HAProxy, ALB, etc.)

### Vertical Scaling
- Connection pooling: increase DB_POOL_MAX
- Worker count: increase WORKER_COUNT
- Memory: in-memory caching if Redis unavailable

### Query Optimization
- Indexes on community_id, status, expires_at
- Pagination limits to 200 results
- Cache list endpoints (30s TTL)

### Monitoring
- Prometheus metrics endpoint
- Query performance tracking
- Cache hit rate monitoring
- Active connection monitoring

---

## Error Handling

### Request Validation Errors (400)
```python
if not payload.get('game'):
    return error_response("VALIDATION_ERROR", "game field required", 400)
```

### Authorization Errors (401)
```python
try:
    verify_token(auth_header)
except InvalidToken:
    return error_response("UNAUTHORIZED", "Invalid token", 401)
```

### Not Found Errors (404)
```python
post = db.query(LfgPost).filter_by(id=post_id).first()
if not post:
    return error_response("POST_NOT_FOUND", "Post not found", 404)
```

### Conflict Errors (409)
```python
if post.status != 'open':
    return error_response("POST_NOT_OPEN", "Post is not open", 409)

if user_already_joined:
    return error_response("ALREADY_JOINED", "User already joined", 409)
```

### Server Errors (500)
```python
try:
    db.insert(lfg_post)
except DatabaseError as e:
    logger.error(f"DB error: {e}")
    return error_response("DATABASE_ERROR", "Internal error", 500)
```

---

## Testing Architecture

### Unit Tests
- Test individual service methods in isolation
- Mock PostgreSQL/Redis
- Test data validation and transformations

### Integration Tests
- Real PostgreSQL container
- Real Redis container
- Full request/response cycle

### E2E Tests
- Full Docker Compose setup
- Simulated client workflows
- Performance benchmarking

---

## Deployment Diagram

```
Client Apps (Discord Bot, Web, etc.)
    │
    ├── HTTPS Load Balancer (ALB/HAProxy)
    │   │
    │   ├── LFG Instance 1 (Pod)
    │   ├── LFG Instance 2 (Pod)
    │   └── LFG Instance 3 (Pod)
    │       │
    │       └── PostgreSQL Primary (Read/Write)
    │           │
    │           └── PostgreSQL Replicas (Read-Only)
    │
    │   All instances share:
    │   ├── Redis Cluster (cache, rate-limiting)
    │   ├── Core API (auth, validation)
    │   └── Router API (routing)
```

---

## Performance Characteristics

| Operation | Complexity | Typical Time |
|-----------|-----------|---|
| Create post | O(1) | 10ms |
| List posts (no filter) | O(log n) | 5ms |
| List posts (with game filter) | O(log n) | 8ms |
| Join post | O(1) | 15ms |
| Leave post | O(1) | 12ms |
| Cancel post | O(m) where m = join count | 20-100ms |
| Expire posts (1000 stale posts) | O(n log n) | 500-1000ms |

*Assumes PostgreSQL indices present and Redis cache enabled*
