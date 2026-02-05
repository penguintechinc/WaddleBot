"""Secrets provider abstraction for multi-backend credential management.

Supports multiple secret backends:
- Kubernetes Secrets (default)
- HashiCorp Vault
- AWS Secrets Manager
- Google Cloud Secret Manager
- Infisical
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SecretProviderError(Exception):
    """Base exception for secret provider errors."""

    pass


class ProviderUnavailableError(SecretProviderError):
    """Raised when secret backend is unavailable."""

    pass


class SecretNotFoundError(SecretProviderError):
    """Raised when secret key not found in backend."""

    pass


class SecretsProvider:
    """Factory for secrets providers with backend abstraction."""

    _provider: Optional["BaseSecretsProvider"] = None
    _backend: Optional[str] = None

    @classmethod
    def get_provider(cls, backend: Optional[str] = None) -> "BaseSecretsProvider":
        """Get or create secrets provider instance.

        Args:
            backend: Backend type (kubernetes, vault, aws, gcp, infisical).
                    If None, reads SECRETS_BACKEND env var. Defaults to kubernetes.

        Returns:
            Initialized secrets provider instance.

        Raises:
            ValueError: If backend type unknown or unavailable.
        """
        # Allow override via parameter
        if backend is None:
            backend = os.getenv("SECRETS_BACKEND", "kubernetes").lower()

        # Use cached provider if same backend
        if cls._provider is not None and cls._backend == backend:
            return cls._provider

        # Create new provider
        if backend == "kubernetes":
            from .kubernetes_provider import KubernetesSecretsProvider

            cls._provider = KubernetesSecretsProvider()
        elif backend == "vault":
            from .vault_provider import VaultProvider

            cls._provider = VaultProvider()
        elif backend == "aws":
            from .aws_provider import AWSSecretsManagerProvider

            cls._provider = AWSSecretsManagerProvider()
        elif backend == "gcp":
            from .gcp_provider import GCPSecretsManagerProvider

            cls._provider = GCPSecretsManagerProvider()
        elif backend == "infisical":
            from .infisical_provider import InfisicalProvider

            cls._provider = InfisicalProvider()
        else:
            raise ValueError(
                f"Unknown secrets backend: {backend}. "
                "Supported: kubernetes, vault, aws, gcp, infisical"
            )

        cls._backend = backend
        logger.info("Initialized secrets provider: %s", backend)
        return cls._provider

    @classmethod
    def reset(cls) -> None:
        """Reset cached provider (useful for testing)."""
        cls._provider = None
        cls._backend = None


__all__ = [
    "SecretsProvider",
    "SecretProviderError",
    "ProviderUnavailableError",
    "SecretNotFoundError",
]
