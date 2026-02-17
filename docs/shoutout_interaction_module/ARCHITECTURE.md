# Shoutout Interaction Module — Architecture

## Module Overview

The Shoutout Interaction Module is a microservice within the Waddlebot ecosystem that orchestrates text and video shoutouts using external platform APIs (Twitch, YouTube) combined with internal services (identity resolution, database persistence).

```
┌─────────────────────────────────────────────────────────────┐
│         Shoutout Interaction Module (Quart App)             │
│                      Port 8011                              │
└─────────────┬───────────────────────────────────────────────┘
              │
    ┌─────────┼─────────┬──────────┬────────────┬──────────────┐
    │         │         │          │            │              │
    v         v         v          v            v              v
┌────────┐ ┌──────────┐┌────────┐┌──────────┐┌─────────────┐┌────────────┐
│TwitchSv│ │ShoutoutSv││VideoSv ││IdentitySv││VideoShoutout││ DAL/Database
│ Service │ │ Service  ││Service ││ Service  ││  Service    ││ (PostgreSQL)
└─┬──────┘ └──────────┘└────┬───┘└──────────┘└─────────────┘└──────┬─────┘
  │                          │                                       │
  └──────────┬───────────────┴───────────────────────────────────────┘
             │
  ┌──────────┴────────────────────────────┬──────────────────────┐
  │                                        │                      │
  v                                        v                      v
┌─────────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐
│  Twitch Helix API       │  │ YouTube Data API     │  │ Identity Core    │
│  (User, Channel, Stream)│  │ (Video Search)       │  │ Service (ID Map) │
└─────────────────────────┘  └──────────────────────┘  └──────────────────┘
```

## Core Services

### 1. TwitchService

**Purpose:** Fetch user, channel, and stream information from Twitch Helix API.

**Key Methods:**
- `get_full_shoutout_data(username)` - Fetch combined user + channel + stream data
- `get_access_token()` - OAuth app access token management
- `_get_user_by_login(username)` - User info lookup
- `_get_channel_info(user_id)` - Channel metadata (game, title)
- `_get_stream_info(user_id)` - Live stream status (viewer count, started_at)

**Features:**
- Circuit breaker pattern (5 failures = 60 second timeout)
- Retry logic for transient failures
- Caches OAuth tokens in memory

**Data Returned:**
```python
{
    'user': {
        'id': str,
        'login': str,
        'display_name': str,
        'description': str,
        'profile_image_url': str,
        'offline_image_url': str
    },
    'channel': {
        'id': str,
        'broadcaster_login': str,
        'game_id': str,
        'game_name': str,
        'title': str
    },
    'stream': {
        'id': str,
        'type': str,  # 'live' or 'offline'
        'viewer_count': int,
        'started_at': str
    }
}
```

### 2. ShoutoutService

**Purpose:** Generate text shoutout messages using templates.

**Key Methods:**
- `generate_shoutout(twitch_data, community_id, platform)` - Create shoutout message
- `save_custom_template(community_id, platform, is_live, template)` - Store template
- `get_shoutout_history(community_id, limit)` - Retrieve past shoutouts
- `get_stats(community_id)` - Compute statistics
- `_get_custom_template(community_id, platform, is_live)` - Load template
- `_substitute_variables(template, twitch_data)` - Variable replacement

**Template System:**
```python
DEFAULT_TEMPLATES = {
    'twitch': {
        'live': "Go check out {display_name} at twitch.tv/{login}! They're currently streaming {game_name} with {viewer_count} viewers!",
        'offline': "Go check out {display_name} at twitch.tv/{login}! They were last seen streaming {game_name}.",
        'minimal': "Shoutout to {display_name}! Check them out at twitch.tv/{login}"
    },
    'discord': {
        'default': "**Shoutout** to {display_name}! Check out their stream at <https://twitch.tv/{login}>"
    },
    'slack': {
        'default': "*Shoutout* to {display_name}! Check them out at <https://twitch.tv/{login}|twitch.tv/{login}>"
    }
}
```

