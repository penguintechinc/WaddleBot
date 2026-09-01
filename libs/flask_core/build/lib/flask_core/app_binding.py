"""
App binding resolution
========================

Resolves *which* App is active for a (feature, tenant, community) slot --
the global-is-not-bindable / tenant / community override ladder from the
design doc's ``Apps -> Binding resolution``:

    community binding  ->  tenant binding  ->  shipped default App

Narrowest scope wins. Unlike the identity ladder (``global -> tenant ->
community``, see ``Identity and data scoping``), App binding has no global
rung: "the shipped default App is code, not a bindable row, so there is no
cluster-wide replacement" -- an operator can hold global admin scope and
still not swap a community's App platform-wide. The two ladders look alike
and are deliberately not the same mechanism.

``resolve_app`` takes its installation lookup as an injected dependency
(:class:`InstallationLookup`) rather than querying a DB directly, per the
task spec -- this module has no DB dependency and stays trivially testable
with an in-memory fake.

App Bundle SDK spec (``2026-08-31-app-bundle-sdk-design.md`` §5.2/§7)
supersedes the single-winner ladder above with a **coexistence set**:
:func:`resolve_apps` returns every enabled/activated App implementing a
Feature at (tenant, community) as a union, not an override -- fan-out to
all of them, not a pick-one binding. :func:`resolve_app` is kept unchanged
for backward compatibility; it is superseded, not removed. :func:`detect_conflict`
is the companion pure-logic check (spec §7.3) the ``app_activations`` write
(C3) runs before enabling a new App alongside an already-active set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence

from .app_manifest import AppManifest
from .app_registry import AppRegistry, get_registry


class BindingError(Exception):
    """
    Raised when no App can be resolved for a Feature slot -- no binding at
    any ladder rung, and no shipped default registered either. Distinct
    from :class:`~flask_core.app_registry.RegistryError`: this is a
    resolution-time failure (nothing bound), not a load-time one.
    """


@dataclass(slots=True, frozen=True)
class AppInstallation:
    """
    One row of the ``app_installations`` table: a (tenant, community,
    feature) -> app_id binding.

    This is the renamed ``hub_module_installations`` table -- see the
    design doc's ``Vocabulary`` section: "Renaming `hub_module_installations`
    to `app_installations` is part of P1. The existing column meaning does
    not change; only the name stops lying." Earlier drafts of this design
    referred to the same (tenant/community, feature-slot) -> bound-App
    concept informally as "feature_installations"; ``app_installations`` /
    :class:`AppInstallation` supersede that name per Task 1.3 -- the
    semantics are unchanged, only the vocabulary is now Feature/App-correct
    rather than the pre-v3 "module" overload described in ``Vocabulary``.

    ``community_id`` is nullable: ``None`` means a tenant-wide binding,
    a specific value means a community-scoped override that narrows it.
    """

    tenant_id: str
    community_id: Optional[int]
    feature: str
    app_id: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class InstallationLookup(Protocol):
    """
    Injected installation source for :func:`resolve_app`. Production code
    implements this against ``app_installations``; tests implement it
    in-memory. Deliberately narrow -- one read method, no write surface --
    so ``resolve_app`` cannot be tempted to mutate bindings as a side effect
    of resolving one.
    """

    async def find(
        self, feature: str, *, tenant: str, community: Optional[int]
    ) -> Sequence[AppInstallation]:
        """
        Return every installation row (enabled or not) bound to ``feature``
        that is visible to ``tenant`` -- both tenant-wide
        (``community_id is None``) and, if ``community`` is given, that
        community's own rows. Filtering to *enabled* rows is
        :func:`resolve_app`'s job, not the lookup's.
        """
        ...


async def resolve_app(
    feature: str,
    *,
    tenant: str,
    community: Optional[int],
    installations: InstallationLookup,
    registry: Optional[AppRegistry] = None,
) -> AppManifest:
    """
    Resolve the single active App for ``feature`` at (``tenant``, ``community``).

    Superseded by :func:`resolve_apps` (design doc §5.2) -- the coexistence
    model returns the full activated set rather than picking one winner.
    Kept unchanged for backward compatibility with existing callers/tests;
    new call sites should prefer :func:`resolve_apps`.

    Precedence, narrowest first:

    1. an *enabled* community-scoped binding (``community_id == community``,
       only when ``community`` is not ``None``)
    2. an *enabled* tenant-wide binding (``community_id is None``)
    3. the Feature's shipped default App (:meth:`AppRegistry.default_app_for`)

    Disabled installation rows are skipped entirely -- they neither bind nor
    block a narrower/broader rung from being considered. Raises
    :class:`BindingError` if nothing binds and no default is registered.
    """
    reg = registry if registry is not None else get_registry()
    rows = [row for row in await installations.find(feature, tenant=tenant, community=community) if row.enabled]

    if community is not None:
        for row in rows:
            if row.community_id == community:
                return reg.get(row.app_id)

    for row in rows:
        if row.community_id is None:
            return reg.get(row.app_id)

    default_app = reg.default_app_for(feature)
    if default_app is not None:
        return default_app

    raise BindingError(
        f"no App bound or defaulted for feature {feature!r} "
        f"(tenant={tenant!r}, community={community!r})"
    )


async def resolve_apps(
    feature: str,
    *,
    tenant: str,
    community: Optional[int],
    installations: InstallationLookup,
    registry: Optional[AppRegistry] = None,
) -> Sequence[AppManifest]:
    """
    Resolve every *enabled, activated* App for ``feature`` visible at
    (``tenant``, ``community``) -- the coexistence set (design doc §5.2/§7.1),
    not the binding ladder's single winner.

    Community-scoped rows (``community_id == community``) and tenant-wide
    rows (``community_id is None``) are a **union**: every enabled row
    ``installations.find`` returns contributes its App to the result.
    ``resolve_app``'s narrowest-scope-wins precedence does not apply here --
    a community-scoped row does not suppress a tenant-wide one, it adds to
    it. Results are de-duplicated by ``app_id`` (first occurrence wins,
    ``installations.find`` row order), so an App somehow bound at both
    scopes at once is not returned twice.

    Falls back to the Feature's shipped default App
    (:meth:`AppRegistry.default_app_for`) only when the resolved set is
    empty -- any non-empty set of enabled activations is returned as-is,
    never topped up with the default. Raises :class:`BindingError` if the
    set is empty and no default is registered either, same failure mode as
    :func:`resolve_app`.
    """
    reg = registry if registry is not None else get_registry()
    rows = [row for row in await installations.find(feature, tenant=tenant, community=community) if row.enabled]

    resolved: List[AppManifest] = []
    seen_app_ids: set[str] = set()
    for row in rows:
        if row.app_id in seen_app_ids:
            continue
        seen_app_ids.add(row.app_id)
        resolved.append(reg.get(row.app_id))

    if resolved:
        return tuple(resolved)

    default_app = reg.default_app_for(feature)
    if default_app is not None:
        return (default_app,)

    raise BindingError(
        f"no App bound or defaulted for feature {feature!r} "
        f"(tenant={tenant!r}, community={community!r})"
    )


def detect_conflict(candidate: AppManifest, active: Iterable[AppManifest]) -> Optional[str]:
    """
    Symmetric coexistence check for activating ``candidate`` alongside
    ``active`` (design doc §7.3). Returns the conflicting ``app_id`` if
    ``candidate`` cannot coexist with some App already in ``active``, or
    ``None`` if there is no conflict.

    A conflict exists when ``candidate.app_id`` appears in
    ``other.incompatible_with`` **or** ``other.app_id`` appears in
    ``candidate.incompatible_with``, for any ``other`` in ``active`` --
    either manifest declaring the restriction is enough, regardless of which
    side authored it (package-manager ``Conflicts``-style, not a
    both-sides-must-agree check).

    ``active`` is expected to already be scoped to the target community's
    currently *enabled* activations -- this function knows nothing about
    ``app_activations`` rows or an ``enabled`` flag, only manifests; a
    disabled activation's App simply should not be in ``active`` when the
    caller builds it. Pure logic, no I/O: this is the check the
    ``app_activations`` insert/update (C3) runs *before* writing, not a
    replacement for that write.
    """
    for other in active:
        if other.app_id == candidate.app_id:
            continue
        if candidate.app_id in other.incompatible_with or other.app_id in candidate.incompatible_with:
            return other.app_id
    return None
