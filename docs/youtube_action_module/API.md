# YouTube Action Module - REST API Reference

## Authentication

All endpoints except `/health` and `/api/v1/token/generate` require JWT bearer token authentication.

### Header Format

```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

### Token Generation Endpoint

**POST** `/api/v1/token/generate`

Generate a JWT token for API authentication.

**Request Body:**
```json
{
  "secret": "your-module-secret-key",
  "channel_id": "optional-channel-id"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 86400
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid secret

---

## Health Check

**GET** `/health`

Health check endpoint. No authentication required.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "module": "youtube_action_module",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00",
  "grpc_port": 50054,
  "rest_port": 8073
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "error": "database connection failed",
  "timestamp": "2024-01-15T10:30:00"
}
```

---

## OAuth Management

### Get Authorization URL

**GET** `/oauth/authorize`

Get the OAuth authorization URL for channel authorization.

**Query Parameters:**
- `state` - Optional state parameter (typically channel_id)

**Response (200 OK):**
```json
{
  "success": true,
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

---

### OAuth Callback

**GET** `/oauth/callback`

Handles Google OAuth callback. Called automatically by browser redirect.

**Query Parameters:**
- `code` - Authorization code from Google
- `state` - State parameter from authorization request

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Authorization successful",
  "channel_id": "UCxxxxx",
  "expires_at": "2024-01-15T11:30:00"
}
```

---

### List Authorized Channels

**GET** `/oauth/channels`

List all authorized YouTube channels.

**Authentication:** Required (Bearer token)

**Response (200 OK):**
```json
{
  "success": true,
  "channels": [
    {
      "channel_id": "UCxxxxx",
      "channel_name": "My Channel",
      "authorized_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

---

### Revoke Authorization

**DELETE** `/oauth/revoke/<channel_id>`

Revoke OAuth authorization for a channel.

**Authentication:** Required (Bearer token)

**Path Parameters:**
- `channel_id` - YouTube channel ID to revoke

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Authorization revoked"
}
```

**Error Responses:**
- `404 Not Found` - Channel not found

---

## Live Chat Operations

### Send Chat Message

**POST** `/api/v1/chat/send`

Send a message to live chat.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "live_chat_id": "AimFLc...",
  "message": "Hello YouTube Live!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message_id": "msg_123456",
    "published_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### Delete Chat Message

**POST** `/api/v1/chat/delete`

Delete a message from live chat.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "message_id": "msg_123456"
}
```

**Response (200 OK):**
```json
{
  "success": true
}
```

---

### Ban User from Chat

**POST** `/api/v1/chat/ban`

Ban a user from live chat.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "live_chat_id": "AimFLc...",
  "target_channel_id": "UCyyyyyy",
  "duration_seconds": null
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "banned_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### Unban User from Chat

**POST** `/api/v1/chat/unban`

Unban a user from live chat.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "live_chat_id": "AimFLc...",
  "target_channel_id": "UCyyyyyy"
}
```

**Response (200 OK):**
```json
{
  "success": true
}
```

---

## Moderation

### Add Moderator

**POST** `/api/v1/moderator/add`

Add a moderator to live chat.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "live_chat_id": "AimFLc...",
  "target_channel_id": "UCyyyyyy"
}
```

**Response (200 OK):**
```json
{
  "success": true
}
```

---

### Remove Moderator

**POST** `/api/v1/moderator/remove`

Remove a moderator from live chat.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "live_chat_id": "AimFLc...",
  "target_channel_id": "UCyyyyyy"
}
```

**Response (200 OK):**
```json
{
  "success": true
}
```

---

## Video Management

### Update Video Title

**PUT** `/api/v1/video/title`

Update video title.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "video_id": "dQw4w9WgXcQ",
  "title": "New Title"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "video_id": "dQw4w9WgXcQ",
    "title": "New Title"
  }
}
```

---

### Update Video Description

**PUT** `/api/v1/video/description`

