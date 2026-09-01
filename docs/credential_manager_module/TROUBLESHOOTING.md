# Credential Manager Module — Troubleshooting Guide

This document covers the most common failure modes encountered with the Credential Manager Module, their root causes, diagnostic steps, and resolutions.

---

## Table of Contents

1. [Quick Diagnostic Checklist](#quick-diagnostic-checklist)
2. [Module Fails to Start](#module-fails-to-start)
3. [Health Endpoint Returns 503 / Degraded](#health-endpoint-returns-503--degraded)
4. [No Tokens Being Refreshed](#no-tokens-being-refreshed)
5. [Token Refresh Failures — Platform API Errors](#token-refresh-failures--platform-api-errors)
6. [Decryption / Encryption Errors](#decryption--encryption-errors)
7. [Missing Credentials — Action Modules Report Stale Tokens](#missing-credentials--action-modules-report-stale-tokens)
8. [Rotation Errors — All Retries Exhausted](#rotation-errors--all-retries-exhausted)
9. [Permission Denied — Database Access Errors](#permission-denied--database-access-errors)
10. [Redis Connection Failures](#redis-connection-failures)
11. [High Error Count in Health Response](#high-error-count-in-health-response)
12. [Credential Listener Not Receiving Events](#credential-listener-not-receiving-events)
13. [Expired Tokens Not Cleared After Refresh](#expired-tokens-not-cleared-after-refresh)
14. [Debug Mode Procedure](#debug-mode-procedure)
15. [Log Level and Log Format Reference](#log-level-and-log-format-reference)
16. [Escalation Checklist](#escalation-checklist)

---

## Quick Diagnostic Checklist

Before investigating a specific issue, run through these steps:

1. Check the health endpoint:
   ```bash
   curl -s http://localhost:8095/health | python3 -m json.tool
   ```

2. Check the credential status endpoint:
   ```bash
   curl -s http://localhost:8095/api/v1/credentials/status | python3 -m json.tool
   ```

3. Check container logs:
   ```bash
   docker logs credential-manager --tail=100
   # or in Kubernetes:
   kubectl logs -n waddlebot deployment/credential-manager --tail=100
   ```

4. Verify environment variables are set (do NOT log or expose actual values):
   ```bash
   docker exec credential-manager env | grep -E "^(DATABASE_URL|REDIS_URL|MODULE_PORT|LOG_LEVEL)=" | sed 's/=.*/=<set>/'
   ```

5. Check database connectivity from within the container:
   ```bash
   docker exec credential-manager python3 -c "
   import asyncio, asyncpg, os
   async def check():
       url = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
       pool = await asyncpg.create_pool(url, min_size=1, max_size=1)
       print('DB connection: OK')
       await pool.close()
   asyncio.run(check())
   "
   ```

---

## Module Fails to Start

### Symptom

Container exits immediately. Logs show:

```
ERROR: Configuration errors: ['DATABASE_URL is required', 'REDIS_URL is required']
```

### Cause

`Config.validate()` detected missing required environment variables. The application exits with code 1.

### Resolution

Ensure `DATABASE_URL` and `REDIS_URL` are set in the container environment. Verify that Docker Compose or Kubernetes Secret injection is working:

```bash
# Docker
docker run --rm -e DATABASE_URL="..." -e REDIS_URL="..." waddlebot/credential-manager:latest

# Kubernetes — check the pod's effective environment
kubectl exec -n waddlebot <pod-name> -- env | grep DATABASE_URL
```

If using `envFrom: secretRef`, verify the Secret exists and contains the correct keys:

```bash
kubectl get secret credential-manager-secrets -n waddlebot -o jsonpath='{.data}' | python3 -m json.tool
```

---

### Symptom

Container exits with a Python `ValueError` immediately on startup:

```
ValueError: invalid literal for int() with base 10: 'five_minutes'
```

### Cause

An integer environment variable (`TOKEN_REFRESH_BUFFER`, `POLL_INTERVAL`, etc.) was set to a non-numeric string.

### Resolution

Check all numeric environment variables. They must be plain integers with no units or other characters:

```bash
# Correct
TOKEN_REFRESH_BUFFER=300

# Incorrect — will crash
TOKEN_REFRESH_BUFFER=5m
TOKEN_REFRESH_BUFFER=five_minutes
```

---

## Health Endpoint Returns 503 / Degraded

### Symptom

```json
{
  "status": "degraded",
  "running": false,
  "last_cycle": null,
  "total_refreshed": 0,
  "total_errors": 1
}
```

### Cause A: Database connection failed during startup

The `RefreshService.start()` method failed to create the `asyncpg` connection pool. This usually means the database is unreachable or the connection string is malformed.

**Diagnosis**:

```
ERROR: ... asyncpg ... connection refused
ERROR: ... asyncpg ... password authentication failed
```

**Resolution**: Verify the `DATABASE_URL` is correct, the database host is reachable from the container, and the database user password is correct. See [Permission Denied](#permission-denied--database-access-errors) below.

### Cause B: Redis connection failed during startup

`RefreshService.start()` failed to connect to Redis via `aioredis.from_url()`.

**Diagnosis**: Check logs for `redis.exceptions.ConnectionError` or similar.

**Resolution**: Verify `REDIS_URL` is correct and Redis is reachable. See [Redis Connection Failures](#redis-connection-failures) below.

### Cause C: Background task crashed after startup

The `_poll_loop` asyncio task raised an unhandled exception and exited.

**Diagnosis**: Look for `ERROR in refresh cycle` followed by a traceback in the logs.

**Resolution**: Identify the exception from the traceback. Common causes include database connection drops (transient — the module should recover on the next poll cycle) or asyncpg pool exhaustion.

---

## No Tokens Being Refreshed

### Symptom

Health is `healthy`, `running: true`, but `total_refreshed` stays at 0. Force-refresh returns `"Refreshed 0 credentials"`.

### Cause A: No integrations in database

The `platform_integrations` table has no rows where `is_active = TRUE` AND `refresh_token IS NOT NULL` AND `expires_at IS NOT NULL` AND `expires_at < NOW() + TOKEN_REFRESH_BUFFER`.

**Diagnosis**:

```bash
# Connect to the database and check
psql "$DATABASE_URL" -c "
SELECT platform, integration_type, COUNT(*),
       MIN(expires_at) as soonest_expiry
FROM platform_integrations
WHERE is_active = TRUE
  AND refresh_token IS NOT NULL
  AND expires_at IS NOT NULL
GROUP BY platform, integration_type;
"
```

**Resolution**: If the table is empty, the Admin Hub or community onboarding flow has not yet stored any OAuth integrations. This is not a Credential Manager problem — it is a data population issue.

### Cause B: All tokens have `expires_at` far in the future

Tokens with long expiry windows (e.g., 30-day Discord bot tokens) will not be picked up until their expiry is within `TOKEN_REFRESH_BUFFER` seconds.

**Resolution**: This is normal behavior. The credential status endpoint shows `expiring_soon: 0` when all tokens are comfortably valid.

### Cause C: `TOKEN_REFRESH_BUFFER` is too small

If `TOKEN_REFRESH_BUFFER` is set to a very small value (e.g., `30`), tokens will only be refreshed when they are within 30 seconds of expiry. This is risky and may cause gaps.

**Resolution**: Increase `TOKEN_REFRESH_BUFFER` to a safer value (default: `300`).

---

## Token Refresh Failures — Platform API Errors

### Symptom

Logs show repeated errors like:

```
WARNING: Refresh attempt 1/3 failed for twitch id=42, retrying in 5s
ERROR: All refresh attempts failed for twitch id=42
```

### Cause A: Invalid or revoked refresh token

The stored `refresh_token` is no longer valid. This happens when:
- The user revoked access in the platform's developer console.
- The platform rotated the refresh token and the database was not updated.
- The token exceeded the platform's maximum refresh token lifetime.

**Resolution**: The user or admin must re-authorize the integration through the Admin Hub OAuth flow. There is no automatic recovery from a revoked refresh token — a new grant is required.

### Cause B: Invalid `client_id` or `client_secret`

The OAuth application credentials stored in `platform_integrations.client_id` or `client_secret` are incorrect or have been rotated at the platform.

**Diagnosis**: Check the platform's developer console to verify the application credentials. Look for `invalid_client` in platform error responses.

**Resolution**: Update `client_id` and `client_secret` in `platform_integrations` for the affected rows. The Credential Manager will use the new values on the next cycle.

### Cause C: Platform API outage

The platform token endpoint is temporarily unavailable.

**Resolution**: Wait for the platform to recover. The module will retry on the next poll cycle. Use the credential status endpoint to monitor how many tokens are expiring.

### Cause D: Network connectivity from container to platform

The container cannot reach external OAuth endpoints (e.g., `id.twitch.tv`, `discord.com`).

**Diagnosis**:

```bash
docker exec credential-manager python3 -c "
import httpx, asyncio
async def check():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get('https://id.twitch.tv')
        print('Twitch reachable:', r.status_code)
asyncio.run(check())
"
```

**Resolution**: Check firewall rules, egress network policies, and proxy configuration.

---

## Decryption / Encryption Errors

### Symptom

Logs show errors when reading or writing token values, with mentions of `cryptography`, `Fernet`, `InvalidToken`, or base64 decode errors.

### Cause A: `PLATFORM_ENCRYPTION_KEY` mismatch

The key used to encrypt the stored tokens does not match the current `PLATFORM_ENCRYPTION_KEY`. This happens when:
- The key was rotated without re-encrypting existing tokens.
- Different services are using different values of `PLATFORM_ENCRYPTION_KEY`.
- The key value was corrupted or truncated.

**Resolution**: Verify that the `PLATFORM_ENCRYPTION_KEY` value is identical across all services that read from or write to `platform_integrations`. Do not log or expose the actual key value — compare by checking whether the service can successfully decrypt a known test value.

### Cause B: `PLATFORM_ENCRYPTION_KEY` is empty in production

If `PLATFORM_ENCRYPTION_KEY` is not set (`""`), tokens stored with encryption cannot be decrypted.

**Resolution**: Ensure the key is set in all production deployments. Verify via:

```bash
kubectl exec -n waddlebot <pod-name> -- \
  python3 -c "from core.credential_manager_module.config import Config; print('Key set:', bool(Config.ENCRYPTION_KEY))"
```

### Cause C: Key format is incorrect

`PLATFORM_ENCRYPTION_KEY` must be a URL-safe Base64-encoded 32-byte value (Fernet key format). If the key is in a different encoding, Fernet will reject it.

**Resolution**: Generate a new key using:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store this value in your secrets manager and update all deployments.

---

## Missing Credentials — Action Modules Report Stale Tokens

### Symptom

An action module (e.g., Twitch push module) receives a 401 Unauthorized from the platform API, even though the Credential Manager reports `running: true`.

### Cause A: Redis pub/sub event not received

The action module's credential listener did not receive the refresh notification, so it continues using the old in-memory token.

**Diagnosis**: Check that the action module subscribed to the correct Redis channel. Check for Redis connection errors in the action module's logs.

**Resolution**: Ensure the action module's credential listener is running and subscribed to:
```
credentials:<platform>:<integration_type>[:<community_id>]:refreshed
```

Restart the action module to force a cold reload of credentials from the database.

### Cause B: Action module is not reading from the database

The action module is using an environment variable or a cached value that was set at startup and never updated. Verify the module implements a credential reload path when notified.

### Cause C: Token was refreshed but database update failed

The platform returned new tokens but the `UPDATE platform_integrations` query failed (e.g., database write error). The Redis event was not published (publishing happens after the DB update succeeds).

**Diagnosis**: Check Credential Manager logs for errors during `_update_tokens()`. Look for `asyncpg` errors in the logs.

**Resolution**: Fix the database connectivity or permission issue, then trigger a force refresh.

---

## Rotation Errors — All Retries Exhausted

### Symptom

```
ERROR: All refresh attempts failed for <platform> id=<n>
```

`total_errors` in the health response is non-zero and increasing.

### Cause

All `MAX_REFRESH_RETRIES` attempts for a specific token refresh failed. This can be due to:
- Platform API returning persistent errors (5xx, invalid_grant, invalid_client)
- Network timeouts on all attempts
- Token permanently revoked

### Resolution

1. Identify the failing integration by platform and ID from the log message.
2. Query the database to inspect the token's state:
   ```sql
   SELECT id, platform, integration_type, expires_at, updated_at
   FROM platform_integrations
   WHERE id = <id>;
   ```
3. Attempt a manual force-refresh to see if the issue is transient:
   ```bash
   curl -X POST http://localhost:8095/api/v1/credentials/refresh-now
   ```
4. If the token is permanently invalid (revoked, expired grant), the affected integration must be re-authorized through the Admin Hub.
5. Consider temporarily disabling the integration (`is_active = FALSE`) to prevent repeated failure noise while re-authorization is arranged.

---

## Permission Denied — Database Access Errors

### Symptom

```
ERROR: asyncpg.exceptions.InsufficientPrivilegeError: permission denied for table platform_integrations
```

### Cause

The database user configured in `DATABASE_URL` does not have the required permissions on `platform_integrations`.

### Resolution

Grant the required permissions to the module's database user. The user needs `SELECT` and `UPDATE` on the table:

```sql
GRANT SELECT, UPDATE ON platform_integrations TO mod_credential_manager;
```

The user does not need `INSERT`, `DELETE`, or schema-level permissions.

---

## Redis Connection Failures

### Symptom

```
ERROR: redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

Or the health endpoint returns `degraded` with Redis-related errors in logs.

### Diagnosis

```bash
# Test Redis connectivity from within the container
docker exec credential-manager python3 -c "
import redis, os
r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
print('Redis ping:', r.ping())
"
```

### Common Causes and Resolutions

| Symptom | Cause | Resolution |
|---|---|---|
| `Connection refused` | Redis not running or wrong host/port | Verify Redis is running and `REDIS_URL` host:port is correct |
| `NOAUTH Authentication required` | Redis requires a password but `REDIS_URL` has none | Add password to `REDIS_URL`: `redis://:<password>@host:port/0` |
| `WRONGPASS invalid username-password pair` | Incorrect Redis password | Verify Redis password in `REDIS_URL` |
| SSL handshake error | Using `redis://` with TLS Redis | Switch to `rediss://` scheme |

---

## High Error Count in Health Response

### Symptom

```json
{
  "status": "healthy",
  "running": true,
  "total_refreshed": 5,
  "total_errors": 47
}
```

`total_errors` is much higher than `total_refreshed`.

### Cause

Either many individual token refreshes are failing, or the poll loop itself is throwing unhandled exceptions.

### Diagnosis

1. Set `LOG_LEVEL=DEBUG` and restart the container.
2. Observe logs during the next poll cycle. Look for `ERROR` lines identifying which platforms and integration IDs are failing.
3. Check the credential status endpoint for non-zero `expired` counts.

### Resolution

Address the root cause for the specific failing integrations (see Token Refresh Failures section above). A high `total_errors` count without corresponding action does not automatically resolve — errors accumulate since process start and do not decay.

---

## Credential Listener Not Receiving Events

### Symptom

The `Config.start_credential_listener()` daemon thread is started but the module that subscribed does not appear to react to credential changes published by the Credential Manager.

### Diagnosis

1. Verify the Redis channel name matches. The Credential Manager publishes to:
   ```
   credentials:credential_manager:bot:refreshed
   ```
   (for its own credential reloads). For other platforms, the channel varies by platform and community_id.

2. Check the listener thread is alive:
   ```python
   import threading
   threads = [t for t in threading.enumerate() if t.name == "credential-listener"]
   print("Listener threads:", len(threads))
   ```

3. Test manually by publishing to the Redis channel:
   ```bash
   redis-cli publish "credentials:credential_manager:bot:refreshed" "2026-02-16T00:00:00+00:00"
   ```

### Resolution

If the thread is not running, call `Config.start_credential_listener(redis_client)` again. If Redis connectivity is the issue, see the Redis Connection Failures section.

---

## Expired Tokens Not Cleared After Refresh

### Symptom

The credential status endpoint continues to show `expired > 0` even after `total_refreshed` increments.

### Cause

The `expired` count in the status endpoint is a live query: `COUNT(*) WHERE expires_at < NOW()`. If the Credential Manager refreshed a token but the `expires_at` column was not updated (e.g., the platform returned no `expires_in` value), the row will still appear as expired.

### Diagnosis

```sql
SELECT id, platform, access_token IS NOT NULL as has_token, expires_at, updated_at
FROM platform_integrations
WHERE expires_at < NOW() AND is_active = TRUE;
```

Check whether `updated_at` was recently set (indicating a refresh occurred) while `expires_at` remains in the past.

### Resolution

If the platform does not return `expires_in` in the token response, the Credential Manager sets `expires_at = NULL` for that refresh. The next cycle will not pick up that token again (the query requires `expires_at IS NOT NULL`). Manually set an appropriate `expires_at` value in the database, or update the platform handler to use a known default expiry for that platform.

---

## Debug Mode Procedure

To enable verbose logging for active diagnosis:

1. Set `LOG_LEVEL=DEBUG` in the container environment.
2. Restart the container.
3. Trigger a force refresh:
   ```bash
   curl -X POST http://localhost:8095/api/v1/credentials/refresh-now
   ```
4. Collect logs:
   ```bash
   docker logs credential-manager --since=5m
   ```
5. Look for:
   - `DEBUG: Published refresh event on channel: credentials:<platform>:...` — confirms Redis publish succeeded
   - `INFO: Tokens updated for <platform> integration id=<n>` — confirms DB write succeeded
   - `WARNING` or `ERROR` lines — identify failing integrations

6. After diagnosis, restore `LOG_LEVEL=INFO` to avoid excessive log volume.

---

## Log Level and Log Format Reference

All log messages follow this format:

```
YYYY-MM-DD HH:MM:SS,mmm [<logger_name>] LEVEL: <message>
```

Example:

```
2026-02-16 12:00:00,000 [credential_manager_module.services.refresh_service] INFO: Tokens updated for twitch integration id=42 (expires=2026-02-16T16:00:00+00:00)
```

Logger names used by the module:

| Logger Name | Source |
|---|---|
| `credential_manager_module.app` | `app.py` — startup, shutdown, endpoint errors |
| `credential_manager_module.config` | `config.py` — config loading, credential listener |
| `credential_manager_module.services.refresh_service` | `refresh_service.py` — refresh cycles, DB updates, Redis events |
| `credential_manager_module.services.oauth_handlers` | `oauth_handlers.py` — per-platform HTTP call errors |

---

## Escalation Checklist

Before escalating to a senior engineer, confirm you have:

- [ ] Checked the health endpoint and noted `status`, `running`, `last_cycle`, `total_refreshed`, `total_errors`
- [ ] Checked the credential status endpoint and noted any non-zero `expired` counts
- [ ] Reviewed the last 200 lines of container logs
- [ ] Verified `DATABASE_URL` and `REDIS_URL` are set and correct (without exposing actual values)
- [ ] Tested database connectivity from within the container
- [ ] Tested Redis connectivity from within the container
- [ ] Identified which specific platform and integration ID is failing (from log lines)
- [ ] Checked whether the affected integration's `refresh_token` is still valid at the platform level
- [ ] Attempted a force refresh and noted the result
- [ ] Captured the full error traceback from the logs

**Support**: support@penguintech.io | https://status.penguintech.io
