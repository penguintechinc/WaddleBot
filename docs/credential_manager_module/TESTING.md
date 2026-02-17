# Credential Manager Module — Testing Guide

This document describes how to run the test suite for the Credential Manager Module, what the existing tests cover, how to mock OAuth endpoints and encryption, and how to write new tests.

---

## Table of Contents

1. [Test Structure](#test-structure)
2. [Test Dependencies](#test-dependencies)
3. [Environment Setup for Testing](#environment-setup-for-testing)
4. [Running the Tests](#running-the-tests)
5. [Test Classes Overview](#test-classes-overview)
6. [Test Fixtures](#test-fixtures)
7. [Mocking OAuth Endpoints](#mocking-oauth-endpoints)
8. [Mocking the Database](#mocking-the-database)
9. [Mocking Redis](#mocking-redis)
10. [Integration Test Patterns](#integration-test-patterns)
11. [Testing Credential Rotation](#testing-credential-rotation)
12. [Testing Error Scenarios](#testing-error-scenarios)
13. [Coverage Targets](#coverage-targets)
14. [CI/CD Test Execution](#cicd-test-execution)

---

## Test Structure

```
core/credential_manager_module/
└── test_credential_manager.py     # Main test file
```

The test file contains five test classes covering OAuth handler instantiation, configuration loading and validation, error handling, data structure expectations, and integration consistency checks.

---

## Test Dependencies

Install test dependencies alongside the module requirements:

```bash
pip install -r core/credential_manager_module/requirements.txt
pip install pytest pytest-asyncio pytest-mock respx
```

**Additional test libraries** (not in `requirements.txt` by default — add to a `requirements-test.txt`):

| Package | Purpose |
|---|---|
| `pytest` | Test runner and assertion framework |
| `pytest-asyncio` | async test support for `@pytest.mark.asyncio` |
| `pytest-mock` | Mocker fixture for patching |
| `respx` | Mock httpx requests (used to simulate OAuth token endpoints) |
| `fakeredis` | In-memory Redis implementation for testing without a real Redis instance |

---

## Environment Setup for Testing

Tests do not require a live database or Redis. Most tests exercise class instantiation and configuration logic. Tests that exercise the `RefreshService` require mocking.

Set minimal environment variables before running tests:

```bash
export DATABASE_URL="postgresql://test_user:test_password@localhost:5432/test_db"
export REDIS_URL="redis://localhost:6379/15"
export PLATFORM_ENCRYPTION_KEY="test-placeholder-key-not-for-production-use"
export LOG_LEVEL="WARNING"
```

Or use a test-specific `.env.test` file:

```dotenv
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/test_db
REDIS_URL=redis://localhost:6379/15
PLATFORM_ENCRYPTION_KEY=test-placeholder-key-not-for-production-use
LOG_LEVEL=WARNING
```

---

## Running the Tests

### Run all tests

```bash
cd /home/penguin/code/waddlebot
python -m pytest core/credential_manager_module/test_credential_manager.py -v
```

### Run a specific test class

```bash
python -m pytest core/credential_manager_module/test_credential_manager.py::TestOAuthHandlers -v
```

### Run a specific test

```bash
python -m pytest core/credential_manager_module/test_credential_manager.py::TestOAuthHandlers::test_get_handler_twitch -v
```

### Run with coverage report

```bash
python -m pytest core/credential_manager_module/test_credential_manager.py \
  --cov=core.credential_manager_module \
  --cov-report=term-missing \
  -v
```

### Run async tests only

```bash
python -m pytest core/credential_manager_module/test_credential_manager.py \
  -m asyncio -v
```

### Run directly (no pytest)

```bash
python core/credential_manager_module/test_credential_manager.py
```

---

## Test Classes Overview

### `TestOAuthHandlers`

Tests that all OAuth handler classes are correctly registered and instantiated via the `get_handler()` factory.

| Test | What it verifies |
|---|---|
| `test_get_handler_twitch` | Factory returns `TwitchOAuthHandler` with correct `TOKEN_URL` |
| `test_get_handler_discord` | Factory returns `DiscordOAuthHandler` with correct `TOKEN_URL` |
| `test_get_handler_slack` | Factory returns `SlackOAuthHandler` with correct `TOKEN_URL` |
| `test_get_handler_youtube` | Factory returns `YouTubeOAuthHandler` with correct `TOKEN_URL` |
| `test_get_handler_spotify` | Factory returns `SpotifyOAuthHandler` with correct `TOKEN_URL` |
| `test_get_handler_kick` | Factory returns `KickOAuthHandler` with correct `TOKEN_URL` |
| `test_get_handler_invalid` | `ValueError` raised for unknown platform name |
| `test_get_handler_case_sensitive` | Platform names must be lowercase (`Twitch` raises `ValueError`) |
| `test_handler_timeout_constant` | All handlers have `TIMEOUT == 10` |

### `TestConfiguration`

Tests configuration loading from defaults and validation logic.

| Test | What it verifies |
|---|---|
| `test_config_defaults` | `MODULE_NAME`, `MODULE_VERSION`, positive values for timing settings |
| `test_config_validate_with_urls` | `validate()` returns a list (may be empty or with errors) |
| `test_config_url_conversion` | `DATABASE_URL` contains a valid PostgreSQL URL scheme |
| `test_config_logging_level` | `LOG_LEVEL` is one of the valid Python logging level names |
| `test_config_retry_settings` | Retry count is positive; max backoff is under 5 minutes |

### `TestErrorHandling`

Tests the error class hierarchy and handler attributes.

| Test | What it verifies |
|---|---|
| `test_oauth_refresh_error_inheritance` | `OAuthRefreshError` is an `Exception` subclass with correct `str()` |
| `test_handler_timeout_attribute` | All handlers have `TIMEOUT` as a positive integer |

### `TestDataStructures`

Tests that expected constants and attributes are present.

| Test | What it verifies |
|---|---|
| `test_handler_token_urls_dict` | All six platforms map to the expected token endpoint URLs |
| `test_config_env_prefix` | `Config` has all required attributes (`DATABASE_URL`, `REDIS_URL`, etc.) |

### `TestIntegration`

Tests internal consistency of configuration.

| Test | What it verifies |
|---|---|
| `test_config_consistency` | `TOKEN_REFRESH_BUFFER` and `POLL_INTERVAL` are valid positive values |
| `test_module_version_format` | Version string is three dot-separated digits |
| `test_handler_factory_consistency` | `get_handler()` returns same type but different instances on repeated calls |

---

## Test Fixtures

### Dummy integration record fixture

Use dummy credential values in test fixtures. Never use real tokens or secrets in test code.

```python
import pytest
from datetime import datetime, timedelta, timezone

@pytest.fixture
def dummy_twitch_integration():
    """Dummy Twitch integration record for testing."""
    return {
        "id": 1001,
        "platform": "twitch",
        "integration_type": "bot",
        "community_id": 42,
        "user_id": None,
        "access_token": "dummy-access-token-twitch-xxxxxxxx",
        "refresh_token": "dummy-refresh-token-twitch-yyyyyyyy",
        "client_id": "dummy-client-id-twitch-zzzzzzzz",
        "client_secret": "dummy-client-secret-twitch-aaaaaa",
        "token_type": "Bearer",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=3),
        "scopes": ["chat:read", "chat:edit"],
        "config_data": None,
    }

@pytest.fixture
def dummy_discord_integration():
    """Dummy Discord integration record for testing."""
    return {
        "id": 1002,
        "platform": "discord",
        "integration_type": "bot",
        "community_id": None,
        "user_id": None,
        "access_token": "dummy-access-token-discord-xxxxxxxx",
        "refresh_token": "dummy-refresh-token-discord-yyyyyyyy",
        "client_id": "dummy-client-id-discord-zzzzzzzz",
        "client_secret": "dummy-client-secret-discord-aaaaaa",
        "token_type": "Bearer",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=2),
        "scopes": ["bot", "identify"],
        "config_data": None,
    }

@pytest.fixture
def dummy_spotify_integration():
    """Dummy Spotify integration record (uses Basic auth)."""
    return {
        "id": 1003,
        "platform": "spotify",
        "integration_type": "bot",
        "community_id": 7,
        "user_id": None,
        "access_token": "dummy-access-token-spotify-xxxxxxxx",
        "refresh_token": "dummy-refresh-token-spotify-yyyyyyyy",
        "client_id": "dummy-client-id-spotify-zzzzzzzz",
        "client_secret": "dummy-client-secret-spotify-aaaaaa",
        "token_type": "Bearer",
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=120),
        "scopes": ["user-read-playback-state"],
        "config_data": None,
    }
```

### Dummy token response fixture

```python
@pytest.fixture
def dummy_token_response_twitch():
    """Dummy Twitch token endpoint response — structure only, no real values."""
    return {
        "access_token": "dummy-new-access-token-twitch",
        "refresh_token": "dummy-new-refresh-token-twitch",
        "expires_in": 14400,
        "token_type": "bearer",
        "scope": ["chat:read", "chat:edit"],
    }

@pytest.fixture
def dummy_token_response_slack():
    """Dummy Slack token response — includes the 'ok' field."""
    return {
        "ok": True,
        "access_token": "dummy-new-access-token-slack",
        "refresh_token": "dummy-new-refresh-token-slack",
        "expires_in": 43200,
        "scope": "chat:write,channels:read",
    }

@pytest.fixture
def dummy_token_response_youtube():
    """Dummy YouTube/Google token response — no new refresh_token."""
    return {
        "access_token": "dummy-new-access-token-youtube",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "https://www.googleapis.com/auth/youtube",
    }
```

---

## Mocking OAuth Endpoints

Use `respx` to intercept `httpx` requests in tests that exercise `BaseOAuthHandler._post_form()` or handler `refresh_token()` methods.

```python
import pytest
import respx
import httpx
from core.credential_manager_module.services.oauth_handlers import TwitchOAuthHandler

@pytest.mark.asyncio
async def test_twitch_handler_refresh_success():
    handler = TwitchOAuthHandler()

    mock_response = {
        "access_token": "dummy-new-access-token",
        "refresh_token": "dummy-new-refresh-token",
        "expires_in": 14400,
        "token_type": "bearer",
        "scope": ["chat:read"],
    }

    with respx.mock:
        respx.post("https://id.twitch.tv/oauth2/token").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await handler.refresh_token(
            refresh_token="dummy-refresh-token",
            client_id="dummy-client-id",
            client_secret="dummy-client-secret",
        )

    assert result["access_token"] == "dummy-new-access-token"
    assert result["refresh_token"] == "dummy-new-refresh-token"
    assert result["expires_in"] == 14400

@pytest.mark.asyncio
async def test_twitch_handler_refresh_failure():
    from core.credential_manager_module.services.oauth_handlers import OAuthRefreshError
    handler = TwitchOAuthHandler()

    with respx.mock:
        respx.post("https://id.twitch.tv/oauth2/token").mock(
            return_value=httpx.Response(401, json={"status": 401, "message": "invalid token"})
        )

        with pytest.raises(OAuthRefreshError):
            await handler.refresh_token(
                refresh_token="dummy-expired-refresh-token",
                client_id="dummy-client-id",
                client_secret="dummy-client-secret",
            )

@pytest.mark.asyncio
async def test_slack_handler_ok_false_raises():
    from core.credential_manager_module.services.oauth_handlers import (
        SlackOAuthHandler, OAuthRefreshError
    )
    handler = SlackOAuthHandler()

    with respx.mock:
        respx.post("https://slack.com/api/oauth.v2.access").mock(
            return_value=httpx.Response(200, json={"ok": False, "error": "token_revoked"})
        )

        with pytest.raises(OAuthRefreshError):
            await handler.refresh_token(
                refresh_token="dummy-refresh-token",
                client_id="dummy-client-id",
                client_secret="dummy-client-secret",
            )
```

---

## Mocking the Database

For `RefreshService` tests, mock `asyncpg` to avoid needing a real database:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.credential_manager_module.services.refresh_service import RefreshService

@pytest.fixture
def mock_refresh_service():
    """RefreshService with mocked DB, Redis, and HTTP."""
    service = RefreshService(
        database_url="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
    )
    service._pool = AsyncMock()
    service._redis = AsyncMock()
    service._http = AsyncMock()
    service._running = True
    return service

@pytest.mark.asyncio
async def test_run_refresh_cycle_no_expiring(mock_refresh_service, dummy_twitch_integration):
    """Test that run_refresh_cycle returns 0 when no tokens need refresh."""
    # Simulate DB returning empty result
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    mock_refresh_service._pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_refresh_service._pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    count = await mock_refresh_service.run_refresh_cycle()
    assert count == 0
```

---

## Mocking Redis

Use `fakeredis` for tests that exercise Redis pub/sub:

```python
import fakeredis.aioredis as fakeredis

@pytest.fixture
async def fake_redis():
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()

@pytest.mark.asyncio
async def test_publish_refresh_event(mock_refresh_service, fake_redis, dummy_twitch_integration):
    """Test that publish_refresh_event sends to the correct Redis channel."""
    mock_refresh_service._redis = fake_redis
    mock_refresh_service._redis_prefix = "credentials:"

    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("credentials:twitch:bot:42:refreshed")

    new_tokens = {"access_token": "dummy-new-token", "refresh_token": "dummy-new-refresh"}
    await mock_refresh_service._publish_refresh_event(dummy_twitch_integration, new_tokens)

    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
    assert message is not None
    assert message["channel"] == "credentials:twitch:bot:42:refreshed"
```

---

## Integration Test Patterns

### Test full cycle with mocked platform

```python
@pytest.mark.asyncio
async def test_full_refresh_cycle(mock_refresh_service, dummy_twitch_integration):
    """Test that a full refresh cycle updates the DB and publishes to Redis."""
    import respx
    import httpx

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [dummy_twitch_integration]
    mock_conn.execute = AsyncMock()
    mock_refresh_service._pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_refresh_service._pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_refresh_service._redis.publish = AsyncMock()

    with respx.mock:
        respx.post("https://id.twitch.tv/oauth2/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "dummy-refreshed-token",
                "refresh_token": "dummy-refreshed-refresh",
                "expires_in": 14400,
                "token_type": "bearer",
                "scope": ["chat:read"],
            })
        )
        count = await mock_refresh_service.run_refresh_cycle()

    assert count == 1
    mock_conn.execute.assert_called_once()
    mock_refresh_service._redis.publish.assert_called_once()
```

---

## Testing Credential Rotation

Test that after a successful refresh, the database update contains the new token values (not the old ones). Use fixture-based assertions — do not include real tokens.

```python
@pytest.mark.asyncio
async def test_update_tokens_writes_correct_columns(mock_refresh_service):
    """Test that _update_tokens writes all expected columns."""
    mock_conn = AsyncMock()
    mock_refresh_service._pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_refresh_service._pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    new_tokens = {
        "access_token": "dummy-updated-access",
        "refresh_token": "dummy-updated-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "chat:read chat:edit",
    }

    await mock_refresh_service._update_tokens(1001, "twitch", new_tokens)

    call_args = mock_conn.execute.call_args
    sql = call_args[0][0]
    assert "UPDATE platform_integrations" in sql
    assert "access_token" in sql
    assert "refresh_token" in sql
    assert "expires_at" in sql
    assert "updated_at" in sql
```

---

## Testing Error Scenarios

```python
@pytest.mark.asyncio
async def test_all_retries_exhausted(mock_refresh_service, dummy_twitch_integration):
    """Test that exhausting all retries increments error counter."""
    import respx
    import httpx

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [dummy_twitch_integration]
    mock_refresh_service._pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_refresh_service._pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_refresh_service._max_retries = 2
    mock_refresh_service._retry_backoff_base = 0  # No wait in tests

    with respx.mock:
        respx.post("https://id.twitch.tv/oauth2/token").mock(
            return_value=httpx.Response(500, json={"error": "server_error"})
        )
        count = await mock_refresh_service.run_refresh_cycle()

    assert count == 0
    assert mock_refresh_service._total_errors >= 1

def test_invalid_platform_raises_value_error():
    """Test get_handler raises ValueError for unknown platform."""
    from core.credential_manager_module.services.oauth_handlers import get_handler
    with pytest.raises(ValueError, match="Unsupported platform"):
        get_handler("fakebook")
```

---

## Coverage Targets

| Module | Target Coverage |
|---|---|
| `app.py` | 80% |
| `config.py` | 85% |
| `services/refresh_service.py` | 75% |
| `services/oauth_handlers.py` | 90% |

The existing test suite covers handler instantiation, configuration defaults, and error class behavior. Additional tests are needed for `RefreshService` lifecycle, token update logic, and Redis pub/sub publishing.

---

## CI/CD Test Execution

In the GitHub Actions workflow, tests run as part of the `test` job:

```yaml
- name: Run credential manager tests
  working-directory: .
  env:
    DATABASE_URL: "postgresql://test_user:test_pass@localhost:5432/test_waddlebot"
    REDIS_URL: "redis://localhost:6379/15"
    PLATFORM_ENCRYPTION_KEY: "test-key-placeholder-not-for-production"
    LOG_LEVEL: "WARNING"
  run: |
    python -m pytest core/credential_manager_module/test_credential_manager.py \
      --cov=core.credential_manager_module \
      --cov-report=xml \
      -v
```

Tests must pass before merging to `main`. The `PLATFORM_ENCRYPTION_KEY` used in CI is a test placeholder value — it is not a real encryption key and is safe to use in non-production test environments.
