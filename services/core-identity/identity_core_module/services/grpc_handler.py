"""gRPC handler for identity service"""
import logging
import os
from typing import Optional, List
from dataclasses import dataclass

import grpc
from grpc import aio
from flask_core.auth import verify_jwt_token
from identity_core_module.config import Config

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

            # Get secret key from environment or config
            secret_key = os.getenv("SECRET_KEY", Config.SECRET_KEY)

            # Verify JWT token using flask_core
            payload = verify_jwt_token(token, secret_key)

            # Check if verification failed
            if payload is None:
                self.logger.warning("JWT verification failed for provided token")
                return False

            # Check for required tenant claim
            tenant = payload.get("tenant")
            if not tenant or not isinstance(tenant, str) or len(tenant.strip()) == 0:
                self.logger.warning("Token missing or empty tenant claim")
                return False

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

            # Validate required parameters
            if not request.platform or not request.platform_user_id:
                self.logger.warning("Missing required parameters: platform and platform_user_id")
                return LookupIdentityResponse(
                    success=False,
                    error="platform and platform_user_id are required"
                )

            # Query database for identity if DAL is available
            if self.dal is None:
                self.logger.warning("DAL not available for LookupIdentity")
                return LookupIdentityResponse(
                    success=False,
                    error="Internal server error"
                )

            # Query to get hub_user_id and username
            identity_query = """
                SELECT hui.hub_user_id, hu.username
                FROM hub_user_identities hui
                JOIN hub_users hu ON hu.id = hui.hub_user_id
                WHERE hui.platform = %s AND hui.platform_user_id = %s
                LIMIT 1
            """

            identity_result = self.dal.executesql(
                identity_query,
                [request.platform, request.platform_user_id]
            )

            if not identity_result:
                self.logger.info(
                    f"Identity not found for platform={request.platform}, "
                    f"platform_user_id={request.platform_user_id}"
                )
                return LookupIdentityResponse(
                    success=False,
                    error="Identity not found"
                )

            # Extract user info from query result
            hub_user_id = identity_result[0][0]
            username = identity_result[0][1]

            # Query linked platforms for this user
            platforms_query = """
                SELECT platform, platform_user_id, platform_username
                FROM hub_user_identities
                WHERE hub_user_id = %s
            """

            platforms_result = self.dal.executesql(platforms_query, [hub_user_id])

            # Build linked platforms list
            linked_platforms = []
            if platforms_result:
                for row in platforms_result:
                    linked_platforms.append(
                        PlatformIdentity(
                            platform=row[0],
                            platform_user_id=row[1],
                            platform_username=row[2]
                        )
                    )

            self.logger.info(
                f"LookupIdentity request processed successfully for hub_user_id={hub_user_id}"
            )

            return LookupIdentityResponse(
                success=True,
                hub_user_id=hub_user_id,
                username=username,
                linked_platforms=linked_platforms
            )

        except Exception as e:
            self.logger.error(f"Error in LookupIdentity: {str(e)}")
            return LookupIdentityResponse(
                success=False,
                error="Internal server error"
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

            # Query database for linked platforms if DAL is available
            if self.dal is None:
                self.logger.warning("DAL not available for GetLinkedPlatforms")
                return GetLinkedPlatformsResponse(
                    success=False,
                    error="Internal server error"
                )

            # Query to get linked platforms
            platforms_query = """
                SELECT platform, platform_user_id, platform_username
                FROM hub_user_identities
                WHERE hub_user_id = %s
                ORDER BY is_primary DESC, linked_at ASC
            """

            platforms_result = self.dal.executesql(platforms_query, [request.hub_user_id])

            # Build platforms list from query result
            platforms = []
            if platforms_result:
                for row in platforms_result:
                    platforms.append(
                        PlatformIdentity(
                            platform=row[0],
                            platform_user_id=row[1],
                            platform_username=row[2]
                        )
                    )

            self.logger.info(
                f"GetLinkedPlatforms request processed successfully for hub_user_id={request.hub_user_id}, "
                f"found {len(platforms)} platforms"
            )

            return GetLinkedPlatformsResponse(
                success=True,
                platforms=platforms
            )

        except Exception as e:
            self.logger.error(f"Error in GetLinkedPlatforms: {str(e)}")
            return GetLinkedPlatformsResponse(
                success=False,
                error="Internal server error"
            )
