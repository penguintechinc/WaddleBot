# Interactive Media Service

Combined microservice that merges 3 media interaction modules into a single Quart application on port 8105.

## Modules Included

1. **Clip Interaction Module** (port 8105 → `/api/v1/clips`, `/api/v1/reels`, `/api/v1/overlay`)
   - Twitch clip creation and management
   - Clip bookmarking and tagging
   - Highlights and highlight reels
   - OBS browser source overlay support

2. **Spotify Integration Module** (port 8105 → `/api/v1/spotify`)
   - Spotify status and interaction endpoints
   - Music integration capabilities

3. **YouTube Music Integration Module** (port 8105 → `/api/v1/youtube-music`)
   - YouTube Music status and interaction endpoints
   - Music streaming integration

## Architecture

```
/app/
  app.py                        # Combined Quart entry point
  config.py                     # Unified configuration
  requirements.txt              # Merged dependencies
  Dockerfile                    # Multi-stage build
  clip_interaction_module/      # Clip service code
    services/
      twitch_clip_service.py    # Twitch clip creation
      clip_service.py           # Clip management, bookmarks, reels
  spotify_interaction_module/   # Spotify service code (placeholder)
  youtube_music_interaction/    # YouTube Music service code (placeholder)
  libs/                         # Shared Flask/Quart utilities
```

## API Endpoints

### Health & Status
- `GET /healthz` - Liveness probe
- `GET /health` - Health with timestamp
- `GET /api/v1/status` - Unified service status

### Clip Management
- `POST /api/v1/clips/<community_id>/create` - Create a Twitch clip
- `POST /api/v1/clips/<community_id>/bookmark` - Bookmark a clip
- `GET /api/v1/clips/<community_id>` - List clips (with filtering)
- `PUT /api/v1/clips/<community_id>/<clip_id>/tags` - Update clip tags
- `POST /api/v1/clips/<community_id>/<clip_id>/highlight` - Mark/unmark clip as highlight

### Highlight Reels
- `POST /api/v1/reels/<community_id>` - Create highlight reel
- `GET /api/v1/reels/<community_id>/<reel_id>` - Get reel with clips
- `PUT /api/v1/reels/<community_id>/<reel_id>/publish` - Publish reel

### OBS Overlay
- `GET /api/v1/overlay/<community_id>` - Get overlay data with latest highlights

### Spotify Integration
- `GET /api/v1/spotify/status` - Spotify module status

### YouTube Music Integration
- `GET /api/v1/youtube-music/status` - YouTube Music module status

## Environment Variables

```bash
# Service
MODULE_NAME=interactive-media
MODULE_VERSION=0.0.1
MODULE_PORT=8105
MODULE_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Security
SERVICE_API_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256

# Twitch/Clip Creation
TWITCH_CLIENT_ID=your-twitch-client-id
TWITCH_SECRET=your-twitch-secret
TWITCH_ACCESS_TOKEN=your-twitch-access-token

# Spotify Integration
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_SECRET=your-spotify-secret
SPOTIFY_ACCESS_TOKEN=your-spotify-access-token

# YouTube Music Integration
YOUTUBE_API_KEY=your-youtube-api-key
YOUTUBE_MUSIC_CLIENT_ID=your-youtube-client-id
YOUTUBE_MUSIC_SECRET=your-youtube-secret

# Logging
LOG_LEVEL=INFO

# Clip Configuration
CLIP_MAX_RESULTS=50
CLIP_DEFAULT_DURATION=60
```

## Building

### Local Build
```bash
docker build -t interactive-media:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8105:8105 \
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot \
  -e SERVICE_API_KEY=secret-key \
  -e JWT_SECRET_KEY=jwt-secret \
  -e TWITCH_CLIENT_ID=twitch-id \
  -e TWITCH_SECRET=twitch-secret \
  -e SPOTIFY_CLIENT_ID=spotify-id \
  -e SPOTIFY_SECRET=spotify-secret \
  -e YOUTUBE_API_KEY=youtube-key \
  interactive-media:latest
```

## Ports

- **8105** - HTTP REST API (all 3 modules)

## Service Key Authentication

All non-health endpoints require the `X-Service-Key` header:

```bash
curl -H "X-Service-Key: your-secret-key" http://localhost:8105/api/v1/status
```

Health endpoints are exempt:
```bash
curl http://localhost:8105/healthz
curl http://localhost:8105/health
```

## Database Schema

The service initializes database tables for clip management:

- Clips: clip_id, community_id, clip_url, title, game, tags, bookmarked_by, is_highlight
- Reels: reel_id, community_id, name, description, created_by, published_at
- Reel clips: reel_id, clip_id (many-to-many)

All use PyDAL with `migrate=False` (schema via Alembic only).

## Logging

Uses `flask_core.setup_aaa_logging()` with structured JSON logging:
- All startup/shutdown events logged
- Service key violations logged
- Per-module initialization status tracked
- Audit logging for clip operations (create, bookmark, tag, highlight)
