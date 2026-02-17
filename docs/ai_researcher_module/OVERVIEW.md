# AI Researcher Module — Overview

**Maintained by:** Penguin Tech Inc
**Language:** Python 3.12
**Port:** 8070 (REST) / 50055 (gRPC, reserved)
**Status:** Production-Ready

## Purpose

The AI Researcher Module provides contextual AI-powered research, conversation analysis, and memory-based knowledge retrieval for WaddleBot communities. It enables users to perform semantic research on topics, ask community-aware questions, recall previous discussions, and analyze sentiment across platforms.

This module integrates with mem0 (vector-based memory via Qdrant) for persistent, semantically-searchable knowledge storage, and supports multiple AI providers (Ollama or WaddleAI) for intelligent processing.

## Core Capabilities

- **Research Queries** (!or/research) — Topic research with optional web context
- **Context-Aware Q&A** (!or/ask) — Answer questions using community conversation history
- **Memory Recall** (!or/recall) — Semantic search through stored memories
- **Summarization** (!or/summarize) — Automatic stream and conversation summaries
- **Insights Generation** — AI-driven analysis of community trends and sentiment
- **Bot Detection** — Identify inauthentic behavior in communities
- **Sentiment Analysis** — Track community mood and emotional patterns
- **User Behavior Profiles** — Profile individual and community interaction patterns
- **Anomaly Detection** — Identify unusual activity patterns
- **Firehose Message Ingestion** — Ingest all community messages for real-time context

## Technical Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | Quart (async) | REST API and async request handling |
| **AI Provider** | Ollama / WaddleAI | Large language models (LLM) |
| **Memory Store** | Qdrant + mem0 | Vector embeddings and semantic search |
| **Caching** | Redis | Session management and result caching |
| **Database** | PostgreSQL | Persistent data storage (via PyDAL) |
| **Language** | Python 3.12 | Implementation |
| **Container** | Docker | Deployment |

## API Endpoints Index

### Public Endpoints (Authenticated)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/status` | Module status and features |
| POST | `/api/v1/researcher/research` | Perform topic research |
| POST | `/api/v1/researcher/ask` | Ask context-aware questions |
| POST | `/api/v1/researcher/recall` | Recall memories by query |
| POST | `/api/v1/researcher/summarize` | Summarize recent activity |
| GET | `/api/v1/researcher/{community_id}/context` | Get conversation context |
| GET | `/api/v1/researcher/{community_id}/memory` | Get stored memories |
| GET | `/api/v1/researcher/{community_id}/insights` | Get generated insights |
| POST | `/api/v1/researcher/{community_id}/insights/generate` | Generate new insights |
| GET | `/api/v1/researcher/{community_id}/sentiment` | Sentiment analysis |
| GET | `/api/v1/researcher/{community_id}/anomalies` | Get detected anomalies |
| POST | `/api/v1/researcher/{community_id}/anomalies/{anomaly_id}/acknowledge` | Mark anomaly as reviewed |
| GET | `/api/v1/researcher/{community_id}/user/{platform}/{user_id}/profile` | User behavior profile |
| GET | `/api/v1/researcher/{community_id}/users/profiles` | All community user profiles |

### Admin Endpoints (Service Key Required)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/researcher/messages/firehose` | Ingest messages for context |
| POST | `/api/v1/researcher/stream/end` | Notify stream end and generate summary |
| GET | `/api/v1/admin/{community_id}/ai-insights` | Get AI insights for community |
| GET | `/api/v1/admin/{community_id}/ai-researcher/config` | Get module configuration |
| PUT | `/api/v1/admin/{community_id}/ai-researcher/config` | Update module configuration |
| GET | `/api/v1/admin/{community_id}/bot-detection` | Get bot detection results |

## Configuration Overview

Key configuration areas:
- **AI Provider Selection** — Choose between Ollama (local) or WaddleAI (cloud proxy)
- **mem0/Qdrant Integration** — Vector store for semantic memory
- **Rate Limiting** — Per-user and global quotas for research and memory operations
- **Caching** — Redis-backed caching with TTL and semantic similarity
- **Batch Processing** — Asynchronous context enrichment and indexing
- **Database** — PostgreSQL connection with connection pooling

## Quick Reference

### Health Check
```bash
curl http://localhost:8070/healthz
```

### Module Status
```bash
curl http://localhost:8070/api/v1/status
```

### Docker Run
```bash
docker run -d \
  --name ai-researcher \
  -p 8070:8070 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/waddlebot" \
  -e REDIS_URL="redis://redis:6379/0" \
  -e AI_PROVIDER="ollama" \
  -e OLLAMA_HOST="ollama" \
  -e OLLAMA_PORT="11434" \
  waddlebot/ai-researcher:latest
```

## Feature Flags

- **BOT_DETECTION_ENABLED** — Enable/disable bot detection analysis
- **FIREHOSE_ENABLED** — Enable/disable message ingestion
- **ENABLE_BATCH_PROCESSING** — Enable/disable batch context processing
- **ENABLE_SEMANTIC_CACHE** — Enable/disable semantic caching

## Documentation Index

| Document | Purpose |
|----------|---------|
| [USAGE.md](USAGE.md) | Getting started, Docker setup, common workflows |
| [API.md](API.md) | Detailed endpoint documentation and request/response formats |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, and component interactions |
| [CONFIGURATION.md](CONFIGURATION.md) | All environment variables and settings |
| [TESTING.md](TESTING.md) | Testing strategy, mock data, sample queries |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common errors and resolution steps |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history and updates |

## Support & Maintenance

- **Issues:** Post in #waddlebot-dev or contact support@penguintech.io
- **Documentation:** See related docs/ folder
- **Version:** Check CONFIG for current version
- **License:** Limited AGPL-3.0 with Penguin Tech modifications
