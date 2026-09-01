"""HMAC-SHA256 request signing + secret resolution for the `webhook` adapter.

`ActionTarget.secret_ref` names an environment variable holding the
bundle's webhook signing secret (security.md Secrets & Credentials: env
vars, never hardcoded; this repo's "secrets from env, never logged"
convention) -- svc-action resolves it at dispatch time, signs the request
body, and never logs the resolved value.
"""

from __future__ import annotations

import hashlib
import hmac
import os


class SecretResolutionError(ValueError):
    """Raised when `secret_ref` names an env var that isn't set -- non-retryable."""


def resolve_secret(secret_ref: str) -> str:
    """Resolve `secret_ref` (an env var name) to its value.

    Raises :class:`SecretResolutionError` if the env var is unset/empty --
    a dispatch with no resolvable secret is a config error, not a transient
    failure, so callers must not retry it.
    """
    value = os.environ.get(secret_ref, "")
    if not value:
        raise SecretResolutionError(f"secret_ref {secret_ref!r} is not set in the environment")
    return value


def sign_body(secret: str, body: bytes) -> str:
    """Return the hex HMAC-SHA256 signature of `body` under `secret`.

    Never logged, never echoed back -- callers attach this as the
    `X-Waddle-Signature` header value only.
    """
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
