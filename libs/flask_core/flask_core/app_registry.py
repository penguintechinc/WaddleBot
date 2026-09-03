"""
App registry
=============

In-memory index of validated :class:`~flask_core.app_manifest.AppManifest`
instances, keyed both by ``app_id`` (unique) and by ``feature`` (many Apps
may implement the same Feature -- see the design doc's ``Apps`` section:
"Two Apps claiming the same Feature is not a conflict; the binding at that
scope picks one.").

Exactly one App per Feature may be marked ``is_default`` -- the shipped
fallback that "cannot be swapped cluster-wide". A second default for the
same Feature is a manifest-authoring bug, not a runtime binding decision,
so it is rejected at registration time rather than resolved silently.

Usage is a module-level singleton (``register`` / ``apps_for_feature`` /
``default_app_for`` / ``get``) backed by a stdlib lock so registration from
multiple event-loop tasks or threads at startup is safe -- App loading is a
startup-time, not per-request, operation, so a coarse lock is sufficient and
never a hot-path bottleneck. Tests that need isolation build their own
:class:`AppRegistry` instance directly rather than sharing the singleton.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from .app_manifest import AppManifest, parse_manifest


class RegistryError(Exception):
    """
    Raised by :class:`AppRegistry` for a bad *registration*, as distinct
    from :class:`~flask_core.app_manifest.ManifestError`'s bad *manifest
    shape*. ``reason`` is a stable machine-checkable code.
    """

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        super().__init__(f"{reason}: {detail}")


REASON_DUPLICATE_APP_ID = "duplicate_app_id"
REASON_DUPLICATE_DEFAULT = "duplicate_default"
REASON_NOT_FOUND = "not_found"


class AppRegistry:
    """
    Loads, validates and indexes App manifests. One instance per process in
    normal operation (see :func:`get_registry`); tests construct additional
    instances freely for isolation.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_id: Dict[str, AppManifest] = {}
        self._by_feature: Dict[str, List[str]] = {}
        self._default_by_feature: Dict[str, str] = {}

    def register(self, manifest: AppManifest) -> AppManifest:
        """Index an already-validated manifest. Raises :class:`RegistryError` on conflict."""
        with self._lock:
            if manifest.app_id in self._by_id:
                raise RegistryError(
                    REASON_DUPLICATE_APP_ID, f"app_id {manifest.app_id!r} already registered"
                )
            if manifest.is_default:
                existing_default = self._default_by_feature.get(manifest.feature)
                if existing_default is not None:
                    raise RegistryError(
                        REASON_DUPLICATE_DEFAULT,
                        f"feature {manifest.feature!r} already has default app "
                        f"{existing_default!r}; cannot also default {manifest.app_id!r}",
                    )
                self._default_by_feature[manifest.feature] = manifest.app_id

            self._by_id[manifest.app_id] = manifest
            self._by_feature.setdefault(manifest.feature, []).append(manifest.app_id)
            return manifest

    def load(self, data: Dict[str, object]) -> AppManifest:
        """Validate a raw manifest dict via :func:`parse_manifest`, then register it."""
        manifest = parse_manifest(data)
        return self.register(manifest)

    def get(self, app_id: str) -> AppManifest:
        """Look up a registered App by id. Raises :class:`RegistryError` if unknown."""
        try:
            return self._by_id[app_id]
        except KeyError:
            raise RegistryError(REASON_NOT_FOUND, f"no App registered with app_id {app_id!r}") from None

    def apps_for_feature(self, feature: str) -> Tuple[AppManifest, ...]:
        """All Apps (default and alternatives) registered against ``feature``, registration order."""
        return tuple(self._by_id[app_id] for app_id in self._by_feature.get(feature, []))

    def all_apps(self) -> Tuple[AppManifest, ...]:
        """Every registered App, registration order -- svc-gateway's own fan-out (`consumes`
        filtering across ALL Features, not one known Feature at a time) needs this; existing
        callers only ever asked "what implements Feature X", never "what exists at all"."""
        return tuple(self._by_id.values())

    def default_app_for(self, feature: str) -> Optional[AppManifest]:
        """The shipped default App for ``feature``, or ``None`` if none is registered."""
        app_id = self._default_by_feature.get(feature)
        return self._by_id[app_id] if app_id is not None else None

    def clear(self) -> None:
        """Drop all registrations. Test-only -- production registries are load-once at startup."""
        with self._lock:
            self._by_id.clear()
            self._by_feature.clear()
            self._default_by_feature.clear()


_registry = AppRegistry()


def get_registry() -> AppRegistry:
    """The process-wide singleton registry."""
    return _registry


def register(manifest: AppManifest) -> AppManifest:
    """Register an already-validated manifest against the singleton registry."""
    return _registry.register(manifest)


def load(data: Dict[str, object]) -> AppManifest:
    """Validate and register a raw manifest dict against the singleton registry."""
    return _registry.load(data)


def apps_for_feature(feature: str) -> Tuple[AppManifest, ...]:
    """All Apps registered against ``feature`` in the singleton registry."""
    return _registry.apps_for_feature(feature)


def all_apps() -> Tuple[AppManifest, ...]:
    """Every App registered in the singleton registry."""
    return _registry.all_apps()


def default_app_for(feature: str) -> Optional[AppManifest]:
    """The shipped default App for ``feature`` in the singleton registry, or ``None``."""
    return _registry.default_app_for(feature)


def get(app_id: str) -> AppManifest:
    """Look up a registered App by id in the singleton registry."""
    return _registry.get(app_id)
