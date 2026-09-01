"""AES-256-GCM helpers for vendor webhook secrets.

Ports `vendorSubmissionController.js`'s `encryptWebhookSecret`/
`decryptWebhookSecret`, fixed rather than faithfully reproduced. Node's
originals used `crypto.createCipheriv('aes-256-cbc', Buffer.from(process.env.
ENCRYPTION_KEY || 'default-key'), iv)` -- AES-256 requires an exact 32-byte key,
but `Buffer.from(str)` on a short/arbitrary-length string silently produces a
key of the WRONG length (Node either throws or, depending on version, truncates/
pads unpredictably), and the `'default-key'` fallback is a hardcoded credential
(security.md: "Never hardcoded credentials or configuration"). This is a case
where faithful porting would ship a real vulnerability -- ported using this
repo's own established pattern instead (`services/bot_crypto.py`: AESGCM,
random 12-byte IV per encryption, 64-hex-char key from an environment
variable, IV-then-ciphertext single hex string so it fits the existing
`webhook_secret` text column with no schema change). No hardcoded fallback
key: `MarketplaceEncryptionKeyError` fails closed if the env var is absent.
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_IV_LENGTH = 12
_KEY_HEX_LENGTH = 64


class MarketplaceEncryptionKeyError(ValueError):
    """`MARKETPLACE_ENCRYPTION_KEY` is missing or not a 64-character hex string."""


def _get_key() -> bytes:
    hex_key = os.environ.get("MARKETPLACE_ENCRYPTION_KEY", "")
    if len(hex_key) != _KEY_HEX_LENGTH:
        raise MarketplaceEncryptionKeyError(
            "MARKETPLACE_ENCRYPTION_KEY must be a 64-character hex string"
        )
    return bytes.fromhex(hex_key)


def encrypt_webhook_secret(plaintext: str) -> str:
    """Encrypt a vendor-submitted webhook secret for storage.

    Returns a single hex string (`iv || ciphertext_with_tag`) that fits the
    existing `webhook_secret` text column unchanged.
    """
    key = _get_key()
    iv = os.urandom(_IV_LENGTH)
    ciphertext = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
    return (iv + ciphertext).hex()


def decrypt_webhook_secret(stored: str) -> str:
    """Decrypt a `webhook_secret` value written by `encrypt_webhook_secret`."""
    key = _get_key()
    raw = bytes.fromhex(stored)
    iv, ciphertext = raw[:_IV_LENGTH], raw[_IV_LENGTH:]
    return AESGCM(key).decrypt(iv, ciphertext, None).decode("utf-8")
