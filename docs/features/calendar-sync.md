# Calendar Synchronization

Calendar synchronization enables WaddleBot to integrate with users' calendars across multiple providers, facilitating meeting coordination, automatic status updates, and intelligent scheduling. This feature supports Google Calendar, Microsoft Outlook, and Apple Calendar with bidirectional sync capabilities.

## Overview

The calendar sync feature provides:
- **Multi-Calendar Integration**: Support for Google, Microsoft, and Apple calendars
- **Bidirectional Synchronization**: Changes sync in both directions
- **Meeting Detection**: Automatic identification of meetings and busy times
- **Auto-Status Update**: Presence automatically updates during meetings
- **Conflict Resolution**: Intelligent handling of calendar conflicts
- **Free/Busy Sharing**: Share availability without exposing meeting details
- **Event Notifications**: Alerts before meetings and at configurable intervals
- **Calendar Analytics**: Insights into meeting patterns and time availability

## Supported Calendar Providers

### Google Calendar

**Features**:
- Read/write access to all calendars
- Support for recurring events
- Integration with Google Meet
- Google Workspace domain integration
- Real-time change notifications via webhook

**OAuth Scopes**:
```
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/calendar.events.readonly
```

### Microsoft Outlook Calendar

**Features**:
- Read/write access to mailbox calendar
- Support for recurring events and series
- Microsoft Teams meeting integration
- Outlook categorization support
- Change notifications via Microsoft Graph webhooks

**OAuth Scopes**:
```
Calendars.Read
Calendars.ReadWrite
Calendars.Read.Shared
Calendars.ReadWrite.Shared
Events.Read
Events.Create
Events.ReadWrite
```

### Apple Calendar (iCloud)

**Features**:
- Read/write access via CalDAV protocol
- Support for shared calendars
- Integration with Apple Contacts
- Event attachments support
- Email-based notifications

**Connection Method**: CalDAV (WebDAV-based)
- **Server**: https://caldav.icloud.com/
- **Port**: 443 (HTTPS)
- **Authentication**: App-specific password (not user password)

## OAuth Setup

### Google Calendar OAuth

#### Step 1: Configure Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (create if needed)
3. Enable the **Google Calendar API**
4. Go to **APIs & Services** → **Credentials**
5. Click "Create Credentials" → "OAuth 2.0 Client ID"
6. Select "Web application"
7. Configure:
   - **Name**: "WaddleBot Calendar Sync"
   - **Authorized JavaScript origins**: `https://your-domain`
   - **Authorized redirect URIs**:
     - `https://your-domain/auth/google/callback`
     - `https://your-domain/auth/callback`
8. Save the Client ID and Client Secret

#### Step 2: Environment Variables

```bash
export GOOGLE_CALENDAR_CLIENT_ID="xxx.apps.googleusercontent.com"
export GOOGLE_CALENDAR_CLIENT_SECRET="xxxxxx"
export GOOGLE_CALENDAR_REDIRECT_URI="https://your-domain/auth/google/callback"
```

### Microsoft Outlook OAuth

#### Step 1: Register Application

1. Go to [Azure App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/RegisteredApps)
2. Click "New registration"
3. Configure:
   - **Name**: "WaddleBot Calendar Sync"
   - **Supported account types**: "Accounts in this organizational directory"
   - **Redirect URI**: `https://your-domain/auth/microsoft/callback`
4. Click "Register"

#### Step 2: Configure Credentials

1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Copy the secret value
4. Go to "API permissions"
5. Add permissions:
   - **Calendars.ReadWrite**
   - **Events.ReadWrite**
   - **User.Read**
6. Grant admin consent

#### Step 3: Environment Variables

```bash
export MICROSOFT_CLIENT_ID="xxxxx"
export MICROSOFT_CLIENT_SECRET="xxxxx"
export MICROSOFT_REDIRECT_URI="https://your-domain/auth/microsoft/callback"
export MICROSOFT_TENANT_ID="common"  # or specific tenant
```

### Apple Calendar (CalDAV)

#### Step 1: Generate App-Specific Password

