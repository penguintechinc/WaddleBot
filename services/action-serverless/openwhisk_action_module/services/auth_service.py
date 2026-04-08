"""
JWT authentication service for OpenWhisk Action Module.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import jwt

from config import Config

logger = logging.getLogger(__name__)


class AuthService:
    """JWT authentication service."""

    @staticmethod
    def create_token(data: Dict[str, Any], expires_in: Optional[int] = None) -> str:
        """
        Create JWT token.

        Args:
            data: Token payload data
            expires_in: Token expiration in seconds (default: from config)

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

        logger.info(f"JWT token created for: {data.get('service', 'unknown')}")
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                Config.MODULE_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )
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
        Validate API key against configured secret key.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        return api_key == Config.MODULE_SECRET_KEY
