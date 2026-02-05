"""
Secure token generation utilities.

Provides cryptographically secure random token generation for:
- API keys
- Session tokens
- Password reset tokens
- Email verification tokens
"""

import base64
import secrets
from typing import Literal


def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Returns hex-encoded string (2 characters per byte).

    Args:
        length: Number of random bytes to generate (default: 32).
                The returned hex string will be 2x this length.

    Returns:
        Hex-encoded random token string.

    Raises:
        ValueError: If length is not positive.

    Example:
        >>> token = generate_token(32)
        >>> len(token)
        64
    """
    if length <= 0:
        raise ValueError(f"Token length must be positive, got {length}")

    return secrets.token_hex(length)


def generate_url_safe_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure URL-safe random token.

    Returns URL-safe base64 encoded string (no padding).
    Suitable for use in URLs, filenames, and other contexts where
    special characters should be avoided.

    Args:
        length: Number of random bytes to generate (default: 32).

    Returns:
        URL-safe base64-encoded random token string (no padding).

    Raises:
        ValueError: If length is not positive.

    Example:
        >>> token = generate_url_safe_token(32)
        >>> '+' in token or '/' in token or '=' in token
        False
    """
    if length <= 0:
        raise ValueError(f"Token length must be positive, got {length}")

    return secrets.token_urlsafe(length)


def generate_api_key(prefix: str = "wa") -> str:
    """
    Generate an API key with a recognizable prefix.

    Format: {prefix}-{random_hex}

    Args:
        prefix: Prefix for the API key (default: "wa" for Waddles).

    Returns:
        API key string in format "prefix-hextoken".

    Example:
        >>> key = generate_api_key("wa")
        >>> key.startswith("wa-")
        True
    """
    return f"{prefix}-{secrets.token_hex(24)}"


def generate_numeric_code(length: int = 6) -> str:
    """
    Generate a numeric verification code.

    Suitable for SMS/email verification, 2FA backup codes, etc.

    Args:
        length: Number of digits (default: 6).

    Returns:
        String of random digits.

    Raises:
        ValueError: If length is not positive or exceeds 20.

    Example:
        >>> code = generate_numeric_code(6)
        >>> len(code) == 6 and code.isdigit()
        True
    """
    if length <= 0:
        raise ValueError(f"Code length must be positive, got {length}")
    if length > 20:
        raise ValueError(f"Code length must not exceed 20, got {length}")

    # Generate random number with exactly 'length' digits
    min_val = 10 ** (length - 1)
    max_val = (10 ** length) - 1
    return str(secrets.randbelow(max_val - min_val + 1) + min_val)


def generate_session_id() -> str:
    """
    Generate a session ID suitable for session management.

    Returns a 256-bit (32 byte) URL-safe token, which provides
    sufficient entropy for session identifiers.

    Returns:
        URL-safe session ID string.
    """
    return generate_url_safe_token(32)


__all__ = [
    "generate_token",
    "generate_url_safe_token",
    "generate_api_key",
    "generate_numeric_code",
    "generate_session_id",
]
