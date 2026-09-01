# Spotify Interaction Module — Troubleshooting Guide

> Solutions for common OAuth failures, token lifecycle issues, scope errors,
> rate limiting, and operational problems with the Spotify Interaction Module.

---

## Quick Diagnostic Commands

Before diving into specific issues, run these to establish the current state:

```bash
# Is the service running?
curl http://localhost:8026/health

# Is the DB reachable and operational?
curl http://localhost:8026/healthz

# Are any tokens stored?
psql $DATABASE_URL -c "SELECT community_id, platform, expires_at, scope FROM music_oauth_tokens WHERE platform = 'spotify';"

# Is the access token expired?
psql $DATABASE_URL -c "SELECT community_id, expires_at, expires_at < NOW() AS expired FROM music_oauth_tokens WHERE platform = 'spotify';"

# Check service logs
docker logs spotify-interaction --tail 100
```

---

## OAuth Authorization Failures

### Problem: "Invalid redirect_uri"

**Symptom**: Spotify returns an error page with message:
```
INVALID_CLIENT: Invalid redirect URI
```

**Cause**: The `SPOTIFY_REDIRECT_URI` value does not exactly match one of the
Redirect URIs registered in the Spotify Developer Dashboard.

**Resolution**:
1. Go to https://developer.spotify.com/dashboard and open your app.
2. Click **Edit Settings** -> **Redirect URIs**.
3. Verify the registered URI exactly matches `SPOTIFY_REDIRECT_URI`.
4. Common mismatches:
   - `http://` vs `https://`
   - Trailing slash: `http://localhost:8026/callback` vs `http://localhost:8026/callback/`
   - Port number missing or wrong
   - Path differs: `/spotify/auth/callback` vs `/auth/callback`
5. Add the correct URI if missing, click **Save**, and retry the OAuth flow.

---

### Problem: "State parameter mismatch"

**Symptom**: The callback handler returns HTTP 400 with error `"Invalid state parameter"`.

**Cause**: The `state` value returned by Spotify does not match the stored CSRF token.
This can happen if:
- The user's browser session was lost between initiating OAuth and receiving the callback
- The `SECRET_KEY` changed between the login redirect and the callback
- The user clicked back and reused an old authorization URL
- A load balancer routed the callback to a different pod than the login request

**Resolution**:
1. Ensure `SECRET_KEY` is consistent across all pods and does not change at runtime.
2. If using multiple Hypercorn workers, use a shared session store (Redis-backed)
   rather than in-memory session storage.
3. Direct the user to restart the OAuth flow from `/api/v1/auth/login?community_id=N`.

---

### Problem: "invalid_grant" on Token Exchange

**Symptom**: Token exchange fails with:
```
Token exchange failed: 400 - {"error": "invalid_grant", "error_description": "Authorization code expired"}
```

**Cause**: The authorization code is single-use and expires after approximately
10 minutes. If the callback is not processed within that window, the code is invalid.

**Resolution**:
1. Ensure the callback is processed promptly (network latency should not cause this).
2. Check for clock skew between the module container and Spotify's servers:
   ```bash
   date -u  # should match real UTC time
   ```
3. If the module is catching exceptions and retrying the callback multiple times,
   stop retrying — authorization codes are single-use. Redirect to `/auth/login` again.

---

### Problem: "invalid_client" on Token Exchange

**Symptom**:
```
Token exchange failed: 400 - {"error": "invalid_client"}
```

**Cause**: The `SPOTIFY_CLIENT_ID` or `SPOTIFY_CLIENT_SECRET` is incorrect or the
app has been deleted/disabled in the Spotify Developer Dashboard.

