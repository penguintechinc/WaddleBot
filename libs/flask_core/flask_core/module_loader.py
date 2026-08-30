"""
Module loader -- global on/off switch for the four toggleable Modules
========================================================================

Makes "Modules toggle globally" real on the app side. Per the design doc
(docs/plans/2026-08-26-v3-scbm-apps-design.md, "four globally-toggleable
Modules (Social, Customer, Bot, Marketing)"), ``k8s/helm/waddlebot/
templates/hub-api.yaml`` and ``svc-{ingest,process,action}.yaml`` already
conditionally set ``MODULE_LOAD_BOT/SOCIAL/CUSTOMER/MARKETING`` from
``.Values.modules.<name>.enabled`` -- the env var reaches the container.
Until this module, nothing read it: each ``<name>_module.features.
register_all()`` ran unconditionally wherever it was imported, so a Module
"disabled" in Helm still had its Feature contracts and default Apps
registered, still showed up in ``flask_core.feature_registry.
entitled_features()`` (the source list for per-tenant MCP tool listings),
and could still be bound to via ``app_binding.py``. :func:`load_enabled_modules`
is the read side: call it once at process startup instead of calling each
Module's ``register_all()`` directly, and a disabled Module's contracts and
Apps are simply never registered -- absent from entitlement checks, tool
listings and bindings, not merely hidden behind a flag *inside* an
already-registered contract.

Core/Platform (``core_platform_module``) is **not** one of the four
toggleable Modules -- analytics, auth, compliance, integrations and tenancy
are always-on platform capabilities in the Core/Modules split, not a
product vertical a deployer switches off. :func:`load_enabled_modules`
registers it unconditionally, every call, regardless of ``enabled``/env.

Enablement source (mirrors the Helm template's own conditional exactly):

- ``enabled=`` argument, when given (including the empty set), is
  authoritative -- tests use this for isolation instead of mutating
  ``os.environ``.
- Otherwise, each toggleable Module's ``MODULE_LOAD_<NAME>`` env var:
  present + truthy (``"true"``, ``"1"``, any value other than unset/``""``/
  ``"false"``/``"0"``/``"no"``, case-insensitive) means enabled -- matching
  the Helm template, which only ever *emits* the var (always as
  ``"true"``) and never emits it as ``"false"``; absence means disabled.
- **If neither `enabled=` nor a single `MODULE_LOAD_*` var is present at
  all, every toggleable Module defaults to enabled** -- safe for local dev,
  ad-hoc scripts and any test that never wires the Helm env vars, so an
  unconfigured process fails open to "everything on" rather than silently
  registering nothing. A real Helm deployment narrows this: as long as at
  least one Module is enabled in ``values.yaml`` (bot and social default
  ``true``), at least one ``MODULE_LOAD_*`` var is present in the
  container's environment, which takes this function out of the
  fail-open branch and into per-var, presence-only evaluation for all
  four. **Known limitation, not a bug to silently work around**: because
  the Helm template never emits an explicit ``"false"``, a deployment that
  disables *all four* Modules at once is indistinguishable from "the env
  was never wired" and would incorrectly fail open. Nothing in the current
  ``values.yaml`` defaults do this (bot/social ship enabled), so it has
  never been observed in practice; a future all-off deployment must pass
  ``enabled=frozenset()`` explicitly (or set at least one ``MODULE_LOAD_*``
  var, even to a falsy value, to leave the fail-open branch) rather than
  relying on Helm omitting all four vars.

Call :func:`load_enabled_modules` once at process startup. Tests pass an
explicit ``enabled`` set (or ``env`` mapping) and fresh
:class:`~flask_core.feature_registry.FeatureRegistry` /
:class:`~flask_core.app_registry.AppRegistry` instances for isolation,
exactly like every Module's own ``register_all()``.
"""

from __future__ import annotations

import os
from types import ModuleType
from typing import Dict, FrozenSet, Mapping, Optional, Set, Tuple, cast

from .app_manifest import AppManifest
from .app_registry import AppRegistry
from .app_registry import get_registry as get_app_registry
from .feature_contract import FeatureContract
from .feature_registry import FeatureRegistry
from .feature_registry import get_registry as get_feature_registry

# The four globally-toggleable Modules, matching the Helm template's
# MODULE_LOAD_BOT/SOCIAL/MARKETING/CUSTOMER block (k8s/helm/waddlebot/
# templates/hub-api.yaml) exactly. core_platform is deliberately absent --
# see module docstring.
TOGGLEABLE_MODULES: Tuple[str, ...] = ("bot", "social", "marketing", "customer")

_ENV_VAR_BY_MODULE: Dict[str, str] = {
    "bot": "MODULE_LOAD_BOT",
    "social": "MODULE_LOAD_SOCIAL",
    "marketing": "MODULE_LOAD_MARKETING",
    "customer": "MODULE_LOAD_CUSTOMER",
}

# Each toggleable Module's register_all() return shape (contracts, manifests).
RegisteredModule = Tuple[Tuple[FeatureContract, ...], Tuple[AppManifest, ...]]

_FALSY_VALUES = frozenset({"", "false", "0", "no"})


def _truthy(value: Optional[str]) -> bool:
    """Present/truthy per the Helm template's shape (only ever ``"true"``).

    Tolerant of any non-empty value other than the obvious falsy spellings
    (``""``/``"false"``/``"0"``/``"no"``, case-insensitive) so a bare
    ``MODULE_LOAD_X=1`` override in local dev also counts as enabled.
    """
    if value is None:
        return False
    return value.strip().lower() not in _FALSY_VALUES


