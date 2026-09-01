# Redis Architecture & Namespace Strategy

## Overview

Waddles uses Redis for multiple purposes with proper separation via namespacing, database selection, and access patterns.

## Redis Use Cases

### 1. Caching (`CacheManager`)
- **Namespace**: `waddlebot:cache:{module_name}:`
- **Redis DB**: 0 (default)
- **TTL**: Variable (30s - 7200s depending on data type)
- **Access Pattern**: High read, moderate write
- **Eviction**: allkeys-lru (configured)

**Examples:**
- `waddlebot:cache:twitch_receiver:channels:all`
- `waddlebot:cache:ai_interaction:response:twitch:chatMessage:hello`
- `waddlebot:cache:loyalty:leaderboard:123:10`

### 2. Rate Limiting (`RateLimiter`)
- **Namespace**: `waddlebot:rate_limit:{module_name}:`
- **Redis DB**: 1
- **Data Structure**: Sorted Sets (ZSET) for sliding window
- **TTL**: Equal to window duration
- **Access Pattern**: High read/write, short-lived keys

**Examples:**
- `waddlebot:rate_limit:router:user_123:!help`
- `waddlebot:rate_limit:router:cooldown:user_456:!dice`

### 3. Message Queue (`MessageQueue`)
- **Namespace**: `waddlebot:stream:{stream_name}` and `waddlebot:dlq:{stream_name}`
- **Redis DB**: 2
- **Data Structure**: Redis Streams (XADD/XREADGROUP)
- **Persistence**: AOF (append-only file) enabled
- **Access Pattern**: Sequential write, consumer group reads

**Examples:**
- `waddlebot:stream:events` - Main event stream
- `waddlebot:dlq:events` - Dead letter queue

### 4. Session Management
- **Namespace**: `waddlebot:session:{module_name}:`
- **Redis DB**: 0 (shares with cache)
- **TTL**: 3600s (1 hour)
- **Access Pattern**: Moderate read/write

**Examples:**
- `waddlebot:session:router:sess_abc123`

## Redis Database Separation

```yaml
# Database allocation
DB 0: Caching & Sessions
  - General application cache
  - Session storage
  - Ephemeral data
  - Eviction: allkeys-lru

DB 1: Rate Limiting
  - Rate limit counters (sorted sets)
  - Cooldown tracking
  - Short TTLs
  - Eviction: volatile-ttl

DB 2: Message Queues
  - Redis Streams
  - Dead letter queues
  - Persistent data
  - Eviction: noeviction (prevent data loss)

DB 3-15: Reserved for future use
```

## Environment Configuration

### Recommended Redis URLs by Module

**Router Module:**
```bash
# Caching
REDIS_URL=redis://:password@redis:6379/0

# Rate limiting (uses DB 1 internally via namespace)
RATE_LIMIT_REDIS_URL=redis://:password@redis:6379/1

# Message queue (uses DB 2 internally)
MESSAGE_QUEUE_REDIS_URL=redis://:password@redis:6379/2
```

**Receiver Modules (Twitch, Discord, etc.):**
```bash
# Caching only
REDIS_URL=redis://:password@redis:6379/0
```

**Action Modules (AI, Calendar, Loyalty):**
```bash
# Caching only
REDIS_URL=redis://:password@redis:6379/0
```

## Redis Configuration

### docker-compose.yml (local dev only — production is Helm-only)

The actual service (`infra-redis`) runs Valkey, not Redis, config-driven rather than inline flags:

```yaml
infra-redis:
  image: valkey/valkey:8-bookworm@sha256:...
  volumes:
    - redis-data:/data
    - ./config/redis/redis.conf:/etc/redis/redis.conf:ro
    - ./config/redis/users.acl:/etc/redis/users.acl.template:ro
  # config/redis/redis.conf sets: appendonly yes, maxmemory 512mb,
  # maxmemory-policy allkeys-lru — per-service passwords/ACLs come from
  # REDIS_<SERVICE>_PASSWORD env vars templated into users.acl at startup
```

