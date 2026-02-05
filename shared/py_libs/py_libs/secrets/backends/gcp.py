"""Google Cloud Secret Manager provider."""

from __future__ import annotations

import logging
from typing import Optional

from py_libs.secrets.base import BaseSecretsProvider, SecretValue

logger = logging.getLogger(__name__)


class GCPSecretsManagerProvider(BaseSecretsProvider):
    """Secrets provider backed by Google Cloud Secret Manager.

    Requires the 'google-cloud-secret-manager' package:
        pip install py_libs[gcp]
    Uses default GCP credential chain (ADC, service account, etc.).
    """

    __slots__ = ("_project_id", "_prefix", "_client")

    def __init__(
        self, project_id: str = "", prefix: str = "/secrets/"
    ) -> None:
        self._project_id = project_id
        self._prefix = prefix.rstrip("/").replace("/", "-")
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from google.cloud import secretmanager
            self._client = secretmanager.SecretManagerServiceClient()
        except ImportError:
            raise ImportError(
                "google-cloud-secret-manager package required. "
                "Install with: pip install py_libs[gcp]"
            )

    def _normalize_name(self, key: str) -> str:
        clean = key.replace("/", "-").strip("-")
        if self._prefix:
            return f"{self._prefix}-{clean}"
        return clean

    def _secret_path(self, name: str) -> str:
        return f"projects/{self._project_id}/secrets/{name}"

    def _version_path(
        self, name: str, version: str = "latest"
    ) -> str:
        return f"{self._secret_path(name)}/versions/{version}"

    def get_secret(self, key: str) -> Optional[SecretValue]:
        self._ensure_client()
        name = self._normalize_name(key)
        try:
            response = self._client.access_secret_version(
                request={"name": self._version_path(name)}
            )
            return SecretValue(
                key=key,
                value=response.payload.data.decode("utf-8"),
                version=response.name.rsplit("/", 1)[-1],
            )
        except Exception as e:
            if "NOT_FOUND" in str(e):
                return None
            raise ConnectionError(
                f"GCP Secret Manager error: {e}"
            ) from e

    def set_secret(
        self, key: str, value: str, metadata: Optional[dict] = None
    ) -> bool:
        self._ensure_client()
        name = self._normalize_name(key)
        parent = f"projects/{self._project_id}"
        try:
            self._client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except Exception as e:
            if "ALREADY_EXISTS" not in str(e):
                raise ConnectionError(
                    f"GCP Secret Manager error: {e}"
                ) from e

        self._client.add_secret_version(
            request={
                "parent": self._secret_path(name),
                "payload": {"data": value.encode("utf-8")},
            }
        )
        return True

    def delete_secret(self, key: str) -> bool:
        self._ensure_client()
        name = self._normalize_name(key)
        try:
            self._client.delete_secret(
                request={"name": self._secret_path(name)}
            )
            return True
        except Exception:
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        self._ensure_client()
        parent = f"projects/{self._project_id}"
        search_prefix = (
            self._normalize_name(prefix) if prefix else self._prefix
        )
        results = []
        for secret in self._client.list_secrets(
            request={"parent": parent}
        ):
            name = secret.name.rsplit("/", 1)[-1]
            if name.startswith(search_prefix):
                results.append(name)
        return results
