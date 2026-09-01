# Calendar Interaction Module — Configuration

## Overview

All configuration for the Calendar Interaction Module is managed through environment variables. The module uses `python-dotenv` to load a `.env` file if present in the module directory. Environment variables always override `.env` file values.

---

## Environment Variables

### Core Module Settings

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODULE_PORT` | No | `8030` | TCP port the Quart server listens on |
| `MODULE_NAME` | No | `calendar_interaction_module` | Module identifier for health/metrics responses (set in config.py as constant) |
| `SECRET_KEY` | Yes (production) | `change-me-in-production` | Flask/Quart secret key for session signing. Must be changed in all non-local environments. |
| `LOG_LEVEL` | No | `INFO` | Python logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

**WARNING:** The default `SECRET_KEY` value `change-me-in-production` must never be used in any deployed environment. Set a random 32-byte hex string in production.

---

### Database

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql://waddlebot:password@localhost:5432/waddlebot` | Full PostgreSQL connection string |

**Format:** `postgresql://USER:PASSWORD@HOST:PORT/DBNAME`

The module uses `AsyncDAL` for all database operations. All queries are parameterized using `$1`, `$2`, etc. placeholders (PostgreSQL-style positional parameters).

**Tables used:**
- `platform_integrations` — OAuth tokens (read/write)
- `connected_calendars` — Calendar connections (read/write)
- `calendar_free_busy` — Busy blocks from external calendars (read/write)
- `user_calendar_settings` — User availability settings (read/write)
- `booking_pages` — Booking page definitions (read/write)
- `booking_page_members` — Group booking page members (read/write)
- `bookings` — Appointment records (read/write)
- `calendar_rsvps` — RSVP records (read/write)
- `calendar_events` — Community event records (read/write)
- `hub_users` — User lookup (read only)

---

### Service Integration

| Variable | Required | Default | Description |
|---|---|---|---|
| `CORE_API_URL` | No | `http://router-service:8000` | Base URL of the WaddleBot router/core service |
| `ROUTER_API_URL` | No | `http://router-service:8000/api/v1/router` | Full router API endpoint |
| `LABELS_API_URL` | No | `http://labels-core-service:8025` | Labels/tags service URL |

These URLs are used for cross-module communication, such as fetching user context from the router or resolving community membership.

---

### Google Calendar OAuth

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_CALENDAR_CLIENT_ID` | Yes (for Google OAuth) | `''` (empty) | OAuth 2.0 client ID from Google Cloud Console |
| `GOOGLE_CALENDAR_CLIENT_SECRET` | Yes (for Google OAuth) | `''` (empty) | OAuth 2.0 client secret from Google Cloud Console |

**How Google OAuth is used:**

The module requests:
- Scope: `https://www.googleapis.com/auth/calendar.readonly`
- Access type: `offline` (to receive a refresh token)
- Prompt: `consent` (forces consent screen even for previously-authorized apps, ensuring refresh token is always returned)

Token exchange endpoint: `https://oauth2.googleapis.com/token`
Free/busy API endpoint: `https://www.googleapis.com/calendar/v3/freeBusy`

If these variables are empty, the Google OAuth endpoints will return auth URLs with blank `client_id` values, and token exchanges will fail. The module will not crash on startup — it will only fail at runtime when Google OAuth is attempted.

---

### Microsoft Calendar OAuth

| Variable | Required | Default | Description |
|---|---|---|---|
| `MICROSOFT_CALENDAR_CLIENT_ID` | Yes (for Microsoft OAuth) | `''` (empty) | Application (client) ID from Azure App Registration |
| `MICROSOFT_CALENDAR_CLIENT_SECRET` | Yes (for Microsoft OAuth) | `''` (empty) | Client secret value from Azure App Registration |

**How Microsoft OAuth is used:**

The module requests:
- Scope: `Calendars.Read` (delegated permission)
- Response mode: `query`
- Tenant: `common` (supports both organizational and personal Microsoft accounts)

Authorization endpoint: `https://login.microsoftonline.com/common/oauth2/v2.0/authorize`
Token exchange endpoint: `https://login.microsoftonline.com/common/oauth2/v2.0/token`
Schedule API endpoint: `https://graph.microsoft.com/v1.0/me/calendar/getSchedule`

---

### Redis (Optional — Credential Refresh Notifications)

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDIS_URL` | No | `''` (empty) | Redis connection URL (e.g., `redis://localhost:6379/0`) |

**Purpose:** When set, the module starts a background daemon thread that subscribes to the Redis pub/sub channel `credentials:calendar_interaction:bot:refreshed`. When a message is received on this channel (published by an admin credential rotation process), the module resets its credential cache and reloads credentials from the `platform_integrations` table on the next request.

