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

from typing import Dict, List, Optional, Sequence, cast

import pytest

from flask_core.app_binding import (
    AppInstallation,
    BindingError,
    InstallationLookup,
    resolve_app,
)
from flask_core.app_manifest import (
    KNOWN_SURFACES,
    REASON_BAD_PLATFORM_COMPAT_SEMVER,
    REASON_BAD_SEMVER,
    REASON_FEATURE_PREFIX_MISMATCH,
    REASON_INVALID_COMPAT_APP_ID,
    REASON_INVALID_EXECUTION_MODEL,
    REASON_INVALID_PROVIDER,
    REASON_MISSING_FIELD,
    REASON_NOT_NAMESPACED,
    REASON_PRESENTATION_HAS_SCRIPT_ENTRYPOINT,
    REASON_PRESENTATION_MISSING_HTML_ENTRYPOINT,
    REASON_SCRIPT_STAGE_HAS_HTML_ENTRYPOINT,
    REASON_UNKNOWN_MODULE,
    REASON_UNKNOWN_SURFACE,
    AppManifest,
    ManifestError,
    PlatformCompat,
    StageSpec,
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

    def test_missing_required_field_rejected(self) -> None:
        data = manifest()
        del data["name"]
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(data)
        assert excinfo.value.reason == REASON_MISSING_FIELD

    def test_empty_string_field_rejected_as_missing(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(provider=""))
        assert excinfo.value.reason == REASON_MISSING_FIELD

    def test_non_namespaced_feature_rejected(self) -> None:
        """`feature` itself must be `waddles.<module>.<feature>` -- distinct
        from `app_id`'s own namespacing check (REASON_NOT_NAMESPACED is
        shared, but this exercises the `feature`-field regex, not the
        `app_id`-field regex)."""
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(app_id="waddles.bot.shoutout.default", feature="bot.shoutout"))
        assert excinfo.value.reason == REASON_NOT_NAMESPACED

    def test_invalid_provider_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(provider="self-hosted"))
        assert excinfo.value.reason == REASON_INVALID_PROVIDER

    def test_unknown_surface_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(manifest(surfaces=["ingest", "publish"]))
        assert excinfo.value.reason == REASON_UNKNOWN_SURFACE


# ---------------------------------------------------------------------------
# C1 -- App Bundle SDK manifest schema extensions
# (docs/plans/2026-08-31-app-bundle-sdk-design.md §3, §3.2, §3.4, §3.5)
# ---------------------------------------------------------------------------
STAGES_MANIFEST: Dict[str, object] = {
    "app_id": "waddles.bot.giveaway.classic",
    "name": "Giveaway Classic",
    "version": "1.0.0",
    "feature": "waddles.bot.giveaway",
    "module": "bot",
    "provider": "builtin",
    "requires_scopes": ["bot.command:write"],
    "execution_model": "native",
    "compatible_with": ["waddles.bot.giveaway.raffle"],
    "incompatible_with": ["waddles.bot.giveaway.legacy"],
    "platform_compatibility": {
        "tested_with": "v3.0.x",
        "min_version": "3.0.0",
        "max_version": "3.999.999",
    },
    "stages": {
        "ingest": {
            "entrypoint": "ingest/handler.py:on_event",
            "consumes": [],
            "produces": ["giveaway.entry_detected"],
            "config": "ingest/config.yaml",
            "spec": "ingest/spec.yaml",
        },
        "process": {
            "entrypoint": "process/handler.py:on_event",
            "consumes": ["giveaway.entry_detected"],
            "produces": ["giveaway.winner_selected"],
            "config": "process/config.yaml",
            "spec": "process/spec.yaml",
        },
        "action": {
            "entrypoint": "action/handler.py:on_event",
            "consumes": ["giveaway.winner_selected"],
            "produces": [],
            "config": "action/config.yaml",
            "spec": "action/spec.yaml",
        },
    },
}


def stages_manifest(**overrides: object) -> Dict[str, object]:
    """A fresh copy of STAGES_MANIFEST with the given field overrides."""
    data = dict(STAGES_MANIFEST)
    data.update(overrides)
    return data


