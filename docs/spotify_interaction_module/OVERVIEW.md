# Spotify Interaction Module — Overview

> Spotify OAuth 2.0 integration service providing per-community token management,
> playback control, song requests, and playlist operations for the WaddleBot platform.

---

## Purpose

The spotify_interaction_module is a dedicated microservice that bridges WaddleBot
communities with the Spotify Web API. Each community authenticates independently via
Spotify Authorization Code OAuth 2.0 flow, and the module manages the full token
lifecycle — acquisition, storage, automatic refresh, and revocation — so that upstream
services can request a valid token at any time without handling credential complexity.

The service is intentionally narrow in scope: it owns the OAuth state machine and
exposes a REST API that other modules (primarily the unified_music_module) call to
perform Spotify operations on behalf of a community. This separation keeps credential
management isolated, auditable, and replaceable.

---

## OAuth Flow Summary

Spotify uses the Authorization Code flow (server-side with a confidential client
secret). The high-level sequence is:

    Community Admin          spotify_interaction_module     Spotify Accounts
          |                            |                           |
          |  /auth/login?community_id  |                           |
          |-------------------------->|                           |
          |                            |  Builds authorize URL     |
          |                            |  (client_id, scopes,     |
          |                            |   state, show_dialog)    |
          |<-- Redirect to Spotify ----|                           |
          |                            |                           |
          |---- Logs in, grants scopes --------------------------->|
          |                            |                           |
          |<-- Redirect: redirect_uri?code=X&state=Y --------------|
          |                            |                           |
          |  GET /auth/callback?code=X |                           |
          |-------------------------->|                           |
          |                            |  POST /api/token         |
          |                            |  grant_type=auth_code    |
          |                            |-------------------------->|
          |                            |<-- access_token + refresh-|
          |                            |  _store_token() upserts  |
          |                            |  music_oauth_tokens      |
          |<-- 200 OK / success -------|                           |

After initial authorization, the module automatically refreshes the access_token
using the stored refresh_token when the token is within 5 minutes of expiry.
This buffer is defined by timedelta(minutes=5) in SpotifyOAuthService.get_valid_token.

---

## Capabilities

| Capability | Description |
|---|---|
| Per-community OAuth | Each community has its own independent Spotify token pair |
| Authorization Code flow | Full server-side OAuth 2.0 with confidential client secret |
| Automatic token refresh | Tokens refreshed 5 minutes before expiry via get_valid_token |
| Token storage | PostgreSQL music_oauth_tokens table with upsert on conflict |
| Token revocation | Hard DELETE from music_oauth_tokens on community disconnect |
| Scope management | 11 default scopes covering playback, playlists, and history |
| Credential live-reload | Redis pub/sub on credentials:spotify:bot:refreshed channel |
| DB credential fallback | Loads credentials from platform_integrations table |
| Health endpoints | /health, /healthz, /metrics via shared flask_core library |
| Status endpoint | GET /api/v1/status returns module operational state |

---

## Default OAuth Scopes

SpotifyOAuthService.DEFAULT_SCOPES contains:

| Scope | Purpose |
|---|---|
| user-read-playback-state | Read current playback device and state |
| user-modify-playback-state | Control playback: play, pause, skip, seek |
| user-read-currently-playing | Read the currently playing track |
| playlist-read-private | Read private playlists |
| playlist-read-collaborative | Read collaborative playlists |
| playlist-modify-public | Create and edit public playlists |
| playlist-modify-private | Create and edit private playlists |
| user-library-read | Read saved tracks and albums |
| user-library-modify | Save and remove tracks and albums |
| user-top-read | Read top artists and tracks |
| user-read-recently-played | Read recently played tracks |

---

## Documentation Index

| Document | Description |
|---|---|
| OVERVIEW.md | Purpose, capabilities, OAuth flow summary (this file) |
| USAGE.md | Getting started, Docker run, OAuth setup walkthrough |
| API.md | All endpoints with request/response schemas |
| ARCHITECTURE.md | Internal components, data flows, token lifecycle |
| CONFIGURATION.md | All environment variables and example .env |
| TESTING.md | Mocking OAuth tokens, fixtures, how to run tests |
| TROUBLESHOOTING.md | Token expiry, scope errors, rate limiting, OAuth failures |
| RELEASE_NOTES.md | Version history |

---

## Quick Reference

| Item | Value |
|---|---|
| Source directory | action/interactive/spotify_interaction_module/ |
| Language | Python 3.12 |
| Framework | Quart (async) + Hypercorn ASGI |
| REST Port | 8026 (default, override with MODULE_PORT env var) |
| Module name | spotify_interaction_module |
| Module version | 2.0.0 |
| Internal service URL | http://spotify-interaction:8026 |
| OAuth token table | music_oauth_tokens (PostgreSQL) |
| Credential table | platform_integrations (PostgreSQL) |
| Redis channel | credentials:spotify:bot:refreshed |
| Spotify auth URL | https://accounts.spotify.com/authorize |
| Spotify token URL | https://accounts.spotify.com/api/token |
| Container user | waddlebot (non-root) |
| Log directory | /var/log/waddlebotlog/ |
| Workers | 4 (Hypercorn, set in Dockerfile CMD) |

