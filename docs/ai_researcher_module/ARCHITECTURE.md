# AI Researcher Module — Architecture

## System Overview

The AI Researcher Module is a microservice component of WaddleBot that provides context-aware AI research, conversation analysis, and semantic memory capabilities. It operates asynchronously using Python 3.12, Quart (async web framework), and integrates with multiple external services.

```
┌────────────────────────────────────────────────────────────────┐
│                     AI Researcher Module                        │
│                      (Quart REST API)                           │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Endpoint Handlers (Flask Blueprints)          │  │
│  │  - research, ask, recall, summarize (commands)          │  │
│  │  - insights, sentiment, anomalies (analysis)            │  │
│  │  - bot-detection, user-profiles (detection)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│       ┌────────────────────┼────────────────────┐              │
│       ▼                    ▼                    ▼              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐      │
│  │ Research     │ │ Safety Layer │ │ Rate Limiter     │      │
│  │ Service      │ │ (Moderation) │ │ (Redis+DB)       │      │
│  └──────────────┘ └──────────────┘ └──────────────────┘      │
│       │                                                         │
│       └─────────────────────┬──────────────────┬─────────────┐ │
│                             ▼                  ▼             │ │
│                      ┌─────────────┐   ┌──────────────┐     │ │
│                      │ AI Provider │   │ mem0 Service │     │ │
│                      │ Service     │   │ (Memory)     │     │ │
│                      └─────────────┘   └──────────────┘     │ │
│                             │                  │             │ │
└─────────────────────────────┼──────────────────┼─────────────┘ │
                              │                  │
      ┌───────────────────────┼──────────────────┼─────────────┐
      ▼                       ▼                  ▼             ▼
┌──────────────┐         ┌──────────┐      ┌─────────┐  ┌─────────┐
│ Ollama/      │         │PostgreSQL│      │Qdrant   │  │ Redis   │
│WaddleAI LLM  │         │(Database)│      │(Vectors)│  │(Cache)  │
└──────────────┘         └──────────┘      └─────────┘  └─────────┘
```

## Core Components

### 1. Endpoint Handlers (Quart Blueprints)

**Location:** `/core/ai_researcher_module/app.py`

Quart blueprints organize endpoints by concern:

- **api_bp** — `/api/v1/` — Module status
- **researcher_bp** — `/api/v1/researcher/` — Research, context, memory, insights
- **admin_bp** — `/api/v1/admin/` — Admin configuration and bot detection

**Key Pattern:**
```python
@researcher_bp.route('/research', methods=['POST'])
@async_endpoint
async def research():
    # 1. Extract and validate request
    # 2. Get community-specific services
    # 3. Call service layer
    # 4. Return response
```

### 2. Research Service

**Location:** `/core/ai_researcher_module/services/research_service.py`

Handles all research-related operations:

**Responsibilities:**
- Execute `!or/research` commands
- Execute `!or/ask` commands
- Execute `!or/recall` commands
- Execute `!or/summarize` commands
- Manage semantic caching
- Track token usage and processing time
- Integrate with AI provider and mem0

**Key Methods:**
```python
async def research(community_id, user_id, topic) -> ResearchResult
async def ask(community_id, user_id, question) -> ResearchResult
async def recall(community_id, user_id, topic) -> ResearchResult
async def summarize(community_id, user_id, duration_minutes) -> ResearchResult
```

**Caching Strategy:**
- Exact match caching via Redis (TTL: CACHE_TTL_RESEARCH)
- Semantic caching with similarity threshold (SEMANTIC_CACHE_THRESHOLD)
- Cache key: hash of query, user, community

### 3. AI Provider Service

**Location:** `/core/ai_researcher_module/services/ai_provider.py`

Abstract interface to AI providers with multi-provider support.

**Supported Providers:**
- **Ollama** — Local or remote Ollama instance
- **WaddleAI** — Centralized AI proxy service

**Responsibilities:**
- Initialize LLM connections
- Queue and execute LLM requests
- Handle retries and timeouts
- Track token usage
- Manage concurrent requests (MAX_CONCURRENT_LLM_CALLS)

**Key Methods:**
```python
async def generate(prompt: str, context: str = "") -> str
async def stream(prompt: str) -> AsyncGenerator[str, None]
async def count_tokens(text: str) -> int
async def close()
```

### 4. mem0 Service

**Location:** `/core/ai_researcher_module/services/mem0_service.py`

Vector-based semantic memory using mem0 + Qdrant.

**Responsibilities:**
- Store user and community memories
- Semantic search via Qdrant vector store
- Manage memory retention and pruning
- Deduplicate similar memories
- Index memories for efficient retrieval

**Key Methods:**
```python
async def add(content: str, metadata: Dict = None) -> str
async def search(query: str, limit: int = 10) -> List[Memory]
async def get_all(limit: int = 100) -> List[Memory]
async def delete(memory_id: str) -> bool
```

**Vector Store:**
- **Provider:** Qdrant (high-performance vector DB)
- **Embedder:** Ollama or WaddleAI embeddings
- **Collection:** `ai_researcher_memory` (configurable)
- **Similarity Metric:** Cosine distance

