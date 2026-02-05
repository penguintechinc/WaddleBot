"""HashiCorp Vault secrets provider."""

import logging
import os
from typing import Optional

from . import ProviderUnavailableError, SecretNotFoundError
from .base import BaseSecretsProvider

logger = logging.getLogger(__name__)


class VaultProvider(BaseSecretsProvider):
    """Reads secrets from HashiCorp Vault KV2 backend.

    Requires:
    - hvac Python package
    - VAULT_ADDR environment variable
    - VAULT_TOKEN or K8s auth configured

    Default secret path: secret/data/database/{module_name}
    """

    def __init__(self) -> None:
        """Initialize Vault provider."""
        try:
            import hvac
        except ImportError as e:
            raise ImportError(
                "hvac package required for VaultProvider. "
                "Install with: pip install py_libs[vault]"
            ) from e

        vault_addr = os.getenv("VAULT_ADDR")
        if not vault_addr:
            raise ValueError("VAULT_ADDR environment variable required")

        vault_token = os.getenv("VAULT_TOKEN")
        if not vault_token:
            logger.warning("VAULT_TOKEN not set, Vault auth will fail")

        self.client = hvac.Client(url=vault_addr, token=vault_token)
        self.mount_point = os.getenv("VAULT_MOUNT", "secret")
        logger.info("Vault provider initialized at %s", vault_addr)

    def get_db_password(self, module_name: str) -> str:
        """Retrieve database password from Vault KV2.

        Path: secret/data/database/{module_name}

        Args:
            module_name: Module name.

        Returns:
            Database password.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If Vault unavailable.
        """
        path = f"database/{module_name}"
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self.mount_point
            )
            password = response["data"]["data"].get("password")
            if not password:
                raise SecretNotFoundError(f"Password field not found in {path}")

            self._log_access("get_db_password", module_name)
            return password
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise SecretNotFoundError(f"Secret not found at {path}") from e
            raise ProviderUnavailableError(f"Vault error: {str(e)}") from e

    def get_secret(self, key: str) -> str:
        """Retrieve arbitrary secret from Vault.

        Key format: path/to/secret:field_name

        Args:
            key: Secret path and field.

        Returns:
            Secret value.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If Vault unavailable.
        """
        try:
            path, field = key.rsplit(":", 1)
        except ValueError as e:
            raise ValueError(
                f"Invalid key format: {key}. Expected 'path:field_name'"
            ) from e

        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self.mount_point
            )
            value = response["data"]["data"].get(field)
            if value is None:
                raise SecretNotFoundError(f"Field {field} not found in {path}")

            self._log_access("get_secret", key)
            return value
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise SecretNotFoundError(f"Secret not found at {path}") from e
            raise ProviderUnavailableError(f"Vault error: {str(e)}") from e

    def rotate_db_password(self, module_name: str, new_password: str) -> bool:
        """Update database password in Vault.

        Args:
            module_name: Module name.
            new_password: New password.

        Returns:
            True if successful.

        Raises:
            ProviderUnavailableError: If Vault unavailable.
        """
        path = f"database/{module_name}"
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret_data={"password": new_password},
                mount_point=self.mount_point,
            )
            logger.info("Database password rotated for module=%s", module_name)
            self._log_access("rotate_db_password", module_name)
            return True
        except Exception as e:
            logger.error("Failed to rotate password in Vault: %s", e)
            raise ProviderUnavailableError(f"Vault error: {str(e)}") from e

    def health_check(self) -> bool:
        """Check Vault connectivity.

        Returns:
            True if Vault is healthy.
        """
        try:
            self.client.sys.is_sealed()
            logger.debug("Vault health check passed")
            return True
        except Exception as e:
            logger.warning("Vault health check failed: %s", e)
            return False