class TestParseManifestStagesAccept:
    def test_full_stages_manifest_parses(self) -> None:
        result = parse_manifest(stages_manifest())
        assert isinstance(result, AppManifest)
        assert result.execution_model == "native"
        assert result.compatible_with == ("waddles.bot.giveaway.raffle",)
        assert result.incompatible_with == ("waddles.bot.giveaway.legacy",)
        assert result.platform_compatibility == PlatformCompat(
            tested_with="v3.0.x", min_version="3.0.0", max_version="3.999.999"
        )

    def test_surfaces_derived_from_stages_keys(self) -> None:
        result = parse_manifest(stages_manifest())
        assert result.surfaces == ("ingest", "process", "action")

    def test_stage_specs_compiled_with_entrypoint_and_streams(self) -> None:
        result = parse_manifest(stages_manifest())
        assert result.stage_specs["ingest"] == StageSpec(
            entrypoint="ingest/handler.py:on_event",
            consumes=(),
            produces=("giveaway.entry_detected",),
            config="ingest/config.yaml",
            spec="ingest/spec.yaml",
        )
        assert result.stage_specs["process"].consumes == ("giveaway.entry_detected",)
        assert result.stage_specs["action"].produces == ()

    def test_requires_scopes_alias_populates_permissions(self) -> None:
        result = parse_manifest(stages_manifest())
        assert result.permissions == ("bot.command:write",)

    def test_legacy_permissions_key_still_populates_permissions(self) -> None:
        """The `requires_scopes` alias is additive -- the pre-existing
        `permissions` raw key must keep working when `requires_scopes` is
        absent, independent of the `stages` map."""
        data = stages_manifest()
        del data["requires_scopes"]
        data["permissions"] = ["bot.command:write"]
        result = parse_manifest(data)
        assert result.permissions == ("bot.command:write",)

    def test_thirdparty_stage_without_entrypoint_parses(self) -> None:
        data = stages_manifest(
            execution_model="thirdparty",
            stages={
                "action": {
                    "execution_model": "thirdparty",
                    "communication_model": "webhook_push",
                    "webhook_url": "https://vendor.example.com/hook",
                    "secret_ref": "${SECRET:vendor_hmac}",
                    "timeout_ms": 5000,
                    "consumes": ["giveaway.winner_selected"],
                    "produces": [],
                },
            },
        )
        result = parse_manifest(data)
        action_spec = result.stage_specs["action"]
        assert action_spec.entrypoint is None
        assert action_spec.execution_model == "thirdparty"
        assert action_spec.communication_model == "webhook_push"
        assert action_spec.webhook_url == "https://vendor.example.com/hook"
        assert action_spec.secret_ref == "${SECRET:vendor_hmac}"
        assert action_spec.timeout_ms == 5000
        assert result.surfaces == ("action",)

    def test_thirdparty_stage_rest_pull_uses_api_base_url(self) -> None:
        data = stages_manifest(
            stages={
                "action": {
                    "execution_model": "thirdparty",
                    "communication_model": "rest_pull",
                    "api_base_url": "https://vendor.example.com/api",
                    "secret_ref": "${SECRET:vendor_api_key}",
                    "timeout_ms": 3000,
                    "consumes": ["giveaway.winner_selected"],
                    "produces": [],
                },
            },
        )
        result = parse_manifest(data)
        action_spec = result.stage_specs["action"]
        assert action_spec.communication_model == "rest_pull"
        assert action_spec.api_base_url == "https://vendor.example.com/api"

    def test_manifest_without_stages_or_new_fields_still_parses(self) -> None:
        """Defaults for every new field when a manifest declares none of
        them -- the pre-C1 shape (see VALID_MANIFEST)."""
        result = parse_manifest(manifest())
        assert result.stage_specs == {}
        assert result.execution_model == "native"
        assert result.compatible_with == ()
        assert result.incompatible_with == ()
        assert result.platform_compatibility == PlatformCompat()


