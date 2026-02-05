"""AWS Secrets Manager provider."""

from __future__ import annotations

import json
import logging
from typing import Optional

from py_libs.secrets.base import BaseSecretsProvider, SecretValue

logger = logging.getLogger(__name__)


class AWSSecretsManagerProvider(BaseSecretsProvider):
    """Secrets provider backed by AWS Secrets Manager.

    Requires the 'boto3' package: pip install py_libs[aws]
    Uses default AWS credential chain (env vars, IAM role, config file).
    """

    __slots__ = ("_region", "_prefix", "_client")

    def __init__(
        self, region: str = "us-east-1", prefix: str = "/secrets/"
    ) -> None:
        self._region = region
        self._prefix = prefix.rstrip("/")
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import boto3
            self._client = boto3.client(
                "secretsmanager", region_name=self._region
            )
        except ImportError:
            raise ImportError(
                "boto3 package required. Install with: pip install py_libs[aws]"
            )

    def _normalize_name(self, key: str) -> str:
        return f"{self._prefix}/{key}".replace("//", "/")

    def get_secret(self, key: str) -> Optional[SecretValue]:
        self._ensure_client()
        name = self._normalize_name(key)
        try:
            response = self._client.get_secret_value(SecretId=name)
            value = response["SecretString"]
            try:
                parsed = json.loads(value)
                value = parsed.get("value", value)
            except (json.JSONDecodeError, AttributeError):
                pass
            return SecretValue(
                key=key,
                value=value,
                version=response.get("VersionId"),
            )
        except self._client.exceptions.ResourceNotFoundException:
            return None
        except Exception as e:
            raise ConnectionError(
                f"AWS Secrets Manager error: {e}"
            ) from e

    def set_secret(
        self, key: str, value: str, metadata: Optional[dict] = None
    ) -> bool:
        self._ensure_client()
        name = self._normalize_name(key)
        secret_data = json.dumps({"value": value, **(metadata or {})})
        try:
            self._client.put_secret_value(
                SecretId=name, SecretString=secret_data
            )
        except self._client.exceptions.ResourceNotFoundException:
            self._client.create_secret(Name=name, SecretString=secret_data)
        return True

    def delete_secret(self, key: str) -> bool:
        self._ensure_client()
        name = self._normalize_name(key)
        try:
            self._client.delete_secret(
                SecretId=name, ForceDeleteWithoutRecovery=True
            )
            return True
        except self._client.exceptions.ResourceNotFoundException:
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        self._ensure_client()
        search_prefix = self._normalize_name(prefix)
        results = []
        paginator = self._client.get_paginator("list_secrets")
        for page in paginator.paginate(
            Filters=[{"Key": "name", "Values": [search_prefix]}]
        ):
            for secret in page.get("SecretList", []):
                results.append(secret["Name"])
        return results
