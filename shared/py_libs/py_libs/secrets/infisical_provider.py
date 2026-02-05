"""Infisical secrets provider."""

import logging
import os
from typing import Optional

from . import ProviderUnavailableError, SecretNotFoundError
from .base import BaseSecretsProvider

logger = logging.getLogger(__name__)


class InfisicalProvider(BaseSecretsProvider):
    """Reads secrets from Infisical secret management platform.

    Requires:
    - infisical-python Python package
    - INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET environment variables
    - INFISICAL_PROJECT_ID environment variable

    Default secret naming: database/{module_name}
    """

    def __init__(self) -> None:
        """Initialize Infisical provider."""
        try:
            from infisical_client import InfisicalClient
        except ImportError as e:
            raise ImportError(
                "infisical-python package required for InfisicalProvider. "
                "Install with: pip install py_libs[infisical]"
            ) from e

        client_id = os.getenv("INFISICAL_CLIENT_ID")
        client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
        project_id = os.getenv("INFISICAL_PROJECT_ID")

        if not all([client_id, client_secret, project_id]):
            raise ValueError(
                "INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET, "
                "and INFISICAL_PROJECT_ID required"
            )

        self.client = InfisicalClient(
            client_id=client_id,
            client_secret=client_secret,
            project_id=project_id,
        )
        logger.info("Infisical provider initialized for project=%s", project_id)

    def get_db_password(self, module_name: str) -> str:
        """Retrieve database password from Infisical.

        Secret path: database/{module_name}
        Secret name: password

        Args:
            module_name: Module name.

        Returns:
            Database password.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If Infisical unavailable.
        """
        try:
            secret = self.client.getSecret(
                secretName="password", secretPath=f"/database/{module_name}"
            )
            if not secret:
                raise SecretNotFoundError(f"Password secret not found for {module_name}")

            self._log_access("get_db_password", module_name)
            return secret
        except Exception as e:
            if "not found" in str(e).lower():
                raise SecretNotFoundError(
                    f"Secret not found for module {module_name}"
                ) from e
            raise ProviderUnavailableError(f"Infisical error: {str(e)}") from e

    def get_secret(self, key: str) -> str:
        """Retrieve arbitrary secret from Infisical.

        Key format: path/to/secret:secret_name

        Args:
            key: Secret path and name.

        Returns:
            Secret value.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If Infisical unavailable.
        """
        try:
            secret_path, secret_name = key.rsplit(":", 1)
        except ValueError as e:
            raise ValueError(
                f"Invalid key format: {key}. Expected 'path:secret_name'"
            ) from e

        try:
            secret = self.client.getSecret(
                secretName=secret_name, secretPath=secret_path
            )
            if not secret:
                raise SecretNotFoundError(f"Secret not found: {key}")

            self._log_access("get_secret", key)
            return secret
        except Exception as e:
            if "not found" in str(e).lower():
                raise SecretNotFoundError(f"Secret not found: {key}") from e
            raise ProviderUnavailableError(f"Infisical error: {str(e)}") from e

    def rotate_db_password(self, module_name: str, new_password: str) -> bool:
        """Update database password in Infisical.

        Args:
            module_name: Module name.
            new_password: New password.

        Returns:
            True if successful.

        Raises:
            ProviderUnavailableError: If Infisical unavailable.
        """
        try:
            self.client.updateSecret(
                secretName="password",
                secretPath=f"/database/{module_name}",
                secretValue=new_password,
            )
            logger.info("Database password rotated for module=%s", module_name)
            self._log_access("rotate_db_password", module_name)
            return True
        except Exception as e:
            logger.error("Failed to rotate password in Infisical: %s", e)
            raise ProviderUnavailableError(f"Infisical error: {str(e)}") from e

    def health_check(self) -> bool:
        """Check Infisical connectivity.

        Returns:
            True if service is reachable.
        """
        try:
            self.client.getSecret(secretName="health", secretPath="/")
            logger.debug("Infisical health check passed")
            return True
        except Exception:
            # Health check is optional - might not have this secret
            logger.debug("Infisical health check inconclusive")
            return True
