"""Infisical secrets provider."""

from __future__ import annotations

import logging
from typing import Optional

from py_libs.secrets.base import BaseSecretsProvider, SecretValue

logger = logging.getLogger(__name__)


class InfisicalProvider(BaseSecretsProvider):
    """Secrets provider backed by Infisical.

    Requires the 'infisical-python' package:
        pip install py_libs[infisical]
    """

    __slots__ = (
        "_token", "_site_url", "_project_id", "_environment", "_client",
    )

    def __init__(
        self,
        token: str = "",
        site_url: str = "https://app.infisical.com",
        project_id: str = "",
        environment: str = "dev",
    ) -> None:
        self._token = token
        self._site_url = site_url
        self._project_id = project_id
        self._environment = environment
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from infisical_client import ClientSettings, InfisicalClient
            self._client = InfisicalClient(ClientSettings(
                auth={
                    "universalAuth": {
                        "client_id": "",
                        "client_secret": self._token,
                    },
                },
                site_url=self._site_url,
            ))
        except ImportError:
            raise ImportError(
                "infisical-python package required. "
                "Install with: pip install py_libs[infisical]"
            )

    def _normalize_key(self, key: str) -> str:
        return key.replace("/", "_").replace("-", "_").upper()

    def get_secret(self, key: str) -> Optional[SecretValue]:
        self._ensure_client()
        secret_name = self._normalize_key(key)
        try:
            result = self._client.getSecret({
                "secretName": secret_name,
                "projectId": self._project_id,
                "environment": self._environment,
            })
            if result and result.secret_value:
                return SecretValue(
                    key=key,
                    value=result.secret_value,
                    version=result.version,
                )
            return None
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise ConnectionError(f"Infisical error: {e}") from e

    def set_secret(
        self, key: str, value: str, metadata: Optional[dict] = None
    ) -> bool:
        self._ensure_client()
        secret_name = self._normalize_key(key)
        try:
            self._client.createSecret({
                "secretName": secret_name,
                "secretValue": value,
                "projectId": self._project_id,
                "environment": self._environment,
            })
        except Exception:
            self._client.updateSecret({
                "secretName": secret_name,
                "secretValue": value,
                "projectId": self._project_id,
                "environment": self._environment,
            })
        return True

    def delete_secret(self, key: str) -> bool:
        self._ensure_client()
        secret_name = self._normalize_key(key)
        try:
            self._client.deleteSecret({
                "secretName": secret_name,
                "projectId": self._project_id,
                "environment": self._environment,
            })
            return True
        except Exception:
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        self._ensure_client()
        search_prefix = self._normalize_key(prefix) if prefix else ""
        try:
            results = self._client.listSecrets({
                "projectId": self._project_id,
                "environment": self._environment,
            })
            return [
                s.secret_name for s in results
                if s.secret_name.startswith(search_prefix)
            ]
        except Exception:
            return []
