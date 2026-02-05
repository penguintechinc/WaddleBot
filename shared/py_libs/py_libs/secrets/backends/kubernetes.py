"""Kubernetes secrets provider.

Reads secrets from Kubernetes Secret objects via the cluster API.
Default provider for production deployments.
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

from py_libs.secrets.base import BaseSecretsProvider, SecretValue

logger = logging.getLogger(__name__)


class KubernetesSecretsProvider(BaseSecretsProvider):
    """Secrets provider backed by Kubernetes Secrets API.

    Requires the 'kubernetes' package: pip install py_libs[kubernetes]
    Service account must have read access to the target Secret.
    """

    __slots__ = ("_namespace", "_secret_name", "_client", "_api")

    def __init__(
        self,
        namespace: str = "default",
        secret_name: str = "waddlebot-db-passwords",
    ) -> None:
        self._namespace = namespace
        self._secret_name = secret_name
        self._client = None
        self._api = None

    def _ensure_client(self) -> None:
        """Lazy-initialize the Kubernetes client."""
        if self._api is not None:
            return
        try:
            from kubernetes import client, config as k8s_config

            try:
                k8s_config.load_incluster_config()
            except k8s_config.ConfigException:
                k8s_config.load_kube_config()
            self._client = client
            self._api = client.CoreV1Api()
        except ImportError:
            raise ImportError(
                "kubernetes package required. "
                "Install with: pip install py_libs[kubernetes]"
            )

    def _get_secret_data(self) -> dict:
        """Fetch the full Secret object data."""
        self._ensure_client()
        try:
            secret = self._api.read_namespaced_secret(
                self._secret_name, self._namespace
            )
            if secret.data is None:
                return {}
            return {
                k: base64.b64decode(v).decode("utf-8")
                for k, v in secret.data.items()
            }
        except self._client.exceptions.ApiException as e:
            if e.status == 404:
                return {}
            raise ConnectionError(
                f"Kubernetes API error: {e.reason}"
            ) from e

    def get_secret(self, key: str) -> Optional[SecretValue]:
        data = self._get_secret_data()
        lookup_key = key.rsplit("/", 1)[-1]
        value = data.get(lookup_key)
        if value is None:
            return None
        return SecretValue(key=key, value=value)

    def set_secret(
        self, key: str, value: str, metadata: Optional[dict] = None
    ) -> bool:
        self._ensure_client()
        lookup_key = key.rsplit("/", 1)[-1]
        encoded = base64.b64encode(value.encode("utf-8")).decode("utf-8")
        try:
            secret = self._api.read_namespaced_secret(
                self._secret_name, self._namespace
            )
            if secret.data is None:
                secret.data = {}
            secret.data[lookup_key] = encoded
            self._api.patch_namespaced_secret(
                self._secret_name, self._namespace, secret
            )
            return True
        except self._client.exceptions.ApiException as e:
            if e.status == 404:
                body = self._client.V1Secret(
                    metadata=self._client.V1ObjectMeta(
                        name=self._secret_name
                    ),
                    data={lookup_key: encoded},
                )
                self._api.create_namespaced_secret(self._namespace, body)
                return True
            raise ConnectionError(
                f"Kubernetes API error: {e.reason}"
            ) from e

    def delete_secret(self, key: str) -> bool:
        self._ensure_client()
        lookup_key = key.rsplit("/", 1)[-1]
        try:
            secret = self._api.read_namespaced_secret(
                self._secret_name, self._namespace
            )
            if secret.data and lookup_key in secret.data:
                del secret.data[lookup_key]
                self._api.patch_namespaced_secret(
                    self._secret_name, self._namespace, secret
                )
                return True
            return False
        except self._client.exceptions.ApiException:
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        data = self._get_secret_data()
        if not prefix:
            return list(data.keys())
        return [k for k in data if k.startswith(prefix)]
