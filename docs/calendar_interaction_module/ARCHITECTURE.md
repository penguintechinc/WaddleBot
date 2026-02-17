# Calendar Interaction Module — Architecture

## Overview

The Calendar Interaction Module is an async Python service built on the Quart framework. It provides REST APIs for event management, appointment booking, OAuth-based calendar integration, and ticketing. All I/O — database queries and external calendar API calls — is async, enabling high concurrency under load.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | Quart (async Flask-compatible) |
| Validation | Pydantic v2 (`BaseModel`, `field_validator`, `model_validator`) |
| Database access | AsyncDAL (PostgreSQL-backed, parameterized queries) |
| External HTTP | httpx (async) |
| Configuration | python-dotenv + environment variables |
| Credential refresh | Redis pub/sub (optional) |
| Module version | 2.0.0 |

---

## Component Breakdown

### app.py — Entry Point and Route Registration

`app.py` is the Quart application entry point. It:

1. Initializes the database connection via `init_database()` from `flask_core`
2. Loads credentials from the `platform_integrations` table via `Config.load_credentials_from_db()`
3. Starts the Redis credential listener thread if `REDIS_URL` is set (via `Config.start_credential_listener()`)
4. Instantiates all service classes, passing the shared database connection
5. Registers three Blueprints:
   - `calendar_bp` — prefix `/api/v1/calendar` — events, OAuth, availability, booking
   - `context_bp` — prefix `/api/v1/context` — multi-community context management
   - `ticket_bp` — prefix `/api/v1/tickets` — ticketing, check-in, event admin roles
6. Registers a health Blueprint from `flask_core.create_health_blueprint()`

Route handlers use the `@async_endpoint` decorator for consistent error handling and the `@validate_json` / `@validate_query` decorators to run Pydantic model validation before the handler body executes.

### config.py — Configuration and Credential Management

`Config` is a class-level configuration object with these responsibilities:

- Reads all settings from environment variables with sensible defaults
- `load_credentials_from_db(db)` — queries the `platform_integrations` table for active `calendar_interaction` bot credentials and caches the result in a thread-safe `_credentials_loaded` flag
- `start_credential_listener(redis_client)` — spawns a daemon thread subscribing to the Redis channel `credentials:calendar_interaction:bot:refreshed`; when a message arrives, it resets `_credentials_loaded` to trigger the next credential reload

### validation_models.py — Input Validation Layer

All request payloads and query parameters are validated through Pydantic v2 models before they reach service logic. This eliminates 500 errors from unsafe type conversions. Notable validation rules:

- `EventCreateRequest.event_date` must be before `end_date` (model-level validator)
- `recurring_days` entries must be integers 0–6
- `cover_image_url` must match `^https?://...`
- `rsvp_deadline` must be before `event_date`
- `BookingCreateRequest.slot_end` must be after `slot_start`
- `BookingPageCreateRequest.slug` must match `^[a-z0-9-]+$`
- All models use `ConfigDict(extra='forbid')` to reject unknown fields

---

## Service Layer

### CalendarOAuthService (`services/calendar_oauth_service.py`)

Manages Google and Microsoft calendar connections.

**Key methods:**

| Method | Description |
|---|---|
| `get_google_auth_url(user_id, redirect_uri)` | Builds Google OAuth URL with `access_type=offline`, `prompt=consent` |
| `get_microsoft_auth_url(user_id, redirect_uri)` | Builds Microsoft OAuth URL via Azure common endpoint |
| `handle_google_callback(user_id, code, redirect_uri)` | Exchanges code for tokens, stores in `platform_integrations`, creates `connected_calendars` record |
| `handle_microsoft_callback(user_id, code, redirect_uri)` | Same flow for Microsoft Graph tokens |
| `refresh_token_if_needed(platform_integration_id)` | Checks token expiry; refreshes if within 5 minutes of expiry |
| `sync_free_busy(user_id, calendar_id, start, end)` | Fetches busy blocks from Google/Microsoft API, deletes stale `calendar_free_busy` rows, inserts fresh data |
| `disconnect_calendar(user_id, calendar_id)` | Sets `sync_enabled=FALSE` on calendar, `is_active=FALSE` on integration |
| `list_connected_calendars(user_id)` | Returns all `connected_calendars` rows for a user ordered by `is_primary DESC` |

**Google free/busy:** Uses the `https://www.googleapis.com/calendar/v3/freeBusy` endpoint with a POST body specifying `timeMin`, `timeMax`, and `items=[{id: calendar_id}]`.

