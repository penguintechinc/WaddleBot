"""Fan a platform-level gateway event out to every bundle's own `:ingest` Valkey key.

A gateway-socket receiver (e.g. `receivers/discord_gateway.py`) holds ONE
persistent connection serving MANY communities -- unlike svc-ingest's
`BundlePoller`, which is a single stage-runner instance already scoped to
one (tenant, community) via `RUNNER_TENANT_SLUG`/`RUNNER_COMMUNITY_ID`,
svc-gateway must discover, per inbound event, which bundle(s) actually want
it. Per this PR's own task spec: call `flask_core.app_binding.resolve_apps`
(the in-process registry ladder), not hub-api's `GET /api/v1/distribution/
bundles` HTTP endpoint -- that endpoint's DTO doesn't carry `consumes`/
`communication_model` at all (`hub_api/services/distribution_service.py`'s
`BundleDistributionRow` only exposes `{entrypoint, config, spec}`), and
extending it to would require new migration/service/blueprint work out of
scope for this PR (see the PR description's own documented gaps).

`resolve_consuming_apps` answers "every enabled/activated App whose ingest
stage declares `consumes_tag`" by scanning `AppRegistry.all_apps()` for
candidate Features, then re-running each through the REAL `resolve_apps`
ladder (community binding -> tenant binding -> shipped default) so a
Feature with more than one implementing App still resolves to whichever
one is actually bound -- not just "the App whose manifest happened to
declare the tag".
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any, Protocol

from flask_core.app_binding import (
    AppInstallation,
    BindingError,
    InstallationLookup,
    resolve_apps,
)
from flask_core.app_manifest import AppManifest, StageSpec
from flask_core.app_registry import AppRegistry
from flask_core.stream_pipeline import bundle_stream_key

logger = logging.getLogger(__name__)

#: Zero-arg stand-in for a missing `stage_specs["ingest"]` -- avoids a
#: `None`-check at the one `manifest.stage_specs.get("ingest", ...)` call
#: site below; `StageSpec()`'s own default `consumes=()` already means
#: "consumes nothing", so it composes for free.
_EMPTY_STAGE_SPEC = StageSpec()


class _NullInstallationLookup:
    """`InstallationLookup` with no rows -- every `resolve_apps` call falls straight to the
    Feature's shipped default (see `bundles/discord_gateway_manifest.py`'s own docstring for
    why this is today's deliberate MVP scope, not the long-term design)."""

    async def find(
        self, feature: str, *, tenant: str, community: int | None
    ) -> Sequence[AppInstallation]:
        """Always empty -- forces `resolve_apps` to its default-App fallback."""
        return ()


#: Shared no-op lookup instance -- stateless, safe to reuse across calls.
NULL_INSTALLATIONS: InstallationLookup = _NullInstallationLookup()


class RedisLike(Protocol):
    """The one Valkey method `fan_out_event` needs -- narrow on purpose, easy to fake in tests."""

    async def lpush(self, key: str, value: str) -> Any:
        """LPUSH `value` onto `key`."""
        ...


async def resolve_consuming_apps(
    consumes_tag: str,
    *,
    tenant: str,
    community: int | None,
    registry: AppRegistry,
    installations: InstallationLookup = NULL_INSTALLATIONS,
) -> tuple[AppManifest, ...]:
    """Every App, resolved through `resolve_apps`, whose ingest stage `consumes` `consumes_tag`.

    Two passes, deliberately: (1) scan every registered App's own manifest
    for candidate Features (cheap, no I/O -- `AppRegistry.all_apps()` is an
    in-memory tuple), then (2) re-resolve each candidate Feature through
    `resolve_apps` so the RESULT reflects whatever App is actually bound
    at (tenant, community) today, not just whichever App's manifest
    happened to declare the tag. A resolved App is only kept if IT ALSO
    declares the tag -- a Feature bound to a different, non-matching App
    at this scope is correctly excluded, not silently included because
    some other App under the same Feature matched in pass 1.
    """
    candidate_features = {
        manifest.feature
        for manifest in registry.all_apps()
        if consumes_tag in manifest.stage_specs.get("ingest", _EMPTY_STAGE_SPEC).consumes
    }

    resolved: list[AppManifest] = []
    seen_app_ids: set[str] = set()
    for feature in candidate_features:
        try:
            apps = await resolve_apps(
                feature,
                tenant=tenant,
                community=community,
                installations=installations,
                registry=registry,
            )
        except BindingError:
            continue
        for candidate in apps:
            if candidate.app_id in seen_app_ids:
                continue
            ingest_spec = candidate.stage_specs.get("ingest")
            if ingest_spec is None or consumes_tag not in ingest_spec.consumes:
                continue
            seen_app_ids.add(candidate.app_id)
            resolved.append(candidate)

    return tuple(resolved)


async def fan_out_event(
    raw_event: dict[str, Any],
    *,
    consumes_tag: str,
    tenant: str,
    community: int | None,
    redis_client: RedisLike,
    registry: AppRegistry,
    installations: InstallationLookup = NULL_INSTALLATIONS,
) -> int:
    """Resolve every consuming bundle and LPUSH `raw_event` onto each one's own `:ingest` key.

    Returns the number of bundles fanned out to (0 is a legitimate,
    logged-but-not-fatal outcome -- no bundle wants this event yet).
    """
    apps = await resolve_consuming_apps(
        consumes_tag,
        tenant=tenant,
        community=community,
        registry=registry,
        installations=installations,
    )
    if not apps:
        logger.info(
            "gateway.fanout_no_consumers consumes=%s tenant=%s community=%s",
            consumes_tag,
            tenant,
            community,
        )
        return 0

    community_str = str(community) if community is not None else None
    payload = json.dumps(raw_event)
    for app in apps:
        ingest_key = bundle_stream_key(tenant, community_str, app.app_id, "ingest")
        await redis_client.lpush(ingest_key, payload)
        logger.debug(
            "gateway.fanout_lpush app_id=%s key=%s",
            app.app_id,
            ingest_key,
        )
    return len(apps)
