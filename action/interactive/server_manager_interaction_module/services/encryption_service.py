"""AES-256-GCM decryption for server credentials."""
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


class EncryptionService:
    """Decrypts server credentials stored as AES-256-GCM ciphertext."""

    def __init__(self, config):
        key_hex = config.RCON_ENCRYPTION_KEY
        if not key_hex or len(key_hex) != 64:
            logger.warning("RCON_ENCRYPTION_KEY not set or invalid length; decryption will fail")
            self.aesgcm = None
        else:
            self.aesgcm = AESGCM(bytes.fromhex(key_hex))

    def decrypt(self, ciphertext: bytes, iv: bytes) -> str:
        if not self.aesgcm:
            raise RuntimeError("Encryption key not configured")
        plaintext = self.aesgcm.decrypt(iv, ciphertext, None)
        return plaintext.decode('utf-8')
