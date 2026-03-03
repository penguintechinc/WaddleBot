# Community Calendar Subscriptions

Community calendars enable organizations to create shared calendars for team events, company holidays, vacation tracking, and other community-wide schedules. This feature allows users to easily subscribe to relevant calendars and stay informed about important events.

## Overview

The community calendars feature provides:
- **Shared Calendar Creation**: Teams create calendars for their groups
- **Public Subscription**: Users discover and subscribe to calendars
- **Event Updates**: Real-time notifications for new and updated events
- **Integration**: Community events appear alongside personal calendars
- **ICAL Export**: Download calendar in standard ICS format
- **Calendar Embedding**: Embed calendars in team pages or wikis
- **Permission Management**: Control who can view, edit, or subscribe
- **Search & Discovery**: Find relevant community calendars easily

## What Are Community Calendars?

Community calendars are shared event calendars managed by team leads, admins, or designated calendar managers. Unlike personal calendars, they're designed to be discoverable and subscribed to by multiple users.

### Common Use Cases

- **Team Calendars**: Team meetings, sprints, team outings
- **Company Holidays**: National and company-specific holidays
- **Vacation Tracking**: Team members' vacation schedules (optional detail level)
- **Conference Calendars**: Industry events, team attendance
- **Office Closures**: Building closures, office facility events
- **Product Launches**: Company-wide launch dates and milestones
- **Executive Calendars**: C-level calendars (when publicly available)
- **On-Call Schedules**: Engineering on-call rotations
- **Sales Pipeline**: Deal deadlines, customer events

## Creating Community Calendars

### Step 1: Create Calendar

1. Go to **Calendars** → **Community Calendars**
2. Click "Create Calendar"
3. Configure:
   - **Calendar Name**: "Q1 Team Events"
   - **Description**: "Engineering team meetings and events"
   - **Color**: Choose calendar color for visibility
   - **Icon**: Select relevant emoji (📅, 🎯, 🎉, etc.)
4. Click "Create"

### Step 2: Configure Permissions

Set access levels for your community calendar:

| Role | Permissions |
|------|-------------|
| **Owner** | Can view, edit, delete all events; manage permissions |
| **Manager** | Can view, create, edit, delete own events; manage permissions |
| **Editor** | Can view all events; create and edit own events |
| **Viewer** | Can view all events; cannot edit |
| **Public** | Can view (if calendar is public) |

**Default Configuration**:
```
Owner: Calendar Creator
Managers: Team Leads
Editors: Team Members (if invited)
Viewers: Public (if enabled)
```

### Step 3: Manage Members

Add users who should have access:

1. Open calendar settings
2. Go to "Members"
3. Click "Add Member"
4. Search for user by name/email
5. Select role: Owner, Manager, Editor, Viewer
6. Send invitation

## Subscribing to Community Calendars

### Discovery

Users can find community calendars in multiple ways:

**1. Calendar Directory**
- Go to **Calendars** → **Discover**
- Browse calendars by category
- Search by name or keyword

**2. Team Page**
- Each team has "Calendars" section
- Shows calendars for that team
- One-click subscribe

**3. Sidebar**
- Right-click workspace
- Select "Browse Calendars"
- Search and subscribe

### Subscribe to Calendar

1. Find calendar in directory or team page
2. Click "Subscribe"
3. Configure subscription:
   - **Calendar Name**: Keep default or customize
   - **Color**: Choose display color
   - **Notifications**: Enable/disable event alerts
   - **Show Details**: Show event details or just busy time
4. Click "Subscribe"

### Unsubscribe

1. In sidebar, hover over calendar
2. Click the three-dot menu
3. Select "Unsubscribe"
4. Confirm

## Dedicated Calendar Creation

When a user subscribes to a community calendar, WaddleBot automatically creates a dedicated calendar to store subscribed events.

### Dedicated Calendar Structure

```
User's Calendar List:
├── Personal Calendar (primary)
├── Work Calendar
├── Shared Calendar (spouse/family)
├── Subscribed Community Calendars (dedicated folder)
│   ├── 🎯 Q1 Team Events (engineering-team-q1)
│   ├── 🎉 Company Events (company-events)
│   ├── 🏢 Office Closures (office-closures)
│   └── 📞 On-Call Schedule (engineering-oncall)
└── Archive (hidden)
    └── Old calendars (read-only)
```

