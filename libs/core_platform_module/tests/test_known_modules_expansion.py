"""
KNOWN_MODULES expansion tests
=================================

Covers the Step 1 spine change: :data:`flask_core.app_manifest.KNOWN_MODULES`
grows from the 4 legacy product Modules (bot/social/marketing/customer) to
include the 7 Core/platform namespaces this package registers Features
under (analytics, video_proxy, auth, compliance, integrations, tenancy,
core). :mod:`flask_core.feature_contract` imports ``KNOWN_MODULES`` from
``app_manifest`` rather than re-declaring it, so a single passing test per
validator (:func:`parse_manifest`, :func:`parse_feature_contract`) proves
both consumers see the same expanded set -- and the bogus-module case
proves the set is still a real allowlist, not accidentally opened wide.

Updated for the P4 SCCEMBS taxonomy migration
(docs/plans/2026-08-31-v3-sccembs-program-plan.md #1.1/#9): the 4 legacy
product Modules are superseded by the 7 canonical SCCEMBS modules (Socials,
Customers, Community, Event, Marketing, Bot, Streaming), with "social"/
"customer" (singular) kept additively as transitional aliases so already
-registered pre-P4 Feature contracts (module="social"/"customer") don't
break -- see the KNOWN_MODULES docstring in app_manifest.py. This test's
expected set now asserts SCCEMBS_MODULES | LEGACY_ALIASES |
CORE_PLATFORM_NAMESPACES rather than the old 4-module set.

Fail-on-purpose proof: ``test_bogus_module_still_rejected_by_manifest`` and
``test_bogus_module_still_rejected_by_feature_contract`` were verified to
catch a regression by temporarily adding ``"widgets"`` to ``KNOWN_MODULES``
in ``app_manifest.py`` and confirming both go red (REASON_UNKNOWN_MODULE no
longer raised), then reverting.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from flask_core.app_manifest import KNOWN_MODULES, REASON_UNKNOWN_MODULE as MANIFEST_REASON_UNKNOWN_MODULE
from flask_core.app_manifest import ManifestError, parse_manifest
from flask_core.feature_contract import REASON_UNKNOWN_MODULE as CONTRACT_REASON_UNKNOWN_MODULE
from flask_core.feature_contract import FeatureContractError, parse_feature_contract

SCCEMBS_MODULES = {"socials", "customers", "community", "event", "marketing", "bot", "streaming"}
LEGACY_MODULE_ALIASES = {"social", "customer"}
PRODUCT_MODULES = SCCEMBS_MODULES | LEGACY_MODULE_ALIASES
CORE_PLATFORM_NAMESPACES = {
    "analytics",
    "video_proxy",
    "auth",
    "compliance",
    "integrations",
    "tenancy",
    "core",
}


def test_known_modules_is_exactly_product_modules_plus_core_platform_namespaces() -> None:
    assert KNOWN_MODULES == PRODUCT_MODULES | CORE_PLATFORM_NAMESPACES


class TestParseManifestAcceptsNewNamespaces:
    @pytest.mark.parametrize("module", sorted(CORE_PLATFORM_NAMESPACES))
    def test_new_namespace_module_accepted(self, module: str) -> None:
        data: Dict[str, Any] = {
            "app_id": f"waddles.{module}.probe.default",
            "name": "Probe (default)",
            "version": "1.0.0",
            "feature": f"waddles.{module}.probe",
            "module": module,
            "provider": "builtin",
        }
        result = parse_manifest(data)
        assert result.module == module

    def test_bogus_module_still_rejected_by_manifest(self) -> None:
        data: Dict[str, Any] = {
            "app_id": "waddles.widgets.probe.default",
            "name": "Probe (default)",
            "version": "1.0.0",
            "feature": "waddles.widgets.probe",
            "module": "widgets",
            "provider": "builtin",
        }
        with pytest.raises(ManifestError) as excinfo:
            parse_manifest(data)
        assert excinfo.value.reason == MANIFEST_REASON_UNKNOWN_MODULE


class TestParseFeatureContractAcceptsNewNamespaces:
    @pytest.mark.parametrize("module", sorted(CORE_PLATFORM_NAMESPACES))
    def test_new_namespace_module_accepted(self, module: str) -> None:
        data: Dict[str, Any] = {
            "id": f"{module}.probe",
            "version": 1,
            "module": module,
            "requires_scopes": {f"{module}.probe:read"},
            "min_tier": "professional",
            "flag": f"waddles.{module}.probe",
        }
        result = parse_feature_contract(data)
        assert result.module == module

    def test_bogus_module_still_rejected_by_feature_contract(self) -> None:
        data: Dict[str, Any] = {
            "id": "widgets.probe",
            "version": 1,
            "module": "widgets",
            "requires_scopes": {"widgets.probe:read"},
            "min_tier": "professional",
            "flag": "waddles.widgets.probe",
        }
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(data)
        assert excinfo.value.reason == CONTRACT_REASON_UNKNOWN_MODULE
