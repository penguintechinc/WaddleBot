# Calendar Interaction Module — Testing Guide

## Overview

This document describes how to test the Calendar Interaction Module, including OAuth flow testing with mock tokens, booking test data, and service-level test strategies.

---

## Table of Contents

1. [Test Environment Setup](#test-environment-setup)
2. [Running Existing Tests](#running-existing-tests)
3. [Testing OAuth Flows Locally](#testing-oauth-flows-locally)
4. [Booking Test Data](#booking-test-data)
5. [Availability Service Testing](#availability-service-testing)
6. [Group Availability Testing](#group-availability-testing)
7. [Event Management Testing](#event-management-testing)
8. [RSVP and Ticketing Testing](#rsvp-and-ticketing-testing)
9. [Validation Model Testing](#validation-model-testing)
10. [Integration Test Patterns](#integration-test-patterns)

---

## Test Environment Setup

### Prerequisites

```bash
cd action/interactive/calendar_interaction_module
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
```

Ensure a local PostgreSQL instance is running with the WaddleBot schema applied. Run migrations in order from `config/postgres/migrations/`, including `036_calendar_appointments.sql` (booking and availability tables) and `037_fix_community_schema.sql`.

```bash
psql -U waddlebot -d waddlebot_test -f config/postgres/migrations/036_calendar_appointments.sql
psql -U waddlebot -d waddlebot_test -f config/postgres/migrations/037_fix_community_schema.sql
```

### Test Environment Variables

```env
MODULE_PORT=8031
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot_test
LOG_LEVEL=DEBUG
SECRET_KEY=test-secret-key-not-for-production
GOOGLE_CALENDAR_CLIENT_ID=test-google-client-id
GOOGLE_CALENDAR_CLIENT_SECRET=test-google-secret
MICROSOFT_CALENDAR_CLIENT_ID=test-ms-client-id
MICROSOFT_CALENDAR_CLIENT_SECRET=test-ms-secret
```

---

## Running Existing Tests

The module includes `test_validation.py` which tests the Pydantic validation models:

```bash
cd action/interactive/calendar_interaction_module
python -m pytest test_validation.py -v
```

This file validates:
- `EventCreateRequest` accepts valid inputs and rejects invalid dates, bad URLs, whitespace-only titles
- `EventSearchParams` date range enforcement (date_to must be after date_from)
- `BookingCreateRequest` slot time order validation (slot_end after slot_start)
- `BookingPageCreateRequest` slug pattern enforcement (`^[a-z0-9-]+$`)
- `GroupMemberAddRequest` user_id positive integer constraint
- `BestSlotsParams` limit range (1–20)
- `recurring_days` entries must be integers 0–6

---

## Testing OAuth Flows Locally

### Strategy: Mock the External Token Exchange

All external HTTP calls in `CalendarOAuthService` use `httpx.AsyncClient`. Mock this at the unit test level to avoid hitting real Google/Microsoft endpoints.

### Example: Google Callback with Mocked Token Response

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from services.calendar_oauth_service import CalendarOAuthService

@pytest.mark.asyncio
async def test_handle_google_callback_success():
    mock_dal = AsyncMock()

    # First execute: INSERT platform_integrations -> returns id=1
    # Second execute: INSERT connected_calendars -> returns calendar record
    mock_dal.execute.side_effect = [
        [{'id': 1}],
        [{'id': 3, 'provider': 'google', 'calendar_id': 'primary',
          'calendar_name': 'Google Calendar', 'is_primary': True}]
    ]

    service = CalendarOAuthService(mock_dal)
    service.google_client_id = 'test-client-id'
    service.google_client_secret = 'test-secret'

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'access_token': 'ya29.mock_access_token',
        'refresh_token': '1//mock_refresh_token',
        'expires_in': 3600,
        'token_type': 'Bearer'
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await service.handle_google_callback(
            user_id=42,
            code='test_authorization_code',
            redirect_uri='https://example.com/oauth/google/callback'
        )

    assert result is not None
    assert result['provider'] == 'google'
    assert result['calendar_id'] == 'primary'
    assert result['is_primary'] is True

    # Confirm tokens were in the INSERT parameters
    first_call_args = mock_dal.execute.call_args_list[0]
    params = first_call_args[0][1]
    assert 'ya29.mock_access_token' in params
    assert '1//mock_refresh_token' in params
```

### Example: Token Refresh Trigger Test

```python
@pytest.mark.asyncio
async def test_refresh_triggers_when_token_expires_soon():
    mock_dal = AsyncMock()

    # Token expires in 3 minutes (within the 5-minute refresh threshold)
    expires_soon = datetime.now(timezone.utc) + timedelta(minutes=3)

    mock_dal.execute.side_effect = [
        [{'id': 1, 'platform': 'google_calendar',
          'access_token': 'old_token', 'refresh_token': 'refresh_tok',
          'token_expires_at': expires_soon}],
        [{'id': 1}]  # UPDATE response
    ]

    service = CalendarOAuthService(mock_dal)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'access_token': 'new_token', 'expires_in': 3600}

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await service.refresh_token_if_needed(1)

    assert result is True
    # Confirm UPDATE was called with the new token
    update_call = mock_dal.execute.call_args_list[1]
    assert 'new_token' in update_call[0][1]


@pytest.mark.asyncio
async def test_refresh_skipped_for_valid_token():
    mock_dal = AsyncMock()
    expires_later = datetime.now(timezone.utc) + timedelta(minutes=30)

    mock_dal.execute.return_value = [
        {'id': 1, 'platform': 'google_calendar',
         'access_token': 'still_valid', 'refresh_token': 'refresh_tok',
         'token_expires_at': expires_later}
    ]

    service = CalendarOAuthService(mock_dal)
    result = await service.refresh_token_if_needed(1)

    assert result is True
    # Only one DB call (SELECT) — no UPDATE issued
    assert mock_dal.execute.call_count == 1
```

### Inserting Mock Tokens Directly for Downstream Testing

When testing booking flows that depend on connected calendars, skip the OAuth flow and insert tokens directly:

```sql
-- Mock Google Calendar connection for user 42
INSERT INTO platform_integrations (
    hub_user_id, platform, integration_type,
    access_token, refresh_token, token_expires_at, is_active, created_at
) VALUES (
    42, 'google_calendar', 'user_oauth',
    'mock_access_token', 'mock_refresh_token',
    NOW() + INTERVAL '1 hour', TRUE, NOW()
) RETURNING id;

-- Use the returned id (e.g., 1) for connected_calendars
INSERT INTO connected_calendars (
    hub_user_id, platform_integration_id, provider,
    calendar_id, calendar_name, is_primary, sync_enabled
) VALUES (42, 1, 'google', 'primary', 'Test Calendar', TRUE, TRUE);

-- Insert mock busy blocks to test slot exclusion
INSERT INTO calendar_free_busy (
    hub_user_id, connected_calendar_id, start_time, end_time, status, fetched_at
) VALUES
    (42, 1, '2026-02-23 10:00:00+00', '2026-02-23 11:00:00+00', 'busy', NOW()),
    (42, 1, '2026-02-23 14:00:00+00', '2026-02-23 14:30:00+00', 'busy', NOW());
```

---

## Booking Test Data

### Insert User Availability Settings

```sql
INSERT INTO user_calendar_settings (
    hub_user_id, slot_durations, default_slot_duration,
    min_notice_hours, max_future_days, buffer_minutes,
    weekly_availability, timezone, booking_enabled
) VALUES (
    42, '[30, 60]', 30, 4, 30, 15,
    '{"monday":[{"start":"09:00","end":"12:00"},{"start":"13:00","end":"17:00"}],
      "tuesday":[{"start":"09:00","end":"17:00"}],
      "wednesday":[{"start":"09:00","end":"17:00"}],
      "thursday":[{"start":"09:00","end":"17:00"}],
      "friday":[{"start":"09:00","end":"13:00"}]}',
    'UTC', TRUE
);
```

### Create a Test Booking Page

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/booking-pages" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42, "slug": "test-30min",
    "title": "Test 30-Minute Booking", "slot_duration": 30, "access_scope": "public"
  }'
```

### Verify Slots Are Returned

```bash
curl "http://localhost:8030/api/v1/calendar/book/test-30min/slots?date=2026-02-23"
```

Expected: 30-minute slots at 09:00, 09:45, 10:30, 11:15, 13:00, 13:45, 14:30, etc. (Monday availability with 15-minute buffers). Mock busy blocks from 10:00–11:00 and 14:00–14:30 will be excluded.

### Create a Booking

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/book/test-30min" \
  -H "Content-Type: application/json" \
  -d '{
    "guest_name": "Test Guest", "guest_email": "test@example.com",
    "slot_start": "2026-02-23T09:00:00Z", "slot_end": "2026-02-23T09:30:00Z"
  }'
```

Verify the booked slot no longer appears in the available slots list.

---

## Availability Service Testing

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta
from services.availability_service import AvailabilityService

BASE_SETTINGS = {
    'id': 1, 'visibility_public': 'hidden',
    'visibility_registered': 'free_busy', 'visibility_community': 'details',
    'slot_durations': [30], 'default_slot_duration': 30,
    'min_notice_hours': 0, 'max_future_days': 365,
    'buffer_minutes': 0, 'timezone': 'UTC',
    'booking_enabled': True, 'booking_slug': None,
    'booking_page_title': None, 'booking_page_description': None,
    'weekly_availability': {
        'monday': [{'start': '09:00', 'end': '11:00'}]
    }
}

@pytest.mark.asyncio
async def test_busy_blocks_exclude_slots():
    mock_dal = AsyncMock()
    mock_dal.execute.side_effect = [
        [BASE_SETTINGS],
        # Busy 09:30-10:00
        [{'start_time': datetime(2026, 2, 23, 9, 30, tzinfo=timezone.utc),
          'end_time': datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc)}],
        []  # No existing bookings
    ]

    service = AvailabilityService(mock_dal)
    # 2026-02-23 is a Monday
    slots = await service.compute_available_slots(42, datetime(2026, 2, 23, tzinfo=timezone.utc), 30)

    starts = [s['start'] for s in slots]
    assert any('09:00' in s for s in starts), "09:00-09:30 should be available"
    assert any('10:00' in s for s in starts), "10:00-10:30 should be available"
    assert not any('09:30' in s for s in starts), "09:30-10:00 should be blocked"


@pytest.mark.asyncio
async def test_weekend_returns_empty():
    mock_dal = AsyncMock()
    mock_dal.execute.return_value = [BASE_SETTINGS]

    service = AvailabilityService(mock_dal)
    # 2026-02-21 is a Saturday — no availability configured
    slots = await service.compute_available_slots(42, datetime(2026, 2, 21, tzinfo=timezone.utc), 30)
    assert slots == []
```

---

## Group Availability Testing

### SQL Setup for Two-Member Group Test

```sql
-- User 42: Monday all day
INSERT INTO user_calendar_settings (hub_user_id, weekly_availability, min_notice_hours, max_future_days, buffer_minutes)
VALUES (42, '{"monday":[{"start":"09:00","end":"17:00"}]}', 0, 365, 0)
ON CONFLICT (hub_user_id) DO UPDATE SET weekly_availability = EXCLUDED.weekly_availability;

-- User 99: Monday afternoon only
INSERT INTO user_calendar_settings (hub_user_id, weekly_availability, min_notice_hours, max_future_days, buffer_minutes)
VALUES (99, '{"monday":[{"start":"13:00","end":"17:00"}]}', 0, 365, 0)
ON CONFLICT (hub_user_id) DO UPDATE SET weekly_availability = EXCLUDED.weekly_availability;

-- Group booking page
INSERT INTO booking_pages (slug, page_type, community_id, title, slot_duration, access_scope)
VALUES ('test-group', 'group', 7, 'Test Group', 30, 'community')
RETURNING id;

-- Both required members (page id from above, e.g., 5)
INSERT INTO booking_page_members (booking_page_id, hub_user_id, is_required)
VALUES (5, 42, TRUE), (5, 99, TRUE)
ON CONFLICT DO NOTHING;
```

```bash
curl "http://localhost:8030/api/v1/calendar/booking-pages/5/group-availability?date=2026-02-23"
```

Expected: Only slots from 13:00 appear with `meets_requirements=true`. Morning slots should not appear.

---

## Event Management Testing

### Test Approval Workflow

```bash
# Create event requiring approval
curl -X POST "http://localhost:8030/api/v1/calendar/7/events" \
  -H "Content-Type: application/json" \
  -d '{"community_id":7,"title":"Approval Test","event_date":"2026-03-15T18:00:00Z","platform":"discord","entity_id":"123","created_by_username":"tester","requires_approval":true}'

# Approve it (replace 1 with returned event id)
curl -X POST "http://localhost:8030/api/v1/calendar/7/events/1/approve" \
  -H "Content-Type: application/json" \
  -d '{"status":"approved","notes":"Approved in test."}'

# Verify appears in upcoming
curl "http://localhost:8030/api/v1/calendar/7/upcoming"
```

### Test Recurring Events

```bash
curl -X POST "http://localhost:8030/api/v1/calendar/7/events" \
  -H "Content-Type: application/json" \
  -d '{"community_id":7,"title":"Weekly Test","event_date":"2026-02-23T09:00:00Z","end_date":"2026-02-23T09:30:00Z","platform":"discord","entity_id":"123","created_by_username":"tester","is_recurring":true,"recurring_pattern":"weekly","recurring_days":[1],"recurring_end_date":"2026-05-01T00:00:00Z"}'
```

---

## RSVP and Ticketing Testing

### Capacity and Waitlist Test

```sql
-- Set low capacity for testing
UPDATE calendar_events SET max_attendees = 2, waitlist_enabled = TRUE WHERE id = 1;
```

```bash
# Fill capacity with 2 RSVPs, then test waitlist on 3rd
for user in u1 u2 u3; do
  curl -X POST "http://localhost:8030/api/v1/calendar/7/events/1/rsvp" \
    -H "Content-Type: application/json" \
    -d "{\"platform\":\"discord\",\"platform_user_id\":\"$user\",\"username\":\"$user\",\"rsvp_status\":\"yes\"}"
  echo ""
done
# Third response should have is_waitlisted=true
```

### Check-In State Machine Test

```bash
# Check in once (success)
curl -X POST "http://localhost:8030/api/v1/tickets/7/events/1/check-in" \
  -H "Content-Type: application/json" \
  -d '{"ticket_code":"TICK-TEST0001","check_in_method":"qr_scan","checked_in_by":42}'
# Expect: result_code=success

# Check in again (already checked in)
curl -X POST "http://localhost:8030/api/v1/tickets/7/events/1/check-in" \
  -H "Content-Type: application/json" \
  -d '{"ticket_code":"TICK-TEST0001","check_in_method":"qr_scan","checked_in_by":42}'
# Expect: result_code=already_checked_in

# Undo check-in
curl -X POST "http://localhost:8030/api/v1/tickets/7/events/1/undo-check-in" \
  -H "Content-Type: application/json" \
  -d '{"ticket_code":"TICK-TEST0001"}'
```

---

## Validation Model Testing

Extend `test_validation.py` with these additional edge cases:

```python
import pytest
from pydantic import ValidationError
from validation_models import BookingPageCreateRequest, BookingCreateRequest, BestSlotsParams
from datetime import datetime, timezone, timedelta

def test_slug_rejects_uppercase():
    with pytest.raises(ValidationError):
        BookingPageCreateRequest(slug="MyPage", title="Test", slot_duration=30)

def test_slug_rejects_spaces():
    with pytest.raises(ValidationError):
        BookingPageCreateRequest(slug="my page", title="Test", slot_duration=30)

def test_slug_rejects_underscores():
    with pytest.raises(ValidationError):
        BookingPageCreateRequest(slug="my_page", title="Test", slot_duration=30)

def test_slot_duration_minimum():
    with pytest.raises(ValidationError):
        BookingPageCreateRequest(slug="test", title="Test", slot_duration=4)  # min is 5

def test_slot_duration_maximum():
    with pytest.raises(ValidationError):
        BookingPageCreateRequest(slug="test", title="Test", slot_duration=481)  # max is 480

def test_booking_invalid_email():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        BookingCreateRequest(
            guest_name="Test",
            guest_email="not-an-email",
            slot_start=now + timedelta(hours=1),
            slot_end=now + timedelta(hours=2)
        )

def test_best_slots_limit_over_max():
    with pytest.raises(ValidationError):
        BestSlotsParams(start="2026-02-17", end="2026-02-21", limit=21)

def test_best_slots_limit_under_min():
    with pytest.raises(ValidationError):
        BestSlotsParams(start="2026-02-17", end="2026-02-21", limit=0)
```