### Technical Details

**Database Entry**:
```sql
INSERT INTO user_calendars (
    user_id,
    provider,
    provider_calendar_id,
    calendar_name,
    access_token,
    is_primary,
    is_active
) VALUES (
    'user-123',
    'community',
    'engineering-team-q1',
    'Q1 Team Events',
    'token...',
    FALSE,
    TRUE
);
```

**Calendar Naming Convention**:
```
Type: community
Source: {community-calendar-id}
Display Name: {calendar-name}
Unique ID: user-{user_id}-community-{calendar_id}
```

## Event Sync and Updates

### Initial Subscription Sync

When a user subscribes to a community calendar:

1. **Fetch Events**: Retrieve all current events from source calendar
2. **Create Dedicated Calendar**: Set up subscription-specific calendar
3. **Sync Events**: Import events to user's dedicated calendar
4. **Set Permissions**: Read-only access (if not a manager)
5. **Enable Notifications**: Configure reminders (if enabled)
6. **Index Events**: Make events searchable

### Ongoing Synchronization

Changes to community calendar events automatically sync:

1. **New Event**: Added to all subscribers' calendars
2. **Updated Event**: Changes reflected in all subscribers' calendars
3. **Deleted Event**: Removed from all subscribers' calendars
4. **Time Changed**: All subscribers notified of new time
5. **Recurrence Updated**: Recurring event changes apply to all instances

### Sync Frequency

- **Real-time**: Webhook delivery (instant)
- **Polling Fallback**: Every 5-15 minutes if no webhook
- **Batch Sync**: At subscription time (fetch last 3 months)

## Notification Settings

Users control notifications for subscribed calendars:

### Per-Calendar Settings

```
Calendar: Q1 Team Events

Notification Preferences
├── Event Created Notification: [ON]
│   └── Send: 0 minutes before (immediately)
├── Event Updated Notification: [ON]
│   └── Send: 0 minutes before (immediately)
├── Event Starting Soon: [ON]
│   └── Send: 15 minutes before
├── Daily Digest: [OFF]
│   └── Send time: 08:00 AM
├── Notification Channels: [Teams] [Slack] [Email]
└── Do Not Disturb: 6:00 PM - 8:00 AM
```

### Default Notification Behavior

```
New Event in Community Calendar
    ↓
Check user's notification settings
    ↓
Is user free/not in DND? → Send notification
    ↓
User notification preferences: [Channels selected]
    ↓
Send via Teams, Slack, Email as configured
```

## ICAL Export and Calendar Links

### Share Calendar View

Users can export community calendars in standard formats:

**1. ICS Download**
- Go to calendar
- Click three-dot menu
- Select "Download ICS"
- Save calendar.ics file
- Import into any calendar app

**2. Calendar Link (Read-only)**
- Go to calendar
- Click three-dot menu
- Select "Get Calendar Link"
- Copy URL: `https://your-domain/calendar/shared/{calendar-id}`
- Share with non-users
- Others can view without account

**3. Webcal Subscription**
- For Outlook, Apple Calendar, Google Calendar
- URL format: `webcal://your-domain/calendar/ical/{calendar-id}`
- Add to calendar app as "Subscribe to calendar"

**4. Embed in Website**
- Get embed code
- Paste in wiki, team page, or website
- Live calendar view

## Dedicated Calendar Features

Dedicated community calendars have special features:

### Event Details

Community calendar events show:
- **Title**: Event name
- **Time**: Start and end times
- **Location**: Physical or virtual location
- **Organizer**: Who scheduled the event
- **Attendee Count**: Number of attendees (if visible)
- **Description**: Event details (if available)
- **Update History**: When event was last changed

### Search and Filter

Find events across subscribed calendars:

```
Search: team sprint
Filters:
├── Calendar: [All] [Q1 Team Events]
├── Date Range: [Last 30 days]
├── Event Type: [All] [Meeting] [Holiday]
└── Organizer: [All organizers]

Results: 12 events found
```

