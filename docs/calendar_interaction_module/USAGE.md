# Calendar Interaction Module — Usage Guide

## Overview

This guide covers running the Calendar Interaction Module locally, connecting OAuth calendars, creating booking pages, and using the event management system end to end.

**Module version**: 2.0.0
**Default port**: 8030

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Running Locally](#running-locally)
3. [Health Check](#health-check)
4. [OAuth Setup Walkthrough](#oauth-setup-walkthrough)
5. [Connecting a Google Calendar](#connecting-a-google-calendar)
6. [Connecting a Microsoft Calendar](#connecting-a-microsoft-calendar)
7. [Availability Configuration](#availability-configuration)
8. [Individual Booking Page Workflow](#individual-booking-page-workflow)
9. [Group Booking Page Workflow](#group-booking-page-workflow)
10. [Event Management Workflow](#event-management-workflow)
11. [RSVP Workflow](#rsvp-workflow)
12. [Ticketing Workflow](#ticketing-workflow)

---

## Prerequisites

- Python 3.10+
- PostgreSQL database with WaddleBot schema applied
- (Optional) Redis for credential refresh notifications
- Google Cloud project with Calendar API enabled and OAuth 2.0 credentials
- Microsoft Azure App Registration with `Calendars.Read` scope
- WaddleBot router service reachable at `CORE_API_URL`

Install Python dependencies:

```bash
cd action/interactive/calendar_interaction_module
pip install -r requirements.txt
```

---

## Running Locally

Copy the environment template and fill in your values:

```bash
cp .env.example .env
# Edit .env with your database URL, OAuth credentials, etc.
```

Start the module:

```bash
MODULE_PORT=8030 python app.py
```

Or with all environment variables set:

```bash
DATABASE_URL="postgresql://waddlebot:password@localhost:5432/waddlebot" \
GOOGLE_CALENDAR_CLIENT_ID="your-google-client-id" \
GOOGLE_CALENDAR_CLIENT_SECRET="your-google-client-secret" \
MICROSOFT_CALENDAR_CLIENT_ID="your-ms-client-id" \
MICROSOFT_CALENDAR_CLIENT_SECRET="your-ms-client-secret" \
MODULE_PORT=8030 \
python app.py
```

The module starts an async Quart server. You should see startup log output indicating the database was initialized and services were wired.

---

## Health Check

Once running, verify the module is healthy:

```bash
curl http://localhost:8030/health
```

Expected response:

```json
{
  "status": "healthy",
  "module": "calendar_interaction_module",
  "version": "2.0.0"
}
```

---

## OAuth Setup Walkthrough

Before users can connect external calendars, you must configure OAuth applications in both Google Cloud Console and Microsoft Azure.

### Google Calendar API Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project or select an existing one
3. Enable the **Google Calendar API** under APIs & Services
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Set application type to **Web application**
6. Add your redirect URI: `https://your-domain.com/api/v1/calendar/oauth/google/callback`
7. Copy the **Client ID** and **Client Secret** into your environment as `GOOGLE_CALENDAR_CLIENT_ID` and `GOOGLE_CALENDAR_CLIENT_SECRET`

The module requests the scope `https://www.googleapis.com/auth/calendar.readonly` with `access_type=offline` and `prompt=consent` to ensure a refresh token is always issued.

### Microsoft Azure App Registration

1. Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **New registration**; set name and select **Accounts in any organizational directory and personal Microsoft accounts** for multi-tenant support
3. Under **Authentication** → **Platform configurations**, add **Web** with redirect URI: `https://your-domain.com/api/v1/calendar/oauth/microsoft/callback`
4. Under **API permissions**, add `Calendars.Read` (Delegated)
5. Under **Certificates & secrets**, create a new client secret
6. Copy the **Application (client) ID** and the **client secret value** into `MICROSOFT_CALENDAR_CLIENT_ID` and `MICROSOFT_CALENDAR_CLIENT_SECRET`

---

## Connecting a Google Calendar

### Step 1 — Get the Authorization URL

```bash
curl "http://localhost:8030/api/v1/calendar/oauth/google/auth-url?user_id=42&redirect_uri=https://your-domain.com/api/v1/calendar/oauth/google/callback"
```

Response:

```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&scope=https://www.googleapis.com/auth/calendar.readonly&access_type=offline&prompt=consent&state=42"
}
```

### Step 2 — User Visits the Authorization URL

Direct the user to the `auth_url`. Google will prompt them to authorize access to their calendar. After approval, Google redirects to your callback URL with `?code=AUTHORIZATION_CODE&state=USER_ID`.

### Step 3 — Handle the Callback

The callback endpoint is called automatically by Google's redirect. Internally it:
1. Exchanges the authorization code for an access token and refresh token via `https://oauth2.googleapis.com/token`
2. Stores tokens in the `platform_integrations` table with `platform='google_calendar'` and `integration_type='user_oauth'`
3. Creates a record in `connected_calendars` with `provider='google'` and `calendar_id='primary'`

You can also trigger this manually for testing:

```bash
curl "http://localhost:8030/api/v1/calendar/oauth/google/callback?code=AUTH_CODE&state=42&redirect_uri=https://your-domain.com/..."
```

### Step 4 — Sync Free/Busy Data

After connecting, trigger a free/busy sync for a time range:

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/oauth/calendars/1/sync" \
  -H "Content-Type: application/json" \
  -d '{"start": "2026-02-16T00:00:00Z", "end": "2026-02-23T00:00:00Z"}'
```

### Step 5 — List Connected Calendars

```bash
curl "http://localhost:8030/api/v1/calendar/oauth/calendars?user_id=42"
```

---

## Connecting a Microsoft Calendar

### Step 1 — Get the Authorization URL

```bash
curl "http://localhost:8030/api/v1/calendar/oauth/microsoft/auth-url?user_id=42&redirect_uri=https://your-domain.com/api/v1/calendar/oauth/microsoft/callback"
```

### Step 2 — User Authorizes via Microsoft

Microsoft redirects back with an authorization code. The callback at `/api/v1/calendar/oauth/microsoft/callback` exchanges this for tokens via the Azure common OAuth endpoint.

The module stores tokens with `platform='microsoft_calendar'` and creates a `connected_calendars` record with `provider='microsoft'` and `calendar_id='default'`.

---

## Availability Configuration

Set your weekly availability windows (these define when you can accept bookings):

```bash
curl -X PUT "http://localhost:8030/api/v1/calendar/availability/weekly" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "availability": {
      "monday": [{"start": "09:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}],
      "tuesday": [{"start": "09:00", "end": "17:00"}],
      "wednesday": [{"start": "09:00", "end": "17:00"}],
      "thursday": [{"start": "09:00", "end": "17:00"}],
      "friday": [{"start": "09:00", "end": "13:00"}]
    }
  }'
```

Configure booking constraints:

```bash
curl -X PUT "http://localhost:8030/api/v1/calendar/availability/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "min_notice_hours": 4,
    "max_future_days": 30,
    "buffer_minutes": 15,
    "slot_durations": [30, 60],
    "default_slot_duration": 30,
    "booking_enabled": true
  }'
```

Check what slots are available for a user on a specific date:

```bash
curl "http://localhost:8030/api/v1/calendar/availability/42/slots?date=2026-02-20&slot_duration=30"
```

---

## Individual Booking Page Workflow

### Create a Booking Page

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/booking-pages" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "slug": "alice-30min",
    "title": "30-Minute Meeting with Alice",
    "description": "Schedule a focused 30-minute meeting.",
    "slot_duration": 30,
    "access_scope": "public",
    "form_fields": [
      {"name": "topic", "label": "Meeting Topic", "type": "text", "required": true}
    ]
  }'
```

Response includes `id`, `slug`, `title`, `slot_duration`, `access_scope`, `form_fields`, and `created_at`.

### View Available Slots (Guest Perspective)

```bash
curl "http://localhost:8030/api/v1/calendar/book/alice-30min/slots?date=2026-02-20"
```

Returns a list of available slot windows:

```json
{
  "slots": [
    {"start": "2026-02-20T09:00:00+00:00", "end": "2026-02-20T09:30:00+00:00"},
    {"start": "2026-02-20T09:45:00+00:00", "end": "2026-02-20T10:15:00+00:00"}
  ]
}
```

### Create a Booking (Guest Books a Slot)

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/book/alice-30min" \
  -H "Content-Type: application/json" \
  -d '{
    "guest_name": "Bob Smith",
    "guest_email": "bob@example.com",
    "slot_start": "2026-02-20T09:00:00+00:00",
    "slot_end": "2026-02-20T09:30:00+00:00",
    "form_responses": {"topic": "Product roadmap discussion"}
  }'
```

Response includes a `booking_uuid` for future reference.

### Retrieve or Cancel a Booking

```bash
# Get booking details
curl "http://localhost:8030/api/v1/calendar/bookings/{booking_uuid}"

# Cancel a booking
curl -X DELETE "http://localhost:8030/api/v1/calendar/bookings/{booking_uuid}"
```

### List Your Bookings (as Host)

```bash
curl "http://localhost:8030/api/v1/calendar/my-bookings?user_id=42&status=confirmed"
```

---

## Group Booking Page Workflow

### Create a Group Booking Page

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/booking-pages" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 7,
    "admin_user_id": 42,
    "page_type": "group",
    "slug": "team-meeting",
    "title": "Team Standup Scheduling",
    "slot_duration": 30,
    "access_scope": "community"
  }'
```

### Add Members

```bash
# Add required member (must be available for slot to show)
curl -X POST "http://localhost:8030/api/v1/calendar/booking-pages/5/members" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 42, "is_required": true}'

# Add optional member
curl -X POST "http://localhost:8030/api/v1/calendar/booking-pages/5/members" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 99, "is_required": false}'
```

### Get Group Availability

```bash
curl "http://localhost:8030/api/v1/calendar/booking-pages/5/group-availability?date=2026-02-20"
```

Returns aggregated slot data — available_count, unavailable_count, and meets_requirements — without exposing individual member calendar details.

### Get Best Slots Across a Date Range

```bash
curl "http://localhost:8030/api/v1/calendar/booking-pages/5/best-slots?start=2026-02-17&end=2026-02-21&limit=5"
```

Returns the top 5 slots with the highest available_count across the date range.

---

## Event Management Workflow

### Create an Event

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/7/events" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 7,
    "title": "Monthly Community Meetup",
    "description": "Our regular community gathering on Discord.",
    "event_date": "2026-03-01T18:00:00Z",
    "end_date": "2026-03-01T20:00:00Z",
    "timezone": "America/New_York",
    "platform": "discord",
    "entity_id": "123456789",
    "created_by_username": "alice",
    "rsvp_enabled": true,
    "max_attendees": 50,
    "waitlist_enabled": true
  }'
```

If the community requires approval, the event is created with `status=pending` and must be approved before it is visible to members.

### Approve an Event

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/7/events/12/approve" \
  -H "Content-Type: application/json" \
  -d '{"status": "approved", "notes": "Looks good, approved for publication."}'
```

### Search and Browse Events

```bash
# Upcoming events for a community
curl "http://localhost:8030/api/v1/calendar/7/upcoming?limit=10"

# Full-text search
curl "http://localhost:8030/api/v1/calendar/7/search?q=meetup&date_from=2026-02-01"

# Trending events
curl "http://localhost:8030/api/v1/calendar/7/trending?limit=5"
```

---

## RSVP Workflow

```bash
# RSVP yes with 1 guest
curl -X POST "http://localhost:8030/api/v1/calendar/7/events/12/rsvp" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "discord",
    "platform_user_id": "987654321",
    "username": "bob",
    "rsvp_status": "yes",
    "guest_count": 1
  }'

# Change to maybe
curl -X PUT "http://localhost:8030/api/v1/calendar/7/events/12/rsvp" \
  -H "Content-Type: application/json" \
  -d '{"platform": "discord", "platform_user_id": "987654321", "username": "bob", "rsvp_status": "maybe"}'

# Cancel RSVP
curl -X DELETE "http://localhost:8030/api/v1/calendar/7/events/12/rsvp?platform=discord&platform_user_id=987654321"

# List attendees
curl "http://localhost:8030/api/v1/calendar/7/events/12/attendees?status=yes&limit=50"
```

---

## Ticketing Workflow

```bash
# Enable ticketing for an event
curl -X POST "http://localhost:8030/api/v1/tickets/7/events/12/ticketing/enable" \
  -H "Content-Type: application/json" \
  -d '{"ticketing_enabled": true}'

# Create a ticket type
curl -X POST "http://localhost:8030/api/v1/tickets/7/events/12/ticket-types" \
  -H "Content-Type: application/json" \
  -d '{"name": "General Admission", "capacity": 100, "price": 0}'

# Check in a ticket by QR code
curl -X POST "http://localhost:8030/api/v1/tickets/7/events/12/check-in" \
  -H "Content-Type: application/json" \
  -d '{"ticket_code": "TICK-ABCD1234", "check_in_method": "qr_scan", "checked_in_by": 42}'

# Verify a ticket without checking in
curl -X POST "http://localhost:8030/api/v1/tickets/verify-ticket" \
  -H "Content-Type: application/json" \
  -d '{"ticket_code": "TICK-ABCD1234"}'
```