**Variable Substitution:**
- `{display_name}` → user.display_name
- `{login}` → user.login (lowercase)
- `{game_name}` → channel.game_name
- `{title}` → channel.title
- `{viewer_count}` → stream.viewer_count (0 if offline)
- `{description}` → user.description

### 3. VideoService

**Purpose:** Retrieve video clips from Twitch and YouTube for video shoutouts.

**Key Methods:**
- `get_video_for_shoutout(platform, username)` - Fetch video + channel info
- `_get_twitch_clips(user_id, num_clips)` - Get recent Twitch clips
- `_get_youtube_videos(channel_name, num_videos)` - Search YouTube
- `_get_twitch_channel_info(user_id)` - Channel metadata
- `_get_youtube_channel_info(channel_id)` - YouTube channel data

**Data Returned:**
```python
{
    'video': VideoInfo(
        platform='twitch',  # or 'youtube'
        video_id=str,
        title=str,
        thumbnail_url=str,
        video_url=str,
        duration_seconds=int,
        view_count=int,
        created_at=str
    ),
    'channel': ChannelInfo(
        platform='twitch',
        user_id=str,
        username=str,
        display_name=str,
        profile_image_url=str,
        game_name=str,
        is_live=bool,
        stream_title=str
    ),
    'game_name': str,
    'is_live': bool
}
```

**Fallback Strategy:**
1. First attempt: Fetch Twitch clips for user_id
2. If no clips found: Query identity service for linked YouTube
3. If YouTube linked: Search YouTube for videos
4. If all fail: Return error, video shoutout cannot proceed

### 4. IdentityService

**Purpose:** Resolve cross-platform identities for fallback video lookup.

**Key Methods:**
- `get_linked_identities(platform, platform_user_id)` - Query all linked accounts
- HTTP request to identity_core module at `IDENTITY_URL`

**Endpoint Used:**
```
GET {IDENTITY_URL}/api/v1/identities/lookup?platform=twitch&platform_user_id=88888888
```

**Response:**
```json
{
    "identities": [
        {
            "platform": "twitch",
            "platform_user_id": "88888888",
            "platform_username": "pokimane",
            "is_primary": true
        },
        {
            "platform": "youtube",
            "platform_user_id": "UC_abcd1234",
            "platform_username": "pokimane_youtube",
            "is_primary": false
        }
    ]
}
```

**Use Case:** When user has no Twitch clips, fall back to their linked YouTube channel.

### 5. VideoShoutoutService

**Purpose:** Orchestrate video shoutouts with permissions, cooldowns, and auto-triggers.

**Key Methods:**
- `execute_video_shoutout(community_id, target_username, ...)` - Execute video shoutout
- `check_auto_shoutout_eligible(community_id, platform, user_id, ...)` - Eligibility check
- `check_community_eligible(community_id)` - Verify community type
- `get_config(community_id)` - Load configuration
- `update_config(community_id, data)` - Save configuration
- `get_creators(community_id)` - List auto-shoutout creators
- `add_creator(community_id, platform, user_id, username, ...)` - Add creator
- `remove_creator(community_id, platform, user_id)` - Remove creator
- `get_history(community_id, limit, offset)` - Retrieve history
- `_check_permission(permission, user_roles)` - Permission evaluation
- `_check_cooldown(community_id, target_username, user_id)` - Cooldown check
- `_record_shoutout(community_id, target_username, ...)` - Log to database

**Permission Evaluation:**
```
PERMISSION_LEVELS = ['admin_only', 'mod', 'vip', 'subscriber', 'everyone']

Check in order:
1. if configured permission == 'admin_only' and 'admin' in user_roles → ALLOW
2. if configured permission == 'mod' and ('mod' or 'admin') in user_roles → ALLOW
3. if configured permission == 'vip' and ('vip', 'mod', or 'admin') in user_roles → ALLOW
4. if configured permission == 'subscriber' and any_subscriber_role in user_roles → ALLOW
5. if configured permission == 'everyone' → ALLOW
6. else → DENY
```