1. Go to [appleid.apple.com](https://appleid.apple.com)
2. Sign in and navigate to "Security" section
3. Click "Generate Password" under "App-specific passwords"
4. Select "Calendar"
5. Copy the generated password

#### Step 2: Store Credentials

Store credentials securely in database or secret management system:

```python
# Example schema
calendar_credentials = {
    "provider": "apple",
    "username": "user@icloud.com",
    "password": "<app-specific-password>",
    "caldav_url": "https://caldav.icloud.com/",
    "encrypted": True  # Always encrypt stored passwords
}
```

## Calendar Synchronization

### Event Sync Process

1. **Initial Sync**: Fetch all events from all connected calendars
2. **Merge & Deduplicate**: Combine events, remove duplicates
3. **Conflict Resolution**: Handle overlapping events
4. **Status Mapping**: Update user presence based on meetings
5. **Notification Queue**: Schedule reminders
6. **Change Detection**: Monitor for updates
7. **Propagate Changes**: Sync changes to other calendars

### Real-time Sync

For Google and Microsoft calendars, WaddleBot uses webhooks for instant updates:

**Google Calendar Webhook**:
- Webhook endpoint: `https://your-domain/calendar/webhooks/google`
- Channel expiration: 24 hours (auto-renewed)

**Microsoft Graph Webhook**:
- Webhook endpoint: `https://your-domain/calendar/webhooks/microsoft`
- Subscription validity: 4230 minutes (auto-renewed at 85% expiry)

### Polling Fallback

For Apple Calendar or when webhooks aren't available:

```python
# Polling schedule
POLLING_INTERVALS = {
    'first_poll': 30,      # seconds - check 30s after change
    'min_interval': 60,    # minimum 1 minute between polls
    'max_interval': 3600,  # maximum 1 hour between polls
    'backoff_factor': 1.5  # exponential backoff multiplier
}
```

## Conflict Resolution

When the same event appears in multiple calendars, WaddleBot uses this strategy:

### Detection

```
Conflict occurs when:
- Same time period
- Overlapping attendees
- Same or similar titles
- Within 15 minutes of each other
```

### Resolution Strategy

```
1. Compare event sources (primary calendar wins)
2. Check event IDs (if same event in multiple providers)
3. Compare content hash (same title, time, attendees)
4. Apply user's conflict resolution preference:
   - Primary-first (default): Keep primary calendar event
   - Merge: Combine details from both events
   - Manual: Ask user to resolve
5. Store resolution decision for future reference
```

### Example Conflict

```
Calendar A (Google): "Team Meeting" 2-3 PM
Calendar B (Outlook): "Team Standup" 2:30-3 PM

Conflict Type: Overlap (15 min shared)
Resolution: Keep "Team Meeting" (primary), note conflict
Result: Single event "Team Meeting" 2-3 PM in merged calendar
```

## Meeting Detection

WaddleBot automatically identifies meetings based on:

- **Event Type**: Marked as "meeting" or has multiple attendees
- **Duration**: Typically 15 minutes or longer
- **Attendee Count**: 2 or more attendees
- **Meeting Details**: Contains video conference URL
- **Calendar Classification**: Event marked as "busy"

### Meeting Metadata

For each detected meeting:

```python
{
    "meeting_id": "uuid",
    "title": "Q1 Planning Session",
    "start_time": "2026-02-28T14:00:00Z",
    "end_time": "2026-02-28T15:30:00Z",
    "duration_minutes": 90,
    "attendee_count": 8,
    "organizer": "jane@company.com",
    "video_conference_url": "https://meet.google.com/abc-defg-hij",
    "location": "Conference Room B",
    "is_recurring": False,
    "calendar_source": "google",
    "busy_status": "busy",
    "response_status": "accepted"
}
```

## Auto-Status Update

WaddleBot automatically updates user presence during meetings:

### Configuration

Users can enable auto-status in calendar settings:

```
Auto-Status Configuration
├── Enable Auto-Status Update: [ON/OFF]
├── Status During Meetings: [idle/busy/dnd]
├── Include Calendar Title: [ON/OFF]
├── Include Meeting Organizer: [ON/OFF]
├── Prepare Time: 5 minutes before
│   └── Auto-update to "busy"
└── Buffer Time: 5 minutes after
    └── Auto-update to "available"
```

### Status Update Flow

```
1. Meeting starts in 5 minutes
2. Update status to "busy"
3. Set custom status: "In Q1 Planning Session"
4. Sync status to all platforms (Teams, Slack, etc.)
5. When meeting ends + 5 min buffer
6. Revert to "available"
```

## Free/Busy Sharing

Users can share free/busy information without exposing meeting details:

### What's Shared

```
Shared:
- Time blocks marked as busy
- Duration of busy periods
- Overall availability percentage

NOT Shared:
- Meeting titles
- Meeting descriptions
- Attendee lists
- Location information
```

### Configuration

```
Free/Busy Settings
├── Share Free/Busy Info: [ON/OFF]
├── Visibility: [Public/Team/Contacts]
├── Include Recurring: [ON/OFF]
├── Look-ahead Period: [1/2/4] weeks
└── Update Frequency: Real-time
```

## Event Notifications

WaddleBot sends notifications at configurable intervals before meetings:

### Default Notification Schedule

- **60 minutes before**: Initial notification
- **15 minutes before**: Urgent reminder
- **At meeting time**: Join reminder (if video conference)

### Customization

Users can adjust notification timing:

```
Notification Preferences
├── 60-min notification: [ON] Duration: [5 min read]
├── 15-min notification: [ON] Duration: [2 min read]
├── At-time notification: [ON] "Join meeting now"
├── Platforms: [Teams/Slack/Email/SMS]
└── Do Not Disturb: [Enable DND during meetings]
```

## Database Schema

Calendar data is stored in these tables:

```sql
CREATE TABLE user_calendars (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL,  -- google, microsoft, apple
    provider_calendar_id VARCHAR(255) NOT NULL,
    calendar_name VARCHAR(255),
    access_token TEXT NOT NULL,     -- encrypted
    refresh_token TEXT,             -- encrypted
    is_primary BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    synced_at TIMESTAMP,
    next_sync_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, provider, provider_calendar_id)
);

CREATE TABLE calendar_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    provider_event_id VARCHAR(255),
    calendar_id UUID NOT NULL,
    title VARCHAR(255),
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    is_all_day BOOLEAN DEFAULT false,
    is_recurring BOOLEAN DEFAULT false,
    location VARCHAR(255),
    organizer_email VARCHAR(255),
    attendee_count INT DEFAULT 1,
    video_conference_url TEXT,
    busy_status VARCHAR(50),  -- busy, free, tentative
    response_status VARCHAR(50),  -- accepted, tentative, declined
    last_updated TIMESTAMP,
    synced_from VARCHAR(50),  -- primary calendar
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (calendar_id) REFERENCES user_calendars(id),
    UNIQUE(user_id, provider_event_id)
);

CREATE TABLE calendar_conflicts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    event_id_1 UUID NOT NULL,
    event_id_2 UUID NOT NULL,
    conflict_type VARCHAR(50),  -- overlap, duplicate, etc
    resolution VARCHAR(50),  -- primary, merge, manual
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (event_id_1) REFERENCES calendar_events(id),
    FOREIGN KEY (event_id_2) REFERENCES calendar_events(id)
);
```

## Troubleshooting

### Calendar Not Syncing

**Problem**: Events don't appear after connecting calendar

**Solutions**:
1. Verify OAuth token is valid
2. Check calendar access permissions in provider settings
3. Try manual sync from settings page
4. Check module logs for authentication errors
5. Ensure calendar is not hidden/archived

### Conflicting Events

**Problem**: Same event appears multiple times

**Solutions**:
1. Check calendar provider for duplicate events
2. Verify conflict resolution settings
3. Manually mark one as "duplicate" to suppress
4. Review recent calendar changes in history

### Status Not Updating

**Problem**: Presence doesn't update during meetings

**Solutions**:
1. Verify auto-status is enabled in calendar settings
2. Check calendar sync is current (no delays)
3. Verify meeting detection found the event
4. Check presence sync module is running
5. Review logs for status update failures

## Performance Optimization

Calendar sync implements several optimizations:

1. **Incremental Sync**: Only fetch changed events since last sync
2. **Caching**: Cache events locally for faster queries
3. **Webhook Priority**: Use webhooks for instant updates
4. **Polling Backoff**: Reduce polling frequency when no changes
5. **Batch Operations**: Combine multiple sync operations
6. **Database Indexes**: Optimize queries on large datasets

## Privacy and Security

- **Encryption**: OAuth tokens stored encrypted in database
- **Scope Limiting**: Request minimum necessary OAuth scopes
- **Data Retention**: Event data retained per user retention policy
- **Access Control**: Only user can access their calendar data
- **Audit Logging**: Track all calendar access and modifications

## Future Enhancements

Planned improvements:

- **Slack Calendar Integration**: Sync with Slack events
- **Timezone Awareness**: Automatic timezone conversion
- **Meeting Recordings**: Automatic recording links in invites
- **Calendar Analytics**: AI-powered insights on availability
- **Smart Scheduling**: AI recommends optimal meeting times

## Additional Resources

- [Calendar Sync Module Source](../../action/interactive/calendar_module/)
- [OAuth Integration Guide](./oauth-setup.md)
- [User Settings Documentation](./user-settings.md)
- [API Reference](../api/calendar-endpoints.md)
