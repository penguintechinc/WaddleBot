# Analytics Core Module — Usage Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-16

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Docker Deployment](#docker-deployment)
3. [Health Checks](#health-checks)
4. [Querying Analytics](#querying-analytics)
5. [Event Tracking Workflows](#event-tracking-workflows)
6. [Configuration & Setup](#configuration--setup)
7. [Real-Time Updates](#real-time-updates)
8. [Premium Features](#premium-features)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 14+ database
- Redis 5.0+ (optional but recommended)
- Docker & Docker Compose (for containerized deployment)

### Local Installation

```bash
# Navigate to module directory
cd core/analytics_core_module

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and service URLs

# Run database migrations (if needed)
python -m alembic upgrade head
```

### Starting the Module

**Development Mode (Local):**
```bash
# Single process, debug logging
python app.py

# Output:
# 2026-02-16 10:30:00 - Starting analytics-core on port 8040
```

**Production Mode (Hypercorn):**
```bash
# Multiple workers, optimized settings
hypercorn app:app --bind 0.0.0.0:8040 --workers 4

# Or via Docker
docker-compose -f docker-compose.yml up analytics-core
```

---

## Docker Deployment

### Development Environment

```bash
# Start all services including core-analytics
docker-compose up

# Or just the analytics module
docker-compose up -d core-analytics

# View logs
docker-compose logs -f core-analytics

# Stop the service
docker-compose stop core-analytics
```

### Docker Build

```bash
# Build the analytics-core image
docker build -f core/analytics_core_module/Dockerfile \
  -t waddlebot/analytics-core:latest \
  .

# Or use the makefile
make docker-build service=analytics-core

# Tag for registry
docker tag waddlebot/analytics-core:latest \
  registry.penguintech.io/waddlebot/analytics-core:latest

# Push to registry
docker push registry.penguintech.io/waddlebot/analytics-core:latest
```

### Environment Configuration

Create a `.env` file in the module directory:

```bash
# Module Settings
MODULE_PORT=8040
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/waddlebot
DB_TYPE=postgresql

# Redis (optional)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Service-to-Service URLs
ROUTER_API_URL=http://router:8000/api/v1/router
REPUTATION_API_URL=http://reputation:8021/api/v1/reputation

# Security
SECRET_KEY=your-secret-key-here
SERVICE_API_KEY=service-api-key-here

# Analytics Configuration
DEFAULT_POLLING_INTERVAL=30
DEFAULT_RAW_RETENTION_DAYS=30
DEFAULT_AGGREGATED_RETENTION_DAYS=365
```

---

## Health Checks

### Module Health Endpoint

```bash
# Check module status
curl http://localhost:8040/health

# Response:
{
  "status": "healthy",
  "module": "analytics-core",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:00Z"
}
```

### Database Connectivity

```bash
# Check from app logs
docker-compose logs core-analytics | grep "Database initialized"

# Or test directly
python -c "from config import Config; import psycopg2; \
  psycopg2.connect(Config.DATABASE_URL)"
```

### Redis Connectivity (Optional)

```bash
# If Redis is configured
redis-cli -h redis -p 6379 ping

# From app logs
docker-compose logs core-analytics | grep "Listening for credential refresh"
```

### Complete Health Check Script

```bash
#!/bin/bash
echo "Checking Analytics Core Module Health..."

# 1. API endpoint
echo "1. Testing API endpoint..."
curl -s http://localhost:8040/health | jq .

# 2. Database
echo "2. Testing database..."
curl -s http://localhost:8040/health | grep -q "healthy" && echo "   ✓ Database OK"

# 3. Sample query
echo "3. Testing analytics query (need community_id)..."
curl -s "http://localhost:8040/api/v1/analytics/1/basic" | jq '.data'

echo "Health check complete!"
```

---

## Querying Analytics

### Basic Statistics (Free Tier)

Get fundamental analytics for a community:

```bash
# Get basic stats for community 123
curl "http://localhost:8040/api/v1/analytics/123/basic"

# Response:
{
  "data": {
    "total_chatters": 150,
    "total_stream_time_hours": 2450.5,
    "messages_per_user": {
      "alice": 1250,
      "bob": 890,
      "charlie": 750
    },
    "active_chatters_7d": 85,
    "active_chatters_30d": 120,
    "updated_at": "2026-02-16T10:30:00Z"
  },
  "status": "success"
}
```

**Use Cases:**
- Dashboard primary metrics display
- Community overview cards
- Quick health assessment
- Historical baseline tracking

### Time-Series Metrics

Query aggregated metrics with configurable time windows:

```bash
# Last 30 days, daily buckets
curl "http://localhost:8040/api/v1/analytics/123/metrics?metric_type=messages&bucket_size=1d"

# Custom date range, hourly buckets
curl "http://localhost:8040/api/v1/analytics/123/metrics?metric_type=messages&bucket_size=1h&start_date=2026-02-10&end_date=2026-02-16"

# Weekly buckets, last 3 months
curl "http://localhost:8040/api/v1/analytics/123/metrics?metric_type=engagement&bucket_size=1w&start_date=2025-11-16"

# Response:
{
  "data": {
    "community_id": 123,
    "metric_type": "messages",
    "bucket_size": "1d",
    "start_date": "2026-01-17T00:00:00Z",
    "end_date": "2026-02-16T23:59:59Z",
    "data": [
      {
        "timestamp": "2026-01-17T00:00:00Z",
        "value": 2500.0,
        "metadata": {"peak_hour": "19:00", "avg_msg_length": 45}
      },
      {
        "timestamp": "2026-01-18T00:00:00Z",
        "value": 2150.0,
        "metadata": {"peak_hour": "20:00", "avg_msg_length": 42}
      }
    ],
    "count": 31
  },
  "status": "success"
}
```

**Supported Metrics:**
- `messages` - Message count per bucket
- `viewers` - Unique viewer count
- `engagement` - Engagement score
- `growth` - User growth rate

**Bucket Sizes:**
- `1h` - Hourly (1 hour intervals)
- `1d` - Daily (24 hour intervals)
- `1w` - Weekly (7 day intervals)
- `1m` - Monthly (30 day intervals)

### Configuration Management

Get current analytics configuration:

```bash
# Get config for community
curl "http://localhost:8040/api/v1/analytics/123/config"

# Response:
{
  "data": {
    "community_id": 123,
    "is_premium": true,
    "basic_stats_enabled": true,
    "community_health_enabled": true,
    "bad_actor_detection_enabled": true,
    "user_journey_enabled": true,
    "polling_interval_seconds": 30
  },
  "status": "success"
}
```

Update analytics configuration:

```bash
# Enable premium features
curl -X PUT "http://localhost:8040/api/v1/analytics/123/config" \
  -H "Content-Type: application/json" \
  -d '{
    "is_premium": true,
    "community_health_enabled": true,
    "bad_actor_detection_enabled": true,
    "polling_interval_seconds": 15
  }'

# Response:
{
  "data": {
    "community_id": 123,
    "is_premium": true,
    "basic_stats_enabled": true,
    "community_health_enabled": true,
    "bad_actor_detection_enabled": true,
    "user_journey_enabled": true,
    "polling_interval_seconds": 15
  },
  "status": "success"
}
```

---

## Event Tracking Workflows

### Sending Activity Events

Events are typically sent by the Router module via the internal API:

```bash
# Send multiple events from router
curl -X POST "http://analytics-core:8040/api/v1/internal/events" \
  -H "Content-Type: application/json" \
  -H "X-Service-API-Key: your-service-key" \
  -d '{
    "community_id": 123,
    "events": [
      {
        "event_type": "message",
        "platform": "discord",
        "platform_user_id": "discord123",
        "timestamp": "2026-02-16T10:30:00Z",
        "metadata": {
          "channel_id": "chan123",
          "message_length": 150,
          "has_media": false
        }
      },
      {
        "event_type": "viewer_join",
        "platform": "twitch",
        "platform_user_id": "twitch456",
        "timestamp": "2026-02-16T10:35:00Z",
        "metadata": {
          "session_id": "sess789",
          "country": "US"
        }
      },
      {
        "event_type": "viewer_leave",
        "platform": "twitch",
        "platform_user_id": "twitch456",
        "timestamp": "2026-02-16T11:00:00Z",
        "metadata": {
          "session_id": "sess789",
          "duration_seconds": 1500
        }
      }
    ]
  }'

# Response:
{
  "data": {
    "processed": 3,
    "status": "success"
  },
  "status": "success"
}
```

**Event Types:**
- `message` - User sent a message
- `viewer_join` - User joined stream/channel
- `viewer_leave` - User left stream/channel
- `reaction` - User reacted to message
- `moderation` - Moderation action taken

### Triggering Aggregation

Manually trigger metrics aggregation:

```bash
# Aggregate all communities
curl -X POST "http://analytics-core:8040/api/v1/internal/aggregate" \
  -H "Content-Type: application/json" \
  -H "X-Service-API-Key: your-service-key" \
  -d '{"force": false}'

# Aggregate specific community
curl -X POST "http://analytics-core:8040/api/v1/internal/aggregate" \
  -H "Content-Type: application/json" \
  -H "X-Service-API-Key: your-service-key" \
  -d '{
    "community_id": 123,
    "force": true
  }'

# Response:
{
  "data": {
    "status": "queued",
    "community_id": 123
  },
  "status": "success"
}
```

---

## Configuration & Setup

### Database Schema

The module expects these tables to exist:

```sql
-- Configuration
CREATE TABLE IF NOT EXISTS analytics_config (
  community_id INTEGER PRIMARY KEY,
  is_premium BOOLEAN DEFAULT FALSE,
  basic_stats_enabled BOOLEAN DEFAULT TRUE,
  community_health_enabled BOOLEAN DEFAULT FALSE,
  bad_actor_detection_enabled BOOLEAN DEFAULT FALSE,
  user_journey_enabled BOOLEAN DEFAULT FALSE,
  polling_interval_seconds INTEGER DEFAULT 30,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Metrics storage
CREATE TABLE IF NOT EXISTS analytics_metrics_timeseries (
  id BIGSERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  metric_type VARCHAR(50) NOT NULL,
  metric_subtype VARCHAR(50),
  timestamp_bucket TIMESTAMP NOT NULL,
  bucket_size VARCHAR(10) NOT NULL,
  value NUMERIC NOT NULL,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE (community_id, metric_type, metric_subtype, timestamp_bucket, bucket_size)
);

-- Bot scores
CREATE TABLE IF NOT EXISTS analytics_bot_scores (
  community_id INTEGER PRIMARY KEY,
  overall_score INTEGER NOT NULL,
  grade CHAR(1) NOT NULL,
  size_category VARCHAR(20) NOT NULL,
  component_scores JSONB NOT NULL,
  component_weights JSONB NOT NULL,
  calculated_at TIMESTAMP NOT NULL,
  next_recalculation TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Retention Policies

Configure data retention based on your needs:

```python
# In config.py
DEFAULT_RAW_RETENTION_DAYS = 30        # Keep raw events 30 days
DEFAULT_AGGREGATED_RETENTION_DAYS = 365 # Keep aggregated data 1 year
```

For databases, set up archival or deletion jobs:

```sql
-- Archive raw events older than 30 days (monthly)
DELETE FROM activity_message_events
WHERE created_at < NOW() - INTERVAL '30 days';

-- Aggregate retention is automatic in queries
```

---

## Real-Time Updates

### REST Polling

For real-time client updates without WebSocket:

```bash
# Poll for updates since last check
curl "http://localhost:8040/api/v1/analytics/123/poll?since=2026-02-16T10:00:00Z"

# Response:
{
  "data": {
    "new_messages": 150,
    "new_viewers": 25,
    "updates_since": "2026-02-16T10:00:00Z",
    "timestamp": "2026-02-16T10:30:00Z"
  },
  "status": "success"
}
```

**Client Polling Pattern:**

```javascript
// JavaScript client
let lastUpdate = new Date().toISOString();

async function pollUpdates(communityId) {
  const response = await fetch(
    `/api/v1/analytics/${communityId}/poll?since=${lastUpdate}`
  );
  const result = await response.json();

  if (result.data) {
    updateDashboard(result.data);
    lastUpdate = result.data.timestamp;
  }
}

// Poll every 30 seconds
setInterval(() => pollUpdates(123), 30000);
```

---

## Premium Features

### Bot Detection & Suspected Bots

Get suspected bots for moderation review (Premium only):

```bash
# Get suspected bots
curl "http://localhost:8040/api/v1/analytics/123/suspected-bots?limit=10&min_confidence=70"

# Response:
{
  "data": {
    "suspected_bots": [
      {
        "community_id": 123,
        "hub_user_id": 456,
        "platform_user_id": "bot_user_1",
        "platform_username": "automation_bot",
        "confidence_score": 92,
        "bot_indicators": {
          "rapid_posting": true,
          "duplicate_messages": true,
          "unusual_timing": false
        },
        "detected_patterns": ["same message 5x in 2 minutes", "100+ messages/hour"],
        "detected_at": "2026-02-15T15:30:00Z"
      }
    ]
  },
  "status": "success"
}
```

### Bot Score Calculation

Get current bot detection score:

```bash
# Get cached score (or recalculate if stale)
curl "http://localhost:8040/api/v1/analytics/123/bot-score"

# Response:
{
  "data": {
    "community_id": 123,
    "overall_score": 85,
    "grade": "B",
    "size_category": "medium",
    "component_scores": {
      "bad_actor_score": 90,
      "reputation_score": 80,
      "security_score": 88,
      "ai_behavioral_score": 82
    },
    "component_weights": {
      "bad_actor": 0.30,
      "reputation": 0.25,
      "security": 0.20,
      "ai_behavioral": 0.25
    },
    "calculated_at": "2026-02-16T09:00:00Z",
    "next_recalculation": "2026-02-17T09:00:00Z"
  },
  "status": "success"
}
```

Force recalculation:

```bash
# Recalculate score immediately
curl -X POST "http://localhost:8040/api/v1/analytics/123/bot-score/calculate"

# Response:
{
  "data": {
    "community_id": 123,
    "overall_score": 85,
    "grade": "B",
    ...
  },
  "status": "success"
}
```

### Review Bot Detection

Mark suspected bots as false positives or confirmed:

```bash
# Mark as false positive
curl -X PUT "http://localhost:8040/api/v1/analytics/123/suspected-bots/456/review" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: moderator_id" \
  -d '{
    "is_false_positive": true
  }'

# Response:
{
  "data": {
    "community_id": 123,
    "hub_user_id": 456,
    "is_false_positive": true,
    "reviewed_by": "moderator_id",
    "reviewed_at": "2026-02-16T10:30:00Z"
  },
  "status": "success"
}
```

---

## Troubleshooting

### Module Won't Start

**Symptoms:** Port already in use or connection errors

**Solutions:**
```bash
# Check if port is in use
lsof -i :8040

# Kill process on port
kill -9 <PID>

# Try different port
MODULE_PORT=8041 python app.py
```

### Database Connection Errors

**Symptoms:** "Failed to connect to database"

**Solutions:**
```bash
# Check DATABASE_URL format
echo $DATABASE_URL

# Test connection directly
psql $DATABASE_URL -c "SELECT 1;"

# Verify tables exist
psql $DATABASE_URL -c "\dt analytics_*"
```

### No Metrics in Query Results

**Check:** Are events being sent? Are aggregations running?

```bash
# Check event count in database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM activity_message_events WHERE community_id = 123;"

# Check aggregation results
psql $DATABASE_URL -c "SELECT * FROM analytics_metrics_timeseries WHERE community_id = 123 LIMIT 5;"

# Check last aggregation time
psql $DATABASE_URL -c "SELECT MAX(timestamp_bucket) FROM analytics_metrics_timeseries WHERE community_id = 123;"
```

### High Query Latency

**Solutions:**
1. Enable Redis caching
2. Add database indexes on community_id and timestamp fields
3. Reduce time window for queries
4. Check database query performance

---

## Next Steps

- Read [API.md](API.md) for complete endpoint reference
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- Read [CONFIGURATION.md](CONFIGURATION.md) for all settings
- Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed debugging

---

**Last Updated:** 2026-02-16
**Maintained By:** Penguin Tech Inc