**Cooldown Logic:**
- Per-user-per-community: User cannot trigger another shoutout for X minutes
- Per-target-global: Target cannot receive shoutouts more than once per Y minutes
- Separate cooldowns for text vs video shoutouts

**Community Type Check:**
```python
SHOUTOUT_ELIGIBLE_TYPES = ['creator', 'gaming']

Fetch from database:
SELECT community_type FROM communities WHERE id = community_id

Only 'creator' and 'gaming' communities support shoutouts.
```

## Data Flow Diagrams

### Text Shoutout Flow
```
POST /api/v1/shoutout
  ↓
Validate username, community_id
  ↓
TwitchService.get_full_shoutout_data(username)
  ├→ OAuth token (if needed)
  ├→ GET /users?login=username
  ├→ GET /channels?broadcaster_id=user_id
  └→ GET /streams?user_id=user_id
  ↓
ShoutoutService.generate_shoutout(twitch_data, community_id, platform)
  ├→ Load custom template (if exists)
  └→ Substitute variables
  ↓
Log audit event
  ↓
Return shoutout text + metadata
```

### Video Shoutout Flow
```
POST /api/v1/video-shoutout
  ↓
Validate community_id, target_username
  ↓
VideoShoutoutService.execute_video_shoutout()
  ├→ Check community eligible (type in ['creator', 'gaming'])
  ├→ Load community config
  ├→ Check user permission (vso_permission)
  ├→ Check cooldown (user not on cooldown)
  ├→ Check target not recently shoutout'd
  ├→ TwitchService.get_full_shoutout_data(target_username)
  │
  └→ VideoService.get_video_for_shoutout(platform, target_username)
     ├→ Attempt 1: GET /clips?broadcaster_id=user_id
     │            (filter by created_at DESC, limit 1)
     │
     ├→ Attempt 2 (if no clips): IdentityService.get_linked_identities()
     │                           → Query identity_core for YouTube link
     │
     └→ Attempt 3 (if YouTube linked): YouTube search API
                                       GET /search?q=username&type=channel
  ↓
Return VideoShoutoutResult with video + channel + game info
  ↓
Record in database (shoutout_history table)
  ↓
Log audit event
  ↓
Return to caller for overlay widget display
```

### Auto-Shoutout Eligibility Flow
```
POST /api/v1/video-shoutout/auto-check
  ↓
Check if auto_shoutout_mode enabled in config
  ↓
Check if user in creators list
  ↓
Check trigger match:
  - trigger_type == 'first_message' and trigger_first_message enabled?
  - trigger_type == 'raid' and trigger_raid_host enabled?
  - trigger_type == 'host' and trigger_raid_host enabled?
  ↓
Check permission matches vso_permission
  ↓
Check user not on cooldown
  ↓
Return eligible: true/false
```

## Database Schema (Key Tables)

### shoutout_history
```sql
CREATE TABLE shoutout_history (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    target_username VARCHAR(255),
    target_platform VARCHAR(50),
    shoutout_text TEXT,
    triggered_by_user_id VARCHAR(255),
    triggered_by_username VARCHAR(255),
    shoutout_type VARCHAR(50),  -- 'manual' or 'auto'
    created_at TIMESTAMP DEFAULT NOW()
);
```

### video_shoutout_history
```sql
CREATE TABLE video_shoutout_history (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    target_username VARCHAR(255),
    target_platform VARCHAR(50),
    triggered_by_username VARCHAR(255),
    trigger_type VARCHAR(50),  -- 'manual', 'first_message', 'raid', 'host'
    video_id VARCHAR(255),
    video_platform VARCHAR(50),  -- 'twitch' or 'youtube'
    created_at TIMESTAMP DEFAULT NOW()
);
```

