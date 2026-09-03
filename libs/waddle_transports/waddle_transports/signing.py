"""HMAC-SHA256 request signing + env-var secret resolution -- shared across transports.

`secret_ref` names an environment variable holding a signing secret/token
(security.md Secrets & Credentials: env vars, never hardcoded) -- resolved
at dispatch time, never logged.
"""

from __future__ import annotations

import hashlib
import hmac
import os


class SecretResolutionError(ValueError):
    """Raised when `secret_ref` names an env var that isn't set -- non-retryable."""


def resolve_secret(secret_ref: str) -> str:
    """Resolve `secret_ref` (an env var name) to its value.

    Raises :class:`SecretResolutionError` if the env var is unset/empty.
    """
    value = os.environ.get(secret_ref, "")
    if not value:
        raise SecretResolutionError(f"secret_ref {secret_ref!r} is not set in the environment")
    return value


def sign_body(secret: str, body: bytes) -> str:
    """Return the hex HMAC-SHA256 signature of `body` under `secret`."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
