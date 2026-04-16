"""
Unit tests for OAuthManager — regression tests for token refresh bugs.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from pydal import DAL

from services.oauth_manager import OAuthManager


@pytest.fixture
def db():
    """In-memory SQLite database for tests."""
    test_db = DAL("sqlite:memory:", migrate=True)
    yield test_db
    test_db.close()


@pytest.fixture
def oauth_manager(db):
    return OAuthManager(db)


def _insert_token(db, channel_id: str, access_token: str, refresh_token: str,
                  expires_at=None):
    """Helper: insert a raw token row into the test DB."""
    db.youtube_oauth_tokens.insert(
        channel_id=channel_id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="test_client_id",
        client_secret="test_client_secret",
        scopes=["https://www.googleapis.com/auth/youtube"],
        expires_at=expires_at,
    )
    db.commit()


# ---------------------------------------------------------------------------
# Bug 1 regression: _refresh_token must persist the new refresh_token
# ---------------------------------------------------------------------------

def test_refresh_token_saves_new_refresh_token(db, oauth_manager):
    """After a successful refresh, the new refresh_token is written to the DB."""
    _insert_token(db, "ch_001", "old_access", "old_refresh",
                  expires_at=datetime.utcnow() - timedelta(hours=1))

    new_credentials = MagicMock()
    new_credentials.token = "new_access"
    new_credentials.refresh_token = "new_refresh"
    new_credentials.expiry = datetime.utcnow() + timedelta(hours=1)

    with patch("services.oauth_manager.Request"), \
         patch("services.oauth_manager.Credentials") as MockCreds:
        # Make the Credentials constructor return a mock that behaves like
        # real google credentials: refresh() mutates self.
        mock_cred_instance = MagicMock()
        mock_cred_instance.token = "new_access"
        mock_cred_instance.refresh_token = "new_refresh"
        mock_cred_instance.expiry = datetime.utcnow() + timedelta(hours=1)
        mock_cred_instance.refresh = MagicMock()
        MockCreds.return_value = mock_cred_instance

        oauth_manager.get_credentials("ch_001")

    row = db(db.youtube_oauth_tokens.channel_id == "ch_001").select().first()
    assert row.refresh_token == "new_refresh", (
        "refresh_token in DB must be updated after a successful token refresh"
    )
    assert row.access_token == "new_access"


def test_refresh_token_preserves_old_refresh_token_when_not_rotated(db, oauth_manager):
    """When Google does not rotate the refresh_token, the existing one is preserved."""
    _insert_token(db, "ch_002", "old_access", "stable_refresh",
                  expires_at=datetime.utcnow() - timedelta(hours=1))

    with patch("services.oauth_manager.Request"), \
         patch("services.oauth_manager.Credentials") as MockCreds:
        mock_cred_instance = MagicMock()
        mock_cred_instance.token = "new_access"
        # google-auth preserves the old refresh_token value — simulate that
        mock_cred_instance.refresh_token = "stable_refresh"
        mock_cred_instance.expiry = datetime.utcnow() + timedelta(hours=1)
        mock_cred_instance.refresh = MagicMock()
        MockCreds.return_value = mock_cred_instance

        oauth_manager.get_credentials("ch_002")

    row = db(db.youtube_oauth_tokens.channel_id == "ch_002").select().first()
    assert row.refresh_token == "stable_refresh"


# ---------------------------------------------------------------------------
# Bug 2 regression: NULL expires_at must trigger a refresh
# ---------------------------------------------------------------------------

def test_get_credentials_null_expires_at_triggers_refresh(db, oauth_manager):
    """When expires_at is NULL in the DB, get_credentials must still refresh."""
    _insert_token(db, "ch_003", "stale_access", "some_refresh", expires_at=None)

    with patch("services.oauth_manager.Request"), \
         patch("services.oauth_manager.Credentials") as MockCreds:
        mock_cred_instance = MagicMock()
        mock_cred_instance.token = "refreshed_access"
        mock_cred_instance.refresh_token = "some_refresh"
        mock_cred_instance.expiry = datetime.utcnow() + timedelta(hours=1)
        mock_cred_instance.refresh = MagicMock()
        MockCreds.return_value = mock_cred_instance

        result = oauth_manager.get_credentials("ch_003")

    assert mock_cred_instance.refresh.called, (
        "credentials.refresh() must be called when expires_at is NULL"
    )


def test_get_credentials_valid_token_no_refresh(db, oauth_manager):
    """A token expiring in 30 minutes is NOT refreshed."""
    future = datetime.utcnow() + timedelta(minutes=30)
    _insert_token(db, "ch_004", "valid_access", "valid_refresh", expires_at=future)

    with patch("services.oauth_manager.Request"), \
         patch("services.oauth_manager.Credentials") as MockCreds:
        mock_cred_instance = MagicMock()
        mock_cred_instance.token = "valid_access"
        mock_cred_instance.refresh_token = "valid_refresh"
        mock_cred_instance.expiry = future
        mock_cred_instance.refresh = MagicMock()
        MockCreds.return_value = mock_cred_instance

        oauth_manager.get_credentials("ch_004")

    assert not mock_cred_instance.refresh.called, (
        "credentials.refresh() must NOT be called for a token that is still valid"
    )


def test_get_credentials_returns_none_for_missing_channel(oauth_manager):
    """Returns None when no token is stored for the channel."""
    result = oauth_manager.get_credentials("nonexistent_channel")
    assert result is None


# ---------------------------------------------------------------------------
# force_reauth: store_credentials / delete_credentials round-trip
# ---------------------------------------------------------------------------

def test_delete_credentials_returns_false_for_unknown_channel(oauth_manager):
    """delete_credentials returns False when the channel has no stored token."""
    assert oauth_manager.delete_credentials("unknown") is False


def test_store_and_delete_credentials(db, oauth_manager):
    """Storing then deleting credentials leaves no row in the DB."""
    mock_creds = MagicMock()
    mock_creds.token = "tok"
    mock_creds.refresh_token = "ref"
    mock_creds.token_uri = "https://oauth2.googleapis.com/token"
    mock_creds.client_id = "cid"
    mock_creds.client_secret = "csec"
    mock_creds.scopes = ["https://www.googleapis.com/auth/youtube"]
    mock_creds.expiry = datetime.utcnow() + timedelta(hours=1)

    oauth_manager.store_credentials("ch_del", mock_creds)
    assert db(db.youtube_oauth_tokens.channel_id == "ch_del").count() == 1

    result = oauth_manager.delete_credentials("ch_del")
    assert result is True
    assert db(db.youtube_oauth_tokens.channel_id == "ch_del").count() == 0
