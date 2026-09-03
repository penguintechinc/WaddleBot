"""runner.py -- ActionRunner's real poll -> RPOP -> load -> dispatch -> record loop.

Mirrors `core/svc_process/tests/test_runner.py`'s shape: `redis_client` is
`fakeredis.FakeAsyncRedis` (real LIST semantics, `conftest.py`),
distribution poll mocked at the HTTP transport layer. Audit-log writes go
through a real file-backed sqlite `AsyncDAL` (PORTING.md Gotcha #2 --
`AsyncDAL` calls run in a ThreadPoolExecutor on a different OS thread per
call, and sqlite's `:memory:` DB is connection-scoped, so a second
connection/thread would see a blank DB).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from flask_core import AsyncDAL
from flask_core.stage_runner import BundlePoller
from flask_core.stream_pipeline import bundle_stream_key

from runner import ActionRunner
from services.dispatch_log import init_action_dispatch_log_table
from services.reference_tables import bind_minimal_reference_tables

TENANT = "acme-corp"
DISCORD_APP_ID = "waddles.bot.discord.default"


def _distribution_handler(bundles: list[dict[str, Any]]) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"success": True, "stage": "action", "bundles": bundles, "meta": {}}
        )

    return handler


def _make_poller(http_client_factory: Any, bundles: list[dict[str, Any]]) -> BundlePoller:
    client = http_client_factory(_distribution_handler(bundles))
    return BundlePoller(
        client, "http://hub-api/api/v1/distribution/bundles", stage="action", jwt_provider=lambda: "t"
    )


@pytest.fixture
def dal(tmp_path: Path) -> AsyncDAL:
    """A real file-backed sqlite `AsyncDAL` with `action_dispatch_log` migrated."""
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/runner_test.db", pool_size=1, migrate=True)
    d = async_dal.dal
    d.define_table("tenants", migrate=True)
    d.define_table("communities", d.Field("tenant_id", "reference tenants"), migrate=True)
    d.define_table(
        "action_dispatch_log",
        d.Field("tenant_id", "reference tenants", notnull=True),
        d.Field("community_id", "reference communities"),
        d.Field("app_id", "string", notnull=True),
        d.Field("target_type", "string", notnull=True),
        d.Field("status", "string", notnull=True),
        d.Field("attempt", "integer", default=1),
        d.Field("http_status", "integer"),
        d.Field("detail", "string", default=""),
        d.Field("envelope_ts", "datetime"),
        d.Field("dispatched_at", "datetime"),
        migrate=True,
    )
    d.tenants.insert(id=1)
    d.communities.insert(id=42, tenant_id=1)
    d.commit()
    return async_dal


def _runner(poller: BundlePoller, redis_client: Any, dal: AsyncDAL, http_client: httpx.AsyncClient) -> ActionRunner:
    return ActionRunner(
        poller=poller,
        redis_client=redis_client,
        dal=dal,
        http_client=http_client,
        tenant_slug=TENANT,
        max_retries=1,
        retry_initial_delay=0.01,
        retry_max_delay=0.05,
    )


async def _last_dispatch_row(async_dal: AsyncDAL) -> Any:
    rows = await async_dal.select_async(
        async_dal.dal(async_dal.dal.action_dispatch_log.id > 0),
        orderby=~async_dal.dal.action_dispatch_log.id,
        limitby=(0, 1),
    )
    return rows[0] if rows else None


def _envelope_json(
    *, app_id: str = DISCORD_APP_ID, community: str = "42", payload: dict | None = None, ts: str = "2026-08-31T12:00:00Z"
) -> str:
    return json.dumps(
        {
            "tenant": "1",
            "community": community,
            "app_id": app_id,
            "stage": "action",
            "payload": payload if payload is not None else {"text": "raid incoming!"},
            "ts": ts,
        }
    )


class TestRunOnce:
    async def test_no_bundles_dispatches_nothing(
        self, redis_client: Any, http_client_factory: Any, dal: AsyncDAL
    ) -> None:
        poller = _make_poller(http_client_factory, [])
        async with httpx.AsyncClient() as http_client:
            runner = _runner(poller, redis_client, dal, http_client)
            assert await runner.run_once() == 0

    async def test_real_end_to_end_loads_and_invokes_the_discord_bundle(
        self, redis_client: Any, http_client_factory: Any, dal: AsyncDAL, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail-first proof: a real queue envelope -> poll -> RPOP -> importlib load -> Discord send.

        Not a stubbed/mocked bundle loader -- the real one
        (`flask_core.stage_runner.load_entrypoint`). Only the outbound
        Discord HTTP call is faked (`guarded_request` monkeypatched inside
        the bundle module), per this task's "mock the Discord API"
        requirement.
        """
        monkeypatch.setenv("SVC_ACTION_TEST_DISCORD_TOKEN", "s3cr3t-bot-token")
        captured: dict[str, Any] = {}

        async def _fake_guarded_request(client, method, url, *, headers=None, content=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return httpx.Response(200, json={"id": "42424242"})

        import bundles.discord_send_action as discord_bundle

        monkeypatch.setattr(discord_bundle, "guarded_request", _fake_guarded_request)

        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": DISCORD_APP_ID,
                    "communityId": 42,
                    "entrypoint": "bundles.discord_send_action:send_message",
                    "spec": {},
                    "config": {
                        "channel_id": "555",
                        "bot_token_ref": "SVC_ACTION_TEST_DISCORD_TOKEN",
                        "api_base": "https://8.8.8.8/api/v10",
                    },
                }
            ],
        )
        action_key = bundle_stream_key(TENANT, "42", DISCORD_APP_ID, "action")
        await redis_client.lpush(action_key, _envelope_json())

        async with httpx.AsyncClient() as http_client:
            runner = _runner(poller, redis_client, dal, http_client)
            dispatched = await runner.run_once()

        assert dispatched == 1
        assert await redis_client.rpop(action_key) is None
        assert captured["url"] == "https://8.8.8.8/api/v10/channels/555/messages"
        assert captured["headers"]["Authorization"] == "Bot s3cr3t-bot-token"
        assert captured["json"] == {"content": "raid incoming!"}

        row = await _last_dispatch_row(dal)
        assert row.status == "success"
        assert row.target_type == "bundle"
        assert "message_id=42424242" in row.detail

    async def test_malformed_json_in_queue_is_skipped_not_fatal(
        self, redis_client: Any, http_client_factory: Any, dal: AsyncDAL, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SVC_ACTION_TEST_DISCORD_TOKEN", "s3cr3t-bot-token")

        async def _fake_guarded_request(client, method, url, *, headers=None, content=None, json=None):
            return httpx.Response(200, json={"id": "1"})

        import bundles.discord_send_action as discord_bundle

        monkeypatch.setattr(discord_bundle, "guarded_request", _fake_guarded_request)

        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": DISCORD_APP_ID,
                    "communityId": 42,
                    "entrypoint": "bundles.discord_send_action:send_message",
                    "spec": {},
                    "config": {
                        "channel_id": "555",
                        "bot_token_ref": "SVC_ACTION_TEST_DISCORD_TOKEN",
                        "api_base": "https://8.8.8.8/api/v10",
                    },
                }
            ],
        )
        action_key = bundle_stream_key(TENANT, "42", DISCORD_APP_ID, "action")
        await redis_client.lpush(action_key, "not valid json{{{")
        await redis_client.lpush(action_key, _envelope_json())

        async with httpx.AsyncClient() as http_client:
            runner = _runner(poller, redis_client, dal, http_client)
            dispatched = await runner.run_once()

        assert dispatched == 1

    async def test_unknown_entrypoint_skips_bundle_leaving_queue_intact(
        self, redis_client: Any, http_client_factory: Any, dal: AsyncDAL
    ) -> None:
        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": DISCORD_APP_ID,
                    "communityId": 42,
                    "entrypoint": "bundles.no_such_module:send",
                    "spec": {},
                    "config": {},
                }
            ],
        )
        action_key = bundle_stream_key(TENANT, "42", DISCORD_APP_ID, "action")
        await redis_client.lpush(action_key, _envelope_json())

        async with httpx.AsyncClient() as http_client:
            runner = _runner(poller, redis_client, dal, http_client)
            assert await runner.run_once() == 0

        # A load-failure never even attempts to drain -- the envelope is
        # still queued for the next poll cycle, exactly like ingest/process.
        assert await redis_client.rpop(action_key) is not None

    async def test_bundle_with_no_entrypoint_is_skipped(
        self, redis_client: Any, http_client_factory: Any, dal: AsyncDAL
    ) -> None:
        poller = _make_poller(
            http_client_factory,
            [{"appId": DISCORD_APP_ID, "communityId": 42, "entrypoint": None, "spec": {}, "config": {}}],
        )
        async with httpx.AsyncClient() as http_client:
            runner = _runner(poller, redis_client, dal, http_client)
            assert await runner.run_once() == 0

    async def test_non_retryable_bundle_failure_is_recorded(
        self, redis_client: Any, http_client_factory: Any, dal: AsyncDAL, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing bot token secret -- the bundle's own config error, non-retryable."""
        monkeypatch.delenv("SVC_ACTION_TEST_MISSING_TOKEN", raising=False)
        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": DISCORD_APP_ID,
                    "communityId": 42,
                    "entrypoint": "bundles.discord_send_action:send_message",
                    "spec": {},
                    "config": {
                        "channel_id": "555",
                        "bot_token_ref": "SVC_ACTION_TEST_MISSING_TOKEN",
                        "api_base": "https://8.8.8.8/api/v10",
                    },
                }
            ],
        )
        action_key = bundle_stream_key(TENANT, "42", DISCORD_APP_ID, "action")
        await redis_client.lpush(action_key, _envelope_json())

        async with httpx.AsyncClient() as http_client:
            runner = _runner(poller, redis_client, dal, http_client)
            dispatched = await runner.run_once()

        assert dispatched == 0
        row = await _last_dispatch_row(dal)
        assert row.status == "non_retryable_failure"
        assert row.target_type == "bundle"
        assert row.attempt == 1  # non-retryable -- never enters the retry loop's 2nd attempt

    async def test_retryable_bundle_failure_exhausts_retries_and_is_recorded(
        self, redis_client: Any, http_client_factory: Any, dal: AsyncDAL, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SVC_ACTION_TEST_DISCORD_TOKEN_5XX", "s3cr3t-bot-token")

        async def _fake_guarded_request(client, method, url, *, headers=None, content=None, json=None):
            return httpx.Response(503)

        import bundles.discord_send_action as discord_bundle

        monkeypatch.setattr(discord_bundle, "guarded_request", _fake_guarded_request)

        poller = _make_poller(
            http_client_factory,
            [
                {
                    "appId": DISCORD_APP_ID,
                    "communityId": 42,
                    "entrypoint": "bundles.discord_send_action:send_message",
                    "spec": {},
                    "config": {
                        "channel_id": "555",
                        "bot_token_ref": "SVC_ACTION_TEST_DISCORD_TOKEN_5XX",
                        "api_base": "https://8.8.8.8/api/v10",
                    },
                }
            ],
        )
        action_key = bundle_stream_key(TENANT, "42", DISCORD_APP_ID, "action")
        await redis_client.lpush(action_key, _envelope_json())

        async with httpx.AsyncClient() as http_client:
            runner = _runner(poller, redis_client, dal, http_client)
            dispatched = await runner.run_once()

        assert dispatched == 0
        row = await _last_dispatch_row(dal)
        assert row.status == "retryable_failure"
        assert row.attempt == 2  # max_retries=1 -- initial attempt + 1 retry


class TestRunForeverLifecycle:
    async def test_stop_ends_run_forever(
        self, redis_client: Any, http_client_factory: Any, dal: AsyncDAL
    ) -> None:
        poller = _make_poller(http_client_factory, [])
        poller._poll_interval_s = 0.01  # noqa: SLF001 -- test-only override

        async with httpx.AsyncClient() as http_client:
            runner = _runner(poller, redis_client, dal, http_client)
            task = asyncio.ensure_future(runner.run_forever())
            await asyncio.sleep(0.05)
            runner.stop()
            await asyncio.wait_for(task, timeout=2.0)
            assert task.done()
