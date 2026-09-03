"""ACTION stage-runner: BRPOP fan-in loop over process->action Valkey queue keys.

Mirrors the App Bundle SDK's stage-runner model (docs/plans/
2026-08-31-app-bundle-sdk-design.md Sec6): dequeue one envelope, resolve
its bundle's declared `action_target`, dispatch via the matching adapter
with retry-with-backoff on retryable failures, audit-log the outcome.

Key discovery + BRPOP: `queue_scanner.scan_action_keys` periodically `SCAN`s
for keys matching `waddles:t:*:c:*:app:*:action` (this task's spec); the
runner blocks on `BRPOP` across that snapshot, re-scanning whenever a
`BRPOP` call times out with nothing popped (so a bundle activated after
the last scan is picked up on the loop's next iteration) or the scan
interval elapses, whichever comes first.

Bundle-script precedence (added by the Discord bundle-runtime proof):
`_handle_item` checks `app_catalog.stages.action.entrypoint`
(`config_lookup.py::get_action_entrypoint`) *before* the generic
`action_target` resolution below -- a bundle that declares an action-stage
script entrypoint (the same `module:function`/importlib convention
ingest/process bundles use, `flask_core.stage_runner.load_entrypoint`)
always dispatches through it via the synthesized `ActionTarget(type=
"bundle", ...)` (`services/adapters/bundle.py`); every other bundle keeps
resolving a generic webhook/rest_api/message_queue/overlay/email target
exactly as before -- purely additive, no existing dispatch path changes.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

import httpx
import redis.asyncio as redis
from flask_core import AsyncDAL, get_logger
from flask_core.app_bundle_tables import init_app_bundle_tables
from flask_core.circuit_breaker import retry_with_backoff

from config import ActionConfig
from services.action_target import ActionTarget, ActionTargetError, parse_action_target
from services.adapters import dispatch_action
from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.config_lookup import ActionConfigLookup
from services.dispatch_log import init_action_dispatch_log_table, record_dispatch
from services.envelope import ActionEnvelope, EnvelopeError, parse_envelope
from services.queue_scanner import scan_action_keys
from services.reference_tables import bind_minimal_reference_tables

logger = get_logger(__name__)


def _parse_envelope_ts(ts: str) -> datetime | None:
    """Best-effort ISO8601 parse of `envelope.ts` -- audit-log-only, never fatal."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


