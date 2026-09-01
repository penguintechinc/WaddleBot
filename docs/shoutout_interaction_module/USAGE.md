# Shoutout Interaction Module — Usage Guide

## Getting Started

### Quick Start with Docker

```bash
# Build and run the module
docker build -t shoutout-module action/interactive/shoutout_interaction_module/
docker run -d \
  -p 8011:8011 \
  -e TWITCH_CLIENT_ID="your_client_id" \
  -e TWITCH_CLIENT_SECRET="your_client_secret" \
  -e YOUTUBE_API_KEY="your_youtube_key" \
  -e DATABASE_URL="postgresql://user:pass@localhost:5432/waddlebot" \
  --name shoutout-module \
  shoutout-module
```

### Health Check

```bash
# Verify the module is running
curl http://localhost:8011/health
# Expected response: {"status": "healthy", "module": "shoutout_interaction_module", "version": "2.0.0"}
```

### Local Development Setup

```bash
# Install dependencies
cd action/interactive/shoutout_interaction_module/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env <<EOF
MODULE_PORT=8011
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_client_secret
YOUTUBE_API_KEY=your_youtube_key
IDENTITY_URL=http://localhost:8050
CORE_API_URL=http://localhost:8000
LOG_LEVEL=INFO
EOF

# Run the module
python app.py
# Server will start at http://localhost:8011
```

## Common Workflows

### 1. Generate a Text Shoutout

Text shoutouts fetch live streamer data from Twitch and generate a message using templates.

**Request:**
```bash
curl -X POST http://localhost:8011/api/v1/shoutout \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ninja",
    "community_id": 123,
    "platform": "twitch"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "shoutout_text": "Go check out ninja at twitch.tv/ninja! They're currently streaming Fortnite with 50000 viewers!",
    "user": {
      "login": "ninja",
      "display_name": "Ninja",
      "description": "Content creator"
    },
    "channel": {
      "game_name": "Fortnite",
      "title": "Ranked Grind"
    },
    "stream": {
      "viewer_count": 50000,
      "is_live": true
    }
  }
}
```

**Template Variables Available:**
- `{display_name}` - User's display name
- `{login}` - Username (lowercase)
- `{game_name}` - Current or last streamed game
- `{title}` - Stream title
- `{viewer_count}` - Current viewer count (0 if offline)
- `{description}` - User bio/description

### 2. Create a Video Shoutout

Video shoutouts (!vso command) display a video clip or YouTube video alongside streamer info.