class TestParseManifestStagesReject:
    """Each case exercises exactly one new REASON_* code -- fail-first:
    reverting the corresponding parse_manifest check makes each of these
    fail (verified manually, see task report)."""

    def test_invalid_execution_model_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(stages_manifest(execution_model="hybrid"))
        assert excinfo.value.reason == REASON_INVALID_EXECUTION_MODEL

    def test_bad_platform_compat_min_version_rejected(self) -> None:
        data = stages_manifest()
        compat = cast(Dict[str, object], data["platform_compatibility"])
        data["platform_compatibility"] = {**compat, "min_version": "v3.0"}
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(data)
        assert excinfo.value.reason == REASON_BAD_PLATFORM_COMPAT_SEMVER

    def test_bad_platform_compat_max_version_rejected(self) -> None:
        data = stages_manifest()
        compat = cast(Dict[str, object], data["platform_compatibility"])
        data["platform_compatibility"] = {**compat, "max_version": "not-semver"}
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(data)
        assert excinfo.value.reason == REASON_BAD_PLATFORM_COMPAT_SEMVER

    def test_invalid_compatible_with_app_id_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(stages_manifest(compatible_with=["not-a-namespaced-id"]))
        assert excinfo.value.reason == REASON_INVALID_COMPAT_APP_ID

    def test_invalid_incompatible_with_app_id_rejected(self) -> None:
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(stages_manifest(incompatible_with=["also-bad"]))
        assert excinfo.value.reason == REASON_INVALID_COMPAT_APP_ID

    def test_unknown_stage_name_in_stages_map_rejected(self) -> None:
        data = stages_manifest(stages={"publish": {"entrypoint": "x.py:f"}})
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(data)
        assert excinfo.value.reason == REASON_UNKNOWN_SURFACE


# ---------------------------------------------------------------------------
# App Bundle SDK spec §3.2a -- presentation component (4th bundle surface)
#
# A per-community HTML/JS overlay (e.g. a giveaway wheel) rendered
# client-side in an OBS browser source by svc-presentation -- not an async
# event script like ingest/process/action. No `entrypoint`; instead
# `html_entrypoint`/`assets`/`browser_source_path` describe the overlay.
# ---------------------------------------------------------------------------
_VALID_PRESENTATION_STAGE: Dict[str, object] = {
    "html_entrypoint": "presentation/overlay.html",
    "assets": ["presentation/overlay.js", "presentation/overlay.css"],
    "browser_source_path": "/presentation/waddles.bot.giveaway.classic",
    "consumes": ["giveaway.winner_selected"],
}


def stages_manifest_with_presentation(presentation: Dict[str, object]) -> Dict[str, object]:
    """A copy of STAGES_MANIFEST with a `presentation` entry added to `stages`
    (on top of the existing ingest/process/action entries)."""
    data = stages_manifest()
    stages = dict(cast(Dict[str, object], data["stages"]))
    stages["presentation"] = presentation
    data["stages"] = stages
    return data


class TestParseManifestPresentationAccept:
    def test_manifest_with_presentation_stage_parses(self) -> None:
        data = stages_manifest_with_presentation(_VALID_PRESENTATION_STAGE)
        result = parse_manifest(data)
        presentation_spec = result.stage_specs["presentation"]
        assert presentation_spec.entrypoint is None
        assert presentation_spec.html_entrypoint == "presentation/overlay.html"
        assert presentation_spec.assets == (
            "presentation/overlay.js",
            "presentation/overlay.css",
        )
        assert presentation_spec.browser_source_path == (
            "/presentation/waddles.bot.giveaway.classic"
        )
        assert presentation_spec.consumes == ("giveaway.winner_selected",)

    def test_surfaces_derived_includes_presentation(self) -> None:
        data = stages_manifest_with_presentation(_VALID_PRESENTATION_STAGE)
        result = parse_manifest(data)
        assert result.surfaces == ("ingest", "process", "action", "presentation")


class TestParseManifestPresentationReject:
    """Each case fail-first: verified against a version of app_manifest.py
    with the corresponding presentation/script-stage check reverted before
    landing (see PR description for the mutation log)."""

    def test_presentation_stage_without_html_entrypoint_rejected(self) -> None:
        bad = dict(_VALID_PRESENTATION_STAGE)
        del bad["html_entrypoint"]
        data = stages_manifest_with_presentation(bad)
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(data)
        assert excinfo.value.reason == REASON_PRESENTATION_MISSING_HTML_ENTRYPOINT

    def test_presentation_stage_with_script_entrypoint_rejected(self) -> None:
        bad = dict(_VALID_PRESENTATION_STAGE)
        bad["entrypoint"] = "presentation/handler.py:on_event"
        data = stages_manifest_with_presentation(bad)
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(data)
        assert excinfo.value.reason == REASON_PRESENTATION_HAS_SCRIPT_ENTRYPOINT

    def test_script_stage_with_html_entrypoint_rejected(self) -> None:
        data = stages_manifest()
        stages = dict(cast(Dict[str, object], data["stages"]))
        action = dict(cast(Dict[str, object], stages["action"]))
        action["html_entrypoint"] = "action/overlay.html"
        stages["action"] = action
        data["stages"] = stages
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(data)
        assert excinfo.value.reason == REASON_SCRIPT_STAGE_HAS_HTML_ENTRYPOINT