### Redis ACL (Advanced - Optional)

For production with Redis ACL support:

```redis
# Cache user - read/write to DB 0
ACL SETUSER cache_user on >cache_password ~waddlebot:cache:* ~waddlebot:session:* +@read +@write +@string +@hash +@set -@dangerous

# Rate limiter user - read/write to DB 1 sorted sets
ACL SETUSER ratelimit_user on >ratelimit_password ~waddlebot:rate_limit:* +@read +@write +@sortedset -@dangerous

# Queue user - read/write to DB 2 streams
ACL SETUSER queue_user on >queue_password ~waddlebot:stream:* ~waddlebot:dlq:* +@read +@write +@stream -@dangerous

# Admin user - full access
ACL SETUSER admin on >admin_password ~* +@all
```

## Namespace Strategy Benefits

### 1. Isolation
- Different modules don't conflict with same key names
- Easy to identify which module owns which data
- Clear separation of concerns

### 2. Monitoring
- Pattern-based monitoring: `INFO keyspace` shows keys per namespace
- Easy to track memory usage per module
- Debug specific module caching issues

### 3. Cleanup
- Delete all keys for a module: `SCAN 0 MATCH waddlebot:cache:twitch_receiver:*`
- Flush specific use case without affecting others
- Maintenance operations are safer

### 4. Scaling
- Can migrate specific namespaces to separate Redis instances
- Shard by namespace for horizontal scaling
- Different eviction policies per database

## Best Practices

### 1. Key Naming Convention
```
{product}:{use_case}:{module}:{entity}:{identifier}:{additional}

Examples:
waddlebot:cache:twitch_receiver:channel:channelname
waddlebot:rate_limit:router:user_123:command_help
waddlebot:stream:events
```

### 2. TTL Strategy
- **Hot data** (user balances): 30-60s
- **Warm data** (leaderboards): 60-300s
- **Cold data** (channel lists): 300-600s
- **Session data**: 3600s (1 hour)
- **Rate limits**: Equal to window duration
- **Streams**: No TTL (manual cleanup or MAXLEN)

### 3. Memory Management
```redis
# Monitor memory usage
INFO memory

# Check keys per database
INFO keyspace

# Monitor evictions
INFO stats
```

### 4. Monitoring Queries
```redis
# Count keys per namespace
SCAN 0 MATCH waddlebot:cache:* COUNT 1000

# Get cache hit rate
INFO stats | grep keyspace_hits
INFO stats | grep keyspace_misses

# Check stream lengths
XLEN waddlebot:stream:events
XLEN waddlebot:dlq:events
```

## Migration Path

If you need to separate Redis instances later:

### Phase 1: Single Redis (Current)
```
All modules → Single Redis (different DBs)
```

### Phase 2: Cache Separation
```
Caching → Redis Instance 1 (DB 0)
Rate Limiting → Redis Instance 2 (DB 0)
Message Queue → Redis Instance 3 (DB 0)
```

### Phase 3: Horizontal Scaling
```
Caching → Redis Cluster (sharded by namespace)
Rate Limiting → Dedicated Redis (high write throughput)
Message Queue → Redis with persistence/replication
```

## Implementation in Code

All flask_core utilities already implement proper namespacing:

```python
# CacheManager
cache = CacheManager(
    redis_url="redis://:pass@redis:6379/0",
    namespace="twitch_receiver",  # Adds waddlebot:cache:twitch_receiver:
    default_ttl=300
)

# RateLimiter
limiter = RateLimiter(
    redis_url="redis://:pass@redis:6379/1",
    namespace="router",  # Adds waddlebot:rate_limit:router:
)

# MessageQueue
queue = MessageQueue(
    redis_url="redis://:pass@redis:6379/2",
    stream_prefix="waddlebot"  # Adds waddlebot:stream: and waddlebot:dlq:
)
```

The namespace is automatically prepended to all keys, ensuring complete isolation.
