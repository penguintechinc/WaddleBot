"""Distribution service -- resolves the active bundle set for one pipeline stage.

Backs `blueprints/v1/distribution.py`'s `GET /api/v1/distribution/bundles`
endpoint, the read the svc-ingest/svc-process stage-runners poll to learn
which App Bundles are installed+activated for their stage, at a given
(tenant, community). Real query against `app_catalog` (migration 069,
extended by 071's `stages` column) joined with `app_activations`
(community-scoped) and, for the tenant-wide fallback, `app_tenant_availability`
-- the exact same JOIN/union/dedupe shape
`flask_core.app_installations_db.DBInstallationLookup.find()` already
established for `resolve_apps()`, just filtered by `stage` (is this stage
present in the bundle's `stages` JSON?) instead of by `feature`.

Read-replica intent (backend.md Database Tier Architecture): this is a
per-poll, high-frequency read from every stage-runner instance across the
platform -- exactly the routing-read case `DBInstallationLookup`'s own
docstring calls out for bypassing the primary. `list_bundles_for_stage`
takes whichever `dal`-shaped connection the caller passes; the blueprint is
responsible for passing the read-replica connection when one is configured.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

#: The three script pipeline stages a bundle may declare -- mirrors
#: `flask_core.stream_pipeline.BUNDLE_STAGES` (not imported directly to
#: keep this service's only dependency the `dal` object it's handed,
#: matching `app_installations_db.py`'s own no-import-of-stream_pipeline
#: precedent).
BUNDLE_STAGES = ("ingest", "process", "action")


class InvalidStageError(ValueError):
    """Raised when `stage` is not one of `BUNDLE_STAGES`."""


@dataclass(slots=True, frozen=True)
class BundleDistributionRow:
    """One bundle's `{entrypoint, config, spec}` for a stage, at a single (tenant, community).

    `config` is the merge of the bundle's own shipped stage default
    (`app_catalog.stages[stage].config`) with the tenant/community's
    override (`app_tenant_availability.config_defaults` /
    `app_activations.config`) -- override wins, same precedence
    `DBInstallationLookup`'s docstring establishes for narrower-scope-wins.
    """

    app_id: str
    community_id: int | None
    entrypoint: str | None
    spec: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


def _stage_data(stages: Any, stage: str) -> dict[str, Any] | None:
    """Extract `stages[stage]` from an `app_catalog.stages` JSON value, or `None`.

    Tolerant of `stages` being `None`/`{}` (a pre-071 row, or a row that
    genuinely never declared this stage) -- a bundle simply doesn't appear
    in that stage's distribution response, never a crash.
    """
    if not isinstance(stages, dict):
        return None
    data = stages.get(stage)
    return data if isinstance(data, dict) else None


async def list_bundles_for_stage(
    async_dal: Any,
    dal: Any,
    *,
    tenant_id: int,
    community_id: int | None,
    stage: str,
) -> Sequence[BundleDistributionRow]:
    """Every enabled, activated bundle implementing `stage` at (`tenant_id`, `community_id`).

    Community-scoped `app_activations` rows (when `community_id` is given)
    come first, then tenant-wide `app_tenant_availability` rows -- same
    ordering as `DBInstallationLookup.find()`, deduped by `app_id` (first
    occurrence wins) so a bundle available at both scopes is returned once,
    with the narrower (community) config winning.

    Raises `InvalidStageError` for any `stage` outside `BUNDLE_STAGES` --
    caught by the blueprint and turned into a 400, never a silently-empty
    result that looks like "no bundles active" for a typo'd stage name.
    """
    if stage not in BUNDLE_STAGES:
        raise InvalidStageError(f"invalid stage {stage!r}; must be one of {BUNDLE_STAGES}")

    rows: list[BundleDistributionRow] = []
    seen_app_ids: set[str] = set()

    if community_id is not None:
        query = (
            (dal.app_activations.tenant_id == tenant_id)
            & (dal.app_activations.community_id == community_id)
            & (dal.app_activations.enabled == True)  # noqa: E712 - pydal query operator, not a bool compare
            & (dal.app_activations.app_id == dal.app_catalog.app_id)
            & (dal.app_catalog.status == "active")
        )
        # Selecting from TWO tables (app_activations + app_catalog) -- pydal
        # returns a nested Row (row.app_activations.*, row.app_catalog.*),
        # not a flat one (hub_api/PORTING.md Gotcha #6).
        activation_rows = await async_dal.select_async(
            dal(query),
            dal.app_activations.app_id,
            dal.app_activations.config,
            dal.app_catalog.stages,
        )
        for row in activation_rows:
            app_id = row.app_activations.app_id
            if app_id in seen_app_ids:
                continue
            stage_data = _stage_data(row.app_catalog.stages, stage)
            if stage_data is None:
                continue
            seen_app_ids.add(app_id)
            merged_config = {**stage_data.get("config", {}), **(row.app_activations.config or {})}
            rows.append(
                BundleDistributionRow(
                    app_id=app_id,
                    community_id=community_id,
                    entrypoint=stage_data.get("entrypoint"),
                    spec=dict(stage_data.get("spec") or {}),
                    config=merged_config,
                )
            )

    avail_query = (
        (dal.app_tenant_availability.tenant_id == tenant_id)
        & (dal.app_tenant_availability.available == True)  # noqa: E712
        & (dal.app_tenant_availability.app_id == dal.app_catalog.app_id)
        & (dal.app_catalog.status == "active")
    )
    availability_rows = await async_dal.select_async(
        dal(avail_query),
        dal.app_tenant_availability.app_id,
        dal.app_tenant_availability.config_defaults,
        dal.app_catalog.stages,
    )
    for row in availability_rows:
        app_id = row.app_tenant_availability.app_id
        if app_id in seen_app_ids:
            continue
        stage_data = _stage_data(row.app_catalog.stages, stage)
        if stage_data is None:
            continue
        seen_app_ids.add(app_id)
        merged_config = {
            **stage_data.get("config", {}),
            **(row.app_tenant_availability.config_defaults or {}),
        }
        rows.append(
            BundleDistributionRow(
                app_id=app_id,
                community_id=None,
                entrypoint=stage_data.get("entrypoint"),
                spec=dict(stage_data.get("spec") or {}),
                config=merged_config,
            )
        )

    return rows
