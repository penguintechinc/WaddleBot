# Interactive Productivity Service

Combined microservice that merges 3 productivity modules into a single Quart application on port 8030.

## Modules Included

1. **Calendar Interaction Module** (port 8030 → `/api/v1/calendar`, `/api/v1/context`, `/api/v1/tournament`)
   - Google Calendar integration with OAuth2
   - Event scheduling and RSVP management
   - Availability checking and group booking
   - Event ticketing system
   - Tournament scheduling

2. **Memories Interaction Module** (port 8030 → `/api/v1/memories`)
   - Community quote management and voting
   - Bookmark collection with metadata fetching
   - Reminder creation and scheduling
   - Category-based search and filtering

3. **Translate Interaction Module** (port 8030 + gRPC 50033 → `/api/v1/translate`)
   - Multi-language translation service
   - Language detection
   - Community-specific translation config
   - Translation caching (LRU + optional Redis)
   - gRPC service on port 50033

## Architecture

```
/app/
  app.py                        # Combined Quart entry point
  config.py                     # Unified configuration
  requirements.txt              # Merged dependencies
  Dockerfile                    # Multi-stage build
  action/
    interactive/
      calendar_interaction_module/     # Calendar service code
      memories_interaction_module/     # Memories service code
      translate_interaction_module/    # Translate service code
      libs/                            # Shared utilities
```

## API Endpoints

### Health & Status
- `GET /healthz` - Liveness probe
- `GET /health` - Health with timestamp
- `GET /api/v1/status` - Unified service status (optional per module)

### Calendar Module
- `GET /api/v1/calendar/<community_id>/events` - List events
- `POST /api/v1/calendar/<community_id>/events` - Create event
- `GET /api/v1/calendar/<community_id>/events/<event_id>` - Get event details
- `PUT /api/v1/calendar/<community_id>/events/<event_id>` - Update event
- `DELETE /api/v1/calendar/<community_id>/events/<event_id>` - Delete event
- `POST /api/v1/calendar/<community_id>/events/<event_id>/rsvp` - RSVP to event
- `GET /api/v1/calendar/<community_id>/availability` - Check user availability
- `POST /api/v1/calendar/<community_id>/availability/group` - Group availability checking
- `POST /api/v1/calendar/<community_id>/booking` - Book available slot
- `GET /api/v1/context/<community_id>` - Get community context
- `POST /api/v1/context/<community_id>` - Update context
- `POST /api/v1/tournament/<tournament_id>/register` - Register for tournament
- `GET /api/v1/tournament/<tournament_id>` - Get tournament details

### Memories Module
- `GET /api/v1/memories/status` - Module health check
- `POST /api/v1/memories/quotes` - Add quote
- `GET /api/v1/memories/quotes/<community_id>` - Search quotes
- `GET /api/v1/memories/quotes/<community_id>/<quote_id>` - Get quote by ID
- `GET /api/v1/memories/quotes/<community_id>/random` - Get random quote
- `POST /api/v1/memories/bookmarks` - Add bookmark
- `GET /api/v1/memories/bookmarks/<community_id>` - Search bookmarks
- `POST /api/v1/memories/reminders` - Create reminder
- `GET /api/v1/memories/reminders/<community_id>` - List reminders for community
- `POST /api/v1/memories/reminders/<reminder_id>/mark-sent` - Mark reminder as sent
- `DELETE /api/v1/memories/quotes/<community_id>/<quote_id>` - Delete quote
- `DELETE /api/v1/memories/bookmarks/<community_id>/<bookmark_id>` - Delete bookmark

### Translate Module
- `POST /api/v1/translate` - Translate text to target language
- `POST /api/v1/translate/detect` - Detect language of text
- `GET /api/v1/translate/cache/stats` - Get cache statistics
- `POST /api/v1/translate/cache/cleanup` - Clean up expired cache entries

## Environment Variables

```bash
# Service (Calendar Module)
MODULE_NAME=interactive-productivity
MODULE_VERSION=2.0.0
MODULE_PORT=8030
MODULE_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Security
SERVICE_API_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256

# Google Calendar Integration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-secret
GOOGLE_CALENDAR_API_KEY=your-calendar-api-key
GOOGLE_REDIRECT_URI=https://your-domain/api/v1/calendar/oauth/callback

# Translation Service
TRANSLATION_API_KEY=your-translation-api-key
SUPPORTED_LANGUAGES=en,es,fr,de,ja,zh
DEFAULT_LANGUAGE=en

# Cache (Translate Module)
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# gRPC (Translate Module)
GRPC_PORT=50033

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/interactive-productivity
```