**Microsoft schedule:** Uses `https://graph.microsoft.com/v1.0/me/calendar/getSchedule` with `availabilityViewInterval=30`.

### AvailabilityService (`services/availability_service.py`)

Manages user availability settings and slot computation.

**Key methods:**

| Method | Description |
|---|---|
| `get_settings(user_id)` | Fetches `user_calendar_settings` row; returns defaults if not found |
| `update_settings(user_id, settings_dict)` | Upserts allowed fields into `user_calendar_settings` |
| `get_weekly_availability(user_id)` | Returns just the `weekly_availability` JSON field |
| `update_weekly_availability(user_id, availability)` | Wrapper around `update_settings` for the `weekly_availability` field |
| `get_free_busy(user_id, start, end)` | Merges rows from `calendar_free_busy` and `bookings` tables into a sorted list of busy blocks |
| `compute_available_slots(user_id, date, slot_duration_minutes)` | Full slot computation algorithm (see below) |

**Slot computation algorithm:**

```
1. Load user settings (min_notice_hours, max_future_days, buffer_minutes, weekly_availability)
2. Determine day name from target date (e.g., "monday")
3. Return empty list if day has no availability windows
4. Calculate earliest_slot = now + min_notice_hours
5. Calculate latest_slot = now + max_future_days
6. Return empty list if target date is outside [earliest_slot, latest_slot]
7. Fetch all busy blocks (calendar_free_busy + bookings) for the date range
8. For each availability window:
   a. Parse start/end time strings ("09:00" -> time object)
   b. Combine with target date to get datetime objects
   c. Clamp window_start to max(window_start, earliest_slot)
   d. Iterate from window_start to window_end in slot_duration steps
   e. Add each slot that fits within allowed range to candidates
   f. Advance by slot_duration + buffer_minutes after each slot
9. For each candidate slot, test against all busy blocks for overlap
10. Return non-overlapping slots as ISO timestamp dicts
```

### BookingService (`services/booking_service.py`)

Handles individual appointment scheduling.

**Key methods:**

| Method | Description |
|---|---|
| `create_booking_page(user_id, data)` | Inserts into `booking_pages` with `page_type='individual'` |
| `update_booking_page(page_id, user_id, data)` | Dynamic UPDATE for allowed fields, owner-only |
| `get_booking_page(slug_or_id)` | Looks up by numeric ID or string slug |
| `get_available_slots(page_id, date)` | Delegates to AvailabilityService.compute_available_slots with page's slot_duration |
| `create_booking(page_id, data)` | Uses `SELECT FOR UPDATE` to lock slot check, then inserts into `bookings` |
| `cancel_booking(booking_uuid, canceller_role)` | Sets booking status to `cancelled_by_host` or `cancelled_by_guest` |
| `list_bookings(user_id, filters)` | Lists bookings for a host with optional status/date filters |

**Race condition protection:** The `create_booking` method wraps the availability check and INSERT in a transaction using `SELECT FOR UPDATE` on the slot's time range in the `bookings` table. If another request claims the slot between the availability check and the insert, the transaction detects the conflict and returns a 409.

### GroupAvailabilityService (`services/group_availability_service.py`)

Handles multi-member appointment scheduling.

**Key methods:**

| Method | Description |
|---|---|
| `create_group_booking_page(community_id, admin_user_id, data)` | Inserts into `booking_pages` with `page_type='group'` |
| `add_member(page_id, user_id, is_required)` | Upserts into `booking_page_members` |
| `remove_member(page_id, user_id)` | Deletes from `booking_page_members` |
| `get_group_members(page_id)` | Returns members with username but no calendar data |
| `get_group_availability(page_id, date)` | Aggregates availability (see algorithm below) |
| `get_most_available_slots(page_id, start, end, limit)` | Iterates date range, collects all slots, sorts by available_count, returns top N |

**Group availability algorithm:**

```
1. Load booking page config (slot_duration)
2. Load all group members (user_id, username, is_required)
3. For each member:
   a. Load user_calendar_settings (weekly_availability, min_notice_hours, etc.)
   b. Generate candidate slots from availability windows (same logic as AvailabilityService)
   c. Fetch busy blocks from calendar_free_busy (status IN ('busy', 'tentative'))
   d. Fetch busy blocks from bookings (status IN ('pending', 'confirmed'))
   e. Filter candidate slots against busy blocks
   f. Store available slots keyed by user_id
4. Collect union of all unique slot (start, end) pairs across all members
5. For each unique slot:
   a. Count available_count (members for whom this slot is available)
   b. Count unavailable_count
   c. Count required_available (available required members)
   d. meets_requirements = (required_available == total required members)
6. Filter to only slots where meets_requirements == True
7. Return aggregated list (never exposing individual member data)
```

