"""svc-process's real poll -> pull -> transform -> enqueue loop.

Mirrors `core/svc_ingest/runner.py`'s shape exactly, one stage over: RPOPs
each active bundle's `:process` Valkey key, runs the bundle's real
`transform()` entrypoint, and LPUSHes the result onto that bundle's
`:action` key as a JSON envelope -- the task's explicit requirement
("enqueue to `waddles:t:{tenant}:c:{community}:app:{app_id}:action`").
Separated from `app.py` for direct unit-testability, same rationale as
svc-ingest's own `runner.py`.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from flask_core.stage_runner import (
    BundleDistribution,
    BundlePoller,
    EntrypointLoadError,
    load_entrypoint,
)
from flask_core.stream_pipeline import bundle_stream_key

logger = logging.getLogger(__name__)


class ProcessRunner:
    """One poll+drain cycle per call to `run_once()`; `run_forever()` loops it in production."""

    def __init__(self, *, poller: BundlePoller, redis_client: Any, tenant_slug: str) -> None:
        """Build a runner bound to one `BundlePoller`, one Valkey client, and one tenant scope."""
        self._poller = poller
        self._redis = redis_client
        self._tenant_slug = tenant_slug
        self._running = False

    def stop(self) -> None:
        """Signal `run_forever()` to exit after its current iteration."""
        self._running = False

    async def run_forever(self) -> None:
        """Production loop: poll, drain every active bundle's process queue, sleep, repeat."""
        self._running = True
        while self._running:
            await self.run_once()
            import asyncio

            await asyncio.sleep(self._poller.next_delay_s)

    async def run_once(self) -> int:
        """One poll+drain cycle; returns total events transformed+enqueued. Never raises."""
        bundles = await self._poller.poll_once()
        total = 0
        for bundle in bundles:
            total += await self._process_bundle(bundle)
        return total

    async def _process_bundle(self, bundle: BundleDistribution) -> int:
        if bundle.entrypoint is None:
            logger.info("process.no_entrypoint app_id=%s -- skipping", bundle.app_id)
            return 0

        try:
            transform_fn = load_entrypoint(bundle.entrypoint)
        except EntrypointLoadError as exc:
            logger.error(
                "process.entrypoint_load_failed app_id=%s entrypoint=%s error=%s",
                bundle.app_id,
                bundle.entrypoint,
                exc,
            )
            return 0

        community_str: str | None = (
            str(bundle.community_id) if bundle.community_id is not None else None
        )
        process_key = bundle_stream_key(self._tenant_slug, community_str, bundle.app_id, "process")
        action_key = bundle_stream_key(self._tenant_slug, community_str, bundle.app_id, "action")

        count = 0
        while True:
            raw = await self._redis.rpop(process_key)
            if raw is None:
                break
            count += await self._transform_and_enqueue(
                raw, transform_fn, bundle=bundle, action_key=action_key
            )
        return count

    async def _transform_and_enqueue(
        self, raw: Any, transform_fn: Any, *, bundle: BundleDistribution, action_key: str
    ) -> int:
        """Parse the incoming envelope, transform its payload, LPUSH the result envelope."""
        try:
            envelope_in = json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.error("process.bad_json app_id=%s error=%s", bundle.app_id, exc)
            return 0

        event = (
            envelope_in.get("payload", envelope_in)
            if isinstance(envelope_in, dict)
            else envelope_in
        )

        try:
            transformed = await transform_fn(event)
        except Exception as exc:  # noqa: BLE001 - one bad event must never kill the loop
            logger.error("process.transform_failed app_id=%s error=%s", bundle.app_id, exc)
            return 0

        envelope_out = {
            "tenant": self._tenant_slug,
            "community": bundle.community_id,
            "app_id": bundle.app_id,
            "stage": "action",
            "payload": transformed,
            "ts": datetime.now(UTC).isoformat(),
        }
        await self._redis.lpush(action_key, json.dumps(envelope_out))
        return 1
