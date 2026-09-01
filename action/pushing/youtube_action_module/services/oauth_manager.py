"""
OAuth2 Token Management for YouTube API
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from pydal import DAL, Field

from config import Config


logger = logging.getLogger(__name__)


class OAuthManager:
    """Manages OAuth2 tokens for YouTube API access"""

    def __init__(self, db: DAL):
        self.db = db
        self._define_tables()

    def _define_tables(self) -> None:
        """Define database tables for token storage"""
        self.db.define_table(
            "youtube_oauth_tokens",
            Field("channel_id", "string", length=255, unique=True, notnull=True),
            Field("access_token", "text", notnull=True),
            Field("refresh_token", "text"),
            Field("token_uri", "string", length=512),
            Field("client_id", "string", length=255),
            Field("client_secret", "string", length=255),
            Field("scopes", "list:string"),
            Field("expires_at", "datetime"),
            Field("created_at", "datetime", default=datetime.utcnow),
            Field("updated_at", "datetime", update=datetime.utcnow),
        )
        self.db.commit()

    def get_credentials(self, channel_id: str) -> Optional[Credentials]:
        """
        Get valid credentials for a channel, refreshing if necessary

        Args:
            channel_id: YouTube channel ID

        Returns:
            Valid Credentials object or None if not found
        """
        token_row = self.db(
            self.db.youtube_oauth_tokens.channel_id == channel_id
        ).select().first()

        if not token_row:
            logger.warning(f"No OAuth token found for channel: {channel_id}")
            return None

        # Create credentials object
        credentials = Credentials(
            token=token_row.access_token,
            refresh_token=token_row.refresh_token,
            token_uri=token_row.token_uri or "https://oauth2.googleapis.com/token",
            client_id=token_row.client_id or Config.YOUTUBE_CLIENT_ID,
            client_secret=token_row.client_secret or Config.YOUTUBE_CLIENT_SECRET,
            scopes=token_row.scopes,
        )

        # Check if token is expired or about to expire (within 5 minutes).
        # Treat NULL expires_at as already expired — always refresh.
        expires_soon = datetime.utcnow() + timedelta(minutes=5)
        if token_row.expires_at is None or token_row.expires_at <= expires_soon:
            logger.info(f"Token expired/expiring for channel: {channel_id}, refreshing")
            credentials = self._refresh_token(channel_id, credentials)

        return credentials

    def _refresh_token(
        self, channel_id: str, credentials: Credentials
    ) -> Credentials:
        """
        Refresh an expired token

        Args:
            channel_id: YouTube channel ID
            credentials: Expired credentials object

        Returns:
            Refreshed credentials object
        """
        try:
            credentials.refresh(Request())

            # Update database with new token.
            # Also persist refresh_token — Google may rotate it on each refresh.
            # google-auth preserves the old value when Google does not rotate it,
            # so credentials.refresh_token is always safe to use here.
            self.db(
                self.db.youtube_oauth_tokens.channel_id == channel_id
            ).update(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                expires_at=credentials.expiry,
                updated_at=datetime.utcnow(),
            )
            self.db.commit()

            logger.info(f"Successfully refreshed token for channel: {channel_id}")
            return credentials

        except Exception as e:
            logger.error(f"Failed to refresh token for channel {channel_id}: {e}")
            raise

    def store_credentials(
        self, channel_id: str, credentials: Credentials
    ) -> None:
        """
        Store or update OAuth credentials

        Args:
            channel_id: YouTube channel ID
            credentials: OAuth2 credentials object
        """
        existing = self.db(
            self.db.youtube_oauth_tokens.channel_id == channel_id
        ).select().first()

        data = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else [],
            "expires_at": credentials.expiry,
            "updated_at": datetime.utcnow(),
        }

        if existing:
            self.db(
                self.db.youtube_oauth_tokens.channel_id == channel_id
            ).update(**data)
            logger.info(f"Updated OAuth token for channel: {channel_id}")
        else:
            data["channel_id"] = channel_id
            data["created_at"] = datetime.utcnow()
            self.db.youtube_oauth_tokens.insert(**data)
            logger.info(f"Stored new OAuth token for channel: {channel_id}")

        self.db.commit()

    def delete_credentials(self, channel_id: str) -> bool:
        """
        Delete stored credentials for a channel

        Args:
            channel_id: YouTube channel ID

        Returns:
            True if deleted, False if not found
        """
        result = self.db(
            self.db.youtube_oauth_tokens.channel_id == channel_id
        ).delete()
        self.db.commit()

        if result:
            logger.info(f"Deleted OAuth token for channel: {channel_id}")
            return True
        else:
            logger.warning(f"No OAuth token found to delete for channel: {channel_id}")
            return False

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": Config.YOUTUBE_CLIENT_ID,
                    "client_secret": Config.YOUTUBE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [Config.YOUTUBE_REDIRECT_URI],
                }
            },
            scopes=Config.YOUTUBE_SCOPES,
        )

        flow.redirect_uri = Config.YOUTUBE_REDIRECT_URI

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",
        )

        return authorization_url

    def exchange_code_for_token(
        self, code: str, channel_id: str
    ) -> Credentials:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from OAuth callback
            channel_id: YouTube channel ID to associate with token

        Returns:
            Credentials object
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": Config.YOUTUBE_CLIENT_ID,
                    "client_secret": Config.YOUTUBE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [Config.YOUTUBE_REDIRECT_URI],
                }
            },
            scopes=Config.YOUTUBE_SCOPES,
        )

        flow.redirect_uri = Config.YOUTUBE_REDIRECT_URI
        flow.fetch_token(code=code)

        credentials = flow.credentials
        self.store_credentials(channel_id, credentials)

        return credentials

    def list_authorized_channels(self) -> list[dict]:
        """
        List all channels with stored OAuth tokens

        Returns:
            List of channel information
        """
        rows = self.db(self.db.youtube_oauth_tokens).select(
            orderby=~self.db.youtube_oauth_tokens.created_at
        )

        return [
            {
                "channel_id": row.channel_id,
                "scopes": row.scopes,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
