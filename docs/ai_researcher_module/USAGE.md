# AI Researcher Module — Usage Guide

## Getting Started

### Prerequisites

- Docker (for containerized deployment)
- PostgreSQL 13+ (database backend)
- Redis 6+ (caching and session storage)
- Ollama or WaddleAI account (AI provider)
- Qdrant 1.7+ (vector store for mem0)

### Quick Start with Docker

#### 1. Pull the Image

```bash
docker pull waddlebot/ai-researcher:latest
```

#### 2. Run Container

```bash
docker run -d \
  --name ai-researcher \
  --network waddlebot-network \
  -p 8070:8070 \
  -e DATABASE_URL="postgresql://waddlebot:password@postgres:5432/waddlebot" \
  -e REDIS_URL="redis://redis:6379/0" \
  -e QDRANT_URL="http://qdrant:6333" \
  -e AI_PROVIDER="ollama" \
  -e OLLAMA_HOST="ollama" \
  -e OLLAMA_PORT="11434" \
  -e OLLAMA_MODEL="tinyllama" \
  -e MODULE_PORT="8070" \
  -e MODULE_VERSION="1.0.0" \
  waddlebot/ai-researcher:latest
```

#### 3. Verify Health

```bash
curl -s http://localhost:8070/healthz | jq
# Expected: { "status": "healthy", "module": "ai_researcher_module", "version": "1.0.0" }
```

### Local Development

#### 1. Install Dependencies

```bash
cd core/ai_researcher_module
pip install -r requirements.txt
```

#### 2. Configure Environment

Create `.env` file:

```bash
# Module Configuration
MODULE_NAME=ai_researcher_module
MODULE_VERSION=1.0.0
MODULE_PORT=8070

# Database
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
REDIS_URL=redis://localhost:6379/0

# AI Provider (Choose one: ollama or waddleai)
AI_PROVIDER=ollama
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=tinyllama

# Vector Store
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=ai_researcher_memory

# Rate Limiting
RATE_LIMIT_RESEARCH=30
RATE_LIMIT_MEMORY=100

# Security
SERVICE_API_KEY=your-service-key-here
```

#### 3. Run Locally

```bash
hypercorn app:app --bind 0.0.0.0:8070 --workers 4
```

## Common Workflows

### 1. Enable Module for Community

**Endpoint:** `PUT /api/v1/admin/{community_id}/ai-researcher/config`

```bash
curl -X PUT http://localhost:8070/api/v1/admin/123/ai-researcher/config \
  -H "Content-Type: application/json" \
  -d {
    "admin_id": 456,
    "firehose_enabled": true,
    "bot_detection_enabled": true,
    "mem0_enabled": true,
    "research_max_queries": 30
  }
```

Response:
```json
{
  "success": true,
  "message": "Configuration updated"
}
```

### 2. Perform Research Query

**Endpoint:** `POST /api/v1/researcher/research`

```bash
curl -X POST http://localhost:8070/api/v1/researcher/research \
  -H "Content-Type: application/json" \
  -d {
    "community_id": 123,
    "user_id": 456,
    "platform": "discord",
    "query": "What is machine learning?"
  }
```

Response:
```json
{
  "success": true,
  "content": "Machine learning is a subset of artificial intelligence...",
  "tokens_used": 125,
  "processing_time_ms": 1250,
  "was_cached": false
}
```

### 3. Ask Context-Aware Question

**Endpoint:** `POST /api/v1/researcher/ask`

```bash
curl -X POST http://localhost:8070/api/v1/researcher/ask \
  -H "Content-Type: application/json" \
  -d {
    "community_id": 123,
    "user_id": 456,
    "platform": "discord",
    "question": "What were we discussing about Python earlier?"
  }
```

Response:
```json
{
  "success": true,
  "content": "Earlier, you discussed Python decorators and their use cases...",
  "tokens_used": 98,
  "processing_time_ms": 890,
  "was_cached": false
}
```

### 4. Recall Memories from Vector Store

**Endpoint:** `POST /api/v1/researcher/recall`

```bash
curl -X POST http://localhost:8070/api/v1/researcher/recall \
  -H "Content-Type: application/json" \
  -d {
    "community_id": 123,
    "user_id": 456,
    "platform": "discord",
    "query": "meetings discussed"
  }
```