### shoutout_templates
```sql
CREATE TABLE shoutout_templates (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    platform VARCHAR(50),  -- 'twitch', 'discord', 'slack'
    is_live BOOLEAN DEFAULT TRUE,
    template TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### video_shoutout_config
```sql
CREATE TABLE video_shoutout_config (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL UNIQUE,
    so_enabled BOOLEAN DEFAULT TRUE,
    so_permission VARCHAR(50),  -- 'admin_only', 'mod', 'vip', 'subscriber', 'everyone'
    vso_enabled BOOLEAN DEFAULT TRUE,
    vso_permission VARCHAR(50),
    auto_shoutout_mode VARCHAR(50),  -- 'disabled', 'enabled', 'vips_only'
    trigger_first_message BOOLEAN DEFAULT FALSE,
    trigger_raid_host BOOLEAN DEFAULT TRUE,
    widget_position VARCHAR(50),  -- 'bottom-right', 'bottom-left', 'top-right', 'top-left'
    widget_duration_seconds INTEGER DEFAULT 30,
    cooldown_minutes INTEGER DEFAULT 60,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### auto_shoutout_creators
```sql
CREATE TABLE auto_shoutout_creators (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    platform VARCHAR(50),  -- 'twitch', 'youtube', 'discord'
    user_id VARCHAR(255),
    username VARCHAR(255),
    custom_trigger VARCHAR(50),  -- 'default', 'raid_only', 'host_only'
    added_at TIMESTAMP DEFAULT NOW()
);
```

## Error Handling & Resilience

### Circuit Breaker Pattern

Both TwitchService and VideoService implement circuit breakers to prevent cascading failures:

```
CLOSED (normal) → 5 failures → OPEN (reject requests) → 60s timeout → HALF_OPEN → on success → CLOSED
```

Failed requests while OPEN get error response immediately without attempting API call.

### Retry Logic

Retryable errors (network timeouts, 5xx responses) are retried up to 3 times with exponential backoff.

Non-retryable errors (4xx, invalid credentials) fail immediately.

### Timeout Management

- Twitch API calls: 10 second timeout
- YouTube API calls: 10 second timeout
- Identity service: 10 second timeout
- Database queries: 30 second timeout

### Fallback Behavior

Video shoutout fallback chain:
1. Twitch clips (preferred, fastest)
2. YouTube (via identity link)
3. Fail with descriptive error

Text shoutout never fails on API error; uses default template instead.

## Configuration & Secrets

Configuration loaded from:

1. **Environment Variables** (primary):
   - `TWITCH_CLIENT_ID`
   - `TWITCH_CLIENT_SECRET`
   - `YOUTUBE_API_KEY`
   - `DATABASE_URL`
   - `IDENTITY_URL`

2. **Database** (fallback):
   - Credentials from platform_integrations table
   - Allows runtime credential updates without restart

3. **Redis** (optional):
   - Listens for credential refresh events
   - Invalidates cached tokens on notification

## Logging & Monitoring

All module actions logged via AAA logging framework:

```python
logger.audit(
    action="create_shoutout",
    community=community_id,
    target_user=username,
    result="SUCCESS"
)
```

Logged events:
- Shoutout creation (success/failure)
- Video shoutout execution (success/failure)
- Auto-shoutout checks
- Template saves
- Config updates
- Creator list modifications
- Permission denials
- Cooldown triggers
- API failures (circuit breaker state)

## Security Considerations

1. **Authentication:** All protected endpoints require Bearer token
2. **Authorization:** Permission checking enforced at VideoShoutoutService level
3. **Rate Limiting:** Cooldown system prevents spam shoutouts
4. **Input Validation:** Username, community_id validated before API calls
5. **Error Messages:** Sensitive info (tokens, exact API errors) not exposed to clients
6. **Timeout Protection:** All external API calls have timeouts to prevent hanging
7. **Circuit Breaker:** Protects against cascading failures from Twitch/YouTube API issues
