"""
Feature contract schema
=========================

Per docs/plans/2026-08-26-v3-scbm-apps-design.md ``Features``: "A Feature is
a **contract**, not code." This module defines that contract's shape and
the validator that keeps a malformed one from ever reaching the registry --
mirrors :mod:`flask_core.app_manifest`'s parse-then-register split
(``ManifestError`` there, :class:`FeatureContractError` here) so both halves
of the App framework fail the same way: typed, reason-coded, at load time
rather than at use time.

Two invariants are load-bearing, both enforced here rather than left to
convention:

- ``id`` is **unprefixed** ``<module>.<feature>`` (e.g. ``bot.shoutout`` --
  the design doc's own Feature id example), while ``flag`` carries the
  ``waddles.`` prefix (``waddles.bot.shoutout``). The two are related by
  exactly one rule, enforced here: ``flag == f"waddles.{id}"``. Getting this
  wrong silently breaks the tier gate -- ``entitlement.py``'s
  ``tier_requirements`` and PostHog are both keyed on ``flag``, not ``id``
  (see ``feature_flags.feature_enabled``), so a contract whose flag drifts
  from its id would evaluate a gate nothing else references.
- ``module`` must equal ``id``'s own prefix segment. A contract cannot
  declare ``module="social"`` while its id starts with ``bot.`` -- that
  mismatch is exactly what would let a Feature masquerade under a different
  Module's toggle.

``KNOWN_MODULES`` is imported from :mod:`flask_core.app_manifest` rather
than re-declared, so Feature and App validation can never drift onto two
different Module lists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet

from .app_manifest import KNOWN_MODULES

_SEGMENT = r"[a-z0-9][a-z0-9_-]*"
# <module>.<feature> -- exactly two dot-separated tokens, no 'waddles.' prefix.
_ID_RE = re.compile(rf"^({_SEGMENT})\.({_SEGMENT})$")

KNOWN_TIERS = frozenset({"free", "professional", "enterprise"})

_REQUIRED_FIELDS = ("id", "version", "module", "requires_scopes", "min_tier", "flag")


class FeatureContractError(Exception):
    """
    Raised when a raw Feature contract dict fails validation. ``reason`` is
    a stable machine-checkable code (see the ``REASON_*`` constants below)
    so callers and tests can assert on *why* a contract was rejected, not
    just that it was.
    """

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        super().__init__(f"{reason}: {detail}")


REASON_MISSING_FIELD = "missing_field"
REASON_NOT_NAMESPACED = "not_namespaced"
REASON_UNKNOWN_MODULE = "unknown_module"
REASON_MODULE_MISMATCH = "module_mismatch"
REASON_BAD_VERSION = "bad_version"
REASON_BAD_TIER = "bad_tier"
REASON_BAD_FLAG = "bad_flag"


@dataclass(slots=True, frozen=True)
class FeatureContract:
    """
    A validated Feature contract -- built exclusively by
    :func:`parse_feature_contract`. Constructing one directly bypasses the
    namespacing/module/version/tier/flag checks, so callers loading
    contracts from a module's ``features.py`` must always go through
    :func:`parse_feature_contract`.
    """

    id: str
    version: int
    module: str
    requires_scopes: FrozenSet[str]
    min_tier: str
    flag: str


def _require(data: Dict[str, Any], key: str) -> Any:
    if key not in data or data[key] in (None, ""):
        raise FeatureContractError(REASON_MISSING_FIELD, f"{key!r} is required")
    return data[key]


def parse_feature_contract(data: Dict[str, Any]) -> FeatureContract:
    """
    Validate a raw Feature contract dict and build a :class:`FeatureContract`.

    Rejects, in order, with a typed :class:`FeatureContractError`:

    1. missing/empty required fields
    2. ``id`` that is not namespaced ``<module>.<feature>``
    3. ``module`` not one of the known Modules
    4. ``module`` not equal to ``id``'s own prefix segment
    5. ``version`` that is not an int ``>= 1``
    6. ``min_tier`` outside ``{free, professional, enterprise}``
    7. ``flag`` not equal to ``f"waddles.{id}"``
    """
    for key in _REQUIRED_FIELDS:
        _require(data, key)

    feature_id = data["id"]
    module = data["module"]
    version = data["version"]
    min_tier = data["min_tier"]
    flag = data["flag"]

    if not isinstance(feature_id, str):
        raise FeatureContractError(REASON_NOT_NAMESPACED, f"id {feature_id!r} must be a string")

    match = _ID_RE.match(feature_id)
    if not match:
        raise FeatureContractError(
            REASON_NOT_NAMESPACED, f"id {feature_id!r} must be namespaced '<module>.<feature>'"
        )
    id_module = match.group(1)

    if module not in KNOWN_MODULES:
        raise FeatureContractError(
            REASON_UNKNOWN_MODULE, f"module {module!r} is not one of {sorted(KNOWN_MODULES)}"
        )

    if id_module != module:
        raise FeatureContractError(
            REASON_MODULE_MISMATCH,
            f"id {feature_id!r} implies module {id_module!r}, but contract declares module {module!r}",
        )

    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise FeatureContractError(
            REASON_BAD_VERSION, f"version {version!r} must be an int >= 1"
        )

    if not isinstance(min_tier, str) or min_tier not in KNOWN_TIERS:
        raise FeatureContractError(
            REASON_BAD_TIER, f"min_tier {min_tier!r} is not one of {sorted(KNOWN_TIERS)}"
        )

    expected_flag = f"waddles.{feature_id}"
    if flag != expected_flag:
        raise FeatureContractError(
            REASON_BAD_FLAG, f"flag {flag!r} must equal {expected_flag!r} (waddles.<id>)"
        )

    requires_scopes = frozenset(data.get("requires_scopes") or ())

    return FeatureContract(
        id=feature_id,
        version=version,
        module=module,
        requires_scopes=requires_scopes,
        min_tier=min_tier,
        flag=flag,
    )
