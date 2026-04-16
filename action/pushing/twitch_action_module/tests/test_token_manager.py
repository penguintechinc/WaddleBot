"""
Unit tests for TokenManager service.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from pydal import DAL

from services.token_manager import TokenManager


@pytest.fixture
def db():
    """Create test database."""
    test_db = DAL("sqlite:memory:")
    yield test_db
    test_db.close()


@pytest.fixture
def token_manager(db):
    """Create TokenManager instance."""
    return TokenManager(
        db=db,
        client_id="test_client_id",
        client_secret="test_client_secret"
    )


@pytest.mark.asyncio
async def test_store_token(token_manager):
    """Test storing OAuth token."""
    result = await token_manager.store_token(
        broadcaster_id="123456",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_in=3600,
        scopes=["chat:write", "moderator:manage:banned_users"]
    )

    assert result is True
    assert token_manager.has_token("123456")


@pytest.mark.asyncio
async def test_get_token_not_expired(token_manager):
    """Test getting token that is not expired."""
    # Store token with future expiration
    await token_manager.store_token(
        broadcaster_id="123456",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_in=7200,  # 2 hours
        scopes=["chat:write"]
    )

    # Get token (should not refresh)
    token = await token_manager.get_token("123456")
    assert token == "test_access_token"


@pytest.mark.asyncio
async def test_has_token(token_manager):
    """Test checking if token exists."""
    # No token initially
    assert token_manager.has_token("123456") is False

    # Store token
    await token_manager.store_token(
        broadcaster_id="123456",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_in=3600
    )

    # Token exists
    assert token_manager.has_token("123456") is True


@pytest.mark.asyncio
async def test_revoke_token(token_manager):
    """Test revoking token."""
    # Store token
    await token_manager.store_token(
        broadcaster_id="123456",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_in=3600
    )

    assert token_manager.has_token("123456") is True

    # Revoke token
    result = await token_manager.revoke_token("123456")
    assert result is True
    assert token_manager.has_token("123456") is False


@pytest.mark.asyncio
async def test_update_existing_token(token_manager):
    """Test updating existing token."""
    # Store initial token
    await token_manager.store_token(
        broadcaster_id="123456",
        access_token="old_token",
        refresh_token="old_refresh",
        expires_in=3600
    )

    # Update with new token
    await token_manager.store_token(
        broadcaster_id="123456",
        access_token="new_token",
        refresh_token="new_refresh",
        expires_in=7200
    )

    # Should still be one record
    token = await token_manager.get_token("123456")
    assert token == "new_token"


def test_token_manager_initialization(db):
    """Test TokenManager initialization."""
    manager = TokenManager(
        db=db,
        client_id="test_id",
        client_secret="test_secret"
    )

    assert manager.client_id == "test_id"
    assert manager.client_secret == "test_secret"
    assert manager.token_url == "https://id.twitch.tv/oauth2/token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_refresh_response(new_access_token: str, new_refresh_token: str, expires_in: int = 3600):
    """Build an aiohttp response mock that returns a Twitch token refresh payload."""
    resp_mock = AsyncMock()
    resp_mock.status = 200
    resp_mock.json = AsyncMock(return_value={
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "expires_in": expires_in,
        "token_type": "bearer",
    })
    resp_mock.text = AsyncMock(return_value="")
    # Support `async with session.post(...) as resp:`
    post_ctx = AsyncMock()
    post_ctx.__aenter__ = AsyncMock(return_value=resp_mock)
    post_ctx.__aexit__ = AsyncMock(return_value=False)
    return post_ctx


def _make_session_mock(post_ctx):
    """Build an aiohttp.ClientSession mock wired to the given post context."""
    session_mock = AsyncMock()
    session_mock.post = MagicMock(return_value=post_ctx)
    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=session_mock)
    session_ctx.__aexit__ = AsyncMock(return_value=False)
    return session_ctx


# ---------------------------------------------------------------------------
# Bug 3 regression: near-expiry token must trigger refresh in get_token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_token_near_expiry_triggers_refresh(token_manager):
    """A token expiring within the refresh buffer is refreshed automatically."""
    # Token expires in 60 s — well inside the 300 s default buffer
    near_expiry = datetime.utcnow() + timedelta(seconds=60)
    token_manager.db.twitch_action_tokens.insert(
        broadcaster_id="near_exp_001",
        access_token="stale_access",
        refresh_token="valid_refresh",
        expires_at=near_expiry,
        scopes=[],
    )
    token_manager.db.commit()

    post_ctx = _make_refresh_response("fresh_access", "valid_refresh")
    session_ctx = _make_session_mock(post_ctx)

    with patch("services.token_manager.aiohttp.ClientSession", return_value=session_ctx):
        token = await token_manager.get_token("near_exp_001")

    assert token == "fresh_access", (
        "get_token must return the refreshed access token when token is near expiry"
    )
    # Verify DB was updated
    row = token_manager.db(
        token_manager.db.twitch_action_tokens.broadcaster_id == "near_exp_001"
    ).select().first()
    assert row.access_token == "fresh_access"


# ---------------------------------------------------------------------------
# force_refresh tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_force_refresh_returns_new_token(token_manager):
    """force_refresh unconditionally calls the Twitch token endpoint and returns new token."""
    future = datetime.utcnow() + timedelta(hours=2)  # Token is NOT expired
    token_manager.db.twitch_action_tokens.insert(
        broadcaster_id="force_001",
        access_token="current_access",
        refresh_token="current_refresh",
        expires_at=future,
        scopes=[],
    )
    token_manager.db.commit()

    post_ctx = _make_refresh_response("rotated_access", "rotated_refresh")
    session_ctx = _make_session_mock(post_ctx)

    with patch("services.token_manager.aiohttp.ClientSession", return_value=session_ctx):
        result = await token_manager.force_refresh("force_001")

    assert result == "rotated_access"
    row = token_manager.db(
        token_manager.db.twitch_action_tokens.broadcaster_id == "force_001"
    ).select().first()
    assert row.access_token == "rotated_access"
    assert row.refresh_token == "rotated_refresh"


@pytest.mark.asyncio
async def test_force_refresh_returns_none_when_no_token(token_manager):
    """force_refresh returns None immediately when there is no stored token."""
    result = await token_manager.force_refresh("nonexistent_broadcaster")
    assert result is None


@pytest.mark.asyncio
async def test_force_refresh_returns_none_when_no_refresh_token(token_manager):
    """force_refresh returns None when stored token has no refresh_token."""
    future = datetime.utcnow() + timedelta(hours=2)
    # Insert row with empty refresh_token (simulates partially-stored state)
    token_manager.db.twitch_action_tokens.insert(
        broadcaster_id="no_refresh_001",
        access_token="some_access",
        refresh_token="",  # blank
        expires_at=future,
        scopes=[],
    )
    token_manager.db.commit()

    result = await token_manager.force_refresh("no_refresh_001")
    assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