**Resolution**:
1. Verify credentials in the Spotify Developer Dashboard.
2. Check that `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are set correctly:
   ```bash
   # Check what the module sees (if you can exec into the container)
   docker exec spotify-interaction env | grep SPOTIFY_CLIENT
   ```
3. If using DB credentials (`platform_integrations` table), verify:
   ```sql
   SELECT client_id, is_active, integration_type
   FROM platform_integrations
   WHERE platform = 'spotify' AND integration_type = 'bot';
   ```
4. If the secret changed, update the environment variable or DB record and restart
   (or trigger Redis credential reload).

---

### Problem: User Sees "This app is not authorized"

**Symptom**: Spotify shows an error page saying the app is not authorized or
is in development mode.

**Cause**: Spotify apps in development mode can only be used by up to 25 users
who are explicitly added to the app's user list.

**Resolution**:
1. In the Spotify Developer Dashboard, go to **Users and Access**.
2. Add the community admin's Spotify account email address.
3. Alternatively, apply for **Extended Quota** mode if your user base exceeds 25.
4. For production deployments, ensure the app is in Extended Quota mode.

---

## Token Expiry and Refresh Issues

### Problem: Access Token Expired, Not Auto-Refreshed

**Symptom**: API calls fail with HTTP 401 from Spotify. The `get_valid_token`
method did not trigger a refresh.

**Cause**: The `expires_at` column in `music_oauth_tokens` may be stored as UTC
but compared against local time, or the 5-minute buffer may not be sufficient.

**Diagnosis**:
```sql
-- Check token expiry vs current time
SELECT
  community_id,
  expires_at AT TIME ZONE 'UTC' AS expires_at_utc,
  NOW() AT TIME ZONE 'UTC' AS now_utc,
  expires_at - NOW() AS time_remaining
FROM music_oauth_tokens
WHERE platform = 'spotify';
```

**Resolution**:
1. Ensure PostgreSQL stores timestamps in UTC (the module uses `datetime.utcnow()`).
2. If the token is expired but not refreshing, trigger a manual refresh:
   ```bash
   curl -X POST http://localhost:8026/api/v1/auth/refresh \
     -H "Content-Type: application/json" \
     -d '{"community_id": 1}'
   ```
3. If refresh fails with `"invalid_grant"`, the refresh token itself has expired or
   been revoked. The community must re-authorize via `/api/v1/auth/login?community_id=1`.

---

### Problem: "No refresh token found" on Refresh

**Symptom**: `SpotifyOAuthService.refresh_token` logs:
```
No refresh token found
```

**Cause**: The `music_oauth_tokens` row exists but `refresh_token` is NULL or empty.

**Resolution**:
1. Check the DB:
   ```sql
   SELECT community_id, refresh_token IS NULL AS missing_refresh
   FROM music_oauth_tokens
   WHERE platform = 'spotify';
   ```
2. If `refresh_token` is NULL, the community must re-authorize. Spotify's refresh
   token does not expire unless:
   - The user revoked access in their Spotify account settings
   - The app was deleted in the Spotify Developer Dashboard
   - The community was disconnected (`revoke_token` was called)
   - A bug prevented storing the refresh token during initial authorization
3. Force re-authorization:
   ```
   http://localhost:8026/api/v1/auth/login?community_id=1
   ```

---

### Problem: Refresh Token Not Being Preserved

**Symptom**: After a successful refresh, subsequent refreshes fail because
`refresh_token` became NULL.

**Cause**: Spotify sometimes omits `refresh_token` from the refresh response.
The `_store_token` method handles this with `COALESCE`:
```sql
refresh_token = COALESCE(EXCLUDED.refresh_token, music_oauth_tokens.refresh_token)
```
But a bug in this logic or a schema issue could cause NULL overwrite.

**Resolution**:
1. Verify the upsert SQL in `_store_token` contains the `COALESCE` on `refresh_token`.
2. Check application logs for the token response content around refresh time.
3. The Python fallback is also present in `refresh_token()`:
   ```python
   if "refresh_token" not in token_data:
       token_data["refresh_token"] = refresh_token  # preserve existing
   ```
   Ensure this code path executes when the refresh response omits the refresh token.

---

## Scope Errors

### Problem: "Insufficient client scope" on Spotify API Calls

**Symptom**: Calls to Spotify's playback endpoints return:
```json
{"error": {"status": 403, "message": "Player command failed: Premium required"}}
```
or:
```json
{"error": {"status": 403, "message": "Insufficient client scope"}}
```

**Cause 1 — Premium required**: Spotify's Web Playback API and playback control
(play, pause, skip) require a Spotify Premium account. The community admin must
have Spotify Premium.

**Cause 2 — Missing scope**: The scope granted during authorization does not include
the required permission. This happens if:
- `SPOTIFY_SCOPES` env var was set to a reduced scope set during authorization
- The user was shown a cached authorization dialog that did not include new scopes
- The scope in `music_oauth_tokens.scope` column does not include the needed scope

**Resolution for scope issues**:
1. Check the stored scope:
   ```sql
   SELECT community_id, scope FROM music_oauth_tokens WHERE platform = 'spotify';
   ```
2. Compare against `SpotifyOAuthService.DEFAULT_SCOPES` (11 scopes).
3. If scopes are missing, the community must re-authorize with `show_dialog=true`
   (already set in `get_authorization_url`) to get a fresh consent screen.
4. Redirect to `/api/v1/auth/login?community_id=1` to restart the OAuth flow.

---

## Rate Limiting

### Problem: Spotify API Returns HTTP 429

**Symptom**: Module logs:
```
Token exchange failed: 429 - ...
```
or downstream Spotify API calls return HTTP 429.

**Cause**: Spotify's Web API enforces rate limits. The limits vary by endpoint:
- Token endpoint: Not typically rate-limited but can throttle on abuse
- Search: ~10 requests/second for most apps
- Playback: Varies by endpoint

**Resolution**:
1. Check the `Retry-After` header in the 429 response — it specifies how many
   seconds to wait.
2. Implement exponential backoff for retries.
3. Use the `CACHE_TTL` (default 300 seconds) to cache search results and avoid
   repeated identical queries.
4. If consistently hitting limits, apply for Extended Quota mode in the Spotify
   Developer Dashboard.

---

## Database Issues

### Problem: "Failed to store token: ..."

**Symptom**: After successful Spotify token exchange, `_store_token` logs an error.

**Common causes**:
1. `music_oauth_tokens` table does not exist — run database migrations.
2. `community_id` references a non-existent community — validate the community ID.
3. PostgreSQL connection lost — check `DATABASE_URL` and DB server status.
4. Unique constraint violation — unexpected schema state.

**Resolution**:
```bash
# Check if table exists
psql $DATABASE_URL -c "\d music_oauth_tokens"

