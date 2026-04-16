"""
Spotify OAuth Service

Handles OAuth 2.0 Authorization Code flow for Spotify API.
"""

import logging
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger(__name__)


class SpotifyOAuthService:
    """
    Service for managing Spotify OAuth tokens.

    Features:
    - Authorization Code flow
    - Automatic token refresh
    - Token storage in database
    - Scope management
    """

    OAUTH_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
    OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"

    # Required scopes for playback control
    DEFAULT_SCOPES = [
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-public",
        "playlist-modify-private",
        "user-library-read",
        "user-library-modify",
        "user-top-read",
        "user-read-recently-played"
    ]

    def __init__(self, dal, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize OAuth service.

        Args:
            dal: Database access layer
            client_id: Spotify application client ID
            client_secret: Spotify application client secret
            redirect_uri: OAuth redirect URI
        """
        self.dal = dal
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(
        self,
        state: str,
        scopes: Optional[list] = None
    ) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection
            scopes: List of permission scopes (uses defaults if None)

        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = self.DEFAULT_SCOPES

        scope_str = " ".join(scopes)

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": scope_str,
            "state": state,
            "show_dialog": "true"
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.OAUTH_AUTHORIZE_URL}?{query_string}"

    async def exchange_code_for_token(
        self,
        code: str,
        community_id: int
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from callback
            community_id: Community ID to associate token with

        Returns:
            Token data dictionary
        """
        try:
            # Prepare authorization header
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_b64 = base64.b64encode(auth_str.encode()).decode()

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.OAUTH_TOKEN_URL,
                    headers=headers,
                    data=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Token exchange failed: {response.status} - {error_text}"
                        )

                    token_data = await response.json()

            # Store token in database
            await self._store_token(community_id, token_data)

            logger.info(f"Spotify token obtained for community {community_id}")

            return token_data

        except Exception as e:
            logger.error(f"Failed to exchange code for token: {e}")
            raise

    async def refresh_token(self, community_id: int) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            community_id: Community ID

        Returns:
            New token data
        """
        try:
            # Get current refresh token
            result = self.dal.executesql(
                """SELECT refresh_token FROM music_oauth_tokens
                   WHERE community_id = %s AND platform = 'spotify'""",
                [community_id]
            )

            if not result or not result[0] or not result[0][0]:
                raise Exception("No refresh token found")

            refresh_token = result[0][0]

            # Prepare authorization header
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_b64 = base64.b64encode(auth_str.encode()).decode()

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.OAUTH_TOKEN_URL,
                    headers=headers,
                    data=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Token refresh failed: {response.status} - {error_text}"
                        )

                    token_data = await response.json()

            # Preserve existing refresh token if not provided
            if "refresh_token" not in token_data:
                token_data["refresh_token"] = refresh_token

            # Update token in database
            await self._store_token(community_id, token_data)

            logger.info(f"Spotify token refreshed for community {community_id}")

            return token_data

        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise

    async def get_valid_token(self, community_id: int) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            community_id: Community ID

        Returns:
            Valid access token or None if not authenticated
        """
        try:
            result = self.dal.executesql(
                """SELECT access_token, expires_at FROM music_oauth_tokens
                   WHERE community_id = %s AND platform = 'spotify'""",
                [community_id]
            )

            if not result or not result[0]:
                return None

            access_token = result[0][0]
            expires_at = result[0][1]

            # Check if token is expired (with 5 minute buffer).
            # Treat NULL expires_at as already expired — always refresh.
            if expires_at is None or expires_at <= datetime.utcnow() + timedelta(minutes=5):
                logger.info(
                    f"Token expired for community {community_id}, refreshing..."
                )
                token_data = await self.refresh_token(community_id)
                return token_data.get("access_token")

            return access_token

        except Exception as e:
            logger.error(f"Failed to get valid token: {e}")
            return None

    async def _store_token(
        self,
        community_id: int,
        token_data: Dict[str, Any]
    ):
        """
        Store or update OAuth token in database.

        Args:
            community_id: Community ID
            token_data: Token data from Spotify
        """
        try:
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            token_type = token_data.get("token_type", "Bearer")
            expires_in = token_data.get("expires_in", 3600)
            scope = token_data.get("scope", "")

            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # Upsert token
            self.dal.executesql(
                """INSERT INTO music_oauth_tokens
                   (community_id, platform, access_token, refresh_token,
                    token_type, expires_at, scope, created_at, updated_at)
                   VALUES (%s, 'spotify', %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (community_id, platform)
                   DO UPDATE SET
                       access_token = EXCLUDED.access_token,
                       refresh_token = COALESCE(EXCLUDED.refresh_token, music_oauth_tokens.refresh_token),
                       token_type = EXCLUDED.token_type,
                       expires_at = EXCLUDED.expires_at,
                       scope = EXCLUDED.scope,
                       updated_at = EXCLUDED.updated_at""",
                [
                    community_id,
                    access_token,
                    refresh_token,
                    token_type,
                    expires_at,
                    scope,
                    datetime.utcnow(),
                    datetime.utcnow()
                ]
            )

            logger.info(f"Token stored for community {community_id}")

        except Exception as e:
            logger.error(f"Failed to store token: {e}")
            raise

    async def revoke_token(self, community_id: int) -> bool:
        """
        Revoke and delete OAuth token.

        Args:
            community_id: Community ID

        Returns:
            True if successful
        """
        try:
            self.dal.executesql(
                """DELETE FROM music_oauth_tokens
                   WHERE community_id = %s AND platform = 'spotify'""",
                [community_id]
            )

            logger.info(f"Token revoked for community {community_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    async def is_authenticated(self, community_id: int) -> bool:
        """
        Check if community has valid authentication.

        Args:
            community_id: Community ID

        Returns:
            True if authenticated
        """
        token = await self.get_valid_token(community_id)
        return token is not None
