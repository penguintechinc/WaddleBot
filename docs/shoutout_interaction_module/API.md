# Shoutout Interaction Module — API Reference

## Base URL

```
http://localhost:8011
```

## Health & Status Endpoints

### Health Check
```
GET /health
```

Verifies the module is running and database is accessible.

**Response:**
```json
{
  "status": "healthy",
  "module": "shoutout_interaction_module",
  "version": "2.0.0",
  "timestamp": "2026-02-15T14:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Module healthy
- `503 Service Unavailable` - Database unavailable

### Module Status
```
GET /api/v1/status
```

Get module operational status and version.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "operational",
    "module": "shoutout_interaction_module",
    "version": "2.0.0"
  }
}
```

## Text Shoutout Endpoints

### Create Shoutout
```
POST /api/v1/shoutout
```

Generate a text shoutout for a Twitch user with live data.

**Request Body:**
```json
{
  "username": "pokimane",
  "community_id": 123,
  "platform": "twitch"
}
```

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| username | string | Yes | Target streamer's username (Twitch) |
| community_id | integer | Yes | Community ID for template lookup |
| platform | string | No | Target platform (twitch, discord, slack). Default: twitch |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "shoutout_text": "Go check out pokimane at twitch.tv/pokimane! They're currently streaming World of Warcraft with 5000 viewers!",
    "user": {
      "id": "88888888",
      "login": "pokimane",
      "display_name": "Pokimane",
      "description": "Content creator",
      "profile_image_url": "https://static-cdn.jtvnw.net/..."
    },
    "channel": {
      "id": "88888888",
      "game_id": "12345",
      "game_name": "World of Warcraft",
      "title": "Mythic+ Dungeons - Day 5"
    },
    "stream": {
      "id": "stream_123456",
      "type": "live",
      "viewer_count": 5000,
      "started_at": "2026-02-15T10:00:00Z"
    }
  }
}
```

**Error Responses:**

`400 Bad Request` - Missing required field:
```json
{
  "success": false,
  "error": "username is required"
}
```

`404 Not Found` - User not found on Twitch:
```json
{
  "success": false,
  "error": "User 'invalid_user' not found on Twitch"
}
```

`500 Internal Server Error` - API or database error:
```json
{
  "success": false,
  "error": "Failed to fetch Twitch data"
}
```

### Get Shoutout History
```
GET /api/v1/history/{community_id}
```

Retrieve past shoutouts for a community.

**Authentication:** Required (Bearer token)

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID (URL path) |
| limit | integer | No | Max results to return. Default: 50, Max: 500 |

**Query Example:**
```
GET /api/v1/history/123?limit=25
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "id": 1,
        "community_id": 123,
        "target_username": "pokimane",
        "target_platform": "twitch",
        "shoutout_text": "Go check out pokimane at twitch.tv/pokimane!",
        "triggered_by_user_id": "123456789",
        "triggered_by_username": "mod_user",
        "created_at": "2026-02-15T14:30:00Z"
      },
      {
        "id": 2,
        "community_id": 123,
        "target_username": "ninja",
        "target_platform": "twitch",
        "shoutout_text": "Go check out ninja at twitch.tv/ninja!",
        "triggered_by_user_id": "987654321",
        "triggered_by_username": "another_mod",
        "created_at": "2026-02-15T13:15:00Z"
      }
    ],
    "count": 2
  }
}
```

**Error Responses:**

`401 Unauthorized` - No token provided:
```json
{
  "success": false,
  "error": "Authorization required"
}
```

### Get Shoutout Statistics
```
GET /api/v1/stats/{community_id}
```

Retrieve community-level shoutout statistics.

**Authentication:** Required (Bearer token)

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID (URL path) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_shoutouts": 145,
    "total_unique_targets": 67,
    "manual_shoutouts": 98,
    "auto_shoutouts": 47,
    "most_shoutout_target": {
      "username": "pokimane",
      "count": 23
    },
    "most_frequent_mod": {
      "username": "mod_user",
      "count": 45
    },
    "last_shoutout": "2026-02-15T14:30:00Z"
  }
}
```

### Save Custom Template
```
POST /api/v1/template
```

Create or update a custom shoutout template for a community.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "community_id": 123,
  "platform": "twitch",
  "is_live": true,
  "template": "Huge shoutout to {display_name}! Go follow them at twitch.tv/{login}!"
}
```

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID |
| platform | string | No | Target platform (twitch, discord, slack). Default: twitch |
| is_live | boolean | No | Template for live streams. Default: true |
| template | string | Yes | Template with {variable} substitutions |

**Available Variables:**
- `{display_name}` - User's display name
- `{login}` - Lowercase username
- `{game_name}` - Current or last game
- `{title}` - Stream title
- `{viewer_count}` - Live viewer count
- `{description}` - User bio

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Template saved"
  }
}
```

