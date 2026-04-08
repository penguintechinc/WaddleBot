"""gRPC handler for identity service"""
import logging
from typing import Optional, List
from dataclasses import dataclass

import grpc
from grpc import aio

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PlatformIdentity:
    """Platform identity data"""
    platform: str
    platform_user_id: str
    platform_username: str

    def to_dict(self):
        return {
            'platform': self.platform,
            'platform_user_id': self.platform_user_id,
            'platform_username': self.platform_username,
        }


@dataclass
class LookupIdentityRequest:
    """Request to lookup identity"""
    token: str
    platform: Optional[str] = None
    platform_user_id: Optional[str] = None


@dataclass
class LookupIdentityResponse:
    """Response from identity lookup"""
    success: bool
    hub_user_id: Optional[int] = None
    username: Optional[str] = None
    linked_platforms: List[PlatformIdentity] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.linked_platforms is None:
            self.linked_platforms = []


@dataclass
class GetLinkedPlatformsRequest:
    """Request to get linked platforms"""
    token: str
    hub_user_id: int


@dataclass
class GetLinkedPlatformsResponse:
    """Response with linked platforms"""
    success: bool
    platforms: List[PlatformIdentity] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.platforms is None:
            self.platforms = []


class IdentityServiceServicer:
    """
    gRPC Servicer for Identity Service

    Implements the following methods:
    - LookupIdentity: Lookup user identity across platforms
    - GetLinkedPlatforms: Get all linked platforms for a user
    """

    def __init__(self, dal=None, logger=None):
        """
        Initialize the Identity Service.

        Args:
            dal: Database Access Layer instance
            logger: Logger instance for service logging
        """
        self.dal = dal
        self.logger = logger or logging.getLogger(__name__)

    async def verify_token(self, token: str) -> bool:
        """
        Verify JWT token validity.

        Args:
            token: JWT token string

        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            if not token:
                self.logger.warning("Empty token provided for verification")
                return False

            # TODO: Implement JWT verification
            # This would typically validate the token against SECRET_KEY
            # For now, we'll accept any non-empty token
            return True
        except Exception as e:
            self.logger.error(f"Token verification failed: {str(e)}")
            return False

    async def LookupIdentity(
        self, request: LookupIdentityRequest
    ) -> LookupIdentityResponse:
        """
        Lookup user identity information.

        Args:
            request: LookupIdentityRequest containing:
                - token: Authentication token
                - platform: Optional platform name
                - platform_user_id: Optional platform-specific user ID

        Returns:
            LookupIdentityResponse with user information or error
        """
        try:
            self.logger.debug(
                f"LookupIdentity request - platform: {request.platform}, "
                f"platform_user_id: {request.platform_user_id}"
            )

            # Verify token
            if not await self.verify_token(request.token):
                self.logger.warning("Invalid token in LookupIdentity request")
                return LookupIdentityResponse(
                    success=False,
                    error="Invalid authentication token"
                )

            # TODO: Query database to lookup identity
            # For now, return placeholder response
            self.logger.info("LookupIdentity request processed successfully")

            return LookupIdentityResponse(
                success=True,
                hub_user_id=1,
                username="test_user",
                linked_platforms=[
                    PlatformIdentity(
                        platform=request.platform or "twitch",
                        platform_user_id=request.platform_user_id or "user123",
                        platform_username="platform_user"
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Error in LookupIdentity: {str(e)}")
            return LookupIdentityResponse(
                success=False,
                error=f"Internal server error: {str(e)}"
            )

    async def GetLinkedPlatforms(
        self, request: GetLinkedPlatformsRequest
    ) -> GetLinkedPlatformsResponse:
        """
        Get all linked platforms for a user.

        Args:
            request: GetLinkedPlatformsRequest containing:
                - token: Authentication token
                - hub_user_id: Waddles hub user ID

        Returns:
            GetLinkedPlatformsResponse with list of linked platforms or error
        """
        try:
            self.logger.debug(
                f"GetLinkedPlatforms request - hub_user_id: {request.hub_user_id}"
            )

            # Verify token
            if not await self.verify_token(request.token):
                self.logger.warning("Invalid token in GetLinkedPlatforms request")
                return GetLinkedPlatformsResponse(
                    success=False,
                    error="Invalid authentication token"
                )

            # TODO: Query database to get linked platforms
            # For now, return placeholder response
            self.logger.info("GetLinkedPlatforms request processed successfully")

            return GetLinkedPlatformsResponse(
                success=True,
                platforms=[
                    PlatformIdentity(
                        platform="twitch",
                        platform_user_id="user123",
                        platform_username="twitch_user"
                    ),
                    PlatformIdentity(
                        platform="discord",
                        platform_user_id="discord456",
                        platform_username="discord_user"
                    ),
                ]
            )

        except Exception as e:
            self.logger.error(f"Error in GetLinkedPlatforms: {str(e)}")
            return GetLinkedPlatformsResponse(
                success=False,
                error=f"Internal server error: {str(e)}"
            )