### 5. Safety Layer

**Location:** `/core/ai_researcher_module/services/safety_layer.py`

Content moderation and safety validation.

**Responsibilities:**
- Filter unsafe/harmful content
- Validate research queries
- Block inappropriate responses
- Enforce safety policies

**Key Methods:**
```python
def is_safe(content: str) -> bool
def sanitize(content: str) -> str
def check_query_safety(query: str) -> Tuple[bool, Optional[str]]
```

### 6. Rate Limiter Service

**Location:** `/core/ai_researcher_module/services/rate_limiter.py`

Two-tier rate limiting with Redis and database fallback.

**Responsibilities:**
- Enforce per-user rate limits
- Enforce global rate limits
- Support both research and memory operations
- Use Redis for fast checking
- Fall back to database if Redis unavailable

**Limits (Configurable):**
- Research: 30 requests/min per user
- Memory: 100 requests/min per user
- Global research: 500/min
- Global memory: 1000/min

**Key Methods:**
```python
async def check_limit(user_id: str, operation: str) -> Tuple[bool, Optional[str]]
async def increment_counter(user_id: str, operation: str)
```

### 7. Additional Services

| Service | Purpose | Location |
|---------|---------|----------|
| **BotDetectionService** | Identify bot accounts | services/bot_detection.py |
| **SentimentAnalyzer** | Community mood analysis | services/sentiment_analyzer.py |
| **AnomalyDetector** | Unusual activity detection | services/anomaly_detector.py |
| **BehaviorProfiler** | User behavior analysis | services/behavior_profiler.py |
| **InsightsService** | Generate community insights | services/insights_service.py |
| **SummaryService** | Generate conversation summaries | services/summary_service.py |

## Data Flow

### Research Query Flow

```
1. Client POST /api/v1/researcher/research
   │
   ├─ Extract: community_id, user_id, query
   │
   ├─ Check Rate Limit
   │  ├─ Redis check (fast path)
   │  └─ DB fallback if Redis down
   │
   ├─ Check Cache
   │  ├─ Exact match in Redis
   │  └─ Semantic similarity search in mem0
   │
   ├─ If cached: Return cached result
   │
   └─ If not cached:
      │
      ├─ Execute LLM Request
      │  ├─ Queue request (MAX_CONCURRENT_LLM_CALLS)
      │  ├─ Call AI Provider (Ollama or WaddleAI)
      │  └─ Get response + token count
      │
      ├─ Safety Check
      │  └─ Validate response content
      │
      ├─ Store in Cache
      │  ├─ Redis (TTL: CACHE_TTL_RESEARCH)
      │  └─ mem0 (semantic embedding)
      │
      └─ Return result with metadata
```

### Message Firehose Flow

```
1. Router/Hub Service
   │
   └─ POST /api/v1/researcher/messages/firehose (X-Service-Key)
      │
      ├─ Batch messages (optional)
      │
      └─ For each message:
         │
         ├─ Insert into ai_context_messages table
         │
         ├─ Queue for batch processing
         │
         └─ Async context enrichment
            │
            ├─ Extract entities, topics
            │
            ├─ Update community context window
            │
            └─ Index in mem0 (vector embedding)
```

### Insights Generation Flow

```
1. Client POST /api/v1/researcher/{community_id}/insights/generate
   │
   ├─ Extract timeframe and insight types
   │
   ├─ Fetch context messages for period
   │
   ├─ Create InsightsService
   │
   ├─ For each insight type:
   │  │
   │  ├─ Prepare data (aggregation)
   │  │
   │  ├─ Generate prompt
   │  │
   │  ├─ Call AI Provider (LLM)
   │  │
   │  └─ Store in ai_insights table
   │
   └─ Return insight results
```

## Database Schema

### Key Tables

