"""Tests for `runner.ProcessRunner` -- the real poll -> RPOP -> transform -> LPUSH loop.

Mirrors `core/svc_ingest/tests/test_runner.py`'s shape -- `redis_client` is
`fakeredis.FakeAsyncRedis` (real LIST semantics), distribution poll mocked
at the HTTP transport layer.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from flask_core.stage_runner import BundlePoller
from flask_core.stream_pipeline import bundle_stream_key

from runner import ProcessRunner

TENANT = "acme-corp"
APP_ID = "waddles.core.demo.echo"


def _distribution_handler(bundles: list[dict[str, Any]]) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"success": True, "stage": "process", "bundles": bundles, "meta": {}}
        )

    return handler


def _make_poller(http_client_factory: Any, bundles: list[dict[str, Any]]) -> BundlePoller:
    client = http_client_factory(_distribution_handler(bundles))
    return BundlePoller(
        client,
        "http://hub-api/api/v1/distribution/bundles",
        stage="process",
        jwt_provider=lambda: "t",
    )


class TestRunOnce:
    async def test_no_bundles_processes_nothing(
        self, redis_client: Any, http_client_factory: Any
    ) -> None:
        poller = _make_poller(http_client_factory, [])
        runner = ProcessRunner(poller=poller, redis_client=redis_client, tenant_slug=TENANT)
        assert await runner.run_once() == 0

    async def test_real_valkey_roundtrip_transforms_and_enqueues_to_action(
        self, redis_client: Any, http_client_factory: Any
    ) -> None:
        """Fail-first proof: prove a real LPUSH/RPOP round trip onto the process->action key.

        Matches the task's explicit key requirement:
        `waddles:t:{tenant}:c:{community}:app:{app_id}:action`.
        """
        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": APP_ID,
                    "communityId": 42,
                    "entrypoint": "bundles.echo_process:transform",
                    "spec": {},
                    "config": {},
                }
            ],
        )
        runner = ProcessRunner(poller=poller, redis_client=redis_client, tenant_slug=TENANT)

        process_key = bundle_stream_key(TENANT, "42", APP_ID, "process")
        await redis_client.lpush(
            process_key,
            json.dumps(
                {
                    "tenant": TENANT,
                    "community": 42,
                    "app_id": APP_ID,
                    "stage": "process",
                    "payload": {"platform": "twitch", "payload": {"text": "hello there"}},
                    "ts": "2026-01-01T00:00:00+00:00",
                }
            ),
        )

        processed = await runner.run_once()
        assert processed == 1

        assert await redis_client.rpop(process_key) is None

        action_key = bundle_stream_key(TENANT, "42", APP_ID, "action")
        assert action_key == f"waddles:t:{TENANT}:c:42:app:{APP_ID}:action"
        raw_out = await redis_client.rpop(action_key)
        assert raw_out is not None
        envelope = json.loads(raw_out)
        assert envelope["stage"] == "action"
        assert envelope["app_id"] == APP_ID
        assert envelope["community"] == 42
        assert envelope["payload"]["payload"]["text"] == "HELLO THERE"
        assert envelope["payload"]["payload"]["word_count"] == 2
        assert envelope["payload"]["processed"] is True

    async def test_malformed_json_in_queue_is_skipped_not_fatal(
        self, redis_client: Any, http_client_factory: Any
    ) -> None:
        """A non-JSON raw value on the `:process` key must not crash the drain loop."""
        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": APP_ID,
                    "communityId": None,
                    "entrypoint": "bundles.echo_process:transform",
                    "spec": {},
                    "config": {},
                }
            ],
        )
        runner = ProcessRunner(poller=poller, redis_client=redis_client, tenant_slug=TENANT)
        process_key = bundle_stream_key(TENANT, None, APP_ID, "process")
        await redis_client.lpush(process_key, "not valid json{{{")
        # Well-formed envelope -- see test_malformed_event_is_skipped_not_fatal's
        # own comment for why "payload" nests one level deeper.
        await redis_client.lpush(
            process_key, json.dumps({"payload": {"payload": {"text": "still works"}}})
        )

        processed = await runner.run_once()
        assert processed == 1

    async def test_malformed_event_is_skipped_not_fatal(
        self, redis_client: Any, http_client_factory: Any
    ) -> None:
        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": APP_ID,
                    "communityId": None,
                    "entrypoint": "bundles.echo_process:transform",
                    "spec": {},
                    "config": {},
                }
            ],
        )
        runner = ProcessRunner(poller=poller, redis_client=redis_client, tenant_slug=TENANT)
        process_key = bundle_stream_key(TENANT, None, APP_ID, "process")
        # Outer envelope's "payload" is missing entirely -- the unwrapped
        # `event` is `{"stage": "process"}`, so transform()'s own
        # `event.get("payload")` check raises ValueError.
        await redis_client.lpush(process_key, json.dumps({"stage": "process"}))
        # A well-formed envelope: outer "payload" is the normalized event
        # object (echo_ingest.normalize's own output shape), which itself
        # nests "payload": {"text": ...} -- matches the real ingest->process
        # envelope contract exactly (see test_real_valkey_roundtrip... above).
        await redis_client.lpush(
            process_key, json.dumps({"payload": {"payload": {"text": "still works"}}})
        )

        processed = await runner.run_once()
        assert processed == 1

    async def test_unknown_entrypoint_skips_bundle_gracefully(
        self, redis_client: Any, http_client_factory: Any
    ) -> None:
        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": APP_ID,
                    "communityId": None,
                    "entrypoint": "bundles.no_such_module:transform",
                    "spec": {},
                    "config": {},
                }
            ],
        )
        runner = ProcessRunner(poller=poller, redis_client=redis_client, tenant_slug=TENANT)
        assert await runner.run_once() == 0

    async def test_bundle_with_no_entrypoint_is_skipped(
        self, redis_client: Any, http_client_factory: Any
    ) -> None:
        poller = _make_poller(
            http_client_factory,
            [{"appId": APP_ID, "communityId": None, "entrypoint": None, "spec": {}, "config": {}}],
        )
        runner = ProcessRunner(poller=poller, redis_client=redis_client, tenant_slug=TENANT)
        assert await runner.run_once() == 0


class TestRunForeverLifecycle:
    async def test_stop_ends_run_forever(self, redis_client: Any, http_client_factory: Any) -> None:
        import asyncio

        poller = _make_poller(http_client_factory, [])
        poller._poll_interval_s = 0.01  # noqa: SLF001 - test-only override
        runner = ProcessRunner(poller=poller, redis_client=redis_client, tenant_slug=TENANT)

        task = asyncio.ensure_future(runner.run_forever())
        await asyncio.sleep(0.05)
        runner.stop()
        await asyncio.wait_for(task, timeout=2.0)
        assert task.done()
