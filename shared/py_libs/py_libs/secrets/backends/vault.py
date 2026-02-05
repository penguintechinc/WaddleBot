"""HashiCorp Vault secrets provider."""

from __future__ import annotations

import logging
from typing import Optional

from py_libs.secrets.base import BaseSecretsProvider, SecretValue

logger = logging.getLogger(__name__)


class VaultProvider(BaseSecretsProvider):
    """Secrets provider backed by HashiCorp Vault KV v2 engine.

    Requires the 'hvac' package: pip install py_libs[vault]
    """

    __slots__ = ("_url", "_token", "_mount_point", "_path_prefix", "_client")

    def __init__(
        self,
        url: str = "http://127.0.0.1:8200",
        token: str = "",
        mount_point: str = "secret",
        path_prefix: str = "/secrets/",
    ) -> None:
        self._url = url
        self._token = token
        self._mount_point = mount_point
        self._path_prefix = path_prefix.rstrip("/")
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import hvac
            self._client = hvac.Client(url=self._url, token=self._token)
            if not self._client.is_authenticated():
                raise PermissionError("Vault authentication failed")
        except ImportError:
            raise ImportError(
                "hvac package required. Install with: pip install py_libs[vault]"
            )

    def _normalize_path(self, key: str) -> str:
        return key.replace(self._path_prefix + "/", "").replace("/", "-")

    def get_secret(self, key: str) -> Optional[SecretValue]:
        self._ensure_client()
        path = self._normalize_path(key)
        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self._mount_point
            )
            data = response["data"]["data"]
            version = str(response["data"]["metadata"]["version"])
            return SecretValue(
                key=key,
                value=data.get("value", ""),
                version=version,
                metadata=data,
            )
        except Exception as e:
            if "404" in str(e):
                return None
            raise ConnectionError(f"Vault error: {e}") from e

    def set_secret(
        self, key: str, value: str, metadata: Optional[dict] = None
    ) -> bool:
        self._ensure_client()
        path = self._normalize_path(key)
        data = {"value": value}
        if metadata:
            data.update(metadata)
        self._client.secrets.kv.v2.create_or_update_secret(
            path=path, secret=data, mount_point=self._mount_point
        )
        return True

    def delete_secret(self, key: str) -> bool:
        self._ensure_client()
        path = self._normalize_path(key)
        try:
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path, mount_point=self._mount_point
            )
            return True
        except Exception:
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        self._ensure_client()
        path = self._normalize_path(prefix) if prefix else ""
        try:
            response = self._client.secrets.kv.v2.list_secrets(
                path=path, mount_point=self._mount_point
            )
            return response["data"]["keys"]
        except Exception:
            return []
