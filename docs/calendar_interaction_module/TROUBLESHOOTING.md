# Calendar Interaction Module — Troubleshooting

## Overview

This document covers common failure modes, debug steps, and resolution paths for the Calendar Interaction Module. Issues are organized by subsystem.

---

## Table of Contents

1. [OAuth Errors](#oauth-errors)
2. [Token Expiry and Refresh Failures](#token-expiry-and-refresh-failures)
3. [Free/Busy Sync Failures](#freebusy-sync-failures)
4. [Booking Conflicts and Slot Issues](#booking-conflicts-and-slot-issues)
5. [Slot Computation Returns Empty](#slot-computation-returns-empty)
6. [Group Availability Issues](#group-availability-issues)
7. [Event Management Issues](#event-management-issues)
8. [Validation Errors](#validation-errors)
9. [Database Connectivity](#database-connectivity)
10. [Module Startup Failures](#module-startup-failures)
11. [FAQ](#faq)

---

## OAuth Errors

### Error: "Token exchange failed: 400 Bad Request"

**Cause:** The authorization code is invalid, expired, or the `redirect_uri` does not match.

**OAuth authorization codes are single-use and expire within 60 seconds** (Google) or 10 minutes (Microsoft). If the callback is delayed or the code is used twice, the exchange fails.

**Resolution:**
1. Confirm the `redirect_uri` passed to the callback endpoint exactly matches the URI registered in Google Cloud Console or Azure App Registration — including scheme, host, port, and path.
2. Ensure the callback is reached within the code's expiry window.
3. Do not call the callback endpoint twice for the same code.
4. Check `GOOGLE_CALENDAR_CLIENT_ID` and `GOOGLE_CALENDAR_CLIENT_SECRET` are set correctly.

```bash
# Verify env vars are set
env | grep GOOGLE_CALENDAR
env | grep MICROSOFT_CALENDAR
```

---

### Error: "redirect_uri_mismatch" from Google

**Cause:** The `redirect_uri` in the token request does not match any URI listed in the Google Cloud Console.

**Resolution:**
1. Go to Google Cloud Console → Credentials → Your OAuth client
2. Under "Authorized redirect URIs", add the exact URI being used
3. Common mistakes: trailing slash present in one place but not another, `http://` vs `https://`, different port

---

### Error: Auth URL Contains Blank `client_id`

**Symptom:** The generated auth URL shows `client_id=` with an empty value.

**Cause:** `GOOGLE_CALENDAR_CLIENT_ID` or `MICROSOFT_CALENDAR_CLIENT_ID` environment variable is not set.

**Resolution:**
```bash
# Check if the variable is set
echo $GOOGLE_CALENDAR_CLIENT_ID

# If empty, set it in your .env file or shell
export GOOGLE_CALENDAR_CLIENT_ID=your-actual-client-id
```

---

### Error: Google Does Not Return a Refresh Token

**Symptom:** `handle_google_callback` receives a token response without a `refresh_token` field. Log shows: `[OAUTH] Failed to store Google tokens` or refresh fails later.

**Cause:** The user has already authorized this app and `prompt=consent` was not honored, or the OAuth scope changed.

**Resolution:**
- The module always includes `prompt=consent` in the Google auth URL, which should force the consent screen and issue a new refresh token.
- If the user previously revoked and re-authorized, ensure `access_type=offline` is present.
- Instruct the user to visit `https://myaccount.google.com/permissions`, revoke access for the app, then re-authorize via the auth URL.

---

### Error: Microsoft "AADSTS65001" — User Consent Required

**Cause:** The Azure app requires admin consent for the tenant, and the user is in a managed tenant where delegated permissions need tenant admin pre-approval.

**Resolution:**
- Use the admin consent URL: `https://login.microsoftonline.com/{tenant-id}/adminconsent?client_id={client-id}&redirect_uri={uri}`
- Alternatively, configure the Azure app to use personal Microsoft accounts only (common endpoint supports these without admin consent).

---

## Token Expiry and Refresh Failures

### Symptom: Free/Busy Sync Returns No Data After Connecting Calendar

**Cause:** The access token expired and the refresh failed, or the refresh token is missing.

**Check `sync_error` field:**

```sql
SELECT calendar_name, sync_error, last_sync_at
FROM connected_calendars
WHERE hub_user_id = 42;
```

If `sync_error` contains "401" or "invalid_grant":

**Resolution — Invalid Grant (refresh token revoked):**
1. The user revoked access or changed their Google/Microsoft password, which invalidates all tokens.
2. The user must reconnect via the OAuth flow. Delete the old record and have them re-authorize:

```sql
-- Deactivate the broken integration
UPDATE platform_integrations SET is_active = FALSE WHERE hub_user_id = 42 AND platform = 'google_calendar';
UPDATE connected_calendars SET sync_enabled = FALSE WHERE hub_user_id = 42 AND provider = 'google';
```

Then direct the user to the auth URL to reconnect.

---

### Symptom: "No refresh token available" in logs

**Log entry:** `[OAUTH] No refresh token available for platform_integration_id=X`

**Cause:** The initial authorization did not return a refresh token. This happens when `access_type=offline` was not set or the user skipped the consent screen.

**Resolution:**
1. Have the user reconnect. The auth URL always includes `access_type=offline&prompt=consent`.
2. If this keeps happening, verify no middleware or proxy is stripping the `access_type` query parameter.

---

### Symptom: Token Refresh Succeeds But Free/Busy Still Shows Stale Data

**Cause:** The sync was triggered before the token was refreshed, or the `calendar_free_busy` table still has old rows from before the token was refreshed.

**Resolution:**
1. Trigger a manual sync after confirming the token is fresh:
   ```bash
   curl -X POST "http://localhost:8030/api/v1/calendar/oauth/calendars/1/sync" \
     -H "Content-Type: application/json" \
     -d '{"user_id": 42, "start": "2026-02-16T00:00:00Z", "end": "2026-02-23T00:00:00Z"}'
   ```
2. The sync deletes old rows for the requested time range before inserting new ones. Re-run with a broader range if needed.

---

## Free/Busy Sync Failures

### Error: "Google free/busy fetch failed: 403 Forbidden"

**Cause:** The OAuth scope `https://www.googleapis.com/auth/calendar.readonly` was not granted, or the calendar ID does not exist.

**Resolution:**
1. Confirm the user authorized the Calendar API scope (check `platform_integrations.access_token` using token introspection).
2. If the calendar ID is not `primary`, verify the calendar exists in the user's Google account.
3. Have the user disconnect and reconnect via the OAuth flow.

---

### Error: "Microsoft schedule fetch failed: 401 Unauthorized"

**Cause:** Access token is expired and refresh failed, or the `Calendars.Read` permission was removed.

**Resolution:**
1. Check `platform_integrations.token_expires_at` for this user.
2. If expired, trigger a refresh by calling `refresh_token_if_needed` via a test sync.
3. If the permission was removed by an Azure admin, the user needs to re-authorize.

---

### Symptom: `sync_error` is set but no log entry visible

**Cause:** The error was caught but the log level is above DEBUG.

**Resolution:**
Set `LOG_LEVEL=DEBUG` in the environment and re-trigger the sync. The `[SYNC]` prefix is used in all sync-related log entries.

---

## Booking Conflicts and Slot Issues

### Error: 409 Conflict — "Slot no longer available"

**Cause:** Two users attempted to book the same slot at the same time. The `FOR UPDATE` lock in `BookingService.create_booking` detected the conflict.

**Behavior:** This is expected and correct. The first request wins; the second receives a 409.

**Resolution for the guest:** Request the available slots list again and pick another slot.

---

### Symptom: Slot Appears Available But Booking Returns 409

**Cause:** The slot was available when the guest fetched the slot list but was claimed by another booking between the fetch and the booking creation.

**This is a race condition handled by design** — the `FOR UPDATE` lock prevents data corruption. The guest must select a different slot.

---

### Symptom: Cancelled Booking Does Not Restore the Slot

**Cause:** The cancelled booking's status is updated to `cancelled_by_guest` or `cancelled_by_host`, which removes it from the `status IN ('pending', 'confirmed')` filter used in busy-block queries. The slot should become available automatically.

**Check:** Verify the booking status was actually updated:

```sql
SELECT booking_uuid, status FROM bookings WHERE booking_uuid = 'your-uuid-here';
```

If the status is still `pending` or `confirmed`, the cancel endpoint may have failed silently. Check logs for errors.

---

## Slot Computation Returns Empty

### Possible Causes and Checks

**1. No weekly availability configured**

```bash
curl "http://localhost:8030/api/v1/calendar/availability/settings?user_id=42"
```

Look at `weekly_availability`. If it is `{}` or missing the target day, no slots will be generated.

**Resolution:** Update weekly availability:
```bash
curl -X PUT "http://localhost:8030/api/v1/calendar/availability/weekly" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 42, "availability": {"monday": [{"start": "09:00", "end": "17:00"}]}}'
```

---

**2. Date is outside `min_notice_hours` constraint**

If `min_notice_hours=4` and the requested date is "today" with all slots starting within the next 4 hours, they will all be filtered out.

```bash
# Check current settings
curl "http://localhost:8030/api/v1/calendar/availability/settings?user_id=42"
```

Look at `min_notice_hours`. For testing, set it to `0`:
```bash
curl -X PUT "http://localhost:8030/api/v1/calendar/availability/settings" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 42, "min_notice_hours": 0}'
```

---

**3. Date is beyond `max_future_days`**

If `max_future_days=30` and the requested date is 45 days away, no slots are returned.

---

**4. All slots are covered by busy blocks**

```sql
SELECT start_time, end_time, status
FROM calendar_free_busy
WHERE hub_user_id = 42
  AND start_time::date = '2026-02-23'
ORDER BY start_time;
```

If the entire day is marked busy, no slots will be available. Check for erroneously broad busy blocks:

```sql
-- Remove bad blocks if needed
DELETE FROM calendar_free_busy
WHERE hub_user_id = 42
  AND start_time >= '2026-02-23 00:00:00'
  AND end_time <= '2026-02-24 00:00:00';
```

---

**5. `booking_enabled` is False**

Check the `booking_enabled` flag in `user_calendar_settings`. Booking pages can only return slots if the host has booking enabled.

---

## Group Availability Issues

### Symptom: Group Availability Returns Empty Even Though Members Are Available

**Cause 1:** All required members are not available simultaneously. The algorithm only includes slots where `meets_requirements=True`, meaning ALL `is_required=True` members are available.

**Debug:** Temporarily make all members `is_required=False` and re-check. If slots appear, one required member is blocking them.

```sql
-- Identify which member has no availability for the target day
SELECT m.hub_user_id, u.username, m.is_required,
       s.weekly_availability
FROM booking_page_members m
JOIN hub_users u ON m.hub_user_id = u.id
LEFT JOIN user_calendar_settings s ON s.hub_user_id = m.hub_user_id
WHERE m.booking_page_id = 5;
```

**Cause 2:** One or more required members have no `user_calendar_settings` record. The algorithm treats users with no settings as unavailable.

**Resolution:** Have those users configure their availability via the settings API.

---

### Symptom: `available_count` is Lower Than Expected

**Cause:** Some members have busy blocks or existing bookings during the expected slots.

```sql
-- Check busy blocks for a specific member on a date
SELECT start_time, end_time, status
FROM calendar_free_busy
WHERE hub_user_id = 99
  AND start_time::date = '2026-02-23';
```

---

## Event Management Issues

### Symptom: Event Stuck in `pending` Status

**Cause:** The community requires approval but no admin has approved it.

**Resolution:**

```bash
# Approve the event (community_id=7, event_id=1)
curl -X POST "http://localhost:8030/api/v1/calendar/7/events/1/approve" \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}'
```

Or check community permission settings to see if approval is required:

```bash
curl "http://localhost:8030/api/v1/calendar/7/config/permissions"
```

---

### Symptom: Event Not Appearing in `/upcoming`

**Cause:** The event status is `pending` or `rejected` (not `approved`), or the event date is in the past.

```sql
SELECT id, title, status, event_date FROM calendar_events WHERE community_id = 7 ORDER BY event_date;
```

---

## Validation Errors

### Error: 400 with "extra inputs are not permitted"

**Cause:** The request body contains a field not defined in the Pydantic model. All models use `ConfigDict(extra='forbid')`.

**Resolution:** Remove the unexpected field from the request. Check the API documentation for the exact allowed fields for the endpoint.

---

### Error: 400 with "value is not a valid datetime"

**Cause:** Date/time field was sent in a format other than ISO 8601.

**Resolution:** Use ISO 8601 format: `2026-03-01T18:00:00Z` or `2026-03-01T18:00:00+00:00`. Do not send plain date strings like `2026-03-01` for datetime fields.

---

### Error: 400 with "String should match pattern '^[a-z0-9-]+$'"

**Cause:** A booking page slug contains uppercase letters, underscores, spaces, or other disallowed characters.

**Resolution:** Use only lowercase letters, digits, and hyphens. Example: `alice-30min` is valid; `Alice_30min` is not.

---

## Database Connectivity

### Symptom: Module Starts But All API Calls Return 500

**Cause:** Database connection failed during startup. The module may have started without a working DB connection.

**Check logs for:**
```
[ERROR] Database initialization failed
```

**Resolution:**
1. Verify `DATABASE_URL` is correct.
2. Confirm PostgreSQL is reachable from the module's network:
   ```bash
   psql "$DATABASE_URL" -c "SELECT 1;"
   ```
3. Verify the WaddleBot schema is applied (tables `platform_integrations`, `connected_calendars`, etc. must exist).

---

## Module Startup Failures

### Symptom: Module Fails to Start — "No module named 'flask_core'"

**Cause:** `flask_core` is a shared library in the WaddleBot monorepo that is not installed as a standard pip package.

**Resolution:**

```bash
# The app.py adds the libs directory to sys.path:
# sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs'))
# Ensure you are running from the correct directory or that PYTHONPATH includes the libs directory
cd action/interactive/calendar_interaction_module
python app.py
```

---

### Symptom: Redis Listener Thread Fails to Start

**Log:** `[ERROR] Credential listener error: ...`

**Cause:** `REDIS_URL` is set but the Redis server is not reachable.

**Resolution:** Either fix the Redis connection or remove `REDIS_URL` from the environment to disable the listener. The module will function without Redis — credentials will just be loaded from environment variables at startup and not refreshed live.

---

## FAQ

**Q: Can I run this module without Google or Microsoft credentials?**
A: Yes. The OAuth-related endpoints will return auth URLs with blank `client_id` values (which will fail at the provider), but all event management, RSVP, ticketing, booking pages, and slot computation features work without OAuth credentials. Connect OAuth only when external calendar sync is needed.

**Q: Why does the slot list sometimes show different results on repeated requests?**
A: If a booking was just made, the `bookings` table query in `get_free_busy` will reflect it. Also, if `min_notice_hours > 0`, slots that cross the notice boundary as time passes will disappear from the list. This is expected behavior.

**Q: Can I delete free/busy data and re-sync?**
A: Yes. Delete rows from `calendar_free_busy` for the relevant user and calendar, then trigger a new sync:
```sql
DELETE FROM calendar_free_busy WHERE hub_user_id = 42 AND connected_calendar_id = 1;
```
```bash
curl -X POST "http://localhost:8030/api/v1/calendar/oauth/calendars/1/sync" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 42, "start": "2026-02-16T00:00:00Z", "end": "2026-03-16T00:00:00Z"}'
```

**Q: How do I test that `FOR UPDATE` locking works correctly?**
A: Send two concurrent POST requests to `POST /book/{slug}` for the same slot within the same millisecond window using a tool like `ab` or `hey`. Exactly one should return 201 and the other should return 409 with "Slot no longer available".

**Q: What happens if a booking page is deleted while bookings are active?**
A: The booking page is soft-deleted (`is_active=FALSE`). Existing booking records in the `bookings` table are not deleted. The slot list endpoint returns 404 for soft-deleted pages, but the bookings themselves remain accessible via `/bookings/{uuid}`.

**Q: The group availability best-slots endpoint is slow for wide date ranges. Why?**
A: The `get_most_available_slots` method iterates day-by-day across the date range and calls `get_group_availability` for each day. For large groups and long ranges, this generates many database queries. Limit the date range to 2–4 weeks for reasonable performance. Future optimization would cache daily results.