**Behavior without Redis:** If `REDIS_URL` is empty or unset, the credential listener is not started and credentials are loaded once at startup from environment variables. This is acceptable for development and simple deployments.

**Redis URL formats:**
```
redis://localhost:6379/0
redis://:password@redis-host:6379/0
rediss://secure-redis-host:6380/0   (TLS)
```

---

## Example .env File

```env
# ============================================================
# Calendar Interaction Module — Environment Configuration
# ============================================================

# Core settings
MODULE_PORT=8030
SECRET_KEY=replace_with_64_char_random_hex_string_in_production
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://waddlebot:dev_password@localhost:5432/waddlebot

# Service integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router
LABELS_API_URL=http://labels-core-service:8025

# Google Calendar OAuth
# Get these from: console.cloud.google.com -> APIs & Services -> Credentials
GOOGLE_CALENDAR_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=GOCSPX-your-secret-here

# Microsoft Calendar OAuth
# Get these from: portal.azure.com -> Azure Active Directory -> App registrations
MICROSOFT_CALENDAR_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CALENDAR_CLIENT_SECRET=your-azure-client-secret-value

# Redis (optional — leave empty to disable credential refresh listener)
# REDIS_URL=redis://localhost:6379/0
```

---

## Kubernetes Deployment Configuration

When deploying via Kubernetes (Kustomize), environment variables are set through a ConfigMap and Secrets manifest. Do not store OAuth client secrets in ConfigMaps — use Kubernetes Secrets.

Example Secret manifest (do not commit to version control):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: calendar-interaction-secrets
  namespace: waddlebot
type: Opaque
stringData:
  SECRET_KEY: "your-64-char-random-key"
  DATABASE_URL: "postgresql://waddlebot:password@postgres:5432/waddlebot"
  GOOGLE_CALENDAR_CLIENT_ID: "your-google-client-id"
  GOOGLE_CALENDAR_CLIENT_SECRET: "your-google-client-secret"
  MICROSOFT_CALENDAR_CLIENT_ID: "your-ms-client-id"
  MICROSOFT_CALENDAR_CLIENT_SECRET: "your-ms-client-secret"
```

Example ConfigMap for non-secret values:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calendar-interaction-config
  namespace: waddlebot
data:
  MODULE_PORT: "8030"
  LOG_LEVEL: "INFO"
  CORE_API_URL: "http://router-service:8000"
  ROUTER_API_URL: "http://router-service:8000/api/v1/router"
  LABELS_API_URL: "http://labels-core-service:8025"
  REDIS_URL: "redis://redis-service:6379/0"
```

---

## Feature Flags via Availability Settings

The following booking behaviors are controlled at runtime through the `user_calendar_settings` table, not environment variables. They are configured per-user via the API.

| Setting | Default | Description |
|---|---|---|
| `booking_enabled` | `false` | Whether the user accepts individual bookings |
| `min_notice_hours` | `4` | Minimum hours before a slot can be booked |
| `max_future_days` | `30` | Maximum days in advance a slot can be booked |
| `buffer_minutes` | `0` | Gap between consecutive bookings |
| `slot_durations` | `[30]` | Available slot durations offered |
| `default_slot_duration` | `30` | Default slot length in minutes |
| `visibility_public` | `hidden` | Free/busy visibility to unauthenticated users |
| `visibility_registered` | `free_busy` | Visibility to registered users |
| `visibility_community` | `details` | Visibility to community members |

---

## OAuth Redirect URI Configuration

The redirect URI is passed by the client at runtime — it is not stored as an environment variable. However, it must be pre-registered in both Google Cloud Console and Microsoft Azure App Registration before it will be accepted.

For WaddleBot deployments:

| Environment | Redirect URI |
|---|---|
| Local (alpha) | `https://waddlebot.localhost.local/api/v1/calendar/oauth/google/callback` |
| Beta | `https://waddlebot.penguintech.cloud/api/v1/calendar/oauth/google/callback` |
| Production | `https://waddlebot.io/api/v1/calendar/oauth/google/callback` |

Register all environments in each OAuth provider's console.

---

## Token Expiry and Refresh Behavior

- Google tokens expire in approximately 1 hour (`expires_in=3600`)
- Microsoft tokens expire in approximately 1 hour
- The `refresh_token_if_needed()` method refreshes a token if it will expire within the next **5 minutes**
- If a refresh token is missing (can happen if `access_type=offline` was not set or was bypassed), the module logs an error and returns `False` — the calendar will need to be reconnected via the OAuth flow
- Refreshed tokens are written back to the `platform_integrations` table with an updated `token_expires_at` and `updated_at`
- Some providers (Google) may issue a new refresh token during refresh — the module stores the new value if present, otherwise keeps the existing one
