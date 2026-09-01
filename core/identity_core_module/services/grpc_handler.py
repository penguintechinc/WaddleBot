"""gRPC handler for identity service"""
import logging
from typing import Optional

import grpc
from flask_core.auth import verify_jwt_token
from proto import common_pb2, identity_pb2, identity_pb2_grpc

try:
    from config import Config
except ImportError:  # Package import used by the source-tree unit tests.
    from identity_core_module.config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Public aliases retained for callers that imported message classes from this
# module before the generated contract was wired into the server.
PlatformIdentity = identity_pb2.PlatformIdentity
LookupIdentityRequest = identity_pb2.LookupIdentityRequest
LookupIdentityResponse = identity_pb2.LookupIdentityResponse
GetLinkedPlatformsRequest = identity_pb2.GetLinkedPlatformsRequest
GetLinkedPlatformsResponse = identity_pb2.GetLinkedPlatformsResponse


class IdentityServiceServicer(identity_pb2_grpc.IdentityServiceServicer):
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

    async def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify JWT token validity.

        Args:
            token: JWT token string

        Returns:
            The verified claims, or None when authentication fails.
        """
        try:
            if not token:
                self.logger.warning("Empty token provided for verification")
                return None

            if not Config.JWT_SECRET:
                self.logger.error("JWT_SECRET is not configured")
                return None

            payload = verify_jwt_token(token, Config.JWT_SECRET)
            if payload is None:
                self.logger.warning("JWT verification failed for provided token")
                return None

            service = payload.get("service")
            if service:
                if service not in Config.ALLOWED_SERVICES:
                    self.logger.warning(
                        "Identity request rejected for unapproved service: %s",
                        service,
                    )
                    return None
                return payload

            if self._user_id_from_claims(payload) is None:
                self.logger.warning(
                    "Token has neither an approved service nor a valid user ID"
                )
                return None

            return payload

        except Exception as e:
            self.logger.error(f"Token verification failed: {str(e)}")
            return None

    @staticmethod
    def _user_id_from_claims(payload: dict) -> Optional[int]:
        """Extract a Hub user ID from current or legacy user JWT claims."""
        value = payload.get("userId", payload.get("sub"))
        try:
            user_id = int(value)
        except (TypeError, ValueError):
            return None
        return user_id if user_id > 0 else None

    @staticmethod
    def _is_service(payload: dict) -> bool:
        return bool(payload.get("service"))

    @staticmethod
    def _error(code: grpc.StatusCode, message: str) -> common_pb2.Error:
        return common_pb2.Error(code=code.value[0], message=message)

    async def LookupIdentity(
        self,
        request: identity_pb2.LookupIdentityRequest,
        context: Optional[grpc.aio.ServicerContext] = None,
    ) -> identity_pb2.LookupIdentityResponse:
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
            claims = await self.verify_token(request.token)
            if claims is None:
                self.logger.warning("Invalid token in LookupIdentity request")
                return identity_pb2.LookupIdentityResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.UNAUTHENTICATED,
                        "Invalid authentication token",
                    ),
                )

            # Validate required parameters
            if not request.platform or not request.platform_user_id:
                self.logger.warning("Missing required parameters: platform and platform_user_id")
                return identity_pb2.LookupIdentityResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "platform and platform_user_id are required",
                    ),
                )

            # Query database for identity if DAL is available
            if self.dal is None:
                self.logger.warning("DAL not available for LookupIdentity")
                return identity_pb2.LookupIdentityResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.INTERNAL, "Internal server error"
                    ),
                )

            # Query to get hub_user_id and username
            identity_query = """
                SELECT hui.hub_user_id, hu.username
                FROM hub_user_identities hui
                JOIN hub_users hu ON hu.id = hui.hub_user_id
                WHERE hui.platform = %s AND hui.platform_user_id = %s
            """
            identity_params = [request.platform, request.platform_user_id]
            if not self._is_service(claims):
                # Constrain the query itself so callers cannot distinguish an
                # existing identity owned by another user from a missing one.
                identity_query += " AND hui.hub_user_id = %s"
                identity_params.append(self._user_id_from_claims(claims))
            identity_query += " LIMIT 1"

            identity_result = self.dal.executesql(
                identity_query,
                identity_params,
            )

            if not identity_result:
                self.logger.info(
                    f"Identity not found for platform={request.platform}, "
                    f"platform_user_id={request.platform_user_id}"
                )
                return identity_pb2.LookupIdentityResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.NOT_FOUND, "Identity not found"
                    ),
                )

            # Extract user info from query result
            hub_user_id = identity_result[0][0]
            username = identity_result[0][1]

            # Internal services resolve chat identities on behalf of users.
            # Human access tokens are restricted to the token owner's record.
            if (
                not self._is_service(claims)
                and self._user_id_from_claims(claims) != hub_user_id
            ):
                self.logger.warning(
                    "User token attempted cross-user identity lookup"
                )
                return identity_pb2.LookupIdentityResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.PERMISSION_DENIED,
                        "Not authorized to access this identity",
                    ),
                )

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
                        identity_pb2.PlatformIdentity(
                            platform=row[0],
                            platform_user_id=row[1],
                            platform_username=row[2]
                        )
                    )

            self.logger.info(
                f"LookupIdentity request processed successfully for hub_user_id={hub_user_id}"
            )

            return identity_pb2.LookupIdentityResponse(
                success=True,
                hub_user_id=hub_user_id,
                username=username,
                linked_platforms=linked_platforms
            )

        except Exception as e:
            self.logger.error(f"Error in LookupIdentity: {str(e)}")
            return identity_pb2.LookupIdentityResponse(
                success=False,
                error=self._error(
                    grpc.StatusCode.INTERNAL, "Internal server error"
                ),
            )

    async def GetLinkedPlatforms(
        self,
        request: identity_pb2.GetLinkedPlatformsRequest,
        context: Optional[grpc.aio.ServicerContext] = None,
    ) -> identity_pb2.GetLinkedPlatformsResponse:
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
            claims = await self.verify_token(request.token)
            if claims is None:
                self.logger.warning("Invalid token in GetLinkedPlatforms request")
                return identity_pb2.GetLinkedPlatformsResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.UNAUTHENTICATED,
                        "Invalid authentication token",
                    ),
                )

            if request.hub_user_id <= 0:
                return identity_pb2.GetLinkedPlatformsResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "hub_user_id must be a positive integer",
                    ),
                )

            if (
                not self._is_service(claims)
                and self._user_id_from_claims(claims) != request.hub_user_id
            ):
                self.logger.warning(
                    "User token attempted cross-user linked-platform lookup"
                )
                return identity_pb2.GetLinkedPlatformsResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.PERMISSION_DENIED,
                        "Not authorized to access this identity",
                    ),
                )

            # Query database for linked platforms if DAL is available
            if self.dal is None:
                self.logger.warning("DAL not available for GetLinkedPlatforms")
                return identity_pb2.GetLinkedPlatformsResponse(
                    success=False,
                    error=self._error(
                        grpc.StatusCode.INTERNAL, "Internal server error"
                    ),
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
                        identity_pb2.PlatformIdentity(
                            platform=row[0],
                            platform_user_id=row[1],
                            platform_username=row[2]
                        )
                    )

            self.logger.info(
                f"GetLinkedPlatforms request processed successfully for hub_user_id={request.hub_user_id}, "
                f"found {len(platforms)} platforms"
            )

            return identity_pb2.GetLinkedPlatformsResponse(
                success=True,
                platforms=platforms
            )

        except Exception as e:
            self.logger.error(f"Error in GetLinkedPlatforms: {str(e)}")
            return identity_pb2.GetLinkedPlatformsResponse(
                success=False,
                error=self._error(
                    grpc.StatusCode.INTERNAL, "Internal server error"
                ),
            )
