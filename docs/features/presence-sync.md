# Presence Synchronization

Presence synchronization enables WaddleBot to keep user status information consistent across multiple connected platforms (Teams, Mattermost, Google Chat, Discord, Slack, etc.). This feature ensures that users' availability and status are reflected accurately wherever they work.

## Overview

The presence sync feature provides:
- **Unified Status Display**: User status appears consistently across all platforms
- **Bidirectional Sync**: Changes on one platform reflect on others automatically
- **Status Mapping**: Automatic translation of platform-specific status values
- **User Availability**: Track when users are available, away, busy, or offline
- **Real-time Updates**: Status changes propagate within seconds
- **Presence History**: Track user activity patterns and availability trends

## Platform Support Matrix

| Platform | Collect | Push | Notes |
|----------|---------|------|-------|
| Microsoft Teams | Yes | Yes | Full bidirectional support |
| Mattermost | Yes | Yes | Full bidirectional support |
| Google Chat | Yes | Yes | Full bidirectional support |
| Slack | Yes | Yes | Full bidirectional support |
| Discord | Yes | No | Collect-only: Discord doesn't allow bot presence changes |
| Apple iCloud | Yes | Yes | iCloud/Apple Contacts integration |
| Custom Status | Yes | Yes | Custom status text and emoji |

**Legend**:
- **Collect**: WaddleBot can read presence from this platform
- **Push**: WaddleBot can update user presence on this platform

## Status Mapping

WaddleBot normalizes platform-specific statuses to a unified model:

| Universal Status | Teams | Mattermost | Google Chat | Discord | Notes |
|------------------|-------|-----------|------------|---------|-------|
| `online` | Available | Online | Active | Online | User actively using the platform |
| `idle` | Idle/AwayFromDesktop | Away | Idle | Idle | User away from keyboard for <15 min |
| `busy` | In a meeting | Do Not Disturb | Out of office | Do Not Disturb | User busy or in meeting |
| `offline` | Offline | Offline | Inactive | Offline | User not currently signed in |
| `away` | Away | Away | Away | Idle (30+ min) | User intentionally away |
| `dnd` | Do Not Disturb | Do Not Disturb | Out of office | Do Not Disturb | User set DND status |

### Platform-Specific Mappings

**Microsoft Teams**:
- `Available` → `online`
- `Idle` → `idle`
- `BeRightBack` → `away`
- `Away` → `away`
- `DoNotDisturb` → `dnd`
- `Offline` → `offline`
- `PresenceUnknown` → `offline`

**Mattermost**:
- `online` → `online`
- `away` → `away`
- `offline` → `offline`
- `dnd` → `dnd` (Do Not Disturb)

**Google Chat**:
- `ACTIVE` → `online`
- `INACTIVE` → `idle`
- `OFFLINE` → `offline`

**Discord**:
- `online` → `online`
- `idle` → `idle`
- `dnd` (Do Not Disturb) → `dnd`
- `offline` → `offline`

**Slack**:
- `active` → `online`
- `away` → `away`
- `offline` → `offline`

## User Configuration

### Enabling Presence Sync

Users can control presence synchronization settings:

1. **Admin Interface**: Go to **Settings** → **Integrations** → **Presence Sync**
2. **Enable/Disable**: Toggle presence sync on or off
3. **Platform Selection**: Choose which platforms to sync across
4. **Primary Platform**: Select which platform's presence is authoritative

### User Settings

```
Presence Sync Configuration
├── Enable Presence Sync
│   └── Toggle on/off for this user
├── Primary Status Source
│   ├── Teams (if connected)
│   ├── Mattermost (if connected)
│   ├── Google Chat (if connected)
│   └── Slack (if connected)
├── Sync Targets
│   ├── [x] Microsoft Teams
│   ├── [x] Mattermost
│   ├── [x] Google Chat
│   ├── [x] Slack
│   └── [ ] Discord (collect-only)
├── Custom Status
│   ├── Text: "In a meeting"
│   ├── Emoji: 📞
│   └── Expires: [time selector]
└── Advanced
    ├── Sync Delay: 0-30 seconds
    ├── Auto-update Away: after X minutes
    └── Logging: [Off/On]
```

## How Presence Sync Works

### Real-time Status Updates

1. **Change Detection**: User changes status on any platform
2. **Collection**: WaddleBot presence module detects the change via:
   - Platform webhooks (Teams, Mattermost)
   - Polling with exponential backoff (Google Chat, Slack, Discord)
3. **Normalization**: Status mapped to unified format
4. **Distribution**: Status pushed to all other configured platforms
5. **Confirmation**: WaddleBot verifies update success

### Status Change Flow

```
User changes status in Teams
    ↓
Teams sends webhook to presence_module:8042
    ↓
Parse and normalize status (e.g., "Idle" → "idle")
    ↓
Look up user's other connected platforms
    ↓
Push to Mattermost, Google Chat, Slack, etc.
    ↓
Receive confirmation/wait for next poll cycle
    ↓
Update user's presence record in database
    ↓
Publish "presence_changed" event to subscribers
```

