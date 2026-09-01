"""AES-256-GCM helpers for RCON server credentials -- ports `utils/encryption.js`.

Wire-format parity is load-bearing: `server_status_configs.credential_enc`
/ `credential_iv` rows written by the Node hub (or the Python
server-manager-service, whichever wrote them first) must decrypt
correctly regardless of which stack wrote them, for the duration of the
strangler-fig split (migration plan §6 "Auth/session during split-brain"
applies equally to this at-rest secret). Same algorithm, same key
material (`RCON_ENCRYPTION_KEY`, 64 hex chars = 32 bytes), same IV
length (12 bytes, GCM-standard), same tag placement (16-byte GCM auth
tag appended to the ciphertext, not stored separately) -- the Node
comment `// Append auth tag to ciphertext (Python cryptography expects
this)` confirms a Python consumer (`cryptography`'s `AESGCM`) already
reads this exact format.
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_IV_LENGTH = 12
_KEY_HEX_LENGTH = 64


class EncryptionKeyError(ValueError):
    """`RCON_ENCRYPTION_KEY` is missing or not a 64-character hex string."""


def _get_key() -> bytes:
    hex_key = os.environ.get("RCON_ENCRYPTION_KEY", "")
    if len(hex_key) != _KEY_HEX_LENGTH:
        raise EncryptionKeyError("RCON_ENCRYPTION_KEY must be a 64-character hex string")
    return bytes.fromhex(hex_key)


def encrypt(plaintext: str) -> tuple[bytes, bytes]:
    """Encrypt `plaintext`; returns `(ciphertext_with_appended_tag, iv)`."""
    key = _get_key()
    iv = os.urandom(_IV_LENGTH)
    ciphertext = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
    return ciphertext, iv


def decrypt(ciphertext: bytes, iv: bytes) -> str:
    """Decrypt `ciphertext` (GCM tag appended) encrypted with `encrypt()`."""
    key = _get_key()
    plaintext = AESGCM(key).decrypt(iv, bytes(ciphertext), None)
    return plaintext.decode("utf-8")
