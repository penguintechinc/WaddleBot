"""
DB-backed InstallationLookup + app-tier write-time invariants
================================================================

Concrete :class:`~flask_core.app_binding.InstallationLookup` implementation
reading the C3 3-tier tables (``app_catalog`` / ``app_tenant_availability`` /
``app_activations``, ``docs/plans/2026-08-31-app-bundle-sdk-design.md`` §5.1,
see :mod:`flask_core.app_bundle_tables`) so ``resolve_apps``
(``app_binding.py`` §5.2) can run against real data instead of the
in-memory fakes C1/C2's tests use.

Read-replica intent (design doc §6.3/§6.4): "Routing on every event through
hub-api would hammer a low-volume admin API with the platform's entire
event throughput... routing is frequent and is data, so it goes straight
to the tier built for high-read-volume queries, bypassing hub-api
entirely." :meth:`DBInstallationLookup.find` is exactly that per-event
routing read. This class deliberately does **not** distinguish primary
from replica itself -- it accepts whatever ``dal``-shaped object it is
constructed with and queries it directly. Picking the replica connection
is the caller's responsibility: stage-runners construct this class with
their **read-only** account against the read replica (``AsyncDAL.read_dal``,
see ``database.py``, or the replica URI directly) per ``backend.md``'s
Database Tier Architecture and ``security.md``'s per-service-DB-account
rule -- hub-api's write path (the sole ``app_catalog`` writer) never
constructs this class against its primary/write connection for routing
reads.

Tenant-wide rows (``community_id=None`` on the returned
:class:`~flask_core.app_binding.AppInstallation`, matching that
dataclass's existing docstring semantics and the C2 test suite's
``community_id=None`` fixture rows): this 3-tier schema has **no literal
tenant-wide row** in ``app_activations`` -- ``community_id`` is ``NOT
NULL`` by design (§5.1), activation is always community-scoped. This
module surfaces ``app_tenant_availability`` (the *available* tier) itself
as the tenant-wide member of ``resolve_apps``'s union, keyed off
``available=True``. This is a **documented interpretation**, not a locked
spec decision: design doc §10 open decision #2 ("config precedence:
bundle default -> tenant -> community... confirm this is strictly
narrowest-wins-overrides") leaves exactly this question open. A stricter
reading -- only ``app_activations`` rows ever bind, full stop -- would
make :meth:`find` return an empty tenant-wide contribution whenever a
tenant has made an App available but no community has activated it yet.
Revisit when §10 #2 is resolved; until then, "available" is treated as a
usable (if overridable) tenant-wide default so ``resolve_apps`` has
something to fan out to before any community opts in.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .app_binding import AppInstallation

#: Stable machine-checkable reason codes, matching the ManifestError/
#: RegistryError REASON_* convention (app_manifest.py, app_registry.py).
REASON_APP_NOT_INSTALLED = "app_not_installed"
REASON_APP_NOT_AVAILABLE = "app_not_available"


class AppTierError(Exception):
    """
    Raised when a write to ``app_tenant_availability`` or
    ``app_activations`` would violate the install -> available -> activate
    subset invariant (``activated ⊆ available ⊆ installed``, design doc
    §5.1). ``reason`` is a stable machine-checkable code so callers/tests
    can assert on *why* a write was rejected, not just that it was.
    """

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}")


class DBInstallationLookup:
    """
    Concrete ``InstallationLookup`` reading ``app_activations`` (+
    tenant-wide ``app_tenant_availability`` rows, see module docstring)
    for :func:`~flask_core.app_binding.resolve_apps`. Construct with
    whichever DAL/connection the caller wants reads to run against --
    pass the read-replica DAL on the hot routing path (§6.3), never
    hub-api's primary/write connection.
    """

    def __init__(self, dal: Any) -> None:
        self._dal = dal

    async def find(
        self, feature: str, *, tenant: str, community: int | None
    ) -> Sequence[AppInstallation]:
        """
        Community-scoped ``app_activations`` rows for ``(tenant,
        community)`` first, then tenant-wide ``app_tenant_availability``
        rows -- ordering matters because ``resolve_apps`` dedupes by
        ``app_id``, first occurrence wins, so a community-specific row's
        ``enabled``/``config`` takes precedence over the tenant-wide
        fallback for the same ``app_id`` (mirrors ``resolve_app``'s old
        narrowest-wins ladder even though ``resolve_apps`` itself no
        longer *suppresses* the broader row -- both are simply present,
        deduped by identity per §5.2).
        """
        tenant_id = int(tenant)
        dal = self._dal
        rows: list[AppInstallation] = []

        if community is not None:
            query = (
                (dal.app_activations.tenant_id == tenant_id)
                & (dal.app_activations.community_id == community)
                & (dal.app_activations.app_id == dal.app_catalog.app_id)
                & (dal.app_catalog.feature == feature)
            )
            # All three selected fields belong to app_activations alone (app_catalog
            # is joined only for its WHERE-clause feature filter, never selected
            # from) -- pydal returns a flat Row here, not the table-namespaced
            # Row a multi-table field selection would produce.
            for row in dal(query).select(
                dal.app_activations.app_id,
                dal.app_activations.enabled,
                dal.app_activations.config,
            ):
                rows.append(
                    AppInstallation(
                        tenant_id=str(tenant_id),
                        community_id=community,
                        feature=feature,
                        app_id=row.app_id,
                        enabled=bool(row.enabled),
                        config=dict(row.config or {}),
                    )
                )

        avail_query = (
            (dal.app_tenant_availability.tenant_id == tenant_id)
            & (dal.app_tenant_availability.app_id == dal.app_catalog.app_id)
            & (dal.app_catalog.feature == feature)
        )
        for row in dal(avail_query).select(
            dal.app_tenant_availability.app_id,
            dal.app_tenant_availability.available,
            dal.app_tenant_availability.config_defaults,
        ):
            rows.append(
                AppInstallation(
                    tenant_id=str(tenant_id),
                    community_id=None,
                    feature=feature,
                    app_id=row.app_id,
                    enabled=bool(row.available),
                    config=dict(row.config_defaults or {}),
                )
            )

        return rows


async def check_availability_insert_allowed(dal: Any, app_id: str) -> None:
    """
    Write-time invariant (design doc §5.1): inserting an
    ``app_tenant_availability`` row requires ``app_id`` to already exist
    in ``app_catalog`` (``available ⊆ installed``). Raises
    :class:`AppTierError` on violation; callers run this immediately
    before the insert, inside the same transaction.
    """
    exists = dal(dal.app_catalog.app_id == app_id).count() > 0
    if not exists:
        raise AppTierError(
            REASON_APP_NOT_INSTALLED,
            f"app_id {app_id!r} has no app_catalog row -- cannot make it available",
        )


async def check_activation_insert_allowed(dal: Any, tenant_id: int, app_id: str) -> None:
    """
    Write-time invariant (design doc §5.1): inserting an
    ``app_activations`` row requires an *available*
    ``app_tenant_availability`` row for ``(tenant_id, app_id)``
    (``activated ⊆ available``). Raises :class:`AppTierError` on
    violation; callers run this immediately before the insert, inside the
    same transaction. Does not re-check ``app_catalog`` itself --
    :func:`check_availability_insert_allowed` already enforced that one
    layer down, and ``app_tenant_availability.app_id`` carries the same FK.
    """
    exists = (
        dal(
            (dal.app_tenant_availability.tenant_id == tenant_id)
            & (dal.app_tenant_availability.app_id == app_id)
            & (dal.app_tenant_availability.available == True)
        ).count()
        > 0
    )
    if not exists:
        raise AppTierError(
            REASON_APP_NOT_AVAILABLE,
            f"app_id {app_id!r} is not available for tenant_id {tenant_id!r} -- cannot activate",
        )
