# Calendar Interaction Module — API Reference

All endpoints are served on port `8030` (configurable via `MODULE_PORT`).

Base path prefixes:
- `/api/v1/calendar` — Event management, OAuth, availability, booking
- `/api/v1/context` — Community context switching
- `/api/v1/tickets` — Ticketing and event admin roles
- `/health`, `/metrics` — Health and observability

Request bodies must be `application/json`. Authentication is handled by the WaddleBot router upstream; individual endpoints expect `user_id` or user context in the request body or query params as documented.

Error responses follow the format:
```json
{"error": "Description of what went wrong", "field": "field_name_if_applicable"}
```

---

## Table of Contents

1. [Health](#health)
2. [Event Management](#event-management)
3. [RSVP](#rsvp)
4. [Search and Discovery](#search-and-discovery)
5. [Platform Sync](#platform-sync)
6. [Community Configuration](#community-configuration)
7. [Context Management](#context-management)
8. [OAuth — Calendar Connections](#oauth--calendar-connections)
9. [Availability Settings](#availability-settings)
10. [Individual Booking Pages](#individual-booking-pages)
11. [Bookings](#bookings)
12. [Group Booking Pages](#group-booking-pages)
13. [Ticketing](#ticketing)
14. [Event Admin Roles](#event-admin-roles)

---

## Health

### GET /health

Returns module health status. No authentication required.

**Response 200:**
```json
{"status": "healthy", "module": "calendar_interaction_module", "version": "2.0.0"}
```

---

## Event Management

All event endpoints are scoped under `/api/v1/calendar/{community_id}/events`.

### GET /api/v1/calendar/{community_id}/events

List events for a community with optional filtering.

**Query Parameters (EventSearchParams):**

| Parameter | Type | Required | Constraints | Description |
|---|---|---|---|---|
| platform | string | No | twitch, discord, slack | Filter by origin platform |
| status | string | No | pending, approved, rejected, cancelled | Filter by status |
| date_from | datetime | No | ISO 8601 | Start date filter |
| date_to | datetime | No | ISO 8601, must be after date_from | End date filter |
| category_id | integer | No | gt 0 | Category filter |
| entity_id | string | No | max 255 chars | Platform entity/server ID filter |
| tags | list[string] | No | — | Match any of these tags |
| limit | integer | No | 1–100, default 50 | Results per page |
| offset | integer | No | >=0, default 0 | Pagination offset |
| include_attendees | boolean | No | default false | Include attendee list |

**Response 200:**
```json
{
  "events": [
    {
      "id": 12,
      "title": "Monthly Community Meetup",
      "event_date": "2026-03-01T18:00:00Z",
      "end_date": "2026-03-01T20:00:00Z",
      "status": "approved",
      "platform": "discord",
      "rsvp_enabled": true,
      "max_attendees": 50
    }
  ],
  "total": 1
}
```

**Error Codes:**
- `400` — Invalid query parameters (Pydantic validation failure)

---

### POST /api/v1/calendar/{community_id}/events

Create a new event. If the community requires approval, the event is created with `status=pending`.

**Request Body (EventCreateRequest):**

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| community_id | integer | Yes | gt 0 | Community ID |
| title | string | Yes | 3–255 chars, non-whitespace | Event title |
| description | string | No | max 5000 chars | Event description |
| event_date | datetime | Yes | ISO 8601 | Event start time |
| end_date | datetime | No | ISO 8601, must be after event_date | Event end time |
| timezone | string | No | max 50 chars, default UTC | Timezone (e.g., America/New_York) |
| location | string | No | max 500 chars | Location or meeting URL |
| platform | string | Yes | twitch, discord, slack | Origin platform |
| entity_id | string | No | max 255 chars | Platform server/channel ID |
| channel_id | string | No | max 255 chars | Platform channel ID |
| created_by_username | string | Yes | 1–255 chars | Username of creator |
| created_by_platform_user_id | string | No | max 255 chars | Platform user ID |
| requires_approval | boolean | No | default false | Whether approval is needed |
| rsvp_enabled | boolean | No | default true | Enable RSVP |
| rsvp_deadline | datetime | No | must be before event_date | RSVP cutoff time |
| max_attendees | integer | No | ge 1 | Capacity limit |
| waitlist_enabled | boolean | No | default false | Enable waitlist |
| is_recurring | boolean | No | default false | Recurring event flag |
| recurring_pattern | string | No | daily, weekly, monthly | Recurrence frequency |
| recurring_rule | string | No | max 200 chars | RRULE format string |
| recurring_days | list[int] | No | each 0–6 (0=Sunday) | Days of week for recurring |
| recurring_end_date | datetime | No | must be after event_date | Recurrence end date |
| category_id | integer | No | gt 0 | Category ID |
| tags | list[string] | No | max 20 tags, each max 50 chars | Event tags |
| cover_image_url | string | No | valid http/https URL, max 1000 chars | Cover image |

**Response 201:**
```json
{"id": 12, "title": "Monthly Community Meetup", "status": "pending", ...}
```

**Error Codes:**
- `400` — Validation failure (invalid dates, missing required fields, bad URL format)
- `403` — Insufficient permissions to create events in this community

---

### GET /api/v1/calendar/{community_id}/events/{event_id}

Get a single event by ID.

**Response 200:** Full event object including attendee counts if RSVP is enabled.

**Error Codes:**
- `404` — Event not found or not in this community

---

### PUT /api/v1/calendar/{community_id}/events/{event_id}

Update an existing event. All fields optional (partial updates supported).

**Request Body (EventUpdateRequest):** Same fields as EventCreateRequest, all optional. Same validation constraints apply.

**Response 200:** Updated event object.

**Error Codes:**
- `400` — Validation failure
- `403` — Not the event creator or community admin
- `404` — Event not found

---

### DELETE /api/v1/calendar/{community_id}/events/{event_id}

Delete an event. Only the creator or community admin can delete.

**Response 200:** `{"message": "Event deleted"}`

**Error Codes:**
- `403` — Not authorized to delete this event
- `404` — Event not found

---

### POST /api/v1/calendar/{community_id}/events/{event_id}/approve

Approve a pending event.

**Request Body (EventApprovalRequest):**

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| status | string | Yes | approved | Must be "approved" |
| notes | string | No | max 1000 chars | Admin notes |
| reason | string | No | — | Reason for decision |

**Response 200:** Updated event object with `status=approved`.

**Error Codes:**
- `400` — Event is not in pending status
- `403` — Not a community admin or moderator

---

### POST /api/v1/calendar/{community_id}/events/{event_id}/reject

Reject a pending event.

**Request Body (EventApprovalRequest):**

| Field | Type | Required | Constraints |
|---|---|---|---|
| status | string | Yes | rejected |
| notes | string | No | max 1000 chars |
| reason | string | No | — |

**Response 200:** Updated event object with `status=rejected`.

---

### POST /api/v1/calendar/{community_id}/events/{event_id}/cancel

Cancel an event. Sets status to `cancelled`.

**Response 200:** `{"message": "Event cancelled"}`

---

## RSVP

### POST /api/v1/calendar/{community_id}/events/{event_id}/rsvp

Create a new RSVP (or use PUT to update an existing one).

**Request Body (RSVPRequest):**

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| platform | string | Yes | twitch, discord, slack | User's platform |
| platform_user_id | string | Yes | — | Platform user ID |
| username | string | Yes | — | Display username |
| rsvp_status | string | Yes | yes, no, maybe | RSVP response |
| guest_count | integer | No | ge 0, default 0 | Additional guests |
| user_note | string | No | — | Optional note |

**Response 200/201:**
```json
{
  "id": 88,
  "event_id": 12,
  "status": "yes",
  "guest_count": 1,
  "is_waitlisted": false,
  "message": "RSVP confirmed"
}
```

When the event is at capacity and `waitlist_enabled=true`, `is_waitlisted` is `true` and `waitlist_position` is included.

**Error Codes:**
- `400` — Invalid status value, RSVP deadline passed
- `409` — Event at capacity and waitlist disabled

---

### PUT /api/v1/calendar/{community_id}/events/{event_id}/rsvp

Update an existing RSVP. Same request body as POST.

---

### DELETE /api/v1/calendar/{community_id}/events/{event_id}/rsvp

Cancel/remove an RSVP. Pass `platform` and `platform_user_id` as query parameters.

**Response 200:** `{"message": "RSVP cancelled"}`

---

### GET /api/v1/calendar/{community_id}/events/{event_id}/attendees

List attendees for an event.

**Query Parameters (AttendeeSearchParams):**

| Parameter | Type | Default | Description |
|---|---|---|---|
| status | string | — | Filter by rsvp_status (yes, no, maybe) |
| limit | integer | 50 | Max 100 |
| offset | integer | 0 | Pagination offset |

**Response 200:** List of attendee records with username, platform, status, guest_count, is_waitlisted.

---

## Search and Discovery

### GET /api/v1/calendar/{community_id}/search

Full-text search across event title and description.

**Query Parameters (EventFullTextSearchParams):**

| Parameter | Type | Description |
|---|---|---|
| q | string | Search query text |
| date_from | datetime | Start date filter |
| date_to | datetime | End date filter |
| limit | integer | Default 50, max 100 |
| offset | integer | Pagination offset |

---

### GET /api/v1/calendar/{community_id}/upcoming

List upcoming approved events in chronological order.

**Query Parameters (UpcomingEventsParams):** `limit` (default 10, max 100), `offset`.

---

### GET /api/v1/calendar/{community_id}/trending

List trending events ordered by RSVP activity.

**Query Parameters:** Same as upcoming.

---

## Platform Sync

### POST /api/v1/calendar/{community_id}/sync/enable

Enable platform sync for a community.

### POST /api/v1/calendar/{community_id}/events/{event_id}/sync

Manually trigger a platform sync for a specific event.

### GET /api/v1/calendar/{community_id}/events/{event_id}/sync/status

Get the last sync status for an event.

### POST /api/v1/calendar/webhooks/discord

Discord webhook receiver for incoming event updates.

### POST /api/v1/calendar/webhooks/twitch

Twitch webhook receiver for incoming event updates.

---

## Community Configuration

### GET /api/v1/calendar/{community_id}/config/permissions

Get permission configuration for the community (who can create events, whether approval is required, etc.).

### PUT /api/v1/calendar/{community_id}/config/permissions

Update permission configuration.

**Request Body (PermissionsConfigRequest):** Community-level permission flags.

### GET|PUT /api/v1/calendar/{community_id}/config/reminders

Get or update event reminder configuration.

### GET /api/v1/calendar/{community_id}/categories

List event categories for a community.

### POST /api/v1/calendar/{community_id}/categories

Create a new event category.

**Request Body (CategoryCreateRequest):**

| Field | Type | Required | Description |
|---|---|---|---|
| name | string | Yes | Category name |
| color | string | No | Hex color code |
| description | string | No | Category description |

---

## Context Management

### GET /api/v1/context/{entity_id}

Get the current community context for a platform entity (user or channel).

### POST /api/v1/context/{entity_id}/switch

Switch the active community context.

**Request Body (ContextSwitchRequest):**

| Field | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | Target community ID |
| platform | string | Yes | Platform identifier |

### GET /api/v1/context/{entity_id}/available

List communities available to this entity.

---

## OAuth — Calendar Connections

### GET /api/v1/calendar/oauth/google/auth-url

Generate the Google Calendar OAuth authorization URL.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| user_id | integer | Yes | Hub user ID (used as OAuth state) |
| redirect_uri | string | Yes | Must match Google Console redirect URI |

**Response 200:**
```json
{"auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."}
```

The URL includes `scope=https://www.googleapis.com/auth/calendar.readonly`, `access_type=offline`, and `prompt=consent` to guarantee a refresh token is always returned.

---

### GET /api/v1/calendar/oauth/google/callback

OAuth callback endpoint. Called by Google's redirect after user authorization.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| code | string | Yes | Authorization code from Google |
| state | string | Yes | Hub user ID (set during auth URL generation) |
| redirect_uri | string | Yes | Same URI used in auth URL request |

**Response 200:**
```json
{
  "id": 3,
  "provider": "google",
  "calendar_id": "primary",
  "calendar_name": "Google Calendar",
  "is_primary": true
}
```

**Error Codes:**
- `400` — Token exchange failed (bad code, expired code, redirect URI mismatch)
- `500` — Database error storing tokens

---

### GET /api/v1/calendar/oauth/microsoft/auth-url

Generate the Microsoft Calendar OAuth authorization URL.

**Query Parameters:** Same as Google — `user_id` and `redirect_uri`.

**Response 200:**
```json
{"auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?..."}
```

The URL uses scope `Calendars.Read` and `response_mode=query`.

---

### GET /api/v1/calendar/oauth/microsoft/callback

OAuth callback for Microsoft. Called by Azure's redirect after user authorization.

**Query Parameters:** `code`, `state` (user_id), `redirect_uri`.

**Response 200:** Same format as Google callback — connected calendar record.

---

### GET /api/v1/calendar/oauth/calendars

List all connected calendars for the authenticated user.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| user_id | integer | Yes | Hub user ID |

**Response 200:**
```json
{
  "calendars": [
    {
      "id": 3,
      "provider": "google",
      "calendar_id": "primary",
      "calendar_name": "Google Calendar",
      "is_primary": true,
      "sync_enabled": true,
      "last_sync_at": "2026-02-16T10:00:00Z",
      "sync_error": null,
      "created_at": "2026-02-10T08:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/calendar/oauth/calendars/{calendar_id}/sync

Trigger a free/busy sync for a connected calendar.

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| user_id | integer | Yes | Hub user ID |
| start | datetime | Yes | Start of sync range (ISO 8601) |
| end | datetime | Yes | End of sync range (ISO 8601) |

**Response 200:** `{"message": "Sync completed", "busy_blocks": 5}`

**Error Codes:**
- `404` — Calendar not found or sync disabled
- `502` — External calendar API returned an error (stored in `sync_error` field)

---

### DELETE /api/v1/calendar/oauth/calendars/{calendar_id}

Disconnect a calendar. Deactivates both the `connected_calendars` record and the associated `platform_integrations` record.

**Query Parameters:** `user_id` (integer, required).

**Response 200:** `{"message": "Calendar disconnected"}`

---

## Availability Settings

### GET /api/v1/calendar/availability/settings

Get calendar and booking settings for a user.

**Query Parameters:** `user_id` (integer, required).

**Response 200:**
```json
{
  "visibility_public": "hidden",
  "visibility_registered": "free_busy",
  "visibility_community": "details",
  "slot_durations": [30, 60],
  "default_slot_duration": 30,
  "min_notice_hours": 4,
  "max_future_days": 30,
  "buffer_minutes": 15,
  "weekly_availability": {
    "monday": [{"start": "09:00", "end": "17:00"}]
  },
  "timezone": "America/New_York",
  "booking_enabled": true,
  "booking_slug": "alice-30min",
  "booking_page_title": "Book time with Alice",
  "booking_page_description": "Schedule a focused meeting."
}
```

---

### PUT /api/v1/calendar/availability/settings

Update availability settings (upsert — creates record if none exists).

**Request Body (AvailabilitySettingsUpdateRequest):** Any subset of fields from the GET response. All fields optional.

---

### GET /api/v1/calendar/availability/weekly

Get the weekly availability schedule for a user.

**Query Parameters:** `user_id` (integer, required).

**Response 200:**
```json
{
  "monday": [{"start": "09:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}],
  "tuesday": [{"start": "09:00", "end": "17:00"}],
  "saturday": [],
  "sunday": []
}
```

---

### PUT /api/v1/calendar/availability/weekly

Update the weekly availability schedule.

**Request Body (WeeklyAvailabilityUpdateRequest):**

| Field | Type | Required | Description |
|---|---|---|---|
| user_id | integer | Yes | Hub user ID |
| availability | object | Yes | Day-name keys with list of {start, end} time windows |

---

### GET /api/v1/calendar/availability/{target_user_id}/slots

Compute available booking slots for a user on a specific date.

**Query Parameters (AvailableSlotsParams):**

| Parameter | Type | Required | Description |
|---|---|---|---|
| date | string | Yes | YYYY-MM-DD format |
| slot_duration | integer | No | Minutes per slot (default: user's default_slot_duration) |

**Response 200:**
```json
{
  "slots": [
    {"start": "2026-02-20T09:00:00+00:00", "end": "2026-02-20T09:30:00+00:00"},
    {"start": "2026-02-20T09:45:00+00:00", "end": "2026-02-20T10:15:00+00:00"}
  ],
  "date": "2026-02-20",
  "slot_duration": 30
}
```

Returns an empty list if the date is outside `min_notice_hours` or `max_future_days` constraints, or if the user has no availability configured for that day of week.

---

## Individual Booking Pages

### POST /api/v1/calendar/booking-pages

Create an individual booking page.

**Request Body (BookingPageCreateRequest):**

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| slug | string | Yes | 3–100 chars, `^[a-z0-9-]+$` | URL-safe unique slug |
| title | string | Yes | 3–255 chars | Page title |
| description | string | No | max 2000 chars | Page description |
| slot_duration | integer | No | 5–480, default 30 | Slot duration in minutes |
| access_scope | string | No | public, registered, community; default public | Who can view |
| form_fields | list[object] | No | max 8 items | Custom form fields |

**Response 201:** Booking page object with `id`, `slug`, `title`, `description`, `slot_duration`, `access_scope`, `form_fields`, `created_at`.

**Error Codes:**
- `400` — Validation failure (slug not URL-safe, too short/long, form_fields exceeds 8)
- `409` — Slug already in use

---

### GET /api/v1/calendar/booking-pages

List booking pages owned by the authenticated user.

**Query Parameters:** `user_id` (integer, required).

---

### GET /api/v1/calendar/booking-pages/{slug_or_id}

Get a booking page by slug or numeric ID.

**Path Parameter:** Either the string slug (e.g., `alice-30min`) or the integer ID.

**Response 200:** Full booking page object.

**Error Codes:**
- `404` — Page not found or `is_active=false`

---

### PUT /api/v1/calendar/booking-pages/{page_id}

Update a booking page. Only the page owner can update.

**Request Body (BookingPageUpdateRequest):** All fields optional — same constraints as create.

---

### DELETE /api/v1/calendar/booking-pages/{page_id}

Deactivate a booking page (`is_active=false`). Only the page owner can delete.

**Response 200:** `{"message": "Booking page deleted"}`

---

## Bookings

### GET /api/v1/calendar/book/{slug}/slots

Get available slots for a booking page on a specific date. This is the public-facing endpoint for guests.

**Path Parameter:** `slug` — booking page URL slug.

**Query Parameters (AvailableSlotsQueryParams):**

| Parameter | Type | Required | Description |
|---|---|---|---|
| date | string | Yes | YYYY-MM-DD |

**Response 200:** List of available slot windows (same format as `/availability/{user_id}/slots`).

---

### POST /api/v1/calendar/book/{slug}

Create a booking on a booking page. Race condition protection via `SELECT FOR UPDATE`.

**Path Parameter:** `slug` — booking page URL slug.

**Request Body (BookingCreateRequest):**

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| guest_name | string | Yes | 1–255 chars | Guest full name |
| guest_email | string | No | valid email format, max 255 chars | Guest email |
| slot_start | datetime | Yes | ISO 8601 | Booking start time |
| slot_end | datetime | Yes | ISO 8601, must be after slot_start | Booking end time |
| form_responses | object | No | — | Responses to custom form fields |

**Response 201:**
```json
{
  "booking_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "status": "confirmed",
  "host_user_id": 42,
  "guest_name": "Bob Smith",
  "slot_start": "2026-02-20T09:00:00Z",
  "slot_end": "2026-02-20T09:30:00Z"
}
```

**Error Codes:**
- `400` — Invalid time order (slot_end before slot_start), invalid email
- `409` — Slot no longer available (claimed by another booking)

---

### GET /api/v1/calendar/bookings/{uuid}

Get a booking by its UUID.

**Response 200:** Full booking object.

**Error Codes:**
- `404` — Booking not found

---

### DELETE /api/v1/calendar/bookings/{uuid}

Cancel a booking. Sets status to `cancelled_by_guest` or `cancelled_by_host` depending on who calls it.

**Response 200:** `{"message": "Booking cancelled"}`

---

### GET /api/v1/calendar/my-bookings

List bookings for the authenticated user (as host).

**Query Parameters (BookingListParams):**

| Parameter | Type | Constraints | Description |
|---|---|---|---|
| status | string | pending, confirmed, cancelled_by_host, cancelled_by_guest, completed, no_show | Filter by status |
| start | string | YYYY-MM-DD | Start date filter |
| end | string | YYYY-MM-DD | End date filter |

---

## Group Booking Pages

### POST /api/v1/calendar/booking-pages (group variant)

Create a group booking page by including `page_type=group` and `community_id` in the request body.

**Request Body (GroupBookingPageCreateRequest):** Same fields as individual booking page — `slug`, `title`, `description`, `slot_duration`, `access_scope`, `form_fields`. Community ID is passed in the body or derived from user context.

---

### POST /api/v1/calendar/booking-pages/{page_id}/members

Add a member to a group booking page.

**Request Body (GroupMemberAddRequest):**

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| user_id | integer | Yes | gt 0 | Hub user ID to add |
| is_required | boolean | No | default true | Required member blocks slot if unavailable |

**Response 200:** `{"message": "Member added"}`

**Error Codes:**
- `404` — Page not found or not a group page
- `409` — User already a member (upserts `is_required` instead)

---

### DELETE /api/v1/calendar/booking-pages/{page_id}/members/{user_id}

Remove a member from a group booking page.

**Response 200:** `{"message": "Member removed"}`

---

### GET /api/v1/calendar/booking-pages/{page_id}/members

List members of a group booking page. Returns `user_id`, `username`, and `is_required` only — no calendar data exposed.

---

### GET /api/v1/calendar/booking-pages/{page_id}/group-availability

Get aggregated availability for a group booking page on a specific date.

**Query Parameters (AvailableSlotsQueryParams):**

| Parameter | Type | Required | Description |
|---|---|---|---|
| date | string | Yes | YYYY-MM-DD |

**Response 200:**
```json
{
  "slots": [
    {
      "start": "2026-02-20T09:00:00+00:00",
      "end": "2026-02-20T09:30:00+00:00",
      "available_count": 4,
      "maybe_count": 0,
      "unavailable_count": 1,
      "meets_requirements": true
    }
  ]
}
```

Only slots where all `is_required=true` members are available have `meets_requirements=true`. Individual member availability is never exposed.

---

### GET /api/v1/calendar/booking-pages/{page_id}/best-slots

Get the top N slots across a date range ranked by availability count.

**Query Parameters (BestSlotsParams):**

| Parameter | Type | Required | Constraints | Description |
|---|---|---|---|---|
| start | string | Yes | YYYY-MM-DD | Start of date range |
| end | string | Yes | YYYY-MM-DD | End of date range |
| limit | integer | No | 1–20, default 5 | Number of top slots to return |

**Response 200:** List of slot objects sorted by `available_count` descending, same format as group-availability.

---

## Ticketing

Base path: `/api/v1/tickets`

### POST /api/v1/tickets/verify-ticket

Verify a ticket is valid without performing check-in.

**Request Body (TicketVerifyRequest):**

| Field | Type | Required | Description |
|---|---|---|---|
| ticket_code | string | Yes | Ticket code (e.g., TICK-ABCD1234) |

**Response 200:**
```json
{
  "valid": true,
  "ticket_status": "valid",
  "event_id": 12,
  "holder_name": "Bob Smith",
  "is_checked_in": false
}
```

---

### GET /api/v1/tickets/{community_id}/events/{event_id}/ticket-types

List ticket types for an event.

---

### POST /api/v1/tickets/{community_id}/events/{event_id}/ticket-types

Create a ticket type for an event.

**Request Body (TicketTypeCreateRequest):**

| Field | Type | Required | Description |
|---|---|---|---|
| name | string | Yes | Ticket type name |
| capacity | integer | No | Max tickets of this type |
| price | decimal | No | Price (0 for free) |
| description | string | No | Type description |

---

### PUT /api/v1/tickets/{community_id}/events/{event_id}/ticket-types/{type_id}

Update a ticket type.

---

### DELETE /api/v1/tickets/{community_id}/events/{event_id}/ticket-types/{type_id}

Delete a ticket type.

---

### POST /api/v1/tickets/{community_id}/events/{event_id}/ticketing/enable

Enable ticketing for an event.

**Request Body (TicketingConfigRequest):** `ticketing_enabled` (boolean).

---

### POST /api/v1/tickets/{community_id}/events/{event_id}/check-in

Check in a ticket holder.

**Request Body (TicketCheckInRequest):**

| Field | Type | Required | Description |
|---|---|---|---|
| ticket_code | string | Yes | Ticket code |
| check_in_method | string | Yes | qr_scan, manual, api, self_checkin, auto_checkin |
| checked_in_by | integer | Yes | Hub user ID performing check-in |

**Response 200:**
```json
{
  "success": true,
  "result_code": "success",
  "ticket_id": 88,
  "holder_name": "Bob Smith",
  "checked_in_at": "2026-03-01T18:05:00Z"
}
```

**Result Codes:** `success`, `already_checked_in`, `invalid_ticket`, `wrong_event`, `expired`, `cancelled`, `event_not_started`, `event_ended`, `unauthorized`

---

### POST /api/v1/tickets/{community_id}/events/{event_id}/undo-check-in

Undo a check-in, setting the ticket back to `valid` status.

---

### GET /api/v1/tickets/{community_id}/events/{event_id}/check-in-log

Retrieve the check-in audit log.

**Query Parameters (CheckInLogParams):** `limit`, `offset`.

---

### POST /api/v1/tickets/{community_id}/tickets/{ticket_id}/transfer

Transfer a ticket to another user.

**Request Body (TicketTransferRequest):** Target user information.

---

### DELETE /api/v1/tickets/{community_id}/tickets/{ticket_id}

Cancel a ticket. Sets status to `cancelled`.

---

## Event Admin Roles

### GET /api/v1/tickets/{community_id}/events/{event_id}/admins

List event admins for an event.

---

### POST /api/v1/tickets/{community_id}/events/{event_id}/admins

Assign an event admin role.

**Request Body (EventAdminAssignRequest):**

| Field | Type | Required | Description |
|---|---|---|---|
| platform_user_id | string | Yes | Platform user ID of new admin |
| platform | string | Yes | Platform identifier |
| username | string | Yes | Display username |
| permissions | object | Yes | Map of permission flags (see EventAdminPermission enum) |
| assignment_notes | string | No | Notes about this assignment |

**Permission flags:** `can_edit_event`, `can_check_in`, `can_view_tickets`, `can_manage_ticket_types`, `can_cancel_tickets`, `can_transfer_tickets`, `can_export_attendance`, `can_assign_event_admins`

---

### PUT /api/v1/tickets/{community_id}/events/{event_id}/admins/{admin_id}

Update permissions for an event admin.

---

### DELETE /api/v1/tickets/{community_id}/events/{event_id}/admins/{admin_id}

Revoke an event admin role.

---

### GET /api/v1/tickets/{community_id}/events/{event_id}/my-permissions

Get the current user's event admin permissions for a specific event.