def enabled_modules_from_env(env: Optional[Mapping[str, str]] = None) -> FrozenSet[str]:
    """Which toggleable Modules are enabled per their ``MODULE_LOAD_*`` var.

    ``env`` defaults to ``os.environ``; tests pass an explicit mapping
    instead of mutating the real environment. Does not apply the
    "nothing specified" fail-open default -- that is
    :func:`load_enabled_modules`'s job, since it alone knows whether
    ``enabled=`` was also omitted.
    """
    source = env if env is not None else os.environ
    return frozenset(
        module for module in TOGGLEABLE_MODULES if _truthy(source.get(_ENV_VAR_BY_MODULE[module]))
    )


def _resolve_enabled(
    enabled: Optional[Set[str]], env: Optional[Mapping[str, str]]
) -> FrozenSet[str]:
    """Resolve the effective enabled set per the precedence in the module docstring."""
    if enabled is not None:
        unknown = set(enabled) - set(TOGGLEABLE_MODULES)
        if unknown:
            raise ValueError(f"not a toggleable module: {sorted(unknown)}")
        return frozenset(enabled)

    source = env if env is not None else os.environ
    any_wired = any(_ENV_VAR_BY_MODULE[module] in source for module in TOGGLEABLE_MODULES)
    if not any_wired:
        # Nothing specified at all -- fail open to "everything on". See
        # module docstring's "Known limitation" paragraph.
        return frozenset(TOGGLEABLE_MODULES)
    return enabled_modules_from_env(source)


def _features_module_for(module: str) -> ModuleType:
    """Import and return ``<module>_module.features``, lazily.

    Deferred so importing :mod:`flask_core.module_loader` itself never
    forces an eager dependency on all four sibling packages under
    ``libs/`` -- a build that never enables e.g. Customer has no need to
    import ``customer_module`` at all, and callers that only want
    :func:`enabled_modules_from_env` (no registration) pay nothing for the
    Module packages.
    """
    # Each import below carries `type: ignore[import-not-found]`: these are
    # sibling packages under libs/, resolved via sys.path at runtime/test
    # time (see libs/flask_core/tests/conftest.py's "libs/ on sys.path"
    # shim and each service container's PYTHONPATH), not installed
    # packages mypy can resolve without a repo-wide MYPYPATH/mypy_path
    # config that does not exist yet.
    if module == "bot":
        import bot_module.features as features_module  # type: ignore[import-not-found]
    elif module == "social":
        import social_module.features as features_module  # type: ignore[import-not-found]
    elif module == "marketing":
        import marketing_module.features as features_module  # type: ignore[import-not-found]
    elif module == "customer":
        import customer_module.features as features_module  # type: ignore[import-not-found]
    else:  # pragma: no cover -- unreachable, TOGGLEABLE_MODULES is the only caller-facing set
        raise ValueError(f"not a toggleable module: {module!r}")
    return cast(ModuleType, features_module)


def load_enabled_modules(
    *,
    enabled: Optional[Set[str]] = None,
    env: Optional[Mapping[str, str]] = None,
    feature_registry: Optional[FeatureRegistry] = None,
    app_registry: Optional[AppRegistry] = None,
) -> Dict[str, RegisteredModule]:
    """
    Register Core/Platform (always) plus every enabled toggleable Module's
    Feature contracts and shipped default Apps.

    Defaults to the process-wide singletons
    (:func:`flask_core.feature_registry.get_registry`,
    :func:`flask_core.app_registry.get_registry`); tests pass fresh
    instances for isolation, same as each Module's own ``register_all()``.
    ``enabled`` overrides environment detection entirely, including the
    empty set; ``env`` (only consulted when ``enabled`` is ``None``)
    overrides ``os.environ`` for tests that want to exercise env parsing
    without mutating the real process environment. See the module
    docstring for the full precedence and the "nothing specified" default.

    Returns a dict keyed by module label (``"core_platform"`` plus any of
    ``"bot"``/``"social"``/``"marketing"``/``"customer"`` that were
    enabled) to that Module's ``register_all()`` return value. A disabled
    Module's label is simply absent from the result -- its
    ``register_all()`` is never called, so its contracts never reach the
    registries and are therefore absent from
    ``feature_registry.for_module(...)``,
    ``flask_core.feature_registry.entitled_features()`` (the MCP tool-list
    source), and ``app_registry.apps_for_feature(...)`` -- unbindable and
    ungateable because they were never registered, not merely filtered at
    read time.
    """
    f_registry = feature_registry if feature_registry is not None else get_feature_registry()
    a_registry = app_registry if app_registry is not None else get_app_registry()

    resolved = _resolve_enabled(enabled, env)

    results: Dict[str, RegisteredModule] = {}

    # `type: ignore[import-not-found]` -- see _features_module_for's
    # comment; core_platform_module is the same kind of libs/-sibling
    # package.
    import core_platform_module.features as core_platform_features  # type: ignore[import-not-found]

    results["core_platform"] = core_platform_features.register_all(
        feature_registry=f_registry, app_registry=a_registry
    )

    for module in TOGGLEABLE_MODULES:
        if module not in resolved:
            continue
        results[module] = _features_module_for(module).register_all(
            feature_registry=f_registry, app_registry=a_registry
        )

    return results