```sql
-- Stores all messages for context
CREATE TABLE ai_context_messages (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    platform VARCHAR(50),
    platform_user_id VARCHAR(255),
    platform_username VARCHAR(255),
    message_content TEXT,
    message_type VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Stores generated insights
CREATE TABLE ai_insights (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    insight_type VARCHAR(50),
    title VARCHAR(255),
    content TEXT,
    content_html TEXT,
    metadata JSONB,
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Community-level configuration
CREATE TABLE ai_researcher_config (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL UNIQUE,
    firehose_enabled BOOLEAN DEFAULT FALSE,
    bot_detection_enabled BOOLEAN DEFAULT FALSE,
    bot_detection_threshold NUMERIC(3,2) DEFAULT 0.7,
    research_max_queries INTEGER DEFAULT 30,
    summary_enabled BOOLEAN DEFAULT TRUE,
    mem0_enabled BOOLEAN DEFAULT TRUE,
    ai_provider VARCHAR(50),
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Bot detection results
CREATE TABLE ai_bot_detection_results (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    platform VARCHAR(50),
    platform_user_id VARCHAR(255),
    platform_username VARCHAR(255),
    confidence_score NUMERIC(3,2),
    behavioral_patterns JSONB,
    timing_regularity NUMERIC(3,2),
    response_latency_avg NUMERIC(5,2),
    emote_text_ratio NUMERIC(3,2),
    copy_paste_frequency NUMERIC(3,2),
    account_age_days INTEGER,
    recommended_action VARCHAR(50),
    is_reviewed BOOLEAN DEFAULT FALSE,
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User behavior profiles
CREATE TABLE ai_user_profiles (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    platform VARCHAR(50),
    platform_user_id VARCHAR(255),
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Caching Strategy

### Three-Tier Cache

1. **Redis Cache (L1)**
   - Exact query matches
   - TTL varies by operation (CACHE_TTL_RESEARCH, CACHE_TTL_CONTEXT, CACHE_TTL_MEMORY)
   - Fast key-value lookups
   - Fallback: Database if Redis unavailable

2. **Semantic Cache (L2)**
   - Vector-based similarity matching
   - Stored in mem0/Qdrant
   - Threshold: SEMANTIC_CACHE_THRESHOLD (0.95 default)
   - Useful for similar but not identical queries

3. **Memory Store (L3)**
   - Community memories in Qdrant
   - Long-term persistent storage
   - Retention: MEMORY_RETENTION_DAYS (90 default)
   - Auto-pruning of old memories

### Cache Key Format

```
{CACHE_PREFIX}:{operation}:{community_id}:{user_id}:{hash(query)}
```

Example:
```
research:research:123:456:abc123def456
```

## Concurrency Model

### Async Architecture

- **Framework:** Quart (async Python web framework)
- **Workers:** 4 Hypercorn workers (configurable)
- **Concurrency:** Per-request async/await

### LLM Request Queue

- **Max concurrent LLM calls:** MAX_CONCURRENT_LLM_CALLS (10 default)
- **Queue size:** LLM_QUEUE_SIZE (100 default)
- **Timeout:** LLM_REQUEST_TIMEOUT (60 seconds)
- **Retry strategy:** LLM_MAX_RETRIES (3) with exponential backoff

### Database Connection Pool

- **Pool size:** DB_POOL_SIZE (20)
- **Max overflow:** DB_MAX_OVERFLOW (40)
- **Timeout:** REQUEST_TIMEOUT (30 seconds)

## Error Handling

### Retry Strategy

```python
# LLM call retries
for attempt in range(LLM_MAX_RETRIES):
    try:
        result = await ai_provider.generate(prompt)
        return result
    except Exception as e:
        if attempt < LLM_MAX_RETRIES - 1:
            await asyncio.sleep(LLM_RETRY_DELAY * (2 ** attempt))
        else:
            raise
```

### Fallback Behaviors

| Failure | Fallback |
|---------|----------|
| Redis unavailable | Use database for rate limiting |
| LLM timeout | Return cached result or error |
| Qdrant down | Skip semantic search, use text search |
| Database error | Return 500, log error |

## Monitoring & Observability

### Metrics Tracked

- **Processing time** (milliseconds) — returned in all responses
- **Tokens used** (LLM tokens) — returned in LLM responses
- **Cache hit rate** — logged per operation
- **Rate limit violations** — logged with user/community
- **Error rates** — per endpoint and operation

### Logging

- **AAA Logging** — Authentication, Authorization, Audit events
- **Location:** `/var/log/waddlebotlog/ai_researcher_module.log`
- **Audit Log:** `/var/log/waddlebotlog/ai_researcher_module_aaa.log`
- **Level:** Configurable (LOG_LEVEL)

### Health Checks

- **Endpoint:** `GET /healthz`
- **Checks:**
  - Database connectivity
  - Redis connectivity
  - Qdrant connectivity
  - LLM provider availability
  - Memory/disk usage

## Security

### Authentication

- **User endpoints:** Bearer token (standard auth)
- **Admin endpoints:** X-Service-Key header (constant-time comparison)
- **Token validation:** Performed in middleware

### Data Protection

- **In transit:** HTTPS (enforced at ingress)
- **At rest:** Database encryption (PostgreSQL TDE recommended)
- **Secrets:** Environment variables, not hardcoded
- **Audit:** All admin actions logged with user, action, result

### Rate Limiting

- **Per-user limits:** Prevents abuse
- **Global limits:** Prevents provider overload
- **Fallback:** Database counting if Redis unavailable

## Deployment Considerations

### Resource Requirements

- **CPU:** 2 cores minimum, 4 cores recommended
- **Memory:** 2GB minimum, 4GB recommended
- **Disk:** 10GB for logs and database
- **Network:** Outbound to Ollama/WaddleAI, inbound HTTP

### Scaling

- **Horizontal:** Run multiple containers behind load balancer
- **Vertical:** Increase CPU, memory, worker threads
- **Database:** Use connection pooling, prepare statements
- **Redis:** Use cluster mode for high availability

### Dependencies

- PostgreSQL 13+ (required)
- Redis 6+ (required for rate limiting)
- Qdrant 1.7+ (required for memory)
- Ollama or WaddleAI account (required for LLM)