### Busy Time Display

By default, community calendars show "busy" blocks without details to protect privacy:

```
Default (Privacy-friendly):
┌─────────────────────────────┐
│ 2:00 PM - 3:00 PM │ Busy    │
└─────────────────────────────┘

With Permissions (Manager/Owner):
┌─────────────────────────────┐
│ 2:00 PM - 3:00 PM │         │
│ Team Sync Meeting            │
│ Conference Room A            │
│ 8 attendees                  │
└─────────────────────────────┘
```

## Managing Subscriptions

### View Active Subscriptions

1. Go to **Calendars**
2. Scroll to "Community Calendars"
3. See all subscribed calendars
4. View subscription status (active, paused, archived)

### Pause Subscription

Temporarily hide a calendar without unsubscribing:

1. Hover over calendar
2. Click three-dot menu
3. Select "Pause"
4. Events won't appear until re-enabled
5. Hover again and select "Resume"

### Archive Old Subscriptions

Move inactive subscriptions out of view:

1. Click three-dot menu
2. Select "Archive"
3. Calendar moves to "Archived" section
4. Can restore later if needed

### Export Subscription

Download all events from a subscribed calendar:

1. Click three-dot menu
2. Select "Export"
3. Choose format: ICS, CSV, or PDF
4. Download file

## Database Schema

Community calendars are stored using the same `user_calendars` table with `provider = 'community'`:

```sql
-- Community calendar definition
CREATE TABLE community_calendars (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7),  -- hex color
    icon VARCHAR(50),  -- emoji
    creator_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    is_public BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    sync_frequency INT DEFAULT 300,  -- seconds
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (creator_id) REFERENCES users(id)
);

-- Permissions for community calendars
CREATE TABLE community_calendar_permissions (
    id UUID PRIMARY KEY,
    community_calendar_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role VARCHAR(50),  -- owner, manager, editor, viewer
    granted_at TIMESTAMP,
    granted_by UUID,
    FOREIGN KEY (community_calendar_id) REFERENCES community_calendars(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(community_calendar_id, user_id)
);

-- User subscriptions
CREATE TABLE calendar_subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    community_calendar_id UUID NOT NULL,
    dedicated_calendar_id UUID,
    subscribed_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true,
    notifications_enabled BOOLEAN DEFAULT true,
    show_details BOOLEAN DEFAULT true,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (community_calendar_id) REFERENCES community_calendars(id),
    FOREIGN KEY (dedicated_calendar_id) REFERENCES user_calendars(id),
    UNIQUE(user_id, community_calendar_id)
);
```

## Troubleshooting

### Events Not Showing Up

**Problem**: Subscribed calendar is empty or missing events

**Solutions**:
1. Verify subscription is active (not paused)
2. Check calendar has events in source
3. Try manual refresh: calendar settings → "Sync Now"
4. Check date range of subscription
5. Verify permissions allow viewing events

### Notification Not Working

**Problem**: Don't receive notifications for calendar events

**Solutions**:
1. Verify notifications enabled in calendar settings
2. Check notification channels are active (Teams, Slack)
3. Verify Do Not Disturb isn't blocking
4. Check user notification preferences globally
5. Review module logs for delivery errors

### Cannot Subscribe

**Problem**: "Subscribe" button doesn't work or shows error

**Solutions**:
1. Verify calendar is public or you're invited
2. Check you're logged in
3. Try refreshing browser
4. Clear browser cache
5. Contact calendar owner if permissions issue

## Best Practices

1. **Clear Naming**: Use descriptive calendar names
2. **Regular Updates**: Keep events current and remove old ones
3. **Permission Management**: Grant minimum necessary permissions
4. **Notification Settings**: Configure sensible defaults
5. **Documentation**: Add descriptions for clarity
6. **Archive**: Regularly archive old calendars
7. **Color Coding**: Use consistent colors by category

## Additional Resources

- [Calendar Sync Documentation](./calendar-sync.md)
- [Community Guidelines](../community/guidelines.md)
- [Calendar API Endpoints](../api/calendar-endpoints.md)
- [Notification Settings Guide](./notification-settings.md)
