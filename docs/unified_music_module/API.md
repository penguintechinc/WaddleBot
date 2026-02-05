# Unified Music Module API Documentation

**Module**: `unified_music_module`
**Version**: 1.0.0
**Type**: Core Service Module
**Protocol**: REST API (HTTP/JSON)

---

## Table of Contents

1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [Response Format](#response-format)
5. [Health & Monitoring Endpoints](#health--monitoring-endpoints)
6. [Provider Management Endpoints](#provider-management-endpoints)
7. [Queue Management Endpoints](#queue-management-endpoints)
8. [Playback Control Endpoints](#playback-control-endpoints)
9. [Radio Station Endpoints](#radio-station-endpoints)
10. [Mode Control Endpoints](#mode-control-endpoints)
11. [Error Codes](#error-codes)
12. [Rate Limiting](#rate-limiting)
13. [Webhooks & Events](#webhooks--events)

---

## Overview

The Unified Music Module API provides a unified interface for managing music playback across multiple providers (Spotify, YouTube, SoundCloud) with support for queue-based playback and radio streaming. The API is designed for high-performance async operations and supports per-community isolation.

### Key Features

- **Multi-Provider Support**: Spotify, YouTube, SoundCloud
- **Queue Management**: Vote-based prioritization, Redis-backed persistence
- **Radio Streaming**: Icecast, Pretzel, Epidemic Sound, StreamBeats, Monstercat
- **Mode Control**: Switch between queue-based music and radio streaming
- **Browser Source Integration**: Real-time now-playing updates
- **Community Isolation**: Separate queues and playback state per community

---

## Base URL

```
http://localhost:8051
```

**Environment Variable**: `MUSIC_MODULE_URL`

**Docker Service Name**: `unified-music-module`

---

## Authentication

Currently, the internal API does not require authentication for service-to-service communication. Provider-specific authentication (OAuth2) is handled separately.

### Provider Authentication

| Provider | Auth Type | Required Credentials |
|----------|-----------|---------------------|
| Spotify | OAuth2 | `client_id`, `client_secret`, `redirect_uri` |
| YouTube | API Key | `api_key` |
| SoundCloud | OAuth2 | `client_id`, `client_secret`, `redirect_uri` |

---

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "timestamp": "2025-12-16T12:34:56.789Z"
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  },
  "timestamp": "2025-12-16T12:34:56.789Z"
}
```

---

## Health & Monitoring Endpoints

### GET /health

**Description**: Basic health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "module": "unified_music_module",
  "version": "1.0.0",
  "timestamp": "2025-12-16T12:34:56.789Z"
}
```

**Status Codes**: `200 OK`

---

### GET /healthz

**Description**: Comprehensive health check with provider status

**Response**:
```json
{
  "status": "healthy",
  "checks": {
    "redis": {
      "status": "healthy",
      "latency_ms": 2
    },
    "spotify": {
      "status": "healthy",
      "authenticated": true
    },
    "youtube": {
      "status": "healthy",
      "authenticated": true
    },
    "soundcloud": {
      "status": "degraded",
      "authenticated": false,
      "error": "No API credentials"
    }
  },
  "timestamp": "2025-12-16T12:34:56.789Z"
}
```

**Status Codes**: `200 OK`, `503 Service Unavailable`

---

### GET /metrics

**Description**: Prometheus-compatible metrics endpoint

**Response** (text/plain):
```
# HELP music_queue_length Current queue length per community
# TYPE music_queue_length gauge
music_queue_length{community_id="1",provider="spotify"} 5
music_queue_length{community_id="1",provider="youtube"} 3

# HELP music_tracks_played_total Total tracks played
# TYPE music_tracks_played_total counter
music_tracks_played_total{community_id="1",provider="spotify"} 127

# HELP music_provider_health Provider health status (1=healthy, 0=unhealthy)
# TYPE music_provider_health gauge
music_provider_health{provider="spotify"} 1
music_provider_health{provider="youtube"} 1
music_provider_health{provider="soundcloud"} 0
```

**Status Codes**: `200 OK`

---

### GET /api/v1/status

**Description**: Detailed service status with all components

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "operational",
    "module": "unified_music_module",
    "version": "1.0.0",
    "uptime_seconds": 3600,
    "providers": {
      "spotify": "connected",
      "youtube": "connected",
      "soundcloud": "disconnected"
    },
    "queue": {
      "backend": "redis",
      "connected": true
    },
    "active_communities": 3,
    "total_tracks_queued": 42
  }
}
```

**Status Codes**: `200 OK`

---

## Provider Management Endpoints

### GET /api/v1/providers

**Description**: List all configured music providers

**Response**:
```json
{
  "success": true,
  "data": {
    "providers": [
      {
        "name": "spotify",
        "display_name": "Spotify",
        "status": "connected",
        "authenticated": true,
        "capabilities": ["search", "play", "pause", "queue", "playlists"]
      },
      {
        "name": "youtube",
        "display_name": "YouTube Music",
        "status": "connected",
        "authenticated": true,
        "capabilities": ["search", "play", "pause"]
      },
      {
        "name": "soundcloud",
        "display_name": "SoundCloud",
        "status": "disconnected",
        "authenticated": false,
        "capabilities": ["search", "play", "pause", "queue"]
      }
    ]
  }
}
```

**Status Codes**: `200 OK`

---

### GET /api/v1/providers/{provider}/status

**Description**: Get status of a specific provider

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| provider | string | Provider name (`spotify`, `youtube`, `soundcloud`) |

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "spotify",
    "display_name": "Spotify",
    "status": "connected",
    "authenticated": true,
    "health": "healthy",
    "last_check": "2025-12-16T12:34:56.789Z",
    "capabilities": ["search", "play", "pause", "queue", "playlists"],
    "limits": {
      "search_max_results": 50,
      "queue_max_size": 100
    }
  }
}
```

**Status Codes**: `200 OK`, `404 Not Found`

---

### POST /api/v1/providers/{provider}/search

**Description**: Search for tracks using a specific provider

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| provider | string | Provider name |

**Request Body**:
```json
{
  "query": "never gonna give you up",
  "limit": 10
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "tracks": [
      {
        "track_id": "4cOdK2GP6pPG3x0fA5CkPo",
        "name": "Never Gonna Give You Up",
        "artist": "Rick Astley",
        "album": "Whenever You Need Somebody",
        "album_art_url": "https://i.scdn.co/image/...",
        "duration_ms": 213000,
        "provider": "spotify",
        "uri": "spotify:track:4cOdK2GP6pPG3x0fA5CkPo"
      }
    ],
    "total": 1,
    "provider": "spotify"
  }
}
```

**Status Codes**: `200 OK`, `400 Bad Request`, `404 Not Found`

---

## Queue Management Endpoints

### GET /api/v1/queue/{community_id}

**Description**: Get current queue for a community

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| community_id | integer | Community/channel ID |

**Response**:
```json
{
  "success": true,
  "data": {
    "community_id": 1,
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "track": {
          "track_id": "4cOdK2GP6pPG3x0fA5CkPo",
          "name": "Never Gonna Give You Up",
          "artist": "Rick Astley",
          "album": "Whenever You Need Somebody",
          "album_art_url": "https://i.scdn.co/image/...",
          "duration_ms": 213000,
          "provider": "spotify",
          "uri": "spotify:track:4cOdK2GP6pPG3x0fA5CkPo"
        },
        "requested_by_user_id": "user123",
        "requested_at": "2025-12-16T12:34:56.789Z",
        "votes": 5,
        "position": 0,
        "status": "queued"
      }
    ],
    "total": 1,
    "stats": {
      "queued": 1,
      "playing": 0,
      "played": 15,
      "skipped": 2
    }
  }
}
```

**Status Codes**: `200 OK`

---

### POST /api/v1/queue/{community_id}/add

**Description**: Add a track to the queue

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| community_id | integer | Community/channel ID |

**Request Body**:
```json
{
  "track_url": "https://open.spotify.com/track/4cOdK2GP6pPG3x0fA5CkPo",
  "requested_by_user_id": "user123",
  "provider": "spotify"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "queue_item": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "track": {
        "track_id": "4cOdK2GP6pPG3x0fA5CkPo",
        "name": "Never Gonna Give You Up",
        "artist": "Rick Astley",
        "album": "Whenever You Need Somebody",
        "album_art_url": "https://i.scdn.co/image/...",
        "duration_ms": 213000,
        "provider": "spotify",
        "uri": "spotify:track:4cOdK2GP6pPG3x0fA5CkPo"
      },
      "requested_by_user_id": "user123",
      "requested_at": "2025-12-16T12:34:56.789Z",
      "votes": 0,
      "position": 5,
      "status": "queued"
    },
    "queue_position": 5,
    "estimated_wait_ms": 852000
  }
}
```

**Status Codes**: `200 OK`, `400 Bad Request`, `404 Not Found`

---

### POST /api/v1/queue/{community_id}/vote/{queue_item_id}

**Description**: Vote on a queued track

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| community_id | integer | Community/channel ID |
| queue_item_id | string | Queue item UUID |

**Request Body**:
```json
{
  "user_id": "user123",
  "direction": "up"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "queue_item_id": "550e8400-e29b-41d4-a716-446655440000",
    "new_votes": 6,
    "new_position": 0,
    "moved_positions": 2
  }
}
```

**Status Codes**: `200 OK`, `400 Bad Request`, `404 Not Found`

---

### DELETE /api/v1/queue/{community_id}/{queue_item_id}

**Description**: Remove a track from the queue

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| community_id | integer | Community/channel ID |
| queue_item_id | string | Queue item UUID |

**Response**:
```json
{
  "success": true,
  "data": {
    "removed": true,
    "queue_item_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Status Codes**: `200 OK`, `404 Not Found`

---

### POST /api/v1/queue/{community_id}/clear

**Description**: Clear all queued tracks (not currently playing)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| community_id | integer | Community/channel ID |

**Response**:
```json
{
  "success": true,
  "data": {
    "cleared_count": 8,
    "remaining_count": 0
  }
}
```

**Status Codes**: `200 OK`

---

### POST /api/v1/queue/{community_id}/skip

**Description**: Skip currently playing track

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| community_id | integer | Community/channel ID |

**Response**:
```json
{
  "success": true,
  "data": {
    "skipped": true,
    "next_track": {
      "track_id": "3n3Ppam7vgaVa1iaRUc9Lp",
      "name": "Mr. Blue Sky",
      "artist": "Electric Light Orchestra"
    }
  }
}
```

**Status Codes**: `200 OK`, `404 Not Found`

---

### GET /api/v1/queue/{community_id}/history

**Description**: Get play history for a community

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| community_id | integer | Community/channel ID |

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 50 | Maximum number of items to return |

**Response**:
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "track": {
          "name": "Never Gonna Give You Up",
          "artist": "Rick Astley"
        },
        "requested_by_user_id": "user123",
        "requested_at": "2025-12-16T12:30:00.000Z",
        "status": "played",
        "votes": 5
      }
    ],
    "total": 1
  }
}
```

**Status Codes**: `200 OK`

---

## Playback Control Endpoints

### POST /api/v1/playback/{community_id}/play

**Description**: Start playing the next track from queue

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| community_id | integer | Community/channel ID |

**Response**:
```json
{
  "success": true,
  "data": {
    "playing": true,
    "track": {
      "track_id": "4cOdK2GP6pPG3x0fA5CkPo",
      "name": "Never Gonna Give You Up",
      "artist": "Rick Astley",
      "provider": "spotify"
    },
    "started_at": "2025-12-16T12:34:56.789Z"
  }
}
```

**Status Codes**: `200 OK`, `404 Not Found`

---

### POST /api/v1/playback/{community_id}/pause

**Description**: Pause current playback

**Response**:
```json
{
  "success": true,
  "data": {
    "paused": true,
    "track": {
      "name": "Never Gonna Give You Up",
      "artist": "Rick Astley"
    }
  }
}
```

**Status Codes**: `200 OK`

---

### POST /api/v1/playback/{community_id}/resume

**Description**: Resume paused playback

**Response**:
```json
{
  "success": true,
  "data": {
    "resumed": true,
    "track": {
      "name": "Never Gonna Give You Up",
      "artist": "Rick Astley"
    }
  }
}
```

**Status Codes**: `200 OK`

---

### POST /api/v1/playback/{community_id}/stop

**Description**: Stop playback completely

**Response**:
```json
{
  "success": true,
  "data": {
    "stopped": true
  }
}
```

**Status Codes**: `200 OK`

---

### GET /api/v1/playback/{community_id}/now-playing

**Description**: Get currently playing track information

**Response**:
```json
{
  "success": true,
  "data": {
    "track": {
      "track_id": "4cOdK2GP6pPG3x0fA5CkPo",
      "name": "Never Gonna Give You Up",
      "artist": "Rick Astley",
      "album": "Whenever You Need Somebody",
      "album_art_url": "https://i.scdn.co/image/...",
      "duration_ms": 213000,
      "provider": "spotify",
      "uri": "spotify:track:4cOdK2GP6pPG3x0fA5CkPo"
    },
    "queue_item": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "requested_by_user_id": "user123",
      "requested_at": "2025-12-16T12:34:56.789Z",
      "votes": 5
    },
    "playback_state": {
      "is_playing": true,
      "is_paused": false,
      "provider": "spotify",
      "started_at": "2025-12-16T12:35:00.000Z"
    }
  }
}
```

**Status Codes**: `200 OK`, `204 No Content`

---

### POST /api/v1/playback/{community_id}/volume

**Description**: Set playback volume (Spotify only)

**Request Body**:
```json
{
  "volume": 75
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "volume": 75,
    "provider": "spotify"
  }
}
```

**Status Codes**: `200 OK`, `400 Bad Request`

---

## Radio Station Endpoints

### GET /api/v1/radio/{community_id}/stations

**Description**: List all configured radio stations for a community

**Response**:
```json
{
  "success": true,
  "data": {
    "stations": [
      {
        "id": "pretzel_lofi",
        "name": "Pretzel Lofi Hip Hop",
        "provider": "pretzel",
        "stream_url": "https://stream.pretzel.rocks/lofi",
        "bitrate": 128,
        "codec": "aac"
      }
    ]
  }
}
```

**Status Codes**: `200 OK`

---

### POST /api/v1/radio/{community_id}/stations

**Description**: Create/configure a new radio station

**Request Body**:
```json
{
  "name": "My Icecast Station",
  "provider": "icecast",
  "stream_url": "https://stream.example.com/radio.mp3",
  "bitrate": 128,
  "codec": "mp3"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "station_id": "icecast_custom_1",
    "created": true
  }
}
```

**Status Codes**: `200 OK`, `400 Bad Request`

---

### POST /api/v1/radio/{community_id}/play

**Description**: Start playing a radio station

**Request Body**:
```json
{
  "station_name": "pretzel_lofi"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "playing": true,
    "station": {
      "name": "Pretzel Lofi Hip Hop",
      "provider": "pretzel",
      "stream_url": "https://stream.pretzel.rocks/lofi"
    }
  }
}
```

**Status Codes**: `200 OK`, `404 Not Found`

---

### POST /api/v1/radio/{community_id}/stop

**Description**: Stop radio playback

**Response**:
```json
{
  "success": true,
  "data": {
    "stopped": true
  }
}
```

**Status Codes**: `200 OK`

---

### GET /api/v1/radio/{community_id}/now-playing

**Description**: Get current radio station and now-playing metadata

**Response**:
```json
{
  "success": true,
  "data": {
    "station_name": "Pretzel Lofi Hip Hop",
    "provider": "pretzel",
    "now_playing": {
      "title": "Midnight Vibes",
      "artist": "Lofi Beats",
      "album": null,
      "duration_seconds": null,
      "updated_at": "2025-12-16T12:34:56.789Z"
    }
  }
}
```

**Status Codes**: `200 OK`, `204 No Content`

---

## Mode Control Endpoints

### GET /api/v1/mode/{community_id}

**Description**: Get current playback mode for a community

**Response**:
```json
{
  "success": true,
  "data": {
    "active_mode": "music",
    "previous_mode": "radio",
    "switched_at": "2025-12-16T12:30:00.000Z"
  }
}
```

**Status Codes**: `200 OK`

---

### POST /api/v1/mode/{community_id}/switch

**Description**: Switch between music and radio modes

**Request Body**:
```json
{
  "mode": "radio"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "switched": true,
    "new_mode": "radio",
    "previous_mode": "music"
  }
}
```

**Status Codes**: `200 OK`, `400 Bad Request`

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed or invalid request |
| `UNAUTHORIZED` | 401 | Provider authentication failed |
| `FORBIDDEN` | 403 | Operation not permitted |
| `NOT_FOUND` | 404 | Resource not found |
| `METHOD_NOT_ALLOWED` | 405 | HTTP method not supported |
| `CONFLICT` | 409 | Resource conflict |
| `PROVIDER_ERROR` | 502 | External provider error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `QUEUE_FULL` | 429 | Queue has reached maximum capacity |

---

## Rate Limiting

Currently not enforced. Future implementation will use:

- **Per-Community Limits**: 100 requests/minute per community
- **Global Limits**: 10,000 requests/minute across all communities

---

## Webhooks & Events

### Browser Source Updates

The module sends real-time updates to the browser source overlay via HTTP POST:

**Endpoint**: `{BROWSER_SOURCE_URL}/api/v1/internal/now-playing`

**Payload**:
```json
{
  "community_id": 1,
  "type": "now_playing",
  "timestamp": "2025-12-16T12:34:56.789Z",
  "track": {
    "name": "Never Gonna Give You Up",
    "artist": "Rick Astley",
    "album": "Whenever You Need Somebody",
    "album_art_url": "https://i.scdn.co/image/...",
    "duration_ms": 213000,
    "provider": "spotify"
  }
}
```

---

## Complete Example Workflow

```bash
# 1. Check service health
curl http://localhost:8051/health

# 2. Search for a track
curl -X POST http://localhost:8051/api/v1/providers/spotify/search \
  -H "Content-Type: application/json" \
  -d '{"query": "never gonna give you up", "limit": 1}'

# 3. Add track to queue
curl -X POST http://localhost:8051/api/v1/queue/1/add \
  -H "Content-Type: application/json" \
  -d '{
    "track_url": "spotify:track:4cOdK2GP6pPG3x0fA5CkPo",
    "requested_by_user_id": "user123",
    "provider": "spotify"
  }'

# 4. Start playback
curl -X POST http://localhost:8051/api/v1/playback/1/play

# 5. Get now-playing info
curl http://localhost:8051/api/v1/playback/1/now-playing

# 6. Vote on a track
curl -X POST http://localhost:8051/api/v1/queue/1/vote/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user456", "direction": "up"}'

# 7. Skip to next track
curl -X POST http://localhost:8051/api/v1/queue/1/skip
```

---

**Last Updated**: 2025-12-16
**API Version**: v1
**Maintainer**: Waddles Development Team
