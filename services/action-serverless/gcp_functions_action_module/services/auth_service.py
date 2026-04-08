"""
Authentication Service - JWT token generation and validation.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import jwt

from config import Config


logger = logging.getLogger(__name__)


class AuthService:
    """Service for JWT authentication."""

    @staticmethod
    def create_token(data: Dict[str, Any], expires_in: int = None) -> str:
        """
        Create JWT token.

        Args:
            data: Payload data to encode
            expires_in: Token expiration in seconds (default from config)

        Returns:
            JWT token string
        """
        if expires_in is None:
            expires_in = Config.JWT_EXPIRATION_SECONDS

        payload = {
            **data,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow()
        }

        token = jwt.encode(
            payload,
            Config.MODULE_SECRET_KEY,
            algorithm=Config.JWT_ALGORITHM
        )

        logger.debug(f"Created JWT token for: {data.get('service', 'unknown')}")
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                Config.MODULE_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )

            logger.debug(f"Token verified for: {payload.get('service', 'unknown')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Validate API key against configured secret.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        # In production, this should check against database
        # For now, simple comparison with module secret key
        is_valid = api_key == Config.MODULE_SECRET_KEY

        if is_valid:
            logger.debug("API key validated successfully")
        else:
            logger.warning("Invalid API key provided")

        return is_valid

    @staticmethod
    def create_service_token(service_name: str, permissions: list = None) -> str:
        """
        Create service token with specific permissions.

        Args:
            service_name: Name of the service
            permissions: List of permission strings

        Returns:
            JWT token string
        """
        if permissions is None:
            permissions = ["invoke_functions"]

        data = {
            "service": service_name,
            "permissions": permissions,
            "token_type": "service"
        }

        return AuthService.create_token(data)

    @staticmethod
    def create_user_token(user_id: str, user_name: str, permissions: list = None) -> str:
        """
        Create user token with specific permissions.

        Args:
            user_id: User ID
            user_name: User display name
            permissions: List of permission strings

        Returns:
            JWT token string
        """
        if permissions is None:
            permissions = ["invoke_functions"]

        data = {
            "user_id": user_id,
            "user_name": user_name,
            "permissions": permissions,
            "token_type": "user"
        }

        return AuthService.create_token(data)
