# Core Data Service

Combined microservice that merges 4 core WaddleBot modules into a single Quart application on port 8040.

## Modules Included

1. **Analytics Core Module** (port 8040 → `/api/v1/analytics`)
   - Community health metrics
   - Engagement analytics
   - Bot detection scoring
   - Time-series metrics aggregation

2. **Engagement Module** (port 8040 → `/api/v1`)
   - Community polls
   - Forms management
   - Visibility-based access control

3. **Reputation Module** (port 8040 → `/api/v1`, `/api/v1/admin`)
   - FICO-style reputation scoring (300-850)
   - User reputation tracking
   - Auto-ban policies
   - gRPC service on port 50051

4. **Labels Core Module** (port 8040 → `/api/v1`)
   - Universal label management
   - Support for any entity type (user, community, item, etc.)
   - Label search and filtering

## Architecture

```
/app/
  app.py                        # Combined Quart entry point
  config.py                     # Unified configuration
  requirements.txt              # Merged dependencies
  Dockerfile                    # Multi-stage build
  core/
    analytics_core_module/      # Analytics service code
    engagement_module/          # Engagement service code
    reputation_module/          # Reputation service code
    labels_core_module/         # Labels service code
  libs/                         # Shared Flask/Quart utilities
```

## API Endpoints

### Health & Status
- `GET /healthz` - Liveness probe
- `GET /health` - Health with timestamp
- `GET /api/v1/status` - Unified service status

### Analytics
- `GET /api/v1/analytics/<community_id>/basic` - Basic stats
- `GET /api/v1/analytics/<community_id>/metrics` - Time-series metrics
- `GET /api/v1/analytics/<community_id>/bot-score` - Bot detection score
- `POST /api/v1/internal/events` - Receive aggregation events

### Engagement
- `POST /api/v1/polls` - Create poll
- `GET /api/v1/polls/<poll_id>` - Get poll
- `POST /api/v1/polls/<poll_id>/vote` - Vote on poll
- `POST /api/v1/forms` - Create form
- `GET /api/v1/forms/<form_id>` - Get form
- `POST /api/v1/forms/<form_id>/submit` - Submit form response

### Reputation
- `GET /api/v1/reputation/<community_id>/user/<user_id>` - Get user reputation
- `POST /api/v1/internal/events` - Process reputation events
- `PUT /api/v1/admin/<community_id>/reputation/<user_id>` - Set reputation (admin)
- `GET /api/v1/admin/<community_id>/reputation/at-risk` - At-risk users

### Labels
- `GET /api/v1/labels` - List all labels
- `POST /api/v1/labels` - Create label
- `POST /api/v1/labels/apply` - Apply label to entity
- `POST /api/v1/labels/search` - Search entities by labels

## Environment Variables

```bash
# Service
MODULE_NAME=core-data
MODULE_VERSION=0.0.1
MODULE_PORT=8040
MODULE_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Security
SERVICE_API_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256

# gRPC (Reputation)
GRPC_PORT=50051

# Logging
LOG_LEVEL=INFO

# Analytics
ANALYTICS_POLLING_INTERVAL=300

# Reputation Tiers
REPUTATION_MIN=300
REPUTATION_MAX=850
REPUTATION_DEFAULT=600
```

## Building

### Local Build
```bash
docker build -t core-data:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8040:8040 \
  -p 50051:50051 \
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot \
  -e SERVICE_API_KEY=secret-key \
  -e JWT_SECRET_KEY=jwt-secret \
  core-data:latest
```

## Ports

- **8040** - HTTP REST API (all 4 modules)
- **50051** - gRPC service (Reputation module only)

## Service Key Authentication

All non-health endpoints require the `X-Service-Key` header:

```bash
curl -H "X-Service-Key: your-secret-key" http://localhost:8040/api/v1/status
```

Health endpoints are exempt:
```bash
curl http://localhost:8040/healthz
curl http://localhost:8040/health
```

## Database Schema

The service initializes database tables for all 4 modules:

- Analytics: events, metrics, aggregations
- Engagement: polls, forms, votes, submissions
- Reputation: reputation_scores, events, weights, policies
- Labels: labels, entity_labels

All use penguin-dal with `migrate=False` (schema via Alembic only).

## Logging

Uses `flask_core.setup_aaa_logging()` with structured JSON logging:
- All startup/shutdown events logged
- Service key violations logged
- Per-module initialization status tracked
