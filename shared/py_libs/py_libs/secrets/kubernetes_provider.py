"""Kubernetes Secrets provider for reading secrets from K8s Secret objects."""

import logging
import os
from typing import Optional

from . import ProviderUnavailableError, SecretNotFoundError
from .base import BaseSecretsProvider

logger = logging.getLogger(__name__)


class KubernetesSecretsProvider(BaseSecretsProvider):
    """Reads secrets from Kubernetes Secret objects.

    Requires:
    - kubernetes Python package
    - In-cluster service account token mounted
    - SECRETS_PATH environment variable

    Default secret naming: {SECRETS_PATH}/{module_name}/database-password
    Example: /secrets/db-passwords/twitch_action/database-password
    """

    def __init__(self) -> None:
        """Initialize Kubernetes provider."""
        try:
            from kubernetes import client, config, watch

            self.client = client
            self.config = config
            self.watch = watch
        except ImportError as e:
            raise ImportError(
                "kubernetes package required for KubernetesSecretsProvider. "
                "Install with: pip install py_libs[kubernetes]"
            ) from e

        self.secrets_path = os.getenv("SECRETS_PATH", "/secrets/db-passwords")
        self.namespace = os.getenv("NAMESPACE", "default")

        # Initialize API client (in-cluster config)
        try:
            self.config.load_incluster_config()
            self.v1 = self.client.CoreV1Api()
            logger.info(
                "Kubernetes provider initialized for namespace=%s", self.namespace
            )
        except self.config.ConfigException as e:
            logger.warning(
                "Not running in Kubernetes cluster, using local config: %s", e
            )
            try:
                self.config.load_kube_config()
                self.v1 = self.client.CoreV1Api()
            except Exception as e2:
                logger.error("Failed to load Kubernetes config: %s", e2)
                raise ProviderUnavailableError(
                    "Kubernetes provider unavailable"
                ) from e2

    def get_db_password(self, module_name: str) -> str:
        """Retrieve database password from Kubernetes Secret.

        Args:
            module_name: Module name (e.g., 'twitch_action').

        Returns:
            Database password.

        Raises:
            SecretNotFoundError: If secret not found.
            ProviderUnavailableError: If K8s API unavailable.
        """
        secret_key = f"{module_name}-db-password"
        secret_name = f"waddlebot-{module_name}"

        try:
            secret = self.v1.read_namespaced_secret(
                name=secret_name, namespace=self.namespace
            )
            if secret.data and secret_key in secret.data:
                password = secret.data[secret_key]
                # Kubernetes secrets are base64-encoded in the API
                if isinstance(password, bytes):
                    password = password.decode("utf-8")
                self._log_access("get_db_password", module_name)
                return password

            raise SecretNotFoundError(
                f"Secret key {secret_key} not found in {secret_name}"
            )
        except self.client.rest.ApiException as e:
            if e.status == 404:
                raise SecretNotFoundError(f"Secret {secret_name} not found") from e
            raise ProviderUnavailableError(
                f"Kubernetes API error: {e.reason}"
            ) from e

    def get_secret(self, key: str) -> str:
        """Retrieve arbitrary secret by key.

        Key format: secret_name:data_key
        Example: waddlebot-twitch-action:access-token

        Args:
            key: Secret key in format 'secret_name:data_key'.

        Returns:
            Secret value.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If API unavailable.
        """
        try:
            secret_name, data_key = key.split(":", 1)
        except ValueError as e:
            raise ValueError(
                f"Invalid key format: {key}. Expected 'secret_name:data_key'"
            ) from e

        try:
            secret = self.v1.read_namespaced_secret(
                name=secret_name, namespace=self.namespace
            )
            if secret.data and data_key in secret.data:
                value = secret.data[data_key]
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                self._log_access("get_secret", key)
                return value

            raise SecretNotFoundError(f"Key {data_key} not found in {secret_name}")
        except self.client.rest.ApiException as e:
            if e.status == 404:
                raise SecretNotFoundError(f"Secret {secret_name} not found") from e
            raise ProviderUnavailableError(
                f"Kubernetes API error: {e.reason}"
            ) from e

    def rotate_db_password(self, module_name: str, new_password: str) -> bool:
        """Update database password in Kubernetes Secret.

        Args:
            module_name: Module name.
            new_password: New password value.

        Returns:
            True if successful.

        Raises:
            ProviderUnavailableError: If API unavailable.
        """
        secret_key = f"{module_name}-db-password"
        secret_name = f"waddlebot-{module_name}"

        try:
            secret = self.v1.read_namespaced_secret(
                name=secret_name, namespace=self.namespace
            )
            if secret.data is None:
                secret.data = {}

            secret.data[secret_key] = new_password
            self.v1.patch_namespaced_secret(
                name=secret_name, namespace=self.namespace, body=secret
            )

            logger.info("Database password rotated for module=%s", module_name)
            self._log_access("rotate_db_password", module_name)
            return True
        except self.client.rest.ApiException as e:
            logger.error("Failed to rotate password: %s", e.reason)
            raise ProviderUnavailableError(
                f"Failed to rotate password: {e.reason}"
            ) from e

    def health_check(self) -> bool:
        """Verify Kubernetes API connectivity.

        Returns:
            True if API reachable.
        """
        try:
            self.v1.get_api_resources()
            logger.debug("Kubernetes API health check passed")
            return True
        except Exception as e:
            logger.warning("Kubernetes API health check failed: %s", e)
            return False
