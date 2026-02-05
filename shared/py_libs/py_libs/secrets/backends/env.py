"""Environment variable secrets provider.

Default provider for development. Reads secrets from environment variables
with a configurable prefix. Suitable for docker-compose and local development.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from py_libs.secrets.base import BaseSecretsProvider, SecretValue

logger = logging.getLogger(__name__)


class EnvSecretsProvider(BaseSecretsProvider):
    """Secrets provider backed by environment variables.

    Secret keys are converted to env var names:
        'db-passwords/mod_action_twitch' -> 'DB_PASSWORDS_MOD_ACTION_TWITCH'

    This is the default provider for development environments.
    """

    __slots__ = ("_prefix",)

    def __init__(self, prefix: str = "/secrets/") -> None:
        self._prefix = prefix

    def _key_to_env(self, key: str) -> str:
        """Convert a secret key to an environment variable name."""
        clean = key.replace(self._prefix, "").replace("/", "_").replace("-", "_")
        return clean.upper()

    def get_secret(self, key: str) -> Optional[SecretValue]:
        env_name = self._key_to_env(key)
        value = os.getenv(env_name)
        if value is None:
            return None
        return SecretValue(key=key, value=value)

    def set_secret(
        self, key: str, value: str, metadata: Optional[dict] = None
    ) -> bool:
        env_name = self._key_to_env(key)
        os.environ[env_name] = value
        return True

    def delete_secret(self, key: str) -> bool:
        env_name = self._key_to_env(key)
        if env_name in os.environ:
            del os.environ[env_name]
            return True
        return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        env_prefix = self._key_to_env(prefix) if prefix else ""
        return [k for k in os.environ if k.startswith(env_prefix)]
