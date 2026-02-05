"""AWS Secrets Manager provider."""

import json
import logging
import os
from typing import Optional

from . import ProviderUnavailableError, SecretNotFoundError
from .base import BaseSecretsProvider

logger = logging.getLogger(__name__)


class AWSSecretsManagerProvider(BaseSecretsProvider):
    """Reads secrets from AWS Secrets Manager.

    Requires:
    - boto3 Python package
    - AWS credentials configured (IAM role, env vars, or ~/.aws/credentials)
    - AWS_REGION environment variable

    Default secret naming: waddlebot/{module_name}/db-password
    """

    def __init__(self) -> None:
        """Initialize AWS Secrets Manager provider."""
        try:
            import boto3
        except ImportError as e:
            raise ImportError(
                "boto3 package required for AWSSecretsManagerProvider. "
                "Install with: pip install py_libs[aws]"
            ) from e

        region = os.getenv("AWS_REGION", "us-east-1")
        self.client = boto3.client("secretsmanager", region_name=region)
        logger.info("AWS Secrets Manager provider initialized for region=%s", region)

    def get_db_password(self, module_name: str) -> str:
        """Retrieve database password from AWS Secrets Manager.

        Secret name: waddlebot/{module_name}/db-password

        Args:
            module_name: Module name.

        Returns:
            Database password.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If AWS unavailable.
        """
        secret_name = f"waddlebot/{module_name}/db-password"
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret = response.get("SecretString") or response.get("SecretBinary")
            if not secret:
                raise SecretNotFoundError(f"Secret {secret_name} is empty")

            self._log_access("get_db_password", module_name)
            return secret
        except self.client.exceptions.ResourceNotFoundException as e:
            raise SecretNotFoundError(f"Secret not found: {secret_name}") from e
        except Exception as e:
            raise ProviderUnavailableError(f"AWS error: {str(e)}") from e

    def get_secret(self, key: str) -> str:
        """Retrieve arbitrary secret from AWS.

        Key format: secret_name or json:secret_name:field

        Args:
            key: Secret identifier.

        Returns:
            Secret value.

        Raises:
            SecretNotFoundError: If not found.
            ProviderUnavailableError: If AWS unavailable.
        """
        # Support JSON field extraction: json:secret_name:field_name
        if key.startswith("json:"):
            secret_name, field = key[5:].rsplit(":", 1)
            try:
                response = self.client.get_secret_value(SecretId=secret_name)
                secret_str = response.get("SecretString")
                if not secret_str:
                    raise SecretNotFoundError(f"Secret {secret_name} is empty")

                secret_json = json.loads(secret_str)
                value = secret_json.get(field)
                if value is None:
                    raise SecretNotFoundError(
                        f"Field {field} not found in {secret_name}"
                    )

                self._log_access("get_secret", key)
                return value
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Secret {secret_name} is not valid JSON"
                ) from e
            except self.client.exceptions.ResourceNotFoundException as e:
                raise SecretNotFoundError(f"Secret not found: {secret_name}") from e
            except Exception as e:
                raise ProviderUnavailableError(f"AWS error: {str(e)}") from e
        else:
            # Simple string secret
            try:
                response = self.client.get_secret_value(SecretId=key)
                secret = response.get("SecretString") or response.get("SecretBinary")
                if not secret:
                    raise SecretNotFoundError(f"Secret {key} is empty")

                self._log_access("get_secret", key)
                return secret
            except self.client.exceptions.ResourceNotFoundException as e:
                raise SecretNotFoundError(f"Secret not found: {key}") from e
            except Exception as e:
                raise ProviderUnavailableError(f"AWS error: {str(e)}") from e

    def rotate_db_password(self, module_name: str, new_password: str) -> bool:
        """Update database password in AWS Secrets Manager.

        Args:
            module_name: Module name.
            new_password: New password.

        Returns:
            True if successful.

        Raises:
            ProviderUnavailableError: If AWS unavailable.
        """
        secret_name = f"waddlebot/{module_name}/db-password"
        try:
            self.client.put_secret_value(SecretId=secret_name, SecretString=new_password)
            logger.info("Database password rotated for module=%s", module_name)
            self._log_access("rotate_db_password", module_name)
            return True
        except Exception as e:
            logger.error("Failed to rotate password in AWS: %s", e)
            raise ProviderUnavailableError(f"AWS error: {str(e)}") from e

    def health_check(self) -> bool:
        """Check AWS Secrets Manager connectivity.

        Returns:
            True if service is reachable.
        """
        try:
            self.client.list_secrets(MaxResults=1)
            logger.debug("AWS Secrets Manager health check passed")
            return True
        except Exception as e:
            logger.warning("AWS health check failed: %s", e)
            return False