**Error Responses:**

`400 Bad Request` - Missing required fields:
```json
{
  "success": false,
  "error": "community_id and template are required"
}
```

### Get Twitch User Data
```
GET /api/v1/twitch/user/{username}
```

Fetch user, channel, and stream data from Twitch (for debugging/testing).

**Authentication:** Required (Bearer token)

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| username | string | Yes | Twitch username (URL path) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "88888888",
      "login": "pokimane",
      "display_name": "Pokimane",
      "description": "IRL streamer and content creator",
      "profile_image_url": "https://static-cdn.jtvnw.net/...",
      "offline_image_url": "https://static-cdn.jtvnw.net/..."
    },
    "channel": {
      "id": "88888888",
      "broadcaster_login": "pokimane",
      "game_id": "12345",
      "game_name": "World of Warcraft",
      "title": "Mythic+ Dungeons"
    },
    "stream": {
      "id": "stream_123456",
      "type": "live",
      "viewer_count": 5000,
      "started_at": "2026-02-15T10:00:00Z"
    }
  }
}
```

### Get Circuit Breaker Metrics
```
GET /api/v1/circuit-breaker/metrics
```

Inspect Twitch API circuit breaker health (rate limiting, failures, timeouts).

**Authentication:** Required (Bearer token)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "circuit_breaker": {
      "name": "twitch_api",
      "state": "closed",
      "failure_count": 0,
      "failure_threshold": 5,
      "timeout_seconds": 60,
      "last_failure": null,
      "recovery_time_left": 0
    }
  }
}
```

## Video Shoutout Endpoints

### Execute Video Shoutout
```
POST /api/v1/video-shoutout
```

Trigger a video shoutout (!vso command) with video clip and channel info.

**Request Body:**
```json
{
  "community_id": 123,
  "target_username": "pokimane",
  "target_platform": "twitch",
  "triggered_by_user_id": "123456789",
  "triggered_by_username": "mod_user",
  "user_roles": ["mod"]
}
```

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID |
| target_username | string | Yes | Streamer to shoutout (Twitch) |
| target_platform | string | No | Target platform (twitch). Default: twitch |
| triggered_by_user_id | string | No | User ID of who triggered |
| triggered_by_username | string | No | Username of who triggered |
| user_roles | array | No | User's roles (admin, mod, vip, subscriber) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "video": {
      "platform": "twitch",
      "video_id": "clip_id_abc123",
      "title": "Best play of the day",
      "thumbnail_url": "https://clips.twitch.tv/...",
      "video_url": "https://clips.twitch.tv/...",
      "duration_seconds": 45,
      "view_count": 1200,
      "created_at": "2026-02-15T12:00:00Z"
    },
    "channel": {
      "platform": "twitch",
      "user_id": "88888888",
      "username": "pokimane",
      "display_name": "Pokimane",
      "profile_image_url": "https://static-cdn.jtvnw.net/...",
      "game_name": "World of Warcraft",
      "is_live": true,
      "stream_title": "Mythic+ Dungeons"
    },
    "game_name": "World of Warcraft",
    "is_live": true
  }
}
```

**Error Responses:**

`400 Bad Request` - Missing required fields:
```json
{
  "success": false,
  "error": "community_id and target_username required"
}
```

`400 Bad Request` - Permission denied:
```json
{
  "success": false,
  "error": "Permission denied. Requires: mod or higher"
}
```

`400 Bad Request` - On cooldown:
```json
{
  "success": false,
  "error": "User is on cooldown. Please wait 30 more seconds."
}
```

### Check Auto-Shoutout Eligibility
```
POST /api/v1/video-shoutout/auto-check
```

Verify a user qualifies for auto-shoutout (permission, cooldown, config enabled).

**Request Body:**
```json
{
  "community_id": 123,
  "platform": "twitch",
  "user_id": "88888888",
  "user_roles": ["vip"],
  "trigger_type": "first_message"
}
```

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID |
| platform | string | Yes | Platform (twitch) |
| user_id | string | Yes | User's platform ID |
| user_roles | array | No | User's roles. Default: [] |
| trigger_type | string | No | Trigger type (first_message, raid, host). Default: first_message |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "eligible": true
  }
}
```

### Get Video Shoutout Configuration
```
GET /api/v1/video-shoutout/config/{community_id}
```

Retrieve video shoutout settings for a community.