Response:
```json
{
  "success": true,
  "content": "Memory 1: Q1 planning meeting on 2026-02-10\nMemory 2: Team standup on 2026-02-15",
  "tokens_used": 0,
  "processing_time_ms": 150,
  "was_cached": false
}
```

### 5. Get Stored Memories

**Endpoint:** `GET /api/v1/researcher/{community_id}/memory`

```bash
curl http://localhost:8070/api/v1/researcher/123/memory?query=python&limit=5

# Response
{
  "success": true,
  "community_id": 123,
  "memories": [
    {
      "id": "mem_001",
      "text": "Discussion about Python 3.12 features",
      "created_at": "2026-02-10T10:30:00Z",
      "relevance_score": 0.95
    }
  ],
  "count": 1
}
```

### 6. Summarize Recent Activity

**Endpoint:** `POST /api/v1/researcher/summarize`

```bash
curl -X POST http://localhost:8070/api/v1/researcher/summarize \
  -H "Content-Type: application/json" \
  -d {
    "community_id": 123,
    "user_id": 456,
    "platform": "discord",
    "duration_minutes": 120
  }
```

Response:
```json
{
  "success": true,
  "content": "Over the past 2 hours, the community discussed...",
  "tokens_used": 256,
  "processing_time_ms": 2100,
  "was_cached": false
}
```

### 7. Ingest Messages (Firehose)

**Endpoint:** `POST /api/v1/researcher/messages/firehose`

Requires `X-Service-Key` header:

```bash
curl -X POST http://localhost:8070/api/v1/researcher/messages/firehose \
  -H "Content-Type: application/json" \
  -H "X-Service-Key: your-service-api-key" \
  -d {
    "messages": [
      {
        "community_id": 123,
        "user_id": 456,
        "platform": "discord",
        "platform_user_id": "user123",
        "username": "john_doe",
        "message": "Hello everyone!",
        "platform_username": "john_doe",
        "timestamp": "2026-02-16T14:30:00Z",
        "metadata": {
          "channel": "general",
          "message_id": "msg_789"
        }
      }
    ]
  }
```

Response:
```json
{
  "success": true,
  "processed": 1,
  "total": 1
}
```

### 8. Get Conversation Context

**Endpoint:** `GET /api/v1/researcher/{community_id}/context`

```bash
curl http://localhost:8070/api/v1/researcher/123/context?limit=50&since=2026-02-16T10:00:00Z

# Response
{
  "success": true,
  "community_id": 123,
  "messages": [
    {
      "id": 1,
      "platform": "discord",
      "platform_user_id": "user123",
      "platform_username": "john_doe",
      "message_content": "Hello everyone!",
      "message_type": "chat",
      "created_at": "2026-02-16T14:30:00Z"
    }
  ],
  "count": 1
}
```

### 9. Generate Community Insights

**Endpoint:** `POST /api/v1/researcher/{community_id}/insights/generate`

```bash
curl -X POST http://localhost:8070/api/v1/researcher/123/insights/generate \
  -H "Content-Type: application/json" \
  -d {
    "timeframe": "7d",
    "insight_types": ["activity", "trending", "sentiment"]
  }
```

Response:
```json
{
  "success": true,
  "insight_id": "insight_001",
  "content": "This week, activity increased by 45%...",
  "insight_type": "activity",
  "tokens_used": 289,
  "processing_time_ms": 3200
}
```

### 10. Analyze Sentiment

**Endpoint:** `GET /api/v1/researcher/{community_id}/sentiment`

```bash
curl http://localhost:8070/api/v1/researcher/123/sentiment?timeframe=7d

# Response
{
  "success": true,
  "community_id": 123,
  "overall_sentiment": "positive",
  "sentiment_score": 0.78,
  "message_count": 542,
  "sentiment_distribution": {
    "positive": 75,
    "neutral": 20,
    "negative": 5
  },
  "trends": ["increasing_positivity", "discussions_about_features"],
  "processing_time_ms": 1500
}
```

### 11. Get User Behavior Profile

**Endpoint:** `GET /api/v1/researcher/{community_id}/user/{platform}/{user_id}/profile`