---

## Relationship to Other Modules

    unified_music_module (8051)
           |
           |  Requests valid Spotify token,
           |  delegates OAuth-gated calls
           v
    spotify_interaction_module (8026)
           |
           |  Fetches/refreshes tokens from PostgreSQL,
           |  calls Spotify Web API on behalf of community
           v
    Spotify Web API (accounts.spotify.com / api.spotify.com)

The unified_music_module is the primary internal consumer of the Spotify module.
The router module at router-service:8000 routes external /spotify/* requests
inbound. Browser source and overlay modules consume now-playing data produced
downstream from Spotify API responses.

---

## Credential Loading Priority

The module uses a two-tier credential resolution strategy defined in Config:

1. Database (platform_integrations table): Config.load_credentials_from_db()
   queries for an active Spotify bot integration record with is_active = TRUE.
   This is the production path.

2. Environment variables (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET): Fallback
   used during local development or if the DB lookup fails. A warning is logged
   when falling back to environment variables.

Live credential rotation is supported via Config.start_credential_listener(),
which subscribes to the Redis channel credentials:spotify:bot:refreshed and resets
_credentials_loaded = False, triggering a re-read from the DB on the next request.
The _credential_lock threading.Lock ensures safe concurrent access to credential
state across Hypercorn worker processes.

---

## Maintained By

Penguin Tech Inc
Support: support@penguintech.io
Website: www.penguintech.io


---

## Technology Stack

The module is built on the following technology choices:

| Component | Technology | Rationale |
|---|---|---|
| Web framework | Quart 0.19+ | Async-native Flask-compatible; supports asyncio natively |
| ASGI server | Hypercorn 0.16+ | ASGI-compatible, production-grade, supports HTTP/2 |
| HTTP client | aiohttp | Async HTTP for Spotify API calls without blocking the event loop |
| Database ORM | PyDAL (via flask_core) | PyDAL `executesql` provides raw SQL with parameter binding |
| Database | PostgreSQL | WaddleBot platform standard; supports JSONB and ON CONFLICT upserts |
| Credential reload | Redis pub/sub | Enables zero-downtime credential rotation |
| Logging | flask_core AAA logger | Structured logging with action/result fields for auditability |

---

## Database Schema Reference

### music_oauth_tokens

Stores per-community Spotify OAuth token pairs. The unique constraint on
`(community_id, platform)` ensures each community has at most one active token pair.

```sql
CREATE TABLE music_oauth_tokens (
    community_id  INTEGER NOT NULL,
    platform      VARCHAR NOT NULL,   -- always 'spotify' for this module
    access_token  TEXT NOT NULL,
    refresh_token TEXT,               -- NULL only if never returned by Spotify
    token_type    VARCHAR DEFAULT 'Bearer',
    expires_at    TIMESTAMP NOT NULL, -- UTC
    scope         TEXT,               -- space-separated granted scopes
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (community_id, platform)
);
```

The `_store_token` method uses:
```sql
INSERT INTO music_oauth_tokens (...) VALUES (...)
ON CONFLICT (community_id, platform)
DO UPDATE SET
    access_token  = EXCLUDED.access_token,
    refresh_token = COALESCE(EXCLUDED.refresh_token, music_oauth_tokens.refresh_token),
    token_type    = EXCLUDED.token_type,
    expires_at    = EXCLUDED.expires_at,
    scope         = EXCLUDED.scope,
    updated_at    = EXCLUDED.updated_at
```

### platform_integrations (read-only from this module)

```sql
-- Relevant columns read by Config.load_credentials_from_db()
SELECT client_id, client_secret, access_token
FROM platform_integrations
WHERE platform = 'spotify'
  AND integration_type = 'bot'
  AND is_active = TRUE
LIMIT 1;
```

---

## Internal Service URL

Within the Docker Compose / Kubernetes stack, the service is reachable at:

```
http://spotify-interaction:8026
```

The router module at `router-service:8000` proxies external `/spotify/*` requests
to this internal URL. Other modules (e.g., `unified_music_module` at port 8051)
call this service directly by its internal hostname.

---

## Security Model

1. **Client secret isolation**: `SPOTIFY_CLIENT_SECRET` is never returned in any
   API response. It is only used server-side to build the Basic auth header.

2. **Per-community token isolation**: Each community's tokens are stored separately.
   One community's token cannot be used to access another community's Spotify account.

3. **State parameter CSRF protection**: The OAuth `state` parameter prevents
   cross-site request forgery attacks during the callback phase.

4. **Non-root container**: The Dockerfile creates a `waddlebot` group and user,
   running the service without root privileges.

5. **Credential rotation support**: The Redis pub/sub channel allows credentials
   to be rotated without restarting containers or exposing secrets in environment
   variable changes visible in process listings.

6. **Thread-safe credential access**: `threading.Lock` (`_credential_lock`) protects
   the `_credentials_loaded` flag from race conditions across Hypercorn workers.