class TestParseManifestBackwardCompat:
    """Every existing default-app dict (five modules' features.py) must
    keep parsing unchanged under the C1 schema extension -- none of them
    use `stages`/`requires_scopes`/`execution_model`/etc, only the
    pre-existing `surfaces`/`permissions` shape."""

    def test_real_bot_module_default_app_def_still_parses(self) -> None:
        from bot_module.features import _DEFAULT_APP_DEFS

        raw = dict(_DEFAULT_APP_DEFS[0])
        assert raw["app_id"] == "waddles.bot.shoutout.default"
        assert "stages" not in raw
        assert "requires_scopes" not in raw

        result = parse_manifest(raw)
        assert result.app_id == "waddles.bot.shoutout.default"
        assert result.surfaces == ("process", "action")
        assert result.permissions == ("bot.command:write",)
        assert result.stage_specs == {}
        assert result.execution_model == "native"
        assert result.platform_compatibility == PlatformCompat()

    def test_presentation_surface_added_without_breaking_existing_manifests(self) -> None:
        """KNOWN_SURFACES gained `presentation` (4th bundle surface, §3.2a)
        alongside the original three -- an existing manifest that never
        declares it keeps parsing to the same `surfaces` tuple as before."""
        assert "presentation" in KNOWN_SURFACES
        assert KNOWN_SURFACES >= {"ingest", "process", "action"}

        result = parse_manifest(manifest())
        assert result.surfaces == ("process", "action")
        assert "presentation" not in result.stage_specs

    def test_real_bot_module_all_default_apps_still_build(self) -> None:
        """build_default_apps() -- the module's own parse_manifest()
        call-site -- must still succeed end to end, not just a single raw
        dict handed directly to parse_manifest()."""
        from bot_module.features import build_default_apps

        manifests = build_default_apps()
        assert len(manifests) == 4
        assert {m.app_id for m in manifests} == {
            "waddles.bot.shoutout.default",
            "waddles.bot.commands.default",
            "waddles.bot.connectors.default",
            "waddles.bot.interactions.default",
        }


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

    def test_load_validates_raw_dict_then_registers(self) -> None:
        """`load()` is the parse_manifest()+register() convenience path used
        when reading manifests from disk/DB rather than already-validated
        AppManifest instances."""
        registry = AppRegistry()
        result = registry.load(manifest())
        assert isinstance(result, AppManifest)
        assert registry.get("waddles.bot.shoutout.default") is result

    def test_load_rejects_invalid_raw_dict_without_registering(self) -> None:
        registry = AppRegistry()
        with pytest.raises(ManifestError):
            registry.load(manifest(version="not-semver"))
        assert registry.apps_for_feature("waddles.bot.shoutout") == ()

    def test_clear_empties_registry(self) -> None:
        registry = AppRegistry()
        registry.register(parse_manifest(manifest(is_default=True)))
        registry.clear()
        assert registry.apps_for_feature("waddles.bot.shoutout") == ()
        assert registry.default_app_for("waddles.bot.shoutout") is None
        with pytest.raises(RegistryError):
            registry.get("waddles.bot.shoutout.default")


class TestAppRegistrySingletonModuleFunctions:
    """The module-level `register`/`load`/`apps_for_feature`/`default_app_for`/
    `get` functions are thin delegations to the process-wide singleton
    (`get_registry()`) -- exercised here directly rather than only through
    `AppRegistry` instances, since a drift between the two call shapes would
    otherwise go uncaught."""

    def test_module_functions_delegate_to_singleton(self) -> None:
        from flask_core import app_registry as app_registry_module

        registry = app_registry_module.get_registry()
        registry.clear()
        try:
            registered = app_registry_module.register(parse_manifest(manifest()))
            assert app_registry_module.get("waddles.bot.shoutout.default") is registered
            assert app_registry_module.apps_for_feature("waddles.bot.shoutout") == (registered,)
            assert app_registry_module.default_app_for("waddles.bot.shoutout") is registered
        finally:
            registry.clear()

    def test_module_load_delegates_to_singleton(self) -> None:
        from flask_core import app_registry as app_registry_module

        registry = app_registry_module.get_registry()
        registry.clear()
        try:
            loaded = app_registry_module.load(manifest())
            assert app_registry_module.get("waddles.bot.shoutout.default") is loaded
        finally:
            registry.clear()


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
