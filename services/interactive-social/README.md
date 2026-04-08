# Interactive Social Service

Combined microservice that merges 4 interactive modules into a single Quart application on port 8010.

## Modules Included

1. **Alias Interaction Module** (port 8010 → `/api/v1`)
   - Alias/nickname management
   - Command variable substitution
   - Execution via template system

2. **Shoutout Interaction Module** (port 8010 → `/api/v1`)
   - Shoutout generation for Twitch/YouTube users
   - Twitch API integration with circuit breaker
   - Custom template support (platform/live variants)
   - Video shoutout execution (!vso command)
   - History and statistics tracking

3. **Presence Module** (port 8010 → `/api/v1`)
   - Multi-platform user presence tracking (Twitch, YouTube, Discord, etc.)
   - Canonical status aggregation
   - Redis-backed state store
   - User-configurable sync settings

4. **Quote Interaction Module** (port 8010 → `/api/v1`)
   - Quote management and approval workflow
   - Full-text search with pagination
   - Author-based filtering
   - Community-scoped statistics

## Architecture

```
/app/
  app.py                                # Combined Quart entry point
  config.py                             # Unified configuration
  requirements.txt                      # Merged dependencies
  Dockerfile                            # Multi-stage build
  alias_interaction_module/             # Alias service code
  shoutout_interaction_module/          # Shoutout service code
  presence_module/                      # Presence service code
  quote_interaction_module/             # Quote service code
  libs/                                 # Shared Flask/Quart utilities
```

## API Endpoints

### Health & Status
- `GET /healthz` - Liveness probe
- `GET /health` - Health with timestamp
- `GET /api/v1/status` - Unified service status (all 4 modules)

### Aliases
- `GET /api/v1/aliases?community_id=<id>` - List aliases for community
- `POST /api/v1/aliases` - Create alias
- `DELETE /api/v1/aliases/<alias_id>` - Delete alias
- `POST /api/v1/aliases/execute` - Execute alias with variable substitution

### Shoutouts
- `POST /api/v1/shoutout` - Generate shoutout for user
- `GET /api/v1/shoutout/history/<community_id>` - Shoutout history (paginated, requires auth)
- `GET /api/v1/shoutout/stats/<community_id>` - Shoutout statistics (requires auth)
- `POST /api/v1/shoutout/template` - Save custom shoutout template (requires auth)
- `GET /api/v1/shoutout/twitch/user/<username>` - Get Twitch user info (requires auth)
- `GET /api/v1/shoutout/circuit-breaker/metrics` - Circuit breaker metrics (requires auth)
- `POST /api/v1/shoutout/video-shoutout` - Execute video shoutout (!vso command)

### Presence
- `POST /api/v1/presence/update` - Process incoming presence update
- `GET /api/v1/presence/<user_id>` - Get aggregated presence for user
- `GET /api/v1/presence/<user_id>/settings` - Get presence sync settings
- `PUT /api/v1/presence/<user_id>/settings` - Update presence sync settings

### Quotes
- `POST /api/v1/quotes` - Add new quote
- `GET /api/v1/quotes/<quote_id>` - Get specific quote
- `GET /api/v1/quotes/random/<community_id>` - Get random quote from community
- `GET /api/v1/quotes/list/<community_id>` - List quotes with pagination
- `GET /api/v1/quotes/search/<community_id>?q=<query>` - Search quotes (min 3 chars)
- `GET /api/v1/quotes/author/<community_id>?author=<name>` - Get quotes by author
- `PUT /api/v1/quotes/<quote_id>` - Update quote
- `DELETE /api/v1/quotes/<quote_id>` - Delete quote (soft-delete)
- `GET /api/v1/quotes/stats/<community_id>` - Quote statistics

## Environment Variables

```bash
# Service
MODULE_NAME=interactive-social
MODULE_VERSION=1.0.0
MODULE_PORT=8010
MODULE_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10
READ_REPLICA_URL=postgresql://user:pass@replica:5432/waddlebot  # Optional

# Cache (Required for Presence)
REDIS_URL=redis://localhost:6379

# Twitch Integration (Shoutouts)
TWITCH_CLIENT_ID=your-twitch-client-id
TWITCH_CLIENT_SECRET=your-twitch-client-secret

# YouTube Integration (Shoutouts)
YOUTUBE_API_KEY=your-youtube-api-key

# Identity Service (Shoutouts)
IDENTITY_URL=http://identity-service:8000

# Quotes
AUTO_APPROVE_QUOTES=false  # Auto-approve new quotes (default: false)

# Pagination (Quotes)
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=100
MIN_SEARCH_QUERY_LENGTH=3

# Logging
LOG_LEVEL=INFO
```

## Building

### Local Build
```bash
docker build -t interactive-social:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8010:8010 \
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot \
  -e REDIS_URL=redis://localhost:6379 \
  -e TWITCH_CLIENT_ID=your-client-id \
  -e TWITCH_CLIENT_SECRET=your-secret \
  -e YOUTUBE_API_KEY=your-api-key \
  -e IDENTITY_URL=http://identity-service:8000 \
  interactive-social:latest
```

## Ports

- **8010** - HTTP REST API (all 4 modules)

## Authentication

Health endpoints are exempt from authentication:
```bash
curl http://localhost:8010/healthz
curl http://localhost:8010/health
```

Protected endpoints (those marked `@auth_required`) require a valid JWT token in the `Authorization` header:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8010/api/v1/shoutout/history/<community_id>
```

Public endpoints (shoutout creation, presence updates, quote retrieval) do not require authentication but may require specific request body fields (community_id, user_id, etc.).

## Database Schema

The service initializes database tables for all 4 modules:

- Aliases: aliases, alias_executions
- Shoutouts: shoutouts, shoutout_history, shoutout_templates, video_shoutouts
- Presence: user_presence, presence_settings, presence_sync_state
- Quotes: quotes, quote_tags, quote_search_index

All use PyDAL with `migrate=False` (schema via Alembic only).

## Logging

Uses `flask_core.setup_aaa_logging()` with structured JSON logging:
- Startup/shutdown events for each module
- Audit logs for shoutout, presence, and quote operations
- Circuit breaker metrics tracking
- Per-module initialization status

## Service Integration

### Dependencies
- **Database**: PostgreSQL (primary), with optional read replica
- **Cache**: Redis (required for Presence module)
- **External APIs**: Twitch API, YouTube API
- **Internal Services**: Identity service

### Circuit Breaker (Shoutouts)
The Twitch service includes a circuit breaker for resilience:
- Metrics available via `/api/v1/shoutout/circuit-breaker/metrics`
- Prevents cascading failures on external API errors