```bash
curl http://localhost:8070/api/v1/researcher/123/user/discord/user456/profile?days=90

# Response
{
  "success": true,
  "profile_id": "profile_001",
  "user_id": "user456",
  "activity_level": "high",
  "communication_style": "collaborative",
  "preferred_hours": "18:00-23:00",
  "average_message_length": 156,
  "total_messages": 342,
  "community_role": "moderator",
  "processing_time_ms": 800
}
```

### 12. Detect Bot Activity

**Endpoint:** `GET /api/v1/admin/{community_id}/bot-detection`

```bash
curl http://localhost:8070/api/v1/admin/123/bot-detection?limit=20&threshold=0.7&flagged_only=false

# Response
{
  "success": true,
  "community_id": 123,
  "results": [
    {
      "id": 1,
      "platform": "discord",
      "platform_user_id": "bot_user123",
      "platform_username": "suspicious_account",
      "confidence_score": 0.89,
      "behavioral_patterns": {
        "regular_intervals": true,
        "copy_paste": true,
        "emoji_spam": false
      },
      "account_age_days": 2,
      "recommended_action": "review",
      "is_reviewed": false,
      "created_at": "2026-02-16T10:00:00Z"
    }
  ],
  "count": 1,
  "threshold": 0.7
}
```

## Environment Configuration Reference

| Variable | Default | Example | Purpose |
|----------|---------|---------|---------|
| `MODULE_PORT` | 8070 | 8070 | REST API port |
| `AI_PROVIDER` | ollama | waddleai | AI provider selection |
| `OLLAMA_HOST` | localhost | ollama-service | Ollama server hostname |
| `OLLAMA_PORT` | 11434 | 11434 | Ollama server port |
| `RATE_LIMIT_RESEARCH` | 30 | 50 | Research queries per minute |
| `RATE_LIMIT_MEMORY` | 100 | 200 | Memory operations per minute |
| `VECTOR_SEARCH_LIMIT` | 10 | 20 | Max memory results per query |

## Troubleshooting

### Rate Limiting Errors

If you receive HTTP 429 (Too Many Requests):
- Check rate limit configuration
- Increase `RATE_LIMIT_RESEARCH` or `RATE_LIMIT_MEMORY`
- Check Redis connection for rate limiter

### Memory/Qdrant Connection Issues

```bash
# Test Qdrant connection
curl http://qdrant-host:6333/health

# Check collection
curl http://qdrant-host:6333/collections/ai_researcher_memory
```

### AI Provider Connection Issues

```bash
# Test Ollama connection
curl http://ollama-host:11434/api/tags

# Test WaddleAI connection
curl -H "Authorization: Bearer $WADDLEAI_API_KEY" \
  http://waddleai-host/api/v1/models
```

## Performance Tuning

### Optimize for High Volume

```bash
# Increase concurrency settings
MAX_CONCURRENT_LLM_CALLS=20
LLM_QUEUE_SIZE=200

# Increase database pool
DB_POOL_SIZE=40
DB_MAX_OVERFLOW=80

# Increase batch processing
CONTEXT_BATCH_SIZE=2000
BATCH_WORKER_THREADS=10
```

### Optimize for Low Latency

```bash
# Enable semantic cache
ENABLE_SEMANTIC_CACHE=true
SEMANTIC_CACHE_THRESHOLD=0.85

# Lower vector search limits
VECTOR_SEARCH_LIMIT=5
VECTOR_SCORE_THRESHOLD=0.8

# Use local caching
CACHE_TTL_RESEARCH=1800
CACHE_TTL_CONTEXT=900
```

## Monitoring

### Health Endpoint

```bash
curl http://localhost:8070/healthz
```

### Status Endpoint

```bash
curl http://localhost:8070/api/v1/status
```

### Logs

```bash
# Docker logs
docker logs -f ai-researcher

# Local logs
tail -f /var/log/waddlebotlog/ai_researcher_module.log

# Follow AAA audit logs
tail -f /var/log/waddlebotlog/ai_researcher_module_aaa.log
```

### Metrics

Check response times and tokens used in API responses. All research endpoints include:
- `tokens_used` — LLM token consumption
- `processing_time_ms` — Total request processing time
- `was_cached` — Whether result came from cache

## Support

For issues or questions:
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common problems
- Review [CONFIGURATION.md](CONFIGURATION.md) for environment setup
- Check logs in `/var/log/waddlebotlog/`
- Contact support@penguintech.io for enterprise support
