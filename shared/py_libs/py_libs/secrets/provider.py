"""Secrets provider factory and registry."""

from __future__ import annotations

import logging
import os
from typing import Optional

from py_libs.secrets.base import BaseSecretsProvider

logger = logging.getLogger(__name__)

_provider_instance: Optional[BaseSecretsProvider] = None


class SecretsProvider:
    """Factory for creating secrets provider instances.

    Configuration via environment variables:
        SECRETS_BACKEND: Provider type ('env', 'kubernetes', 'infisical',
                         'vault', 'aws', 'gcp'). Default: 'env'.
        SECRETS_PATH: Path prefix for secrets. Default: '/secrets/'.
    """

    @staticmethod
    def get_provider(backend: Optional[str] = None) -> BaseSecretsProvider:
        """Create or return a cached secrets provider instance.

        Args:
            backend: Override the SECRETS_BACKEND env var.

        Returns:
            Configured BaseSecretsProvider instance.

        Raises:
            ValueError: If the backend type is unknown.
            ImportError: If optional dependencies are missing.
        """
        global _provider_instance

        if _provider_instance is not None and backend is None:
            return _provider_instance

        backend = backend or os.getenv("SECRETS_BACKEND", "env")
        secrets_path = os.getenv("SECRETS_PATH", "/secrets/")

        if backend == "env":
            from py_libs.secrets.backends.env import EnvSecretsProvider
            provider = EnvSecretsProvider(prefix=secrets_path)

        elif backend == "kubernetes":
            from py_libs.secrets.backends.kubernetes import (
                KubernetesSecretsProvider,
            )
            provider = KubernetesSecretsProvider(
                namespace=os.getenv("K8S_NAMESPACE", "default"),
                secret_name=os.getenv(
                    "K8S_SECRET_NAME", "waddlebot-db-passwords"
                ),
            )

        elif backend == "infisical":
            from py_libs.secrets.backends.infisical import InfisicalProvider
            provider = InfisicalProvider(
                token=os.getenv("INFISICAL_TOKEN", ""),
                site_url=os.getenv(
                    "INFISICAL_SITE_URL", "https://app.infisical.com"
                ),
                project_id=os.getenv("INFISICAL_PROJECT_ID", ""),
                environment=os.getenv("INFISICAL_ENV", "dev"),
            )

        elif backend == "vault":
            from py_libs.secrets.backends.vault import VaultProvider
            provider = VaultProvider(
                url=os.getenv("VAULT_ADDR", "http://127.0.0.1:8200"),
                token=os.getenv("VAULT_TOKEN", ""),
                mount_point=os.getenv("VAULT_MOUNT", "secret"),
                path_prefix=secrets_path,
            )

        elif backend == "aws":
            from py_libs.secrets.backends.aws import AWSSecretsManagerProvider
            provider = AWSSecretsManagerProvider(
                region=os.getenv("AWS_REGION", "us-east-1"),
                prefix=secrets_path,
            )

        elif backend == "gcp":
            from py_libs.secrets.backends.gcp import GCPSecretsManagerProvider
            provider = GCPSecretsManagerProvider(
                project_id=os.getenv("GCP_PROJECT_ID", ""),
                prefix=secrets_path,
            )

        else:
            raise ValueError(
                f"Unknown secrets backend: {backend!r}. "
                f"Supported: env, kubernetes, infisical, vault, aws, gcp"
            )

        if backend != "env":
            logger.info("Secrets provider initialized: %s", backend)

        _provider_instance = provider
        return provider


def get_secrets_provider(
    backend: Optional[str] = None,
) -> BaseSecretsProvider:
    """Convenience function to get the configured secrets provider."""
    return SecretsProvider.get_provider(backend)