## Custom Status

Users can set custom status text and emoji that syncs across platforms:

### Setting Custom Status

1. Go to **User Profile** → **Status**
2. Click "Set Custom Status"
3. Enter:
   - **Text**: Up to 250 characters (e.g., "In a meeting", "Working from home")
   - **Emoji**: Select from emoji picker or type (e.g., `:coffee:`, 📞)
   - **Expires**: Set expiration time (1 hour, 4 hours, end of day, custom)
4. Click "Set"

### Custom Status Mapping

Custom status text is preserved across platforms where supported:

| Platform | Custom Text | Emoji | Notes |
|----------|------------|-------|-------|
| Teams | Yes | Yes | Full support |
| Mattermost | Yes | Yes | Full support |
| Google Chat | Yes | Yes | Full support |
| Slack | Yes | Yes | Full support |
| Discord | Limited | Yes | Text limited to username only |

## Database Schema

Presence data is stored in the `user_presence` table:

```sql
CREATE TABLE user_presence (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    custom_status TEXT,
    custom_emoji VARCHAR(255),
    last_updated TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    device_type VARCHAR(50),
    client_type VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, platform)
);

CREATE TABLE presence_history (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    custom_status TEXT,
    changed_at TIMESTAMP NOT NULL,
    changed_by VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Limitations and Constraints

### Discord Limitation

Discord does not provide a public API for bots to change user presence. Therefore:
- **Collect Only**: WaddleBot can read Discord presence status
- **No Push**: WaddleBot cannot update presence in Discord
- **Workaround**: Manual status updates, or integrate Discord with other platforms that support bidirectional sync

### Rate Limiting Considerations

Each platform has rate limits on presence changes:

| Platform | Limit | Window | Backoff |
|----------|-------|--------|---------|
| Teams | 60 updates | Per minute | 1s → 60s |
| Mattermost | 30 updates | Per minute | 1s → 30s |
| Google Chat | 10 updates | Per minute | 5s → 60s |
| Slack | 20 updates | Per minute | 2s → 30s |
| Discord | N/A (read-only) | N/A | N/A |

The presence module implements intelligent batching and exponential backoff to respect these limits.

### Timezone Considerations

Custom status expiration times are stored in UTC. The frontend displays expiration times in the user's local timezone:

```javascript
// Expiration time conversion
expiresAt (UTC: 2026-02-28T18:00:00Z)
  ↓
User timezone: America/New_York (EST -5)
  ↓
Display: 2026-02-28 1:00 PM EST
```

## Privacy and Permissions

### Privacy Controls

Users can configure who sees their presence:

- **Public**: All workspace members
- **Team Only**: Team members only
- **Direct Contacts**: Selected contacts only
- **Admin Only**: Administrators only
- **Hidden**: No one (offline status only)

### Permission Requirements

| Action | Required Permission |
|--------|-------------------|
| View own presence | None (always allowed) |
| View team presence | `view_team_presence` |
| View all presence | `admin` or `view_all_presence` |
| Change own presence | `change_own_presence` |
| Change others' presence | `admin` or `change_user_presence` |

## Troubleshooting

### Presence Not Syncing

**Problem**: Status changes on one platform don't appear on others

**Solutions**:
1. Verify user has presence sync enabled in settings
2. Check all platforms are connected and authenticated
3. Verify user has connected accounts on target platforms
4. Check presence module logs for sync errors
5. Wait up to 30 seconds for next polling cycle (if webhook isn't available)

### Incorrect Status Mapping

**Problem**: Status appears wrong on some platforms

**Solutions**:
1. Check status mapping in `config.py` matches platform-specific values
2. Verify platform APIs return expected status values
3. Check for platform-specific status values not in mapping (edge cases)
4. Review presence_sync module logs for parsing errors

### Sync Delays

**Problem**: Status updates take a long time to sync

**Solutions**:
1. Configure webhook endpoints for faster push delivery
2. Reduce polling interval if using polling fallback
3. Check network connectivity between WaddleBot and platforms
4. Verify rate limiting isn't delaying updates

## Performance Optimization

The presence module implements several optimizations:

1. **Webhook Delivery**: Instant delivery via webhooks where available
2. **Polling with Backoff**: Exponential backoff reduces API calls when unchanged
3. **Batching**: Multiple updates batched into single API calls
4. **Caching**: Recent presence cached to reduce database queries
5. **Event Streaming**: Redis pub/sub for real-time status updates

## Future Enhancements

Planned improvements to presence sync:

- **Proximity Detection**: Use location data to adjust availability
- **Calendar Integration**: Auto-update based on calendar events
- **Context Awareness**: Status based on current activity
- **Mobile Integration**: Mobile app presence support
- **Presence Analytics**: Reports on user availability patterns

## Additional Resources

- [Presence Module Source](../../action/interactive/presence_module/)
- [Platform Integration Guides](./README.md)
- [User Settings Documentation](../features/user-settings.md)
- [API Reference](../api/presence-endpoints.md)
