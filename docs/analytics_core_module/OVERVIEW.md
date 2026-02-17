# Analytics Core Module — Overview

**Version:** 1.0.0
**Module Name:** analytics-core
**Port:** 8040 (REST API), 50040 (gRPC - reserved)
**Language:** Python 3.13+
**Framework:** Quart (async Python web framework)
**Company:** Penguin Tech Inc

---

## Purpose

The Analytics Core Module provides comprehensive analytics and metrics collection for Waddles communities. It tracks community health, user engagement, message activity, and bot detection across all connected platforms (Discord, Slack, Twitch, YouTube).

The module operates as both a data collection pipeline and an analytics query engine, processing activity events in real-time and aggregating them into time-series metrics for historical analysis and community health scoring.

---

## Core Capabilities

### Free Tier Analytics
- **Basic Statistics**: Total chatters, stream time tracking, messages per user
- **Active User Counts**: 7-day and 30-day active user metrics
- **Event Processing**: Real-time activity event ingestion from platform modules
- **Health Checks**: Module status and dependency verification

### Premium Features
- **Community Health Scoring**: Composite health grades (A+ through F)
- **Bot Detection**: Suspected bot identification with confidence scoring
- **Bad Actor Detection**: Flagged user identification and pattern analysis
- **User Journey Tracking**: Cross-session user behavior analysis
- **Retention Cohorts**: Cohort analysis and retention trends
- **Engagement Funnels**: Funnel analytics and conversion tracking

### Technical Capabilities
- **Time-Series Metrics**: Configurable bucket sizes (1h, 1d, 1w, 1m)
- **Aggregation Pipeline**: Automatic and manual event aggregation
- **Configuration Management**: Per-community analytics settings
- **REST Polling**: Real-time update polling for client applications
- **Service-to-Service Communication**: gRPC and internal API endpoints

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│   Analytics Core Module (Port 8040)     │
├─────────────────────────────────────────┤
│                                         │
│  ┌─ Event Ingestion Pipeline ────────┐ │
│  │ • Receive events from Router      │ │
│  │ • Parse platform-specific formats │ │
│  │ • Store in activity_* tables      │ │
│  └────────────────────────────────────┘ │
│                                         │
│  ┌─ Aggregation Engine ──────────────┐ │
│  │ • Process raw event data          │ │
│  │ • Calculate time-series metrics   │ │
│  │ • Update analytics_metrics table  │ │
│  └────────────────────────────────────┘ │
│                                         │
│  ┌─ Query Engine ────────────────────┐ │
│  │ • Basic stats queries             │ │
│  │ • Time-series metric retrieval    │ │
│  │ • Configuration management        │ │
│  └────────────────────────────────────┘ │
│                                         │
│  ┌─ Bot Score Service ───────────────┐ │
│  │ • Calculate bot detection scores  │ │
│  │ • Track suspected bots            │ │
│  │ • Weighted scoring formula        │ │
│  └────────────────────────────────────┘ │
│                                         │
│  Database: PostgreSQL                  │
│  Cache: Redis (optional)                │
│                                         │
└─────────────────────────────────────────┘
```

---

## Data Flow

### Event Ingestion
1. Router module sends activity events via `/api/v1/internal/events` endpoint
2. Events include message, viewer join/leave, and custom platform events
3. Events stored in activity_message_events, activity_watch_sessions tables
4. Events are timestamped with creation timestamp

### Aggregation
1. Manual trigger via `/api/v1/internal/aggregate` endpoint or scheduled jobs
2. Raw events aggregated into time-series buckets
3. Metrics calculated and stored in analytics_metrics_timeseries
4. Time bucket sizes: 1 hour, 1 day, 1 week, 1 month

### Bot Detection
1. BotScoreService calculates 4 component scores:
   - Bad Actor Score (30% weight): flagged user percentage
   - Reputation Score (25% weight): community health metrics
   - Security Score (20% weight): content filter violations
   - AI Behavioral Score (25% weight): pattern anomalies
2. Components combined into 0-100 overall score
3. Score cached for 24 hours, then recalculated

### Query/Reporting
1. Clients query analytics via REST endpoints with community_id
2. Premium status determines available features
3. Time-series queries support custom date ranges and bucket sizes
4. Results cached in Redis when available

---

## Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| [USAGE.md](USAGE.md) | Getting started, Docker setup, querying | Developers, Operators |
| [API.md](API.md) | Complete endpoint reference, schemas | Integration Engineers |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flows, components | Architects, Maintainers |
| [CONFIGURATION.md](CONFIGURATION.md) | Environment variables, settings | Operations, DevOps |
| [TESTING.md](TESTING.md) | Test fixtures, running tests | QA, Developers |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues, debugging | Support, Operations |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history, changes | All |

---

## Quick Reference

### Starting the Module (Docker)
```bash
docker-compose -f docker-compose.dev.yml up analytics-core
```

### Health Check
```bash
curl http://localhost:8040/health
```

### Getting Basic Stats
```bash
curl http://localhost:8040/api/v1/analytics/123/basic
```

### Getting Time-Series Metrics
```bash
curl "http://localhost:8040/api/v1/analytics/123/metrics?metric_type=messages&bucket_size=1d&start_date=2026-02-01&end_date=2026-02-16"
```

### Getting Bot Score
```bash
curl http://localhost:8040/api/v1/analytics/123/bot-score
```

### Calculating Bot Score
```bash
curl -X POST http://localhost:8040/api/v1/analytics/123/bot-score/calculate
```

### Sending Events (Service-to-Service)
```bash
curl -X POST http://localhost:8040/api/v1/internal/events \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "events": [
      {
        "event_type": "message",
        "platform": "discord",
        "platform_user_id": "user123",
        "timestamp": "2026-02-16T10:30:00Z",
        "metadata": {"channel_id": "chan123"}
      }
    ]
  }'
