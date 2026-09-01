"""
Unit tests for SpotifyOAuthService — regression test for Bug 4.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.oauth_service import SpotifyOAuthService


@pytest.fixture
def oauth_service():
    """Create a SpotifyOAuthService with a mocked DAL."""
    dal = MagicMock()
    return SpotifyOAuthService(
        dal=dal,
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="https://example.com/callback",
    )


# ---------------------------------------------------------------------------
# Bug 4 regression: NULL expires_at must not raise TypeError, must refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_valid_token_null_expires_at_triggers_refresh(oauth_service):
    """When expires_at is NULL, get_valid_token must refresh rather than crash."""
    # Simulate a DB row with NULL expires_at
    oauth_service.dal.executesql = MagicMock(
        return_value=[("stale_access_token", None)]
    )

    refreshed_token = "fresh_access_token"
    oauth_service.refresh_token = AsyncMock(
        return_value={"access_token": refreshed_token}
    )

    result = await oauth_service.get_valid_token(community_id=42)

    assert result == refreshed_token, (
        "get_valid_token must refresh when expires_at is NULL"
    )
    oauth_service.refresh_token.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_get_valid_token_expired_triggers_refresh(oauth_service):
    """An expired token (expires_at in the past) triggers a refresh."""
    past = datetime.utcnow() - timedelta(hours=1)
    oauth_service.dal.executesql = MagicMock(
        return_value=[("old_access", past)]
    )

    oauth_service.refresh_token = AsyncMock(
        return_value={"access_token": "new_access"}
    )

    result = await oauth_service.get_valid_token(community_id=1)

    assert result == "new_access"
    oauth_service.refresh_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_valid_token_valid_returns_without_refresh(oauth_service):
    """A token expiring in 30 minutes is returned as-is (no refresh)."""
    future = datetime.utcnow() + timedelta(minutes=30)
    oauth_service.dal.executesql = MagicMock(
        return_value=[("valid_access", future)]
    )

    oauth_service.refresh_token = AsyncMock()

    result = await oauth_service.get_valid_token(community_id=99)

    assert result == "valid_access"
    oauth_service.refresh_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_valid_token_returns_none_when_not_authenticated(oauth_service):
    """Returns None when there is no stored token for the community."""
    oauth_service.dal.executesql = MagicMock(return_value=[])

    result = await oauth_service.get_valid_token(community_id=0)

    assert result is None
