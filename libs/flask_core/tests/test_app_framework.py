"""
App framework tests
=====================

Covers Task 1.2 (manifest schema + registry) and Task 1.3 (binding
resolution ladder) of docs/plans/2026-08-26-v3-scbm-apps-design.md.

Every reject reason and every precedence rung has a paired test proving
both the accept and the reject/lower-precedence path, so a check that
silently stopped firing would fail here rather than just never firing in
production.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import pytest

from flask_core.app_binding import (
    AppInstallation,
    BindingError,
    InstallationLookup,
    resolve_app,
)
from flask_core.app_manifest import (
    REASON_BAD_SEMVER,
    REASON_FEATURE_PREFIX_MISMATCH,
    REASON_NOT_NAMESPACED,
    REASON_UNKNOWN_MODULE,
    AppManifest,
    ManifestError,
    parse_manifest,
)
from flask_core.app_registry import AppRegistry, RegistryError

VALID_MANIFEST: Dict[str, object] = {
    "app_id": "waddles.bot.shoutout.default",
    "name": "Shoutout (default)",
    "version": "1.0.0",
    "feature": "waddles.bot.shoutout",
    "module": "bot",
    "provider": "builtin",
    "surfaces": ["process", "action"],
    "permissions": ["bot.command:write"],
    "config_schema": {"type": "object"},
    "is_default": True,
}


def manifest(**overrides: object) -> Dict[str, object]:
    """A fresh copy of VALID_MANIFEST with the given field overrides."""
    data = dict(VALID_MANIFEST)
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# 1.2 -- manifest schema
# ---------------------------------------------------------------------------
class TestParseManifestAccept:
    def test_valid_manifest_parses_to_app_manifest(self) -> None:
        result = parse_manifest(manifest())
        assert isinstance(result, AppManifest)
        assert result.app_id == "waddles.bot.shoutout.default"
        assert result.feature == "waddles.bot.shoutout"
        assert result.module == "bot"
        assert result.provider == "builtin"
        assert result.surfaces == ("process", "action")
        assert result.permissions == ("bot.command:write",)
        assert result.is_default is True

    def test_third_party_app_with_different_id_and_not_default(self) -> None:
        result = parse_manifest(
            manifest(
                app_id="waddles.bot.shoutout.acme-pro",
                name="Acme Shoutout Pro",
                version="2.3.1-rc.1+build.7",
                provider="thirdparty",
                is_default=False,
            )
        )
        assert result.app_id == "waddles.bot.shoutout.acme-pro"
        assert result.provider == "thirdparty"
        assert result.is_default is False


class TestParseManifestReject:
    """Each case exercises exactly one REASON_* code from app_manifest.py."""

    def test_bad_semver_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(version="v1.0"))
        assert excinfo.value.reason == REASON_BAD_SEMVER

    def test_bad_semver_rejects_leading_zero(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(version="1.02.0"))
        assert excinfo.value.reason == REASON_BAD_SEMVER

    def test_non_namespaced_app_id_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(app_id="shoutout-default"))
        assert excinfo.value.reason == REASON_NOT_NAMESPACED

    def test_non_namespaced_app_id_missing_waddles_prefix_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(app_id="bot.shoutout.default.extra"))
        assert excinfo.value.reason == REASON_NOT_NAMESPACED

    def test_unknown_module_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(module="widgets"))
        assert excinfo.value.reason == REASON_UNKNOWN_MODULE

    def test_app_id_feature_prefix_mismatch_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(feature="waddles.bot.raid"))
        assert excinfo.value.reason == REASON_FEATURE_PREFIX_MISMATCH

    def test_app_id_feature_prefix_mismatch_across_modules_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(
                manifest(
                    app_id="waddles.social.shoutout.default",
                    feature="waddles.bot.shoutout",
                    module="social",
                )
            )
        assert excinfo.value.reason == REASON_FEATURE_PREFIX_MISMATCH


# ---------------------------------------------------------------------------
# 1.2 -- registry
# ---------------------------------------------------------------------------
class TestAppRegistry:
    def test_register_indexes_by_id_and_feature(self) -> None:
        registry = AppRegistry()
        default = parse_manifest(manifest())
        alt = parse_manifest(
            manifest(app_id="waddles.bot.shoutout.acme-pro", provider="thirdparty", is_default=False)
        )
        registry.register(default)
        registry.register(alt)

        assert registry.get("waddles.bot.shoutout.default") is default
        assert set(a.app_id for a in registry.apps_for_feature("waddles.bot.shoutout")) == {
            "waddles.bot.shoutout.default",
            "waddles.bot.shoutout.acme-pro",
        }
        assert registry.default_app_for("waddles.bot.shoutout") is default

    def test_get_unknown_app_id_raises_registry_error(self) -> None:
        registry = AppRegistry()
        with pytest.raises(RegistryError):
            registry.get("waddles.bot.shoutout.nonexistent")

    def test_apps_for_feature_with_no_apps_returns_empty_tuple(self) -> None:
        registry = AppRegistry()
        assert registry.apps_for_feature("waddles.bot.shoutout") == ()

    def test_default_app_for_with_no_default_returns_none(self) -> None:
        registry = AppRegistry()
        alt = parse_manifest(
            manifest(app_id="waddles.bot.shoutout.acme-pro", provider="thirdparty", is_default=False)
        )
        registry.register(alt)
        assert registry.default_app_for("waddles.bot.shoutout") is None

    def test_duplicate_app_id_raises_registry_error(self) -> None:
        registry = AppRegistry()
        registry.register(parse_manifest(manifest(is_default=False)))
        with pytest.raises(RegistryError):
            registry.register(parse_manifest(manifest(is_default=False)))

    def test_duplicate_default_for_same_feature_raises_registry_error(self) -> None:
        registry = AppRegistry()
        registry.register(parse_manifest(manifest(is_default=True)))
        second_default = parse_manifest(
            manifest(app_id="waddles.bot.shoutout.acme-pro", provider="thirdparty", is_default=True)
        )
        with pytest.raises(RegistryError):
            registry.register(second_default)


# ---------------------------------------------------------------------------
# 1.3 -- binding resolution
# ---------------------------------------------------------------------------
class FakeInstallations:
    """In-memory InstallationLookup fake -- test double for app_installations."""

    def __init__(self, rows: List[AppInstallation]) -> None:
        self._rows = rows

    async def find(
        self, feature: str, *, tenant: str, community: Optional[int]
    ) -> Sequence[AppInstallation]:
        return [
            row
            for row in self._rows
            if row.feature == feature
            and row.tenant_id == tenant
            and (row.community_id is None or row.community_id == community)
        ]


FEATURE = "waddles.bot.shoutout"


def _registry_with_default() -> AppRegistry:
    registry = AppRegistry()
    registry.register(parse_manifest(manifest(is_default=True)))
    registry.register(
        parse_manifest(
            manifest(app_id="waddles.bot.shoutout.acme-pro", provider="thirdparty", is_default=False)
        )
    )
    registry.register(
        parse_manifest(
            manifest(app_id="waddles.bot.shoutout.beta-app", provider="thirdparty", is_default=False)
        )
    )
    return registry


class TestResolveAppBindingLadder:
    async def test_community_binding_wins_over_tenant_binding_and_default(self) -> None:
        registry = _registry_with_default()
        installations = FakeInstallations(
            [
                AppInstallation(
                    tenant_id="acme", community_id=None, feature=FEATURE,
                    app_id="waddles.bot.shoutout.beta-app",
                ),
                AppInstallation(
                    tenant_id="acme", community_id=42, feature=FEATURE,
                    app_id="waddles.bot.shoutout.acme-pro",
                ),
            ]
        )
        result = await resolve_app(
            FEATURE, tenant="acme", community=42, installations=installations, registry=registry
        )
        assert result.app_id == "waddles.bot.shoutout.acme-pro"

    async def test_tenant_binding_wins_over_default_when_no_community_binding(self) -> None:
        registry = _registry_with_default()
        installations = FakeInstallations(
            [
                AppInstallation(
                    tenant_id="acme", community_id=None, feature=FEATURE,
                    app_id="waddles.bot.shoutout.beta-app",
                ),
            ]
        )
        result = await resolve_app(
            FEATURE, tenant="acme", community=42, installations=installations, registry=registry
        )
        assert result.app_id == "waddles.bot.shoutout.beta-app"

    async def test_tenant_binding_applies_when_community_is_none(self) -> None:
        registry = _registry_with_default()
        installations = FakeInstallations(
            [
                AppInstallation(
                    tenant_id="acme", community_id=None, feature=FEATURE,
                    app_id="waddles.bot.shoutout.beta-app",
                ),
            ]
        )
        result = await resolve_app(
            FEATURE, tenant="acme", community=None, installations=installations, registry=registry
        )
        assert result.app_id == "waddles.bot.shoutout.beta-app"

    async def test_falls_back_to_default_when_no_binding(self) -> None:
        registry = _registry_with_default()
        installations = FakeInstallations([])
        result = await resolve_app(
            FEATURE, tenant="acme", community=42, installations=installations, registry=registry
        )
        assert result.app_id == "waddles.bot.shoutout.default"
        assert result.is_default is True

    async def test_disabled_community_binding_is_skipped_in_favour_of_tenant_binding(self) -> None:
        registry = _registry_with_default()
        installations = FakeInstallations(
            [
                AppInstallation(
                    tenant_id="acme", community_id=42, feature=FEATURE,
                    app_id="waddles.bot.shoutout.acme-pro", enabled=False,
                ),
                AppInstallation(
                    tenant_id="acme", community_id=None, feature=FEATURE,
                    app_id="waddles.bot.shoutout.beta-app",
                ),
            ]
        )
        result = await resolve_app(
            FEATURE, tenant="acme", community=42, installations=installations, registry=registry
        )
        assert result.app_id == "waddles.bot.shoutout.beta-app"

    async def test_community_binding_for_a_different_community_does_not_apply(self) -> None:
        registry = _registry_with_default()
        installations = FakeInstallations(
            [
                AppInstallation(
                    tenant_id="acme", community_id=99, feature=FEATURE,
                    app_id="waddles.bot.shoutout.acme-pro",
                ),
            ]
        )
        result = await resolve_app(
            FEATURE, tenant="acme", community=42, installations=installations, registry=registry
        )
        assert result.app_id == "waddles.bot.shoutout.default"

    async def test_raises_binding_error_when_no_binding_and_no_default(self) -> None:
        registry = AppRegistry()
        registry.register(
            parse_manifest(
                manifest(app_id="waddles.bot.shoutout.acme-pro", provider="thirdparty", is_default=False)
            )
        )
        installations = FakeInstallations([])
        with pytest.raises(BindingError):
            await resolve_app(
                FEATURE, tenant="acme", community=42, installations=installations, registry=registry
            )
