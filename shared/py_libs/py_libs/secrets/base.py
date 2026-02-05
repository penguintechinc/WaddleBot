"""Base class for secrets provider implementations."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseSecretsProvider(ABC):
    """Abstract base class for secrets providers.

    All implementations must provide methods to retrieve and manage secrets
    from their respective backends.
    """

    @abstractmethod
    def get_db_password(self, module_name: str) -> str:
        """Retrieve database password for a module.

        Args:
            module_name: Name of the module (e.g., 'twitch_action', 'slack_action').

        Returns:
            The plaintext database password.

        Raises:
            SecretNotFoundError: If password not found.
            ProviderUnavailableError: If backend unavailable.
        """
        pass

    @abstractmethod
    def get_secret(self, key: str) -> str:
        """Retrieve arbitrary secret by key.

        Args:
            key: Secret key/path (backend-specific format).

        Returns:
            The plaintext secret value.

        Raises:
            SecretNotFoundError: If secret not found.
            ProviderUnavailableError: If backend unavailable.
        """
        pass

    @abstractmethod
    def rotate_db_password(self, module_name: str, new_password: str) -> bool:
        """Store rotated database password.

        Args:
            module_name: Name of the module.
            new_password: New password to store.

        Returns:
            True if rotation successful.

        Raises:
            ProviderUnavailableError: If backend unavailable.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verify backend connectivity and health.

        Returns:
            True if backend is healthy and accessible.
        """
        pass

    def _log_access(self, action: str, key: str) -> None:
        """Log secret access without revealing values.

        Args:
            action: Action type (get, set, rotate, etc.).
            key: Secret key being accessed (safe to log).
        """
        logger.debug("Secrets access: action=%s key=%s", action, key)