## Building

### Local Build
```bash
docker build -t interactive-productivity:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8030:8030 \
  -p 50033:50033 \
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot \
  -e SERVICE_API_KEY=secret-key \
  -e JWT_SECRET_KEY=jwt-secret \
  -e GOOGLE_CLIENT_ID=your-google-id \
  -e GOOGLE_CLIENT_SECRET=your-google-secret \
  -e TRANSLATION_API_KEY=your-api-key \
  interactive-productivity:latest
```

## Ports

- **8030** - HTTP REST API (all 3 modules)
- **50033** - gRPC service (Translate module only)

## Service Key Authentication

All non-health endpoints may require the `X-Service-Key` header (depending on module configuration):

```bash
curl -H "X-Service-Key: your-secret-key" http://localhost:8030/api/v1/calendar/123/events
```

Health endpoints are exempt:
```bash
curl http://localhost:8030/healthz
curl http://localhost:8030/health
```

## Module-Specific Configuration

### Calendar Module
Requires Google Calendar OAuth2 credentials. Configure via environment variables or config file:
- `GOOGLE_CLIENT_ID` - OAuth2 client ID
- `GOOGLE_CLIENT_SECRET` - OAuth2 client secret
- `GOOGLE_CALENDAR_API_KEY` - Calendar API key
- `GOOGLE_REDIRECT_URI` - OAuth callback URL

OAuth callback endpoint: `GET /api/v1/calendar/oauth/callback`

### Memories Module
Standalone module - no external API requirements. All data stored in PostgreSQL.

### Translate Module
Requires translation service API key and optional Redis for caching:
- `TRANSLATION_API_KEY` - API key for translation provider
- `REDIS_URL` - Optional Redis URL for distributed caching
- `SUPPORTED_LANGUAGES` - Comma-separated list of supported language codes
- `DEFAULT_LANGUAGE` - Default language for detection fallback

Both LRU (in-memory, max 1000 items) and Redis caching are supported. LRU is always available; Redis is optional.

## Database Schema

The service initializes database tables for all 3 modules:

- **Calendar**: events, attendees, tickets, tournament_schedules, availability_slots, bookings
- **Memories**: quotes, bookmarks, reminders, reminder_schedules
- **Translate**: translation_configs, translation_cache, translation_logs

All use penguin-dal with `migrate=False` (schema via Alembic only).

## Logging

Uses structured logging with per-module loggers:
- `calendar_interaction_module` - Calendar events and OAuth flows
- `memories_interaction_module` - Quote/bookmark/reminder operations
- `translate_interaction_module` - Translation requests and cache stats

Log output:
- Stdout (real-time monitoring)
- Rotating file: `/var/log/interactive-productivity/interactive-productivity.log` (default `/tmp/`)

## gRPC Service

The Translate module runs an additional gRPC server on port 50033 for high-performance translation requests from internal services.

**Proto Definition**: `action/interactive/translate_interaction_module/proto/translate_interaction.proto`

**Service**: `TranslateInteractionServicer`

To use gRPC client:
```python
import grpc
from action.interactive.translate_interaction_module.proto import translate_interaction_pb2_grpc

channel = grpc.aio.secure_channel('localhost:50033', grpc.ssl_channel_credentials())
stub = translate_interaction_pb2_grpc.TranslateInteractionStub(channel)
```

## Module Initialization

Modules initialize on application startup in this order:
1. Calendar (required)
2. Memories (required)
3. Translate (optional - if proto files unavailable, service starts without this module)

If a module fails to initialize, the application continues with remaining modules. Check logs for initialization status.

## Caching Strategy

**Translate Module Cache**:
- **LRU (In-Memory)**: Always available, max 1000 items per instance
- **Redis (Distributed)**: Optional, enabled if `REDIS_URL` is set
- **TTL**: Configurable per cache layer, default 3600 seconds

Cache keys: `translate:{community_id}:{text_hash}:{target_lang}`

## Performance Notes

- Calendar event queries benefit from community_id indexing
- Translation results are cached per community and language pair
- Reminder processing is async and event-driven
- gRPC translate service bypasses REST serialization overhead