### Supporting Services

| Service | File | Description |
|---|---|---|
| RSVPService | `services/rsvp_service.py` | RSVP creation/update with capacity check and automatic waitlist positioning |
| TicketService | `services/ticket_service.py` | Full ticket lifecycle — create, verify, check-in, undo, transfer, cancel |
| EventAdminService | `services/event_admin_service.py` | Per-event admin roles with 8 granular permission flags |
| CalendarService | `services/calendar_service.py` | Core event CRUD, approval workflow, recurring event expansion |
| ContextService | `services/context_service.py` | Multi-community context switching and resolution |
| PermissionService | `services/permission_service.py` | Community-level permission checking for event operations |
| CacheManager | `services/cache_manager.py` | In-process caching layer for frequently read data |

---

## OAuth Flow Diagram

```
User                  WaddleBot              Google/Microsoft
 |                       |                         |
 |-- Request auth URL -->|                         |
 |                       |-- Build auth URL ------>|
 |<-- Return auth URL ---|                         |
 |                       |                         |
 |-- Visit auth URL ------------------------------------>|
 |                                                       |
 |<-- Redirect to callback with ?code=AUTH_CODE&state=UID|
 |                       |                         |
 |-- GET /oauth/google/callback?code=...&state=... ->|   |
 |                       |                         |
 |           POST /token with code, client_id, secret -->|
 |                       |<-- {access_token, refresh_token, expires_in} --|
 |                       |                         |
 |                       |-- INSERT platform_integrations (tokens)        |
 |                       |-- INSERT connected_calendars (calendar record) |
 |                       |                         |
 |<-- {id, provider, calendar_name} --|            |
 |                       |                         |

Token Refresh Flow (automatic, triggered on sync):
 |                       |                         |
 |-- POST /calendars/1/sync -->|                   |
 |                       |-- Check token expiry    |
 |                       |   (expires within 5 min?)|
 |                       |-- POST /token with refresh_token -->|
 |                       |<-- {new_access_token, expires_in} --|
 |                       |-- UPDATE platform_integrations      |
 |                       |                         |
 |                       |-- POST /freeBusy or /getSchedule -->|
 |                       |<-- {busy blocks} -------------------|
 |                       |-- DELETE old calendar_free_busy rows|
 |                       |-- INSERT new calendar_free_busy rows|
 |<-- {message: "Sync completed", busy_blocks: N} --|         |
```

---

## Database Schema (Key Tables)

### platform_integrations

Stores OAuth tokens for both user-connected calendars and bot integrations.

| Column | Type | Description |
|---|---|---|
| id | integer | Primary key |
| hub_user_id | integer | WaddleBot user ID |
| platform | string | `google_calendar` or `microsoft_calendar` |
| integration_type | string | `user_oauth` for calendar connections, `bot` for module credentials |
| access_token | string | Current OAuth access token |
| refresh_token | string | OAuth refresh token (may be NULL if not provided) |
| token_expires_at | timestamp | When the access token expires |
| is_active | boolean | False after disconnect |
| created_at | timestamp | Record creation time |
| updated_at | timestamp | Last token refresh time |

### connected_calendars

One record per user per connected calendar.

| Column | Type | Description |
|---|---|---|
| id | integer | Primary key |
| hub_user_id | integer | WaddleBot user ID |
| platform_integration_id | integer | FK to platform_integrations |
| provider | string | `google` or `microsoft` |
| calendar_id | string | Provider calendar identifier (`primary` for Google) |
| calendar_name | string | Display name |
| is_primary | boolean | Primary calendar flag |
| sync_enabled | boolean | Whether free/busy sync is active |
| last_sync_at | timestamp | Last successful sync time |
| sync_error | string | Last sync error message if any |

### calendar_free_busy

Busy time blocks fetched from external calendars.

| Column | Type | Description |
|---|---|---|
| id | integer | Primary key |
| hub_user_id | integer | WaddleBot user ID |
| connected_calendar_id | integer | FK to connected_calendars |
| start_time | timestamp | Busy block start |
| end_time | timestamp | Busy block end |
| status | string | `busy` or `tentative` |
| fetched_at | timestamp | When this block was fetched |

### user_calendar_settings

Per-user availability and booking configuration.

