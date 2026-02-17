# Analytics Core Module — Architecture

**Version:** 1.0.0
**Last Updated:** 2026-02-16

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow Pipelines](#data-flow-pipelines)
4. [Database Schema](#database-schema)
5. [Service Integration](#service-integration)
6. [Caching Strategy](#caching-strategy)
7. [Scaling Considerations](#scaling-considerations)
8. [Security Architecture](#security-architecture)

---

## System Overview

The Analytics Core Module is a microservice designed to collect, aggregate, and analyze community activity data from multiple platforms. It follows a layered architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────────────┐
│                     REST API Layer (8040)                       │
├─────────────────────────────────────────────────────────────────┤
│  • Public endpoints (/api/v1/analytics/*)                      │
│  • Internal endpoints (/api/v1/internal/*)                     │
│  • Health checks (/health)                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Service Layer (async services)                 │
├─────────────────────────────────────────────────────────────────┤
│  • AnalyticsService       - Core calculation & config           │
│  • MetricsService         - Time-series management              │
│  • BotScoreService        - Bot detection scoring               │
│  • PollingService         - Real-time updates                   │
│  • HealthService          - Status monitoring                   │
│  • RetentionService       - Data cleanup                        │
│  • BadActorService        - User flagging                       │
│  • FunnelService          - Funnel analytics                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Data Access Layer (PyDAL)                      │
├─────────────────────────────────────────────────────────────────┤
│  • Execute SQL queries via database abstraction                │
│  • Connection pooling                                           │
│  • Transaction management                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            Storage Layer (PostgreSQL + Redis Cache)             │
├─────────────────────────────────────────────────────────────────┤
│  • PostgreSQL: Primary data store                               │
│  • Redis: Caching layer (optional)                              │
│  • Activity tables, metrics tables, config tables               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. REST API Handler (Quart)

**File:** `/core/analytics_core_module/app.py`

The main application entry point using Quart (async Python web framework).

**Responsibilities:**
- Route HTTP requests to appropriate service methods
- Handle request/response serialization
- Provide authentication middleware integration
- Manage application lifecycle (startup/shutdown)

**Key Routes:**
```python
# Public API
GET  /health                                    # Health check
GET  /api/v1/analytics/status                  # Module status
GET  /api/v1/analytics/{id}/basic              # Basic stats
GET  /api/v1/analytics/{id}/metrics            # Time-series metrics
GET  /api/v1/analytics/{id}/config             # Get config
PUT  /api/v1/analytics/{id}/config             # Update config
GET  /api/v1/analytics/{id}/poll               # Poll updates
GET  /api/v1/analytics/{id}/bot-score          # Bot score
GET  /api/v1/analytics/{id}/suspected-bots    # List bots
PUT  /api/v1/analytics/{id}/suspected-bots/{bid}/review  # Review bot

# Internal API (service-to-service)
POST /api/v1/internal/events                   # Receive events
POST /api/v1/internal/aggregate                # Trigger aggregation
```

### 2. Analytics Service

**File:** `/core/analytics_core_module/services/analytics_service.py`

Core analytics calculations and configuration management.

**Class:** `AnalyticsService`

**Methods:**
- `get_config()` - Retrieve community analytics configuration
- `update_config()` - Modify analytics settings
- `get_basic_stats()` - Calculate free-tier statistics
- `process_events()` - Ingest activity events
- `run_aggregation()` - Trigger metrics aggregation

**Key Algorithms:**

**Basic Stats Calculation:**
```
total_chatters = COUNT(DISTINCT hub_user_id) FROM activity_message_events
total_stream_time = SUM(duration_seconds) FROM activity_watch_sessions / 3600
messages_per_user = SELECT username, COUNT(*) GROUP BY username LIMIT 10
active_7d = COUNT(DISTINCT hub_user_id) WHERE created_at >= NOW() - 7 days
active_30d = COUNT(DISTINCT hub_user_id) WHERE created_at >= NOW() - 30 days
```

**Event Processing:**
- Events received via `/internal/events` endpoint
- Batch ingestion from Router module
- Events stored in activity_* tables with timestamps
- Aggregation job picks up new events

### 3. Metrics Service

**File:** `/core/analytics_core_module/services/metrics_service.py`

Time-series metrics management and aggregation.

**Class:** `MetricsService`

**Methods:**
- `get_timeseries()` - Query aggregated metrics with bucket sizes
- `record_metric()` - Store calculated metric values

**Bucket Aggregation Logic:**
```
1h  bucket = TIME_BUCKET(1 hour, timestamp)
1d  bucket = TIME_BUCKET(24 hours, timestamp)
1w  bucket = TIME_BUCKET(7 days, timestamp)
1m  bucket = TIME_BUCKET(30 days, timestamp)
```

**Query Pattern:**
```sql
SELECT timestamp_bucket, value, metadata
FROM analytics_metrics_timeseries
WHERE community_id = $1
  AND metric_type = $2
  AND bucket_size = $3
  AND timestamp_bucket BETWEEN $4 AND $5
ORDER BY timestamp_bucket ASC
```

### 4. Bot Score Service

**File:** `/core/analytics_core_module/services/bot_score_service.py`

Community bot detection scoring system using weighted formula.

**Class:** `BotScoreService`

**Methods:**
- `calculate_score()` - Calculate composite bot detection score
- `get_score()` - Get cached score or recalculate if stale
- `get_suspected_bots()` - List suspected bot users
- `mark_bot_reviewed()` - Mark bot as false positive or confirmed

**Scoring Formula:**

```
overall_score = (
    bad_actor_score * 0.30 +
    reputation_score * 0.25 +
    security_score * 0.20 +
    ai_behavioral_score * 0.25
)
```

**Component Score Calculations:**

**Bad Actor Score (0-100, 100=clean):**
```
bad_actor_count = COUNT(DISTINCT platform_user_id)
                  FROM analytics_bad_actor_alerts
                  WHERE status = 'pending'
total_users = COUNT(DISTINCT hub_user_id)
              FROM activity_message_events
              WHERE created_at >= NOW() - 30 days
bad_actor_percentage = (bad_actor_count / total_users) * 100
score = MAX(0, 100 - (bad_actor_percentage * 5))
```

**Reputation Score (0-100):**
```
health_score = SELECT health_score FROM analytics_community_health
engagement_level = SELECT engagement_level FROM analytics_community_health
score = (health_score * 0.7) + (engagement_level * 0.3)
```

**Security Score (0-100):**
```
violations = COUNT(*) FROM activity_message_events
             WHERE violation_detected = TRUE
             AND created_at >= NOW() - 30 days
total_events = COUNT(*) FROM activity_message_events
               WHERE created_at >= NOW() - 30 days
violation_rate = (violations / total_events) * 100
score = MAX(0, 100 - (violation_rate * 10))
```

**AI Behavioral Score (0-100):**
```
rapid_posters = COUNT(DISTINCT hub_user_id)
                WHERE message_count > 5
                IN time_bucket('1 minute')
                AND created_at >= NOW() - 24 hours

duplicate_users = COUNT(DISTINCT hub_user_id)
                  WHERE same_message_count >= 3
                  IN time_bucket('5 minutes')

anomaly_percentage = ((rapid_posters + duplicate_users) / active_users) * 100
score = MAX(0, 100 - (anomaly_percentage * 10))
```

**Grade Mapping:**
- A: 90-100
- B: 80-89
- C: 70-79
- D: 60-69
- F: 0-59

**Caching:**
- Scores cached in `analytics_bot_scores` table
- Valid for 24 hours (next_recalculation field)
- Manual recalculation available via API

### 5. Other Services

**PollingService:** Real-time update polling
**RetentionService:** Data cleanup and archival
**HealthService:** Module status monitoring
**BadActorService:** User flagging and alerts
**FunnelService:** Funnel analysis (future)

---

## Data Flow Pipelines

### Event Ingestion Pipeline

```
┌─────────────────┐
│  Router Module  │
│  (sends events) │
└────────┬────────┘
         │ HTTP POST /api/v1/internal/events
         ↓
┌─────────────────────────────────────┐
│   Analytics Core - receive_events() │
│   • Parse event payload             │
│   • Validate community_id           │
│   • Dispatch to AnalyticsService    │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  AnalyticsService.process_events()  │
│  • Iterate through event list       │
│  • Store in activity_* tables       │
│  • Log audit trail                  │
│  • Return processed count           │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│   PostgreSQL Storage                │
│   • activity_message_events         │
│   • activity_watch_sessions         │
│   • activity_reaction_events        │
│   • activity_custom_events          │
└─────────────────────────────────────┘
```

**Event Processing Steps:**

1. **Validation**
   - Check community_id exists
   - Validate event_type is known
   - Check platform is recognized

2. **Enrichment**
   - Map platform_user_id to hub_user_id (if exists)
   - Add timestamp normalization
   - Parse metadata JSON

3. **Storage**
   - Insert into appropriate activity_* table
   - Commit transaction
   - Log audit event

4. **Aggregation Trigger**
   - Mark community for aggregation (optional)
   - Or await scheduled aggregation job

### Metrics Aggregation Pipeline

```
┌──────────────────────────────────┐
│   Aggregation Trigger            │
│   • Manual API call              │
│   • Scheduled job (e.g., hourly) │
│   • Event volume threshold       │
└────────────┬─────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  AnalyticsService.run_aggregation()  │
│  • Lock community (prevent double)   │
│  • Determine time buckets to fill    │
│  • Iterate time windows              │
└────────────┬─────────────────────────┘
             │
             ├─ Query 1h bucket data
             ├─ Query 1d bucket data
             ├─ Query 1w bucket data
             └─ Query 1m bucket data
             │
             ↓
┌──────────────────────────────────────┐
│  MetricsService.record_metric()      │
│  • Calculate aggregate value         │
│  • Prepare metadata                  │
│  • INSERT ... ON CONFLICT            │
└────────────┬─────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│   PostgreSQL - analytics_metrics_*   │
│   • analytics_metrics_timeseries     │
│   • Indexed on (community_id,        │
│     metric_type, timestamp_bucket)   │
└──────────────────────────────────────┘
```

**Aggregation Algorithm:**

```python
FOR each bucket_size IN ['1h', '1d', '1w', '1m']:
    FOR each metric_type IN ['messages', 'viewers', 'engagement']:
        last_aggregated = get_last_aggregation_timestamp()

        FOR each bucket BETWEEN last_aggregated AND now:
            raw_value = query_activity_table(
                community_id,
                metric_type,
                bucket_timerange
            )

            record_metric(
                community_id=community_id,
                metric_type=metric_type,
                bucket_size=bucket_size,
                timestamp=bucket.start_time,
                value=raw_value,
                metadata={...}
            )

        update_last_aggregation_timestamp()
```

### Bot Detection Pipeline

```
┌──────────────────────────────────┐
│   Manual Request or Scheduled     │
│   GET /bot-score or cron job     │
└────────────┬─────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  BotScoreService.get_score()         │
│  • Check analytics_bot_scores cache  │
│  • If stale/missing, recalculate    │
└────────────┬─────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  BotScoreService.calculate_score()   │
│  • Get community size category       │
│  • Calculate 4 components in parallel│
│  • Apply weighted formula            │
│  • Determine grade A-F              │
└────────────┬─────────────────────────┘
             │
        ┌────┼────┬────┬─────┐
        │    │    │    │     │
        ↓    ↓    ↓    ↓     ↓
      [1]  [2]  [3]  [4]   Size
       │    │    │    │     │
   BadAct Rep  Sec  AIBhv  Cat
   Score Score Score Score  └─→ Query 30-day user count
        │    │    │    │        └─→ small/medium/large
        └────┴────┴────┘
             │
             ↓
┌──────────────────────────────────────┐
│  Compose Final Score                 │
│  • Weighted combination              │
│  • Score to grade mapping            │
│  • Upsert to analytics_bot_scores   │
│  • Set next_recalculation = +24h    │
└────────────┬─────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  Return Score Result to Client       │
└──────────────────────────────────────┘
```

---

## Database Schema

### Configuration Tables

```sql
-- Per-community analytics settings
CREATE TABLE analytics_config (
  community_id INTEGER PRIMARY KEY,
  is_premium BOOLEAN DEFAULT FALSE,
  basic_stats_enabled BOOLEAN DEFAULT TRUE,
  community_health_enabled BOOLEAN DEFAULT FALSE,
  bad_actor_detection_enabled BOOLEAN DEFAULT FALSE,
  user_journey_enabled BOOLEAN DEFAULT FALSE,
  polling_interval_seconds INTEGER DEFAULT 30,
  raw_data_retention_days INTEGER DEFAULT 30,
  aggregated_data_retention_days INTEGER DEFAULT 365,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Metrics Tables

```sql
-- Time-series metrics storage
CREATE TABLE analytics_metrics_timeseries (
  id BIGSERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  metric_type VARCHAR(50) NOT NULL,        -- messages, viewers, engagement, growth
  metric_subtype VARCHAR(50),              -- optional sub-type
  timestamp_bucket TIMESTAMP NOT NULL,     -- bucket start time
  bucket_size VARCHAR(10) NOT NULL,        -- 1h, 1d, 1w, 1m
  value NUMERIC NOT NULL,                  -- aggregated metric value
  metadata JSONB,                          -- additional data (peak_hour, etc)
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(community_id, metric_type, metric_subtype, timestamp_bucket, bucket_size)
);

CREATE INDEX idx_metrics_community_time
  ON analytics_metrics_timeseries(community_id, timestamp_bucket);
CREATE INDEX idx_metrics_type_bucket
  ON analytics_metrics_timeseries(metric_type, bucket_size);
```

### Bot Detection Tables

```sql
-- Bot detection scores
CREATE TABLE analytics_bot_scores (
  community_id INTEGER PRIMARY KEY,
  overall_score INTEGER NOT NULL,         -- 0-100
  grade CHAR(1) NOT NULL,                 -- A-F
  size_category VARCHAR(20) NOT NULL,     -- small, medium, large
  component_scores JSONB NOT NULL,        -- {bad_actor, reputation, security, ai_behavioral}
  component_weights JSONB NOT NULL,       -- {bad_actor: 0.30, ...}
  calculated_at TIMESTAMP NOT NULL,
  next_recalculation TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Suspected bot users
CREATE TABLE analytics_suspected_bots (
  id BIGSERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  hub_user_id INTEGER,
  platform_user_id VARCHAR(255) NOT NULL,
  platform_username VARCHAR(255),
  confidence_score INTEGER NOT NULL,      -- 0-100
  bot_indicators JSONB,                   -- {rapid_posting, duplicate_messages, ...}
  detected_patterns TEXT[],               -- ["same message 5x in 2 min", ...]
  is_false_positive BOOLEAN,
  reviewed_by INTEGER,
  reviewed_at TIMESTAMP,
  detected_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(community_id, hub_user_id)
);

CREATE INDEX idx_suspected_bots_community
  ON analytics_suspected_bots(community_id);
CREATE INDEX idx_suspected_bots_confidence
  ON analytics_suspected_bots(confidence_score DESC);
```

### Bad Actor Tables

```sql
-- Bad actor alerts and flags
CREATE TABLE analytics_bad_actor_alerts (
  id BIGSERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  hub_user_id INTEGER,
  platform_user_id VARCHAR(255) NOT NULL,
  platform_username VARCHAR(255),
  alert_type VARCHAR(50) NOT NULL,        -- spam, hate_speech, doxxing, etc
  severity VARCHAR(20) NOT NULL,          -- low, medium, high, critical
  status VARCHAR(50) DEFAULT 'pending',   -- pending, reviewed, resolved
  flagged_by INTEGER,
  reviewed_by INTEGER,
  reviewed_at TIMESTAMP,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bad_actor_community
  ON analytics_bad_actor_alerts(community_id, status);
```

### Activity Tables (Read-only from Analytics perspective)

```sql
-- Source tables (populated by Router module)
activity_message_events
  - community_id
  - hub_user_id
  - platform_user_id
  - platform_username
  - message_text
  - created_at
  - violation_detected
  - metadata JSONB

activity_watch_sessions
  - community_id
  - hub_user_id
  - platform_user_id
  - start_time
  - end_time
  - duration_seconds
  - created_at
```

---

## Service Integration

### Inbound Dependencies

Services that send data TO analytics-core:

**Router Module** (`http://router:8000/api/v1/router`)
- Sends activity events via `/internal/events` endpoint
- Provides platform-specific event normalization
- Triggers analytics processing

**Scheduled Jobs** (external)
- Trigger aggregation via `/internal/aggregate` endpoint
- Run bot score recalculation
- Data cleanup and retention

### Outbound Dependencies

Services that analytics-core queries:

**PostgreSQL Database**
- Primary data store
- Query execution via PyDAL
- Connection pooling

**Redis** (optional)
- Cache layer for bot scores
- Credential refresh pub/sub channel
- Performance optimization

**Reputation Module** (`http://reputation:8021/api/v1/reputation`)
- Provides reputation data for scoring
- Community health metrics
- User reputation signals

---

## Caching Strategy

### Bot Score Caching

```
Request for bot score
    ↓
Check analytics_bot_scores table
    ↓
Is next_recalculation > NOW()?
    │
    ├─ YES: Return cached score with cached=true
    │
    └─ NO: Recalculate score
        ├─ Update analytics_bot_scores
        ├─ Return fresh score with cached=false
```

**Cache Duration:** 24 hours per community

**Invalidation:**
- Automatic: After 24 hours
- Manual: POST `/bot-score/calculate` endpoint
- Event-based: On significant activity spikes (future)

### Redis Caching (Optional)

If Redis is configured:

```python
KEY = f"analytics:bot-score:{community_id}"
TTL = 86400  # 24 hours

# On calculation
redis.setex(KEY, TTL, json.dumps(score_data))

# On query
cached = redis.get(KEY)
if cached:
    return json.loads(cached)
```

### Query Result Caching

Metrics queries are generally not cached (real-time data), but can be cached at the client level:

```javascript
// Client-side caching pattern
const CACHE_TTL = 300000; // 5 minutes
let metricsCache = {};

async function getMetrics(communityId, params) {
  const key = `${communityId}:${JSON.stringify(params)}`;

  if (metricsCache[key] &&
      Date.now() - metricsCache[key].time < CACHE_TTL) {
    return metricsCache[key].data;
  }

  const data = await fetch(`/api/v1/analytics/${communityId}/metrics?...`);
  metricsCache[key] = { data, time: Date.now() };
  return data;
}
```

---

## Scaling Considerations

### Horizontal Scaling

Multiple analytics-core instances can run behind a load balancer:

```
┌─────────────────────────────────────┐
│   Load Balancer (8040)              │
├─────────────────────────────────────┤
│  ↓              ↓              ↓     │
│ [AC-1]      [AC-2]        [AC-3]   │
│ :8040       :8040         :8040    │
│                                     │
│ All instances share:                │
│ • PostgreSQL database               │
│ • Redis cache                       │
│ • Configuration                     │
└─────────────────────────────────────┘
```

**Scaling Strategy:**
- Stateless API instances (can scale freely)
- Database connection pooling (PyDAL handles)
- Redis for distributed caching
- Aggregation jobs run on single instance (distributed locking needed)

### Database Optimization

**Indexes to add:**
```sql
CREATE INDEX idx_activity_msg_community_time
  ON activity_message_events(community_id, created_at);

CREATE INDEX idx_metrics_query
  ON analytics_metrics_timeseries(community_id, metric_type, timestamp_bucket);

CREATE INDEX idx_bot_scores_grade
  ON analytics_bot_scores(community_id, grade);
```

**Partitioning (for very large deployments):**
```sql
-- Partition activity tables by community_id (thousands of communities)
CREATE TABLE activity_message_events_partitioned
PARTITION BY HASH (community_id);
```

### Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Basic stats query | <500ms | ? |
| Metrics query (30d) | <1s | ? |
| Bot score calculation | <5s | ? |
| Event processing | <10ms/event | ? |
| Aggregation (1000 events) | <5s | ? |

---

## Security Architecture

### Authentication & Authorization

**Public API Endpoints:**
- Require Flask-Security-Too authentication
- User must have admin or moderator role
- Community_id in URL must match user's communities

**Internal Service Endpoints:**
- Require `X-Service-API-Key` header
- Key matches SERVICE_API_KEY env var
- No user context required (service-to-service)

### Data Access Control

```python
@api_bp.route('/<int:community_id>/basic', methods=['GET'])
@auth_required  # Flask-Security-Too decorator
async def get_basic_stats(community_id: int):
    # Check if current user can access this community
    if not user_can_access_community(current_user, community_id):
        return error_response("Access denied", 403)

    stats = await analytics_service.get_basic_stats(community_id)
    return jsonify(success_response(stats))
```

### Credential Management

Credentials loaded with fallback strategy:

```python
# Priority 1: Load from database (platform_integrations table)
Config.load_credentials_from_db(db_connection)

# Priority 2: Fallback to environment variables
ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://router:8000/...')

# Credential refresh via Redis pub/sub
Config.start_credential_listener(redis_client)
```

### Data Retention & Privacy

- Raw activity events: Configurable retention (default 30 days)
- Aggregated metrics: Longer retention (default 365 days)
- Bot detection scores: 24-hour cache, permanent storage
- Audit logs: Indefinite retention

---

**Last Updated:** 2026-02-16
**Maintained By:** Penguin Tech Inc
