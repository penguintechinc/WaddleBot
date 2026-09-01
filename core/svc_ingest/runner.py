"""svc-ingest's real poll -> pull -> normalize -> enqueue loop.

Separated from `app.py` so `run_once()`/`_process_bundle()` are directly
unit-testable (mock the distribution poll, real in-memory/fakeredis Valkey
round-trip) without booting a Quart app or an infinite loop. Production
wiring (`app.py`'s `@app.before_serving`) calls `run_forever()`.

Per-bundle Valkey isolation keys reuse `flask_core.stream_pipeline.
bundle_stream_key` exactly (`waddles:t:{tenant}:c:{community}:app:{app_id}:
{stage}`, App Bundle SDK Phase C4): ingest RPOPs raw inbound events off its
OWN `:ingest` key (populated by whatever external receiver/webhook -- out
of scope for this PR) and LPUSHes the normalized result onto that same
bundle's `:process` key, symmetric with `process` popping `:process` and
pushing `:action` (task-specified). This is this PR's own interpretation of
where a normalized ingest event goes next -- the task only specified
process's destination explicitly; using the bundle's own 3-key convention
for ingest's output keeps the naming self-consistent rather than inventing
a fourth key.
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


class IngestRunner:
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
        """Production loop: poll, drain every active bundle's ingest queue, sleep, repeat."""
        self._running = True
        while self._running:
            await self.run_once()
            import asyncio

            await asyncio.sleep(self._poller.next_delay_s)

    async def run_once(self) -> int:
        """One poll+drain cycle; returns total events normalized+enqueued. Never raises."""
        bundles = await self._poller.poll_once()
        total = 0
        for bundle in bundles:
            total += await self._process_bundle(bundle)
        return total

    async def _process_bundle(self, bundle: BundleDistribution) -> int:
        if bundle.entrypoint is None:
            logger.info("ingest.no_entrypoint app_id=%s -- skipping", bundle.app_id)
            return 0

        try:
            normalize_fn = load_entrypoint(bundle.entrypoint)
        except EntrypointLoadError as exc:
            logger.error(
                "ingest.entrypoint_load_failed app_id=%s entrypoint=%s error=%s",
                bundle.app_id,
                bundle.entrypoint,
                exc,
            )
            return 0

        community_str: str | None = (
            str(bundle.community_id) if bundle.community_id is not None else None
        )
        ingest_key = bundle_stream_key(self._tenant_slug, community_str, bundle.app_id, "ingest")
        process_key = bundle_stream_key(self._tenant_slug, community_str, bundle.app_id, "process")

        count = 0
        while True:
            raw = await self._redis.rpop(ingest_key)
            if raw is None:
                break
            count += await self._normalize_and_enqueue(
                raw, normalize_fn, bundle=bundle, process_key=process_key
            )
        return count

    async def _normalize_and_enqueue(
        self, raw: Any, normalize_fn: Any, *, bundle: BundleDistribution, process_key: str
    ) -> int:
        """Parse + normalize one raw event; LPUSH the envelope. Returns 1 on success, 0 on skip."""
        try:
            raw_value = json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.error("ingest.bad_json app_id=%s error=%s", bundle.app_id, exc)
            return 0

        # A raw ingest-queue entry is either a bare event dict, or (if the
        # upstream receiver already wrapped it in our own envelope shape)
        # carries the event under "payload" -- unwrap defensively so either
        # producer shape works without a second queue/format.
        raw_event = (
            raw_value["payload"]
            if isinstance(raw_value, dict) and "payload" in raw_value and "stage" in raw_value
            else raw_value
        )

        try:
            normalized = await normalize_fn(raw_event)
        except Exception as exc:  # noqa: BLE001 - one bad event must never kill the loop
            logger.error("ingest.normalize_failed app_id=%s error=%s", bundle.app_id, exc)
            return 0

        envelope = {
            "tenant": self._tenant_slug,
            "community": bundle.community_id,
            "app_id": bundle.app_id,
            "stage": "process",
            "payload": normalized,
            "ts": datetime.now(UTC).isoformat(),
        }
        await self._redis.lpush(process_key, json.dumps(envelope))
        return 1