**Authentication:** Required (Bearer token)

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID (URL path) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "so_enabled": true,
    "so_permission": "mod",
    "vso_enabled": true,
    "vso_permission": "mod",
    "auto_shoutout_mode": "enabled",
    "trigger_first_message": false,
    "trigger_raid_host": true,
    "widget_position": "bottom-right",
    "widget_duration_seconds": 30,
    "cooldown_minutes": 60
  }
}
```

### Update Video Shoutout Configuration
```
PUT /api/v1/video-shoutout/config/{community_id}
```

Modify video shoutout settings.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "vso_enabled": true,
  "vso_permission": "mod",
  "auto_shoutout_mode": "enabled",
  "trigger_first_message": false,
  "trigger_raid_host": true,
  "widget_position": "bottom-right",
  "widget_duration_seconds": 30,
  "cooldown_minutes": 60
}
```

**All fields optional. Only specified fields will be updated.**

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Configuration updated"
  }
}
```

### Get Auto-Shoutout Creators
```
GET /api/v1/video-shoutout/creators/{community_id}
```

Retrieve list of creators eligible for auto-shoutouts.

**Authentication:** Required (Bearer token)

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID (URL path) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "creators": [
      {
        "platform": "twitch",
        "user_id": "88888888",
        "username": "pokimane",
        "custom_trigger": "default",
        "added_at": "2026-02-01T10:00:00Z"
      },
      {
        "platform": "twitch",
        "user_id": "99999999",
        "username": "shroud",
        "custom_trigger": "raid_only",
        "added_at": "2026-02-05T15:30:00Z"
      }
    ]
  }
}
```

### Add Creator to Auto-Shoutout
```
POST /api/v1/video-shoutout/creators/{community_id}
```

Add a creator to the auto-shoutout list.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "platform": "twitch",
  "user_id": "88888888",
  "username": "pokimane",
  "custom_trigger": "default"
}
```

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| platform | string | Yes | Platform (twitch) |
| user_id | string | Yes | User's platform ID |
| username | string | Yes | Username |
| custom_trigger | string | No | Trigger rule (default, raid_only, host_only). Default: default |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Creator added"
  }
}
```

### Remove Creator from Auto-Shoutout
```
DELETE /api/v1/video-shoutout/creators/{community_id}/{platform}/{user_id}
```

Remove a creator from auto-shoutout list.

**Authentication:** Required (Bearer token)

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID (URL path) |
| platform | string | Yes | Platform (URL path) |
| user_id | string | Yes | User ID (URL path) |

**Example URL:**
```
DELETE /api/v1/video-shoutout/creators/123/twitch/88888888
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Creator removed"
  }
}
```

**Error Response:**

`404 Not Found`:
```json
{
  "success": false,
  "error": "Creator not found"
}
```

### Get Video Shoutout History
```
GET /api/v1/video-shoutout/history/{community_id}
```

Retrieve past video shoutout executions.

**Authentication:** Required (Bearer token)

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Community ID (URL path) |
| limit | integer | No | Max results. Default: 50 |
| offset | integer | No | Results offset for pagination. Default: 0 |

**Query Example:**
```
GET /api/v1/video-shoutout/history/123?limit=25&offset=0
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "id": 501,
        "community_id": 123,
        "target_username": "pokimane",
        "target_platform": "twitch",
        "triggered_by_username": "mod_user",
        "trigger_type": "manual",
        "video_id": "clip_id_abc123",
        "video_platform": "twitch",
        "created_at": "2026-02-15T14:30:00Z"
      }
    ],
    "count": 1
  }
}
```

### Get Video Content for Testing
```
GET /api/v1/video-shoutout/video/{platform}/{username}
```

Fetch video and channel info (for preview/debugging).

**Authentication:** Required (Bearer token)

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| platform | string | Yes | Platform (twitch) (URL path) |
| username | string | Yes | Username (URL path) |

**Example URL:**
```
GET /api/v1/video-shoutout/video/twitch/pokimane
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "video": {
      "platform": "twitch",
      "video_id": "clip_id_xyz789",
      "title": "Epic moment",
      "thumbnail_url": "https://clips.twitch.tv/...",
      "video_url": "https://clips.twitch.tv/...",
      "duration_seconds": 30,
      "view_count": 5000,
      "created_at": "2026-02-14T08:00:00Z"
    },
    "channel": {
      "platform": "twitch",
      "user_id": "88888888",
      "username": "pokimane",
      "display_name": "Pokimane",
      "profile_image_url": "https://static-cdn.jtvnw.net/...",
      "game_name": "World of Warcraft",
      "is_live": true,
      "stream_title": "Mythic+ Dungeons"
    },
    "game_name": "World of Warcraft",
    "is_live": true
  }
}
```

## Error Codes

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

Common HTTP status codes:

| Status | Meaning |
|---|---|
| 200 | Success |
| 400 | Bad request (invalid parameters, missing fields) |
| 401 | Unauthorized (authentication required) |
| 403 | Forbidden (permission denied) |
| 404 | Not found (user, resource doesn't exist) |
| 500 | Server error |
| 503 | Service unavailable (database down) |

## Authentication

Protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

Token obtained from identity service during user login.
