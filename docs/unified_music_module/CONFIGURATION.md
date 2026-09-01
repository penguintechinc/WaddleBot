# Unified Music Module Configuration Guide

**Module**: `unified_music_module`
**Version**: 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [Environment Variables](#environment-variables)
3. [Provider Configuration](#provider-configuration)
4. [Queue Configuration](#queue-configuration)
5. [Radio Configuration](#radio-configuration)
6. [Browser Source Configuration](#browser-source-configuration)
7. [Docker Configuration](#docker-configuration)
8. [Redis Configuration](#redis-configuration)
9. [Advanced Configuration](#advanced-configuration)
10. [Configuration Examples](#configuration-examples)

---

## Overview

The Unified Music Module requires configuration for:
- Music provider authentication (Spotify, YouTube, SoundCloud)
- Redis connection for queue persistence
- Browser source integration for overlays
- Radio station providers
- Service-level settings

---

## Environment Variables

### Core Service Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `MUSIC_MODULE_PORT` | integer | No | `8051` | HTTP server port |
| `MUSIC_MODULE_HOST` | string | No | `0.0.0.0` | HTTP server bind address |
| `LOG_LEVEL` | string | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ENVIRONMENT` | string | No | `production` | Environment (`development`, `production`) |

### Redis Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `REDIS_URL` | string | Yes | - | Redis connection URL |
| `REDIS_QUEUE_NAMESPACE` | string | No | `music_queue` | Namespace prefix for queue keys |
| `REDIS_QUEUE_TTL` | integer | No | `86400` | Queue item TTL in seconds (24 hours) |

**Redis URL Format**:
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_URL=redis://:password@localhost:6379/0
```

### Browser Source Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `BROWSER_SOURCE_URL` | string | No | `http://browser-source:8050` | Browser source API URL |
| `BROWSER_SOURCE_TIMEOUT` | float | No | `10.0` | HTTP request timeout (seconds) |

---

## Provider Configuration

### Spotify Configuration

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `SPOTIFY_CLIENT_ID` | string | Yes | Spotify application client ID |
| `SPOTIFY_CLIENT_SECRET` | string | Yes | Spotify application client secret |
| `SPOTIFY_REDIRECT_URI` | string | Yes | OAuth2 redirect URI |

**Getting Spotify Credentials**:

1. Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Copy Client ID and Client Secret
4. Add redirect URI to app settings

**Example**:
```bash
export SPOTIFY_CLIENT_ID="abc123def456ghi789"
export SPOTIFY_CLIENT_SECRET="xyz987wvu654tsr321"
export SPOTIFY_REDIRECT_URI="http://localhost:8888/callback"
```

**Required Scopes**:
- `user-read-playback-state`
- `user-modify-playback-state`
- `user-read-currently-playing`
- `playlist-read-private`
- `playlist-read-collaborative`
- `user-library-read`

---

### YouTube Configuration

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `YOUTUBE_API_KEY` | string | Yes | YouTube Data API v3 key |
| `YOUTUBE_CLIENT_ID` | string | No | OAuth2 client ID (future use) |
| `YOUTUBE_CLIENT_SECRET` | string | No | OAuth2 client secret (future use) |

**Getting YouTube API Key**:

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create API credentials (API Key)
5. Restrict key to YouTube Data API v3

**Example**:
```bash
export YOUTUBE_API_KEY="This15TotallyAnExampleKey!NotReal"
```

**API Limits**:
- Default quota: 10,000 units/day
- Search costs: 100 units per request
- Video details: 1 unit per request

---

### SoundCloud Configuration

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `SOUNDCLOUD_CLIENT_ID` | string | Yes | SoundCloud application client ID |
| `SOUNDCLOUD_CLIENT_SECRET` | string | Yes | SoundCloud application client secret |
| `SOUNDCLOUD_REDIRECT_URI` | string | Yes | OAuth2 redirect URI |

**Getting SoundCloud Credentials**:

1. Register app at [SoundCloud Developers](https://developers.soundcloud.com/)
2. Create new application
3. Copy credentials
4. Configure redirect URI

**Example**:
```bash
export SOUNDCLOUD_CLIENT_ID="sc_client_123456"
export SOUNDCLOUD_CLIENT_SECRET="sc_secret_abcdef"
export SOUNDCLOUD_REDIRECT_URI="http://localhost:8888/callback"
```

**Required Scopes**:
- `non-expiring` (for persistent tokens)

---

## Queue Configuration

### UnifiedQueue Settings

Configuration is primarily done via Redis environment variables and constructor parameters:

```python
from services.unified_queue import UnifiedQueue

queue = UnifiedQueue(
    redis_url=os.getenv("REDIS_URL"),
    namespace="music_queue",
    queue_ttl=86400,  # 24 hours
    enable_fallback=True  # Use in-memory if Redis unavailable
)
```

### Queue Behavior

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `namespace` | string | `music_queue` | Redis key namespace |
| `queue_ttl` | integer | `86400` | Item TTL in seconds |
| `enable_fallback` | boolean | `True` | Enable in-memory fallback |

**Queue Limits**:
- No hard limit on queue size
- Vote range: unlimited (can be negative)
- Position: 0-indexed, auto-managed

---

## Radio Configuration

### Radio Station Providers

Radio stations are configured per-community in the database (`music_provider_config` table).

**Supported Providers**:
| Provider | Type | Requires API Key | Metadata Support |
|----------|------|------------------|------------------|
| `icecast` | Generic stream | No | Via stream metadata |
| `pretzel` | Licensed music | Yes | API-based |
| `epidemic` | Licensed music | Yes | API-based |
| `streambeats` | Licensed music | Yes | API-based |
| `monstercat` | Licensed music | Yes | API-based |

### Icecast Configuration

```json
{
  "provider": "icecast",
  "name": "My Radio Station",
  "stream_url": "https://stream.example.com/radio.mp3",
  "metadata_path": null,
  "bitrate": 128,
  "codec": "mp3",
  "custom_headers": {}
}
```

### Pretzel Configuration

```json
{
  "provider": "pretzel",
  "name": "Pretzel Lofi",
  "stream_url": "https://stream.pretzel.rocks/lofi",
  "api_endpoint": "https://api.pretzel.rocks/v1",
  "api_key": "your_pretzel_api_key",
  "bitrate": 128,
  "codec": "aac"
}
```

### Epidemic Sound Configuration

```json
{
  "provider": "epidemic",
  "name": "Epidemic Chill",
  "stream_url": "https://stream.epidemicsound.com/chill",
  "api_key": "your_epidemic_api_key",
  "metadata_path": "stream_id_123",
  "bitrate": 192,
  "codec": "aac"
}
```

### Monstercat Configuration

```json
{
  "provider": "monstercat",
  "name": "Monstercat",
  "stream_url": "https://stream.monstercat.com/radio",
  "api_key": "your_monstercat_api_key",
  "bitrate": 320,
  "codec": "mp3"
}
```

### StreamBeats Configuration

```json
{
  "provider": "streambeats",
  "name": "StreamBeats Lofi",
  "stream_url": "https://stream.streambeats.com/lofi",
  "api_key": "your_streambeats_api_key",
  "bitrate": 128,
  "codec": "aac"
}
```

---

## Browser Source Configuration

### Now-Playing Update Configuration

```bash
# Browser source API endpoint
BROWSER_SOURCE_URL=http://browser-source:8050

# Request timeout for browser source updates
BROWSER_SOURCE_TIMEOUT=10.0
```

### Update Payload Format

The module sends updates to `{BROWSER_SOURCE_URL}/api/v1/internal/now-playing`:

```json
{
  "community_id": 1,
  "type": "now_playing",
  "timestamp": "2025-12-16T12:34:56.789Z",
  "track": {
    "name": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "album_art_url": "https://...",
    "duration_ms": 213000,
    "provider": "spotify"
  }
}
```

---

## Docker Configuration

### Docker Compose Example

```yaml
version: '3.8'

services:
  unified-music-module:
    build: ./core/unified_music_module
    container_name: waddlebot-music
    restart: unless-stopped
    ports:
      - "8051:8051"
    environment:
      # Core settings
      - MUSIC_MODULE_PORT=8051
      - MUSIC_MODULE_HOST=0.0.0.0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production

      # Redis
      - REDIS_URL=redis://redis:6379/2
      - REDIS_QUEUE_NAMESPACE=music_queue
      - REDIS_QUEUE_TTL=86400

      # Spotify
      - SPOTIFY_CLIENT_ID=${SPOTIFY_CLIENT_ID}
      - SPOTIFY_CLIENT_SECRET=${SPOTIFY_CLIENT_SECRET}
      - SPOTIFY_REDIRECT_URI=${SPOTIFY_REDIRECT_URI}

      # YouTube
      - YOUTUBE_API_KEY=${YOUTUBE_API_KEY}

      # SoundCloud
      - SOUNDCLOUD_CLIENT_ID=${SOUNDCLOUD_CLIENT_ID}
      - SOUNDCLOUD_CLIENT_SECRET=${SOUNDCLOUD_CLIENT_SECRET}
      - SOUNDCLOUD_REDIRECT_URI=${SOUNDCLOUD_REDIRECT_URI}

      # Browser source
      - BROWSER_SOURCE_URL=http://browser-source:8050
      - BROWSER_SOURCE_TIMEOUT=10.0

    depends_on:
      - redis
      - browser-source

    networks:
      - waddlebot-network

    volumes:
      - ./logs/music:/app/logs

  redis:
    image: redis:7-alpine
    container_name: waddlebot-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - waddlebot-network

volumes:
  redis-data:

networks:
  waddlebot-network:
    driver: bridge
```

### Dockerfile Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 waddlebot && \
    chown -R waddlebot:waddlebot /app

USER waddlebot

# Expose port
EXPOSE 8051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8051/health')"

# Run application
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8051"]
```

---

## Redis Configuration

### Connection Settings

**Standalone Redis**:
```bash
REDIS_URL=redis://localhost:6379/2
```

**Redis with Authentication**:
```bash
REDIS_URL=redis://:mypassword@localhost:6379/2
```

**Redis Sentinel**:
```bash
REDIS_URL=redis-sentinel://sentinel1:26379,sentinel2:26379/mymaster/2
```

**Redis Cluster**:
```bash
REDIS_URL=redis://node1:6379,node2:6379,node3:6379/2
```

### Redis Key Structure

Queue data is stored with the following key pattern:

```
{namespace}:{community_id}:queue
```

**Examples**:
```
music_queue:1:queue
music_queue:42:queue
music_queue:9999:queue
```

### Redis Data Format

Queue items are stored as JSON arrays:

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "track": {
      "track_id": "4cOdK2GP6pPG3x0fA5CkPo",
      "name": "Never Gonna Give You Up",
      "artist": "Rick Astley",
      "album": "Whenever You Need Somebody",
      "album_art_url": "https://...",
      "duration_ms": 213000,
      "provider": "spotify",
      "uri": "spotify:track:4cOdK2GP6pPG3x0fA5CkPo",
      "metadata": {}
    },
    "requested_by_user_id": "user123",
    "requested_at": "2025-12-16T12:34:56.789Z",
    "votes": 5,
    "position": 0,
    "status": "queued",
    "community_id": 1,
    "voters": ["user123", "user456"]
  }
]
```

---

## Advanced Configuration

### Timeout Settings

```bash
# HTTP client timeout for provider API calls (seconds)
PROVIDER_API_TIMEOUT=30.0

# Browser source update timeout (seconds)
BROWSER_SOURCE_TIMEOUT=10.0

# Redis connection timeout (seconds)
REDIS_CONNECT_TIMEOUT=5.0
REDIS_SOCKET_TIMEOUT=5.0
```

### Retry Configuration

```bash
# Number of retries for provider API calls
PROVIDER_API_RETRIES=3

# Retry backoff multiplier
PROVIDER_API_RETRY_BACKOFF=2.0
```

### Logging Configuration

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log format
LOG_FORMAT=json  # or 'text'

# Log file path (optional)
LOG_FILE=/app/logs/music.log

# Log to stdout
LOG_STDOUT=true
```

### Performance Tuning

```bash
# Maximum concurrent HTTP connections per provider
MAX_CONNECTIONS=100

# Maximum queue items to process per batch
QUEUE_BATCH_SIZE=50

# Metadata cache TTL for radio stations (seconds)
RADIO_METADATA_CACHE_TTL=30
```

---

## Configuration Examples

### Development Environment

**.env.development**:
```bash
# Core
MUSIC_MODULE_PORT=8051
MUSIC_MODULE_HOST=0.0.0.0
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Redis (local)
REDIS_URL=redis://localhost:6379/0
REDIS_QUEUE_TTL=3600  # 1 hour for testing

# Spotify (development app)
SPOTIFY_CLIENT_ID=dev_client_id
SPOTIFY_CLIENT_SECRET=dev_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# YouTube
YOUTUBE_API_KEY=dev_youtube_key

# Browser source (local)
BROWSER_SOURCE_URL=http://localhost:8050
BROWSER_SOURCE_TIMEOUT=5.0

# Logging
LOG_FORMAT=text
LOG_STDOUT=true
```

### Production Environment

**.env.production**:
```bash
# Core
MUSIC_MODULE_PORT=8051
MUSIC_MODULE_HOST=0.0.0.0
LOG_LEVEL=INFO
ENVIRONMENT=production

# Redis (production cluster)
REDIS_URL=redis://:prod_password@redis-cluster:6379/2
REDIS_QUEUE_TTL=86400  # 24 hours

# Spotify (production app)
SPOTIFY_CLIENT_ID=${SPOTIFY_PROD_CLIENT_ID}
SPOTIFY_CLIENT_SECRET=${SPOTIFY_PROD_CLIENT_SECRET}
SPOTIFY_REDIRECT_URI=https://music.waddlebot.com/callback

# YouTube
YOUTUBE_API_KEY=${YOUTUBE_PROD_API_KEY}

# SoundCloud
SOUNDCLOUD_CLIENT_ID=${SOUNDCLOUD_PROD_CLIENT_ID}
SOUNDCLOUD_CLIENT_SECRET=${SOUNDCLOUD_PROD_CLIENT_SECRET}
SOUNDCLOUD_REDIRECT_URI=https://music.waddlebot.com/callback

# Browser source (internal service)
BROWSER_SOURCE_URL=http://browser-source:8050
BROWSER_SOURCE_TIMEOUT=10.0

# Logging
LOG_FORMAT=json
LOG_FILE=/var/log/waddlebot/music.log
LOG_STDOUT=true

# Performance
MAX_CONNECTIONS=200
QUEUE_BATCH_SIZE=100
```

### Minimal Configuration (Testing)

```bash
# Minimum required for basic functionality
REDIS_URL=redis://localhost:6379/0
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

---

## Configuration Validation

### Validation Script

```python
#!/usr/bin/env python3
import os
import sys

def validate_config():
    """Validate required configuration is present."""
    required = [
        'REDIS_URL',
    ]

    # Check optional providers
    providers = []

    if all([
        os.getenv('SPOTIFY_CLIENT_ID'),
        os.getenv('SPOTIFY_CLIENT_SECRET'),
        os.getenv('SPOTIFY_REDIRECT_URI')
    ]):
        providers.append('Spotify')

    if os.getenv('YOUTUBE_API_KEY'):
        providers.append('YouTube')

    if all([
        os.getenv('SOUNDCLOUD_CLIENT_ID'),
        os.getenv('SOUNDCLOUD_CLIENT_SECRET'),
        os.getenv('SOUNDCLOUD_REDIRECT_URI')
    ]):
        providers.append('SoundCloud')

    # Validate required vars
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print(f"ERROR: Missing required variables: {', '.join(missing)}")
        sys.exit(1)

    if not providers:
        print("WARNING: No music providers configured!")
        print("Configure at least one of: Spotify, YouTube, SoundCloud")
        sys.exit(1)

    print("Configuration valid!")
    print(f"Configured providers: {', '.join(providers)}")
    sys.exit(0)

if __name__ == '__main__':
    validate_config()
```

**Usage**:
```bash
python validate_config.py
```

---

**Last Updated**: 2025-12-16
**Configuration Version**: 1.0.0
**Maintainer**: Waddles Development Team
