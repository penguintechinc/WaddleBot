"""Google Cloud Secret Manager provider."""

import json
import logging
import os
from typing import Optional

from . import ProviderUnavailableError, SecretNotFoundError
from .base import BaseSecretsProvider

logger = logging.getLogger(__name__)


class GCPSecretsManagerProvider(BaseSecretsProvider):
    """Reads secrets from Google Cloud Secret Manager.

    Requires:
    - google-cloud-secret-manager Python package
    - GCP credentials (service account or ADC)
    - GCP_PROJECT_ID environment variable

    Default secret naming: waddlebot-{module_name}-db-password
    """

    def __init__(self) -> None:
        """Initialize GCP Secret Manager provider."""
        try:
            from google.cloud import secretmanager
        except ImportError as e:
            raise ImportError(
                "google-cloud-secret-manager package required for GCPSecretsManagerProvider. "
                "Install with: pip install py_libs[gcp]"
            ) from e

        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            raise ValueError("GCP_PROJECT_ID environment variable required")

        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = project_id
        logger.info("GCP Secret Manager provider initialized for project=%s", project_id)

    def get_db_password(self, module_name: str) -> str:
        """Retrieve database password from GCP Secret Manager.

        Secret name: waddlebot-{module_name}-db-password

        Args:
            module_name: Module name.

        Returns:
            Database password.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If GCP unavailable.
        """
        secret_name = f"waddlebot-{module_name}-db-password"
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"

        try:
            from google.cloud import secretmanager

            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            self._log_access("get_db_password", module_name)
            return secret_value
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise SecretNotFoundError(f"Secret not found: {secret_name}") from e
            raise ProviderUnavailableError(f"GCP error: {str(e)}") from e

    def get_secret(self, key: str) -> str:
        """Retrieve arbitrary secret from GCP Secret Manager.

        Key format: secret_name or json:secret_name:field

        Args:
            key: Secret identifier.

        Returns:
            Secret value.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If GCP unavailable.
        """
        if key.startswith("json:"):
            secret_name, field = key[5:].rsplit(":", 1)
        else:
            secret_name = key
            field = None

        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"

        try:
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")

            if field:
                secret_json = json.loads(secret_value)
                value = secret_json.get(field)
                if value is None:
                    raise SecretNotFoundError(f"Field {field} not found in {secret_name}")
                self._log_access("get_secret", key)
                return value
            else:
                self._log_access("get_secret", key)
                return secret_value
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Secret {secret_name} is not valid JSON"
            ) from e
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise SecretNotFoundError(f"Secret not found: {secret_name}") from e
            raise ProviderUnavailableError(f"GCP error: {str(e)}") from e

    def rotate_db_password(self, module_name: str, new_password: str) -> bool:
        """Update database password in GCP Secret Manager.

        Args:
            module_name: Module name.
            new_password: New password.

        Returns:
            True if successful.

        Raises:
            ProviderUnavailableError: If GCP unavailable.
        """
        secret_name = f"waddlebot-{module_name}-db-password"
        name = f"projects/{self.project_id}/secrets/{secret_name}"

        try:
            from google.cloud import secretmanager

            self.client.add_secret_version(
                request={"parent": name, "payload": {"data": new_password.encode()}}
            )
            logger.info("Database password rotated for module=%s", module_name)
            self._log_access("rotate_db_password", module_name)
            return True
        except Exception as e:
            logger.error("Failed to rotate password in GCP: %s", e)
            raise ProviderUnavailableError(f"GCP error: {str(e)}") from e

    def health_check(self) -> bool:
        """Check GCP Secret Manager connectivity.

        Returns:
            True if service is reachable.
        """
        try:
            self.client.list_secrets(request={"parent": f"projects/{self.project_id}"})
            logger.debug("GCP Secret Manager health check passed")
            return True
        except Exception as e:
            logger.warning("GCP health check failed: %s", e)
            return False
