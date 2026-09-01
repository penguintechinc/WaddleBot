"""AES-256-GCM at-rest encryption for community BYOK provider keys.

Same primitive and wire format as `services/github_sync_service.py`'s
`encrypt_token`/`decrypt_token` (`cryptography.hazmat.primitives.ciphers.
aead.AESGCM`, already a pinned runtime dependency -- see that module's own
docstring and `requirements.in`'s `cryptography` entry) -- this is the
"grep for the repo's existing crypto util, don't roll your own" primitive,
re-keyed under its own env var (`AI_BYOK_ENCRYPTION_KEY`) so a BYOK-key
compromise and a GitHub-token compromise never share a key. One string
column (base64 of `iv(12) || ciphertext || tag`), matching that module's
format exactly rather than `services/bot_crypto.py`'s two-column
`(ciphertext, iv)` tuple shape -- `ai_byok_keys.encrypted_key` is a single
TEXT column (migration 077).
"""

from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from services.errors import ApiError

_IV_LENGTH = 12
_KEY_HEX_LENGTH = 64


def _encryption_key() -> bytes:
    """Return the 32-byte AES-256 key from `AI_BYOK_ENCRYPTION_KEY` (64 hex chars)."""
    raw = os.getenv("AI_BYOK_ENCRYPTION_KEY")
    key_error = (
        "AI_BYOK_ENCRYPTION_KEY must be a 64-character hex string (32 bytes)",
        500,
        "INTERNAL_ERROR",
    )
    if not raw:
        raise ApiError(
            "AI_BYOK_ENCRYPTION_KEY environment variable is not set", 500, "INTERNAL_ERROR"
        )
    try:
        key = bytes.fromhex(raw)
    except ValueError as exc:
        raise ApiError(*key_error) from exc
    if len(key) != 32:
        raise ApiError(*key_error)
    return key


def encrypt_key(plaintext_key: str) -> str:
    """AES-256-GCM encrypt a BYOK provider key; returns base64(iv + ciphertext + tag).

    Callers must never log `plaintext_key` -- see `config_service.py`'s
    `set_byok_key()`, the only call site.
    """
    key = _encryption_key()
    iv = os.urandom(_IV_LENGTH)
    ciphertext_and_tag = AESGCM(key).encrypt(iv, plaintext_key.encode("utf-8"), None)
    return base64.b64encode(iv + ciphertext_and_tag).decode("ascii")


def decrypt_key(encrypted_b64: str) -> str:
    """Decrypt a value produced by `encrypt_key()`. Raises `ApiError` on tamper/corruption.

    The returned plaintext must never be logged or included in any HTTP
    response -- `clients.py`'s BYOK clients consume it directly as an
    outbound `Authorization`/`x-api-key` header value and nothing else.
    """
    key = _encryption_key()
    try:
        raw = base64.b64decode(encrypted_b64, validate=True)
        iv, ciphertext_and_tag = raw[:_IV_LENGTH], raw[_IV_LENGTH:]
        plaintext = AESGCM(key).decrypt(iv, ciphertext_and_tag, None)
    except (InvalidTag, ValueError, binascii.Error) as exc:
        raise ApiError("Failed to decrypt BYOK key", 500, "INTERNAL_ERROR") from exc
    return plaintext.decode("utf-8")


def mask_key(plaintext_key: str) -> str:
    """Return the last 4 chars only -- for the `key_last4` display column, never the full key."""
    if not plaintext_key or len(plaintext_key) < 4:
        return "****"
    return plaintext_key[-4:]