```

---

## Technology Stack

- **Framework**: Quart 0.19+ (async Python)
- **Server**: Hypercorn 0.16+ (ASGI server)
- **Database**: PostgreSQL (PyDAL abstraction)
- **Cache**: Redis 5.0+
- **HTTP Client**: httpx 0.27+
- **Date Parsing**: python-dateutil 2.8.2+

---

## Database Dependencies

**Primary Tables:**
- `analytics_config` - Per-community analytics configuration
- `analytics_metrics_timeseries` - Aggregated metrics data
- `analytics_bot_scores` - Cached bot detection scores
- `analytics_suspected_bots` - Suspected bot user list
- `analytics_bad_actor_alerts` - Bad actor flags
- `analytics_community_health` - Community health metrics

**Read From:**
- `activity_message_events` - Message activity data
- `activity_watch_sessions` - Watch session data
- `hub_users` - User information
- `platform_integrations` - Platform credentials

---

## Service Dependencies

- **Router Module** (http://router:8000): Provides activity events via gRPC/REST
- **Reputation Module** (http://reputation:8021): Provides reputation data
- **Database**: PostgreSQL instance
- **Redis**: Optional caching layer (recommended for production)

---

## Security Considerations

- All endpoints require proper authentication (Flask-Security-Too integration)
- Service-to-Service endpoints require SERVICE_API_KEY header
- Bot detection features available only to premium communities
- Moderators can review and override bot detection flags
- Credentials loaded from platform_integrations table with fallback to env vars

---

## Performance Characteristics

- **Event Processing**: Handles thousands of events/second
- **Query Response**: <500ms for typical analytics queries
- **Bot Score Calculation**: 1-5 seconds per community (cached 24h)
- **Aggregation Job**: Scales with event volume and community count
- **Database Connections**: Pooled via PyDAL

---

## Common Use Cases

1. **Dashboard Display**: Query basic stats for UI dashboard
2. **Community Moderation**: Get suspected bots for review
3. **Health Monitoring**: Track community health grade changes
4. **Event Processing**: Ingest activity from platform modules
5. **Historical Analysis**: Query time-series metrics for reports
6. **Automated Triggers**: Use bot score for automated actions

---

## Logging & Observability

The module uses structured logging with AAA (Authentication, Authorization, Audit) patterns:

- **System logs**: Module lifecycle events
- **Audit logs**: Configuration changes, bot reviews, score calculations
- **Error logs**: Exceptions, failed queries, service issues
- **Log Level**: Configurable via LOG_LEVEL env var

---

## Support & Contact

For issues, questions, or feature requests:
- **Email**: support@penguintech.io
- **Status Page**: https://status.penguintech.io
- **Documentation**: See related docs in `/docs/analytics_core_module/`

---

**Last Updated:** 2026-02-16
**Maintained By:** Penguin Tech Inc