Update video description.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "video_id": "dQw4w9WgXcQ",
  "description": "Updated description"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "video_id": "dQw4w9WgXcQ",
    "description": "Updated description"
  }
}
```

---

## Playlist Management

### Create Playlist

**POST** `/api/v1/playlist/create`

Create a new playlist.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "title": "My Playlist",
  "description": "Playlist description",
  "privacy": "private"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "playlist_id": "PLxxxxx",
    "title": "My Playlist",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### Add Video to Playlist

**POST** `/api/v1/playlist/add`

Add a video to playlist.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "playlist_id": "PLxxxxx",
  "video_id": "dQw4w9WgXcQ"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "playlist_item_id": "PLitem_123"
  }
}
```

---

### Remove Video from Playlist

**POST** `/api/v1/playlist/remove`

Remove a video from playlist.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "playlist_item_id": "PLitem_123"
}
```

**Response (200 OK):**
```json
{
  "success": true
}
```

---

## Broadcast Management

### Update Broadcast Status

**PUT** `/api/v1/broadcast/status`

Update broadcast status.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "broadcast_id": "broadcast_123",
  "status": "live"
}
```

**Valid Status Values:**
- `testing` - Test broadcast
- `live` - Live broadcast
- `all` - All statuses

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "broadcast_id": "broadcast_123",
    "status": "live",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### Insert Ad Break Cuepoint

**POST** `/api/v1/broadcast/cuepoint`

Insert an ad break cuepoint.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "broadcast_id": "broadcast_123",
  "duration_seconds": 30
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "cuepoint_id": "cuepoint_123",
    "duration_seconds": 30
  }
}
```

---

## Comment Management

### Post Comment on Video

**POST** `/api/v1/comment/post`

Post a comment on a video.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "video_id": "dQw4w9WgXcQ",
  "text": "Great video!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "comment_id": "comment_123",
    "text": "Great video!"
  }
}
```

---

### Reply to Comment

**POST** `/api/v1/comment/reply`

Reply to a comment.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "parent_id": "comment_123",
  "text": "Thanks for watching!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "comment_id": "comment_reply_456"
  }
}
```

---

### Delete Comment

**DELETE** `/api/v1/comment/delete`

Delete a comment.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "comment_id": "comment_123"
}
```

**Response (200 OK):**
```json
{
  "success": true
}
```

---

### Set Comment Moderation Status

**PUT** `/api/v1/comment/moderate`

Set moderation status for a comment.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "channel_id": "UCxxxxx",
  "comment_id": "comment_123",
  "status": "held_for_review"
}
```

**Status Options:**
- `held_for_review` - Hold for review
- `approved` - Approve comment
- `rejected` - Reject comment
- `spam` - Mark as spam

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "comment_id": "comment_123",
    "status": "held_for_review"
  }
}
```

---

## Error Handling

All error responses follow this format:

```json
{
  "success": false,
  "message": "Error message"
}
```

### Common HTTP Status Codes

| Status | Meaning |
|--------|---------|
| `200 OK` | Request successful |
| `400 Bad Request` | Invalid request parameters |
| `401 Unauthorized` | Authentication failed |
| `403 Forbidden` | Insufficient permissions |
| `404 Not Found` | Resource not found |
| `500 Internal Server Error` | Server error |
| `503 Service Unavailable` | Database unavailable |

### Common YouTube API Errors

| Error Code | Meaning | Solution |
|-----------|---------|----------|
| `quotaExceeded` | Daily API quota exceeded | Wait until next day |
| `invalidCredentials` | OAuth token invalid | Re-authorize |
| `liveChatNotFound` | Live chat ID invalid | Verify channel is live |
| `accessDenied` | User denied permission | Request authorization |
| `resourceNotFound` | Video/comment not found | Verify resource exists |
| `forbidden` | Action not allowed | Check user permissions |

---

## Rate Limiting

YouTube API rate limits:
- **100 requests per 100 seconds** per API key
- **User rate limit**: 1,000,000 queries per day

Module implementation:
- Queues excess requests
- Implements exponential backoff
- Tracks quota usage
- Auto-retries after reset

**Response Headers:**
```
X-Ratelimit-Limit: 100
X-Ratelimit-Remaining: 95
X-Ratelimit-Reset: 1234567890
```