class ActionRunner:
    """Owns the Valkey/DB connections and the BRPOP dispatch loop's lifecycle."""

    def __init__(self, config: ActionConfig) -> None:
        """Store `config`; connections open lazily in `start()`, not here."""
        self._config = config
        self._redis: redis.Redis | None = None
        self._dal: AsyncDAL | None = None
        self._config_lookup: ActionConfigLookup | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Open connections and start the background dispatch loop."""
        self._redis = redis.from_url(self._config.valkey_url, decode_responses=False)
        self._dal = AsyncDAL(
            self._config.database_url,
            pool_size=self._config.db_pool_size,
            migrate=False,
        )
        bind_minimal_reference_tables(self._dal.dal)
        init_action_dispatch_log_table(self._dal.dal)
        init_app_bundle_tables(self._dal.dal)
        self._config_lookup = ActionConfigLookup(self._dal)
        self._http_client = httpx.AsyncClient(
            follow_redirects=False, timeout=self._config.http_timeout_seconds
        )
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "svc-action runner started (valkey_scheme=%s)",
            self._config.valkey_url.split("://")[0],
        )

    async def stop(self) -> None:
        """Stop the dispatch loop and close all connections."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._http_client is not None:
            await self._http_client.aclose()
        if self._redis is not None:
            await self._redis.aclose()
        if self._dal is not None:
            # Defensive try/except, matching hub_api/app.py's established
            # shutdown pattern: AsyncDAL.close_async() runs pydal's
            # DAL.close() inside its ThreadPoolExecutor, on a different
            # thread than the one that created the DAL -- pydal's close()
            # reads THREAD_LOCAL._pydal_db_instances_, only ever populated
            # on the *creating* thread, so a cross-thread close raises
            # AttributeError (a flask_core bug, out of scope to patch a
            # shared lib from this PR). Failing to release the pool
            # cleanly on shutdown must never crash the ASGI lifespan.
            try:
                await self._dal.close_async()
            except Exception as exc:  # noqa: BLE001 -- shutdown must not raise
                logger.warning("error closing DAL on shutdown: %s", exc)
        logger.info("svc-action runner stopped")

    async def _loop(self) -> None:
        assert self._redis is not None
        keys: list[str] = []
        last_scan = 0.0

        while self._running:
            now = time.monotonic()
            if not keys or (now - last_scan) >= self._config.queue_scan_interval_seconds:
                try:
                    keys = await scan_action_keys(
                        self._redis, pattern=self._config.queue_scan_pattern
                    )
                except redis.RedisError as exc:
                    logger.error("queue key scan failed: %s", exc)
                    keys = []
                last_scan = now

            if not keys:
                await asyncio.sleep(self._config.queue_scan_interval_seconds)
                continue

            try:
                result = await self._redis.brpop(
                    keys, timeout=self._config.queue_block_timeout_seconds
                )
            except redis.RedisError as exc:
                logger.error("BRPOP failed: %s", exc)
                await asyncio.sleep(1.0)
                continue

            if result is None:
                continue  # timed out with nothing popped -- loop re-scans if interval elapsed

            _popped_key, raw_value = result
            await self._handle_item(raw_value)

    async def _handle_item(self, raw_value: bytes | str) -> None:
        try:
            envelope = parse_envelope(raw_value)
        except EnvelopeError as exc:
            logger.error("dropping malformed action envelope: %s", exc)
            return

        ctx = f"tenant={envelope.tenant} community={envelope.community} app_id={envelope.app_id}"

        assert self._config_lookup is not None
        bundle_entrypoint = await self._config_lookup.get_action_entrypoint(app_id=envelope.app_id)
        if bundle_entrypoint is not None:
            entrypoint_path, bundle_config = bundle_entrypoint
            bundle_target = ActionTarget(
                type="bundle", entrypoint=entrypoint_path, bundle_config=bundle_config
            )
            await self._dispatch_with_retry(envelope, bundle_target, ctx)
            return

        raw_target = envelope.payload.get("target")
        if not raw_target:
            assert self._config_lookup is not None
            raw_target = await self._config_lookup.get_action_target_config(
                tenant=envelope.tenant, community=envelope.community, app_id=envelope.app_id
            )

        if not raw_target:
            logger.warning("no action_target configured (%s)", ctx)
            await self._record(
                envelope,
                target_type="unknown",
                status="non_retryable_failure",
                attempt=1,
                http_status=None,
                detail="no action_target configured",
            )
            return

        try:
            target = parse_action_target(raw_target)
        except ActionTargetError as exc:
            logger.error("invalid action_target config (%s): %s", ctx, exc)
            await self._record(
                envelope,
                target_type=str(raw_target.get("type", "unknown")),
                status="non_retryable_failure",
                attempt=1,
                http_status=None,
                detail=f"invalid action_target: {exc}",
            )
            return

        await self._dispatch_with_retry(envelope, target, ctx)

    async def _dispatch_with_retry(
        self, envelope: ActionEnvelope, target: ActionTarget, ctx: str
    ) -> None:
        assert self._redis is not None and self._http_client is not None
        # Local captures so the closure below sees the narrowed (non-None)
        # type -- mypy does not narrow `self.*` attributes across a nested
        # function boundary even after the assert above.
        redis_client = self._redis
        http_client = self._http_client
        attempt_count = 0

        async def _attempt() -> AdapterResult:
            nonlocal attempt_count
            attempt_count += 1
            return await dispatch_action(
                target,
                envelope,
                config=self._config,
                redis_client=redis_client,
                http_client=http_client,
            )

        try:
            result = await retry_with_backoff(
                _attempt,
                max_retries=self._config.max_retries,
                initial_delay=self._config.retry_initial_delay,
                max_delay=self._config.retry_max_delay,
                exceptions=(RetryableDispatchError,),
            )
        except NonRetryableDispatchError as exc:
            logger.error(
                "dispatch failed, non-retryable (%s target_type=%s): %s", ctx, target.type, exc
            )
            await self._record(
                envelope,
                target_type=target.type,
                status="non_retryable_failure",
                attempt=attempt_count,
                http_status=exc.http_status,
                detail=str(exc),
            )
            return
        except RetryableDispatchError as exc:
            logger.error(
                "dispatch failed after retries exhausted (%s target_type=%s): %s",
                ctx,
                target.type,
                exc,
            )
            await self._record(
                envelope,
                target_type=target.type,
                status="retryable_failure",
                attempt=attempt_count,
                http_status=exc.http_status,
                detail=str(exc),
            )
            return

        logger.info("dispatch succeeded (%s target_type=%s): %s", ctx, target.type, result.detail)
        await self._record(
            envelope,
            target_type=result.target_type,
            status="success",
            attempt=attempt_count,
            http_status=result.http_status,
            detail=result.detail,
        )

    async def _record(
        self,
        envelope: ActionEnvelope,
        *,
        target_type: str,
        status: str,
        attempt: int,
        http_status: int | None,
        detail: str,
    ) -> None:
        assert self._dal is not None
        try:
            await record_dispatch(
                self._dal,
                tenant_id=int(envelope.tenant),
                community_id=int(envelope.community) if envelope.community else None,
                app_id=envelope.app_id,
                target_type=target_type,
                status=status,
                attempt=attempt,
                http_status=http_status,
                detail=detail,
                envelope_ts=_parse_envelope_ts(envelope.ts),
            )
        except Exception as exc:  # audit-log write failure must never mask the dispatch outcome
            logger.error("failed to write action_dispatch_log row: %s", exc)
