# Memories Interaction Module - Usage Guide

## Getting Started

The Memories Interaction Module provides a REST API for managing quotes, bookmarks, and reminders in communities. This guide covers deployment, health checks, and common workflows.

## Prerequisites

- Docker or Python 3.12+
- PostgreSQL 12+ with required schema
- Network access to module port (default: 8031)
- Optional: Redis for credential refresh notifications

## Docker Deployment

### Basic Docker Run

Start the module as a standalone container:

```bash
docker run -d \
  --name memories-module \
  -e DATABASE_URL="postgresql://waddlebot:password@postgres:5432/waddlebot" \
  -e MODULE_PORT=8031 \
  -e LOG_LEVEL=INFO \
  -p 8031:8031 \
  waddlebot/memories-interaction:latest
```

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  memories-interaction:
    image: waddlebot/memories-interaction:latest
    container_name: memories-interaction-module
    ports:
      - "8031:8031"
    environment:
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      MODULE_PORT: 8031
      LOG_LEVEL: INFO
      CORE_API_URL: http://router-service:8000
      ROUTER_API_URL: http://router-service:8000/api/v1/router
      SECRET_KEY: your-secret-key-here
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - /var/log/waddlebotlog:/var/log/waddlebotlog
    networks:
      - waddlenet
```

## Health Checks

### HTTP Health Endpoint

Check module health and version:

```bash
curl http://localhost:8031/health
```

**Response**:
```json
{
  "status": "healthy",
  "module": "memories_interaction_module",
  "version": "2.0.0",
  "uptime": 3600,
  "timestamp": "2026-02-16T10:00:00Z"
}
```

### Health Check via Docker

```bash
docker exec memories-module curl -f http://localhost:8031/health || exit 1
```

### Liveness Probe (Kubernetes)

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8031
  initialDelaySeconds: 10
  periodSeconds: 10
```

## Common Workflows

### Workflow 1: Create and Search Quotes

1. **Create a quote**:
   ```bash
   curl -X POST http://localhost:8031/api/v1/memories/quotes \
     -H "Content-Type: application/json" \
     -d '{
       "community_id": 1,
       "quote_text": "Innovation distinguishes between a leader and a follower",
       "created_by_username": "alice",
       "created_by_user_id": 101,
       "author_username": "stevejobs",
       "category": "innovation"
     }'
   ```

2. **Search quotes**:
   ```bash
   curl "http://localhost:8031/api/v1/memories/quotes/1?q=innovation&limit=10"
   ```

3. **Get random quote**:
   ```bash
   curl http://localhost:8031/api/v1/memories/quotes/1/random
   ```

4. **Vote on quote** (assuming quote_id=5):
   ```bash
   curl -X POST http://localhost:8031/api/v1/memories/quotes/1/5/vote \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 102,
       "username": "bob",
       "vote_type": "up"
     }'
   ```

### Workflow 2: Manage Bookmarks

1. **Add bookmark** (auto-fetch metadata):
   ```bash
   curl -X POST http://localhost:8031/api/v1/memories/bookmarks \
     -H "Content-Type: application/json" \
     -d '{
       "community_id": 1,
       "url": "https://example.com/guide",
       "created_by_username": "alice",
       "created_by_user_id": 101,
       "tags": ["tutorial", "guide"],
       "auto_fetch_metadata": true
     }'
   ```

2. **Search bookmarks**:
   ```bash
   curl "http://localhost:8031/api/v1/memories/bookmarks/1?q=guide&tags=tutorial&limit=10"
   ```

3. **Get popular bookmarks**:
   ```bash
   curl "http://localhost:8031/api/v1/memories/bookmarks/1/popular?limit=5"
   ```

4. **View bookmark** (increments visit count):
   ```bash
   curl http://localhost:8031/api/v1/memories/bookmarks/1/3
   ```

### Workflow 3: Schedule Reminders

1. **Create one-time reminder** (5 minutes from now):
   ```bash
   curl -X POST http://localhost:8031/api/v1/memories/reminders \
     -H "Content-Type: application/json" \
     -d '{
       "community_id": 1,
       "user_id": 101,
       "username": "alice",
       "reminder_text": "Check the channel announcements",
       "remind_in": "5m",
       "channel": "twitch",
       "platform_channel_id": "twitch_channel_123"
     }'
   ```

2. **Create recurring reminder** (daily):
   ```bash
   curl -X POST http://localhost:8031/api/v1/memories/reminders \
     -H "Content-Type: application/json" \
     -d '{
       "community_id": 1,
       "user_id": 101,
       "username": "alice",
       "reminder_text": "Daily standup",
       "remind_in": "2026-02-16T10:00:00Z",
       "recurring_rule": "FREQ=DAILY;INTERVAL=1;BYDAY=MO,TU,WE,TH,FR",
       "channel": "discord",
       "platform_channel_id": "discord_channel_456"
     }'
   ```

3. **Get pending reminders** (for reminder processor):
   ```bash
   curl http://localhost:8031/api/v1/memories/reminders/pending
   ```

4. **Mark reminder as sent**:
   ```bash
   curl -X POST http://localhost:8031/api/v1/memories/reminders/5/sent \
     -H "Content-Type: application/json" \
     -d '{"schedule_next": true}'
   ```

5. **Get user reminders**:
   ```bash
   curl "http://localhost:8031/api/v1/memories/reminders/1/user/101?include_sent=false"
   ```

## Authentication

Certain endpoints require authentication (deletion, mark-sent operations):

```bash
curl -X DELETE http://localhost:8031/api/v1/memories/quotes/1/5 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"user_id": 101}'
```

## Pagination

All search endpoints support pagination:

```bash
# First 50 results
curl "http://localhost:8031/api/v1/memories/quotes/1?limit=50&offset=0"

# Next 50 results
curl "http://localhost:8031/api/v1/memories/quotes/1?limit=50&offset=50"
```

## Statistics

Get module-wide statistics:

```bash
# Quote statistics
curl http://localhost:8031/api/v1/memories/quotes/1/stats

# Bookmark statistics
curl http://localhost:8031/api/v1/memories/bookmarks/1/stats

# Reminder statistics
curl http://localhost:8031/api/v1/memories/reminders/1/stats
```

## Monitoring

### Log Monitoring

View container logs:

```bash
docker logs -f memories-module
```

Monitor specific log level:

```bash
docker logs memories-module | grep ERROR
```

### Performance Monitoring

Check module status:

```bash
curl http://localhost:8031/metrics
```

## Troubleshooting Quick Links

- Database connection issues → See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- API errors → See [API.md](API.md) for error codes
- Configuration problems → See [CONFIGURATION.md](CONFIGURATION.md)

---

**Last Updated**: February 16, 2026  
**Module Version**: 2.0.0