**Request:**
```bash
curl -X POST http://localhost:8011/api/v1/video-shoutout \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "target_username": "pokimane",
    "target_platform": "twitch",
    "triggered_by_user_id": "98765432",
    "triggered_by_username": "mod_user",
    "user_roles": ["mod"]
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "video": {
      "platform": "twitch",
      "video_id": "clip_id_123",
      "title": "Best moment of the stream",
      "thumbnail_url": "https://clips.twitch.tv/...",
      "video_url": "https://clips.twitch.tv/...",
      "duration_seconds": 45,
      "created_at": "2026-02-15T10:30:00Z"
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

### 3. Set Custom Shoutout Template

Communities can define custom templates for text shoutouts.

**Request:**
```bash
curl -X POST http://localhost:8011/api/v1/template \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "platform": "twitch",
    "is_live": true,
    "template": "Big shout to {display_name}! Go support their stream at twitch.tv/{login}"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Template saved"
  }
}
```

### 4. Configure Video Shoutout Settings

Configure which roles can trigger video shoutouts, cooldowns, and auto-trigger behavior.

**Request:**
```bash
curl -X PUT http://localhost:8011/api/v1/video-shoutout/config/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vso_enabled": true,
    "vso_permission": "mod",
    "auto_shoutout_mode": "enabled",
    "trigger_first_message": false,
    "trigger_raid_host": true,
    "widget_position": "bottom-right",
    "widget_duration_seconds": 30,
    "cooldown_minutes": 60
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Configuration updated"
  }
}
```

### 5. Add Creator to Auto-Shoutout List

Auto-shoutouts trigger when configured users join your community.

**Request:**
```bash
curl -X POST http://localhost:8011/api/v1/video-shoutout/creators/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "twitch",
    "user_id": "99999999",
    "username": "shroud",
    "custom_trigger": "default"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Creator added"
  }
}
```

### 6. Check Auto-Shoutout Eligibility

Before triggering an auto-shoutout, verify the user is eligible (not on cooldown, has proper roles, etc.).

**Request:**
```bash
curl -X POST http://localhost:8011/api/v1/video-shoutout/auto-check \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "platform": "twitch",
    "user_id": "99999999",
    "user_roles": ["vip"],
    "trigger_type": "first_message"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "eligible": true
  }
}
```

### 7. Get Shoutout History

Retrieve past shoutouts for analytics, moderation, or audit purposes.

**Request:**
```bash
curl "http://localhost:8011/api/v1/history/123?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
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
        "triggered_by_username": "mod_user",
        "created_at": "2026-02-15T14:30:00Z",
        "type": "manual"
      },
      {
        "id": 2,
        "community_id": 123,
        "target_username": "ninja",
        "target_platform": "twitch",
        "shoutout_text": "Go check out ninja at twitch.tv/ninja!",
        "triggered_by_username": "system",
        "created_at": "2026-02-15T13:15:00Z",
        "type": "auto"
      }
    ],
    "count": 2
  }
}
```

### 8. Get Shoutout Statistics

View community-level shoutout statistics.

**Request:**
```bash
curl "http://localhost:8011/api/v1/stats/123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_shoutouts": 145,
    "total_unique_targets": 67,
    "manual_shoutouts": 98,
    "auto_shoutouts": 47,
    "most_shoutout_target": "pokimane",
    "most_frequent_mod": "mod_user",
    "last_shoutout": "2026-02-15T14:30:00Z"
  }
}
```

### 9. Get Video Shoutout History

Retrieve video shoutout execution history with pagination.

**Request:**
```bash
curl "http://localhost:8011/api/v1/video-shoutout/history/123?limit=25&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
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
        "video_id": "clip_id_456",
        "video_platform": "twitch",
        "created_at": "2026-02-15T14:30:00Z"
      }
    ],
    "count": 1
  }
}
```

### 10. Get Video Content for Testing

Retrieve video and channel info for a user (useful for testing/preview).

**Request:**
```bash
curl "http://localhost:8011/api/v1/video-shoutout/video/twitch/pokimane" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "video": {
      "platform": "twitch",
      "video_id": "clip_id_789",
      "title": "Epic pog moment",
      "thumbnail_url": "https://clips.twitch.tv/...",
      "video_url": "https://clips.twitch.tv/...",
      "duration_seconds": 30
    },
    "channel": {
      "platform": "twitch",
      "user_id": "88888888",
      "username": "pokimane",
      "display_name": "Pokimane",
      "game_name": "WoW",
      "is_live": true
    },
    "game_name": "WoW",
    "is_live": true
  }
}
```

## Chat Command Integration

The shoutout module is typically integrated with chat bots that recognize these commands:

### !so command (Text Shoutout)
```
!so <username> → Generates text shoutout, displays in chat
Example: !so pokimane → "Go check out pokimane at twitch.tv/pokimane! They're streaming WoW with 5000 viewers!"
```

### !vso command (Video Shoutout)
```
!vso <username> → Generates video shoutout with overlay widget
Example: !vso pokimane → Displays video clip of pokimane with channel info in overlay widget
```

## Permission Levels

Permission levels are evaluated in this order (first match wins):
1. **admin_only** - Only community admins
2. **mod** - Moderators and admins
3. **vip** - VIPs, moderators, and admins
4. **subscriber** - Subscribers, VIPs, moderators, and admins
5. **everyone** - Any chat member

Default is **mod** (moderators and above).

## Cooldown Behavior

After a shoutout is generated:
- User cannot trigger another shoutout for X minutes (cooldown_minutes)
- Same target user cannot receive two shoutouts within Y minutes (global cooldown)
- Video shoutouts have independent cooldown from text shoutouts

To check remaining cooldown, monitor the `cooldown_remaining` field in error responses.

## Troubleshooting Common Issues

### Module Not Starting
- Verify DATABASE_URL is correct and PostgreSQL is running
- Check TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET are set
- Review logs: `docker logs shoutout-module`

### Shoutout Returns User Not Found
- Verify username spelling (Twitch is case-insensitive but username must exist)
- Check Twitch API credentials are valid
- Review circuit breaker status: `GET /api/v1/circuit-breaker/metrics`

### Video Not Found for User
- Module first attempts Twitch clips, then falls back to YouTube
- If user has no clips on Twitch, requires YouTube channel to be linked
- Verify cross-platform identity linking in identity_core module

### Permission Denied
- Verify user has required role (default: mod)
- Check community configuration for vso_permission setting
- Review audit logs for permission details

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more detailed debugging.