| Column | Type | Description |
|---|---|---|
| hub_user_id | integer | WaddleBot user ID (unique) |
| visibility_public | string | `hidden`, `free_busy`, or `details` |
| visibility_registered | string | Same options |
| visibility_community | string | Same options |
| slot_durations | json array | Supported slot durations (e.g., [30, 60]) |
| default_slot_duration | integer | Default slot length in minutes |
| min_notice_hours | integer | Minimum advance booking notice |
| max_future_days | integer | How far ahead bookings are accepted |
| buffer_minutes | integer | Buffer between consecutive slots |
| weekly_availability | json | Day-keyed availability windows |
| timezone | string | User timezone |
| booking_enabled | boolean | Whether individual bookings are open |
| booking_slug | string | Legacy slug field |
| booking_page_title | string | Legacy page title field |
| booking_page_description | string | Legacy page description field |

### booking_pages

Individual and group booking page configurations.

| Column | Type | Description |
|---|---|---|
| id | integer | Primary key |
| slug | string | Unique URL slug |
| page_type | string | `individual` or `group` |
| hub_user_id | integer | Owner for individual pages (nullable for group) |
| community_id | integer | Owner for group pages (nullable for individual) |
| title | string | Page title |
| description | string | Page description |
| slot_duration | integer | Slot duration in minutes |
| access_scope | string | `public`, `registered`, or `community` |
| form_fields | json array | Custom form field definitions |
| is_active | boolean | Soft delete flag |

### booking_page_members

Members of group booking pages.

| Column | Type | Description |
|---|---|---|
| booking_page_id | integer | FK to booking_pages |
| hub_user_id | integer | FK to hub_users |
| is_required | boolean | Required members block slot if unavailable |
| (unique constraint) | — | (booking_page_id, hub_user_id) |

### bookings

Individual appointment records.

| Column | Type | Description |
|---|---|---|
| id | integer | Primary key |
| booking_uuid | uuid | Public-facing booking reference |
| booking_page_id | integer | FK to booking_pages |
| host_user_id | integer | Host user ID |
| guest_name | string | Guest full name |
| guest_email | string | Guest email (optional) |
| start_time | timestamp | Booking start |
| end_time | timestamp | Booking end |
| status | string | pending, confirmed, cancelled_by_host, cancelled_by_guest, completed, no_show |
| form_responses | json | Responses to custom form fields |

---

## Data Flow: Slot Computation

```
Request: GET /availability/42/slots?date=2026-02-20&slot_duration=30

AvailabilityService.compute_available_slots(user_id=42, date=2026-02-20, slot_duration=30)
  |
  +-- get_settings(42)
  |     -> SELECT FROM user_calendar_settings WHERE hub_user_id = 42
  |     -> Returns {weekly_availability, min_notice_hours=4, max_future_days=30, buffer_minutes=15}
  |
  +-- Determine day name: "friday"
  |
  +-- Get friday availability: [{"start":"09:00","end":"13:00"}]
  |
  +-- Compute constraints:
  |     earliest_slot = now + 4 hours
  |     latest_slot = now + 30 days
  |
  +-- get_free_busy(42, date_start, date_end)
  |     -> SELECT FROM calendar_free_busy WHERE hub_user_id = 42 AND ...
  |     -> SELECT FROM bookings WHERE host_user_id = 42 AND ...
  |     -> Merge and sort: [{start, end, source}, ...]
  |
  +-- Generate candidate slots from 09:00 to 13:00 in 30-min increments with 15-min buffer
  |     09:00-09:30, 09:45-10:15, 10:30-11:00, 11:15-11:45, 12:00-12:30
  |
  +-- Filter: remove any candidate that overlaps a busy block
  |
  +-- Return: [{start: "...T09:00:00+00:00", end: "...T09:30:00+00:00"}, ...]
```

---

## Credential Refresh Architecture

The module supports live credential rotation without restart via Redis pub/sub:

```
Admin rotates credentials in platform_integrations table
  |
  +-- Publishes message to Redis channel:
  |     "credentials:calendar_interaction:bot:refreshed"
  |
  +-- Config._credential_listener() thread receives message
  |
  +-- Sets Config._credentials_loaded = False (thread-safe with _credential_lock)
  |
  +-- Next request that needs credentials calls Config.load_credentials_from_db()
        -> Queries platform_integrations for fresh tokens
        -> Sets _credentials_loaded = True
```

If `REDIS_URL` is not set, this feature is disabled and credentials are loaded from environment variables only.