# Check PostgreSQL connectivity
psql $DATABASE_URL -c "SELECT 1"

# Check for constraint violations
psql $DATABASE_URL -c "
  SELECT conname, contype, pg_get_constraintdef(oid)
  FROM pg_constraint
  WHERE conrelid = 'music_oauth_tokens'::regclass;
"
```

---

## Container and Configuration Issues

### Problem: Service Fails to Start

**Symptom**: Container exits immediately. Check logs:
```bash
docker logs spotify-interaction
```

**Common causes and fixes**:

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: flask_core` | Shared library not installed | Rebuild image from repo root |
| `ConnectionRefusedError` on DB | DATABASE_URL wrong or DB not ready | Check DB_URL, use depends_on |
| `OSError: [Errno 98] Address in use` | Port 8026 already bound | Stop conflicting process or change MODULE_PORT |
| `SECRET_KEY=change-me-in-production` warning | Default secret in production | Set SECRET_KEY env var |

### Problem: Redis Credential Listener Not Starting

**Symptom**: Credential updates are not being picked up without container restart.

**Diagnosis**:
```bash
# Check REDIS_URL is set
docker exec spotify-interaction env | grep REDIS_URL

# Verify Redis is reachable
redis-cli -u $REDIS_URL ping
```

**Resolution**: Ensure `REDIS_URL` is set in the container environment. If empty,
`Config.start_credential_listener` returns `None` and the listener thread does not
start. The service falls back to using the credentials loaded at startup.

---

## Log Reference

| Log Message | Level | Meaning |
|---|---|---|
| `Starting spotify_interaction_module` | INFO | Startup initiated |
| `spotify_interaction_module started` | INFO | DB initialized, ready to serve |
| `Spotify token obtained for community N` | INFO | Successful initial authorization |
| `Spotify token refreshed for community N` | INFO | Successful token refresh |
| `Token expired for community N, refreshing...` | INFO | Auto-refresh triggered |
| `Token stored for community N` | INFO | `_store_token` upsert succeeded |
| `Token revoked for community N` | INFO | `revoke_token` DELETE succeeded |
| `Spotify credentials loaded from platform_integrations` | INFO | DB credentials used |
| `Failed to load credentials from DB, using env vars: ...` | WARNING | Env var fallback |
| `Listening for credential refresh on: credentials:spotify:bot:refreshed` | INFO | Redis listener active |
| `Credential refresh notification received` | INFO | Live reload triggered |
| `Failed to exchange code for token: ...` | ERROR | Token exchange failed |
| `Failed to refresh token: ...` | ERROR | Token refresh failed |
| `Failed to get valid token: ...` | ERROR | get_valid_token exception |
| `Failed to store token: ...` | ERROR | DB upsert failed |
| `Failed to revoke token: ...` | ERROR | DB delete failed |
| `Credential listener error: ...` | ERROR | Redis listener crashed |
