"""
Token management service for Twitch OAuth tokens.
Handles token refresh and storage in database.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import aiohttp
from pydal import DAL, Field

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages Twitch OAuth tokens with automatic refresh."""

    def __init__(self, db: DAL, client_id: str, client_secret: str):
        """Initialize token manager."""
        self.db = db
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://id.twitch.tv/oauth2/token"

        # Define tokens table
        self.db.define_table(
            "twitch_action_tokens",
            Field("broadcaster_id", "string", required=True, unique=True),
            Field("access_token", "string", required=True),
            Field("refresh_token", "string", required=True),
            Field("token_type", "string", default="bearer"),
            Field("expires_at", "datetime", required=True),
            Field("scopes", "list:string"),
            Field("last_refreshed", "datetime", default=datetime.utcnow),
            Field("created_at", "datetime", default=datetime.utcnow),
            Field("updated_at", "datetime", update=datetime.utcnow)
        )

    async def get_token(self, broadcaster_id: str, buffer_seconds: int = 300) -> Optional[str]:
        """
        Get valid access token for broadcaster.
        Automatically refreshes if expired or near expiration.

        Args:
            broadcaster_id: Twitch broadcaster ID
            buffer_seconds: Refresh token if expires within this time

        Returns:
            Valid access token or None if not found
        """
        try:
            # Get token from database
            token_record = self.db(
                self.db.twitch_action_tokens.broadcaster_id == broadcaster_id
            ).select().first()

            if not token_record:
                logger.warning(f"No token found for broadcaster {broadcaster_id}")
                return None

            # Check if token needs refresh
            now = datetime.utcnow()
            expires_at = token_record.expires_at

            if expires_at <= now + timedelta(seconds=buffer_seconds):
                logger.info(f"Token for broadcaster {broadcaster_id} needs refresh")
                return await self._refresh_token(broadcaster_id, token_record.refresh_token)

            return token_record.access_token

        except Exception as e:
            logger.error(f"Error getting token for broadcaster {broadcaster_id}: {e}")
            return None

    async def _refresh_token(self, broadcaster_id: str, refresh_token: str) -> Optional[str]:
        """
        Refresh access token using refresh token.

        Args:
            broadcaster_id: Twitch broadcaster ID
            refresh_token: Refresh token

        Returns:
            New access token or None on failure
        """
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }

                async with session.post(self.token_url, data=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Token refresh failed: {resp.status} - {error_text}")
                        return None

                    result = await resp.json()

                    # Calculate expiration time
                    expires_in = result.get("expires_in", 3600)
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                    # Update token in database
                    self.db(
                        self.db.twitch_action_tokens.broadcaster_id == broadcaster_id
                    ).update(
                        access_token=result["access_token"],
                        refresh_token=result.get("refresh_token", refresh_token),
                        expires_at=expires_at,
                        last_refreshed=datetime.utcnow()
                    )
                    self.db.commit()

                    logger.info(f"Token refreshed successfully for broadcaster {broadcaster_id}")
                    return result["access_token"]

        except Exception as e:
            logger.error(f"Error refreshing token for broadcaster {broadcaster_id}: {e}")
            return None

    async def store_token(
        self,
        broadcaster_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        scopes: Optional[list] = None
    ) -> bool:
        """
        Store or update token in database.

        Args:
            broadcaster_id: Twitch broadcaster ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token expiration time in seconds
            scopes: List of OAuth scopes

        Returns:
            True if successful, False otherwise
        """
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # Check if token exists
            existing = self.db(
                self.db.twitch_action_tokens.broadcaster_id == broadcaster_id
            ).select().first()

            if existing:
                # Update existing token
                self.db(
                    self.db.twitch_action_tokens.broadcaster_id == broadcaster_id
                ).update(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    scopes=scopes or [],
                    last_refreshed=datetime.utcnow()
                )
            else:
                # Insert new token
                self.db.twitch_action_tokens.insert(
                    broadcaster_id=broadcaster_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    scopes=scopes or []
                )

            self.db.commit()
            logger.info(f"Token stored successfully for broadcaster {broadcaster_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing token for broadcaster {broadcaster_id}: {e}")
            self.db.rollback()
            return False

    async def revoke_token(self, broadcaster_id: str) -> bool:
        """
        Remove token from database.

        Args:
            broadcaster_id: Twitch broadcaster ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.db(
                self.db.twitch_action_tokens.broadcaster_id == broadcaster_id
            ).delete()
            self.db.commit()

            logger.info(f"Token revoked for broadcaster {broadcaster_id}")
            return True

        except Exception as e:
            logger.error(f"Error revoking token for broadcaster {broadcaster_id}: {e}")
            self.db.rollback()
            return False

    async def force_refresh(self, broadcaster_id: str) -> Optional[str]:
        """
        Unconditionally refresh the token regardless of expiry.

        Used by the service layer after a 401 response to recover
        from tokens that passed the DB expiry check but were rejected
        by the Twitch API.

        Args:
            broadcaster_id: Twitch broadcaster ID

        Returns:
            New access token or None on failure
        """
        token_record = self.db(
            self.db.twitch_action_tokens.broadcaster_id == broadcaster_id
        ).select().first()

        if not token_record or not token_record.refresh_token:
            logger.warning(
                f"Cannot force-refresh: no refresh token for broadcaster {broadcaster_id}"
            )
            return None

        return await self._refresh_token(broadcaster_id, token_record.refresh_token)

    def has_token(self, broadcaster_id: str) -> bool:
        """
        Check if token exists for broadcaster.

        Args:
            broadcaster_id: Twitch broadcaster ID

        Returns:
            True if token exists, False otherwise
        """
        try:
            return bool(
                self.db(
                    self.db.twitch_action_tokens.broadcaster_id == broadcaster_id
                ).count()
            )
        except Exception as e:
            logger.error(f"Error checking token for broadcaster {broadcaster_id}: {e}")
            return False
