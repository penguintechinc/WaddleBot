"""services/runner.py -- ActionRunner end-to-end via fakeredis + sqlite AsyncDAL.

External transports are faked per this task's spec ("mock the HTTP/SMTP
layer + fakeredis for the queue") -- everything else (envelope parsing,
action_target resolution/validation, dispatch routing, retry
classification, audit-log writes) is real code, not mocked.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import fakeredis.aioredis
import httpx
import pytest
from flask_core import AsyncDAL

from config import ActionConfig
from services.runner import ActionRunner


def _config() -> ActionConfig:
    return ActionConfig(
        module_name="svc-action",
        module_version="0.1.0",
        module_port=8202,
        pipeline_stage="action",
        log_level="INFO",
        valkey_url="redis://fake",
        queue_scan_pattern="waddles:t:*:c:*:app:*:action",
        queue_scan_interval_seconds=0.05,
        queue_block_timeout_seconds=1,
        database_url="sqlite:memory",
        db_pool_size=1,
        http_timeout_seconds=2.0,
        max_retries=1,
        retry_initial_delay=0.01,
        retry_max_delay=0.05,
        presentation_base_url="https://8.8.8.8",
        smtp_host="localhost",
        smtp_port=587,
        smtp_user="",
        smtp_password="",
        smtp_use_tls=True,
        smtp_from_addr="noreply@waddlebot.com",
    )


@pytest.fixture
async def wired_runner(tmp_path: Path):
    """An ActionRunner with fakeredis + a real file-backed sqlite AsyncDAL wired in.

    Bypasses `start()`'s real `redis.from_url`/`AsyncDAL(postgres_url)`
    connection logic -- everything downstream of those two objects
    (queue scan, BRPOP, action_target lookup, dispatch, audit log) is the
    real production code path.
    """
    config = _config()
    runner = ActionRunner(config)

    fake_redis = fakeredis.aioredis.FakeRedis()
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/runner_test.db", pool_size=1, migrate=True)
    d = async_dal.dal

    # migrate=True throughout (unlike production's init_action_dispatch_log_table/
    # init_app_bundle_tables, both migrate=False) -- PORTING.md Gotcha #2, same
    # rationale as test_config_lookup.py/test_dispatch_log.py's own fixtures.
    d.define_table("tenants", migrate=True)
    d.define_table("communities", d.Field("tenant_id", "reference tenants"), migrate=True)
    d.define_table(
        "app_catalog",
        d.Field("app_id", "string", notnull=True),
        d.Field("manifest_version", "string", notnull=True),
        d.Field("module", "string", notnull=True),
        d.Field("feature", "string", notnull=True),
        d.Field("provider", "string", notnull=True),
        d.Field("execution_model", "string", notnull=True),
        d.Field("is_default", "boolean", default=False),
        d.Field("compatible_with", "list:string", default=[]),
        d.Field("incompatible_with", "list:string", default=[]),
        d.Field("platform_compatibility", "json", notnull=True),
        d.Field("status", "string", default="active"),
        d.Field("stages", "json", default={}),
        migrate=True,
    )
    d.define_table(
        "app_tenant_availability",
        d.Field("tenant_id", "reference tenants", notnull=True),
        d.Field("app_id", "string", notnull=True),
        d.Field("available", "boolean", default=True),
        d.Field("config_defaults", "json", default={}),
        migrate=True,
    )
    d.define_table(
        "app_activations",
        d.Field("community_id", "reference communities", notnull=True),
        d.Field("tenant_id", "reference tenants", notnull=True),
        d.Field("app_id", "string", notnull=True),
        d.Field("enabled", "boolean", default=True),
        d.Field("config", "json", default={}),
        migrate=True,
    )
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

    runner._redis = fake_redis  # noqa: SLF001 -- test wiring, see docstring
    runner._dal = async_dal
    from services.config_lookup import ActionConfigLookup

    runner._config_lookup = ActionConfigLookup(async_dal)
    runner._http_client = httpx.AsyncClient(follow_redirects=False, timeout=2.0)
    runner._running = True

    yield runner, fake_redis, async_dal

    await runner._http_client.aclose()
    await fake_redis.aclose()
    try:  # known flask_core cross-thread close bug -- see runner.py's stop() comment
        await async_dal.close_async()
    except Exception:  # noqa: BLE001, S110 -- teardown must not fail the test
        pass


def _envelope_json(
    *,
    target: dict | None = None,
    community: str = "42",
    app_id: str = "waddles.bot.shoutout.default",
) -> str:
    payload: dict = {"event": "raid", "raider": "bob"}
    if target is not None:
        payload["target"] = target
    return json.dumps(
        {
            "tenant": "1",
            "community": community,
            "app_id": app_id,
            "stage": "action",
            "payload": payload,
            "ts": "2026-08-31T12:00:00Z",
        }
    )


async def _last_dispatch_row(async_dal: AsyncDAL):
    rows = await async_dal.select_async(
        async_dal.dal(async_dal.dal.action_dispatch_log.id > 0),
        orderby=~async_dal.dal.action_dispatch_log.id,
        limitby=(0, 1),
    )
    return rows[0] if rows else None


async def test_handle_item_dispatches_inline_target_via_message_queue(wired_runner) -> None:
    runner, fake_redis, async_dal = wired_runner
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("waddles:notify")
    await pubsub.get_message(timeout=1)

    raw = _envelope_json(target={"type": "message_queue", "channel": "waddles:notify"})
    await runner._handle_item(raw.encode("utf-8"))  # noqa: SLF001

    message = await pubsub.get_message(timeout=1)
    assert message is not None
    assert json.loads(message["data"])["raider"] == "bob"

    row = await _last_dispatch_row(async_dal)
    assert row.status == "success"
    assert row.target_type == "message_queue"
    await pubsub.aclose()


async def test_handle_item_resolves_target_from_db_config(wired_runner) -> None:
    runner, fake_redis, async_dal = wired_runner
    async_dal.dal.app_activations.insert(
        community_id=42,
        tenant_id=1,
        app_id="waddles.bot.shoutout.default",
        enabled=True,
        config={"action_target": {"type": "message_queue", "channel": "db-resolved"}},
    )
    async_dal.dal.commit()

    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("db-resolved")
    await pubsub.get_message(timeout=1)

    raw = _envelope_json()  # no inline target -- forces the DB lookup path
    await runner._handle_item(raw.encode("utf-8"))  # noqa: SLF001

    message = await pubsub.get_message(timeout=1)
    assert message is not None
    row = await _last_dispatch_row(async_dal)
    assert row.status == "success"
    await pubsub.aclose()


async def test_handle_item_drops_poison_envelope_without_raising(wired_runner) -> None:
    runner, _fake_redis, _async_dal = wired_runner
    await runner._handle_item(b"{not valid json")  # noqa: SLF001  -- must not raise


async def test_handle_item_records_non_retryable_when_no_target_configured(wired_runner) -> None:
    runner, _fake_redis, async_dal = wired_runner
    # community="42" exists (FK-valid, seeded by the fixture) but has no
    # app_activations/app_tenant_availability row for this app_id.
    raw = _envelope_json(app_id="waddles.bot.unknown.default")
    await runner._handle_item(raw.encode("utf-8"))  # noqa: SLF001

    row = await _last_dispatch_row(async_dal)
    assert row.status == "non_retryable_failure"
    assert "no action_target configured" in row.detail


async def test_handle_item_records_non_retryable_for_invalid_target_config(wired_runner) -> None:
    runner, _fake_redis, async_dal = wired_runner
    raw = _envelope_json(target={"type": "webhook"})  # missing required url/secret_ref
    await runner._handle_item(raw.encode("utf-8"))  # noqa: SLF001

    row = await _last_dispatch_row(async_dal)
    assert row.status == "non_retryable_failure"
    assert "invalid action_target" in row.detail


async def test_loop_consumes_from_the_bundle_stream_key(wired_runner) -> None:
    """End-to-end: SCAN discovers the key, BRPOP pops it, the item is dispatched."""
    runner, fake_redis, async_dal = wired_runner
    key = "waddles:t:1:c:42:app:waddles.bot.shoutout.default:action"
    raw = _envelope_json(target={"type": "message_queue", "channel": "loop-test"})
    await fake_redis.lpush(key, raw)

    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("loop-test")
    await pubsub.get_message(timeout=1)

    loop_task = asyncio.create_task(runner._loop())  # noqa: SLF001
    try:
        message = await asyncio.wait_for(pubsub.get_message(timeout=2), timeout=3)
    finally:
        runner._running = False
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass
        await pubsub.aclose()

    assert message is not None
    assert json.loads(message["data"])["raider"] == "bob"


async def test_handle_item_records_non_retryable_dispatch_failure(wired_runner) -> None:
    """A webhook target with a missing secret env var -- adapter-level non-retryable failure."""
    runner, _fake_redis, async_dal = wired_runner
    raw = _envelope_json(
        target={
            "type": "webhook",
            "url": "https://8.8.8.8/hook",
            "secret_ref": "SVC_ACTION_TEST_UNSET_SECRET",
        }
    )
    await runner._handle_item(raw.encode("utf-8"))  # noqa: SLF001

    row = await _last_dispatch_row(async_dal)
    assert row.status == "non_retryable_failure"
    assert row.target_type == "webhook"


async def test_handle_item_records_retryable_failure_after_exhausting_retries(
    wired_runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SSRF-safe but unreachable webhook target -- retries exhausted, retryable_failure logged."""
    runner, _fake_redis, async_dal = wired_runner
    monkeypatch.setenv("SVC_ACTION_TEST_RETRY_SECRET", "s3cr3t")

    async def _always_5xx(client, method, url, **kwargs):  # noqa: ANN001, ANN202, ARG001
        return httpx.Response(503, request=httpx.Request(method, url))

    import services.adapters.webhook as webhook_module

    monkeypatch.setattr(webhook_module, "guarded_request", _always_5xx)

    raw = _envelope_json(
        target={
            "type": "webhook",
            "url": "https://8.8.8.8/hook",
            "secret_ref": "SVC_ACTION_TEST_RETRY_SECRET",
        }
    )
    await runner._handle_item(raw.encode("utf-8"))  # noqa: SLF001

    row = await _last_dispatch_row(async_dal)
    assert row.status == "retryable_failure"
    assert row.attempt == runner._config.max_retries + 1  # noqa: SLF001


async def test_handle_item_loads_and_invokes_the_discord_bundle_end_to_end(
    wired_runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-first proof: a real action envelope -> catalog lookup -> importlib load -> Discord send.

    Exercises the actual bundle-runtime path this task exists to prove:
    `app_catalog.stages.action.entrypoint` (seeded here exactly as
    migration 082 seeds it in production) drives `_handle_item` to load
    `bundles.discord_send_action:send_message` via `flask_core.
    stage_runner.load_entrypoint` and invoke it against the popped
    envelope -- not a stubbed/mocked bundle loader, the real one. Only the
    outbound Discord HTTP call is faked (`monkeypatch` on `guarded_request`
    inside the bundle module), per this task's "mock the Discord API"
    requirement.
    """
    runner, _fake_redis, async_dal = wired_runner
    async_dal.dal.app_catalog.insert(
        app_id="waddles.bot.discord.default",
        manifest_version="1.0.0",
        module="bot",
        feature="waddles.bot.discord",
        provider="builtin",
        execution_model="native",
        platform_compatibility={},
        stages={
            "action": {
                "entrypoint": "bundles.discord_send_action:send_message",
                "config": {
                    "channel_id": "555",
                    "bot_token_ref": "SVC_ACTION_TEST_DISCORD_TOKEN",
                    "api_base": "https://8.8.8.8/api/v10",
                },
            }
        },
    )
    async_dal.dal.commit()
    monkeypatch.setenv("SVC_ACTION_TEST_DISCORD_TOKEN", "s3cr3t-bot-token")

    captured = {}

    async def _fake_guarded_request(client, method, url, *, headers=None, content=None, json=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return httpx.Response(200, json={"id": "42424242"})

    import bundles.discord_send_action as discord_bundle

    monkeypatch.setattr(discord_bundle, "guarded_request", _fake_guarded_request)

    # `_envelope_json`'s default payload only carries {"event", "raider"};
    # the discord bundle requires a 'text' field, so build the raw JSON
    # directly here rather than layering an override onto that helper.
    raw = json.dumps(
        {
            "tenant": "1",
            "community": "42",
            "app_id": "waddles.bot.discord.default",
            "stage": "action",
            "payload": {"text": "raid incoming!"},
            "ts": "2026-08-31T12:00:00Z",
        }
    )

    await runner._handle_item(raw.encode("utf-8"))  # noqa: SLF001

    assert captured["url"] == "https://8.8.8.8/api/v10/channels/555/messages"
    assert captured["headers"]["Authorization"] == "Bot s3cr3t-bot-token"
    assert captured["json"] == {"content": "raid incoming!"}

    row = await _last_dispatch_row(async_dal)
    assert row.status == "success"
    assert row.target_type == "bundle"
    assert "message_id=42424242" in row.detail


async def test_handle_item_catalog_entrypoint_takes_precedence_over_action_target(
    wired_runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bundle with a catalog-declared action entrypoint ignores any inline `action_target`."""
    runner, _fake_redis, async_dal = wired_runner
    async_dal.dal.app_catalog.insert(
        app_id="waddles.bot.discord.default",
        manifest_version="1.0.0",
        module="bot",
        feature="waddles.bot.discord",
        provider="builtin",
        execution_model="native",
        platform_compatibility={},
        stages={
            "action": {
                "entrypoint": "bundles.discord_send_action:send_message",
                "config": {
                    "channel_id": "555",
                    "bot_token_ref": "SVC_ACTION_TEST_DISCORD_TOKEN_2",
                    "api_base": "https://8.8.8.8/api/v10",
                },
            }
        },
    )
    async_dal.dal.commit()
    monkeypatch.setenv("SVC_ACTION_TEST_DISCORD_TOKEN_2", "s3cr3t-bot-token")

    async def _fake_guarded_request(client, method, url, *, headers=None, content=None, json=None):
        return httpx.Response(200, json={"id": "1"})

    import bundles.discord_send_action as discord_bundle

    monkeypatch.setattr(discord_bundle, "guarded_request", _fake_guarded_request)

    # Inline `action_target` present too -- must be ignored in favor of the
    # catalog entrypoint (never dispatched to message_queue).
    raw = json.dumps(
        {
            "tenant": "1",
            "community": "42",
            "app_id": "waddles.bot.discord.default",
            "stage": "action",
            "payload": {
                "text": "raid incoming!",
                "target": {"type": "message_queue", "channel": "should-not-be-used"},
            },
            "ts": "2026-08-31T12:00:00Z",
        }
    )

    await runner._handle_item(raw.encode("utf-8"))  # noqa: SLF001

    row = await _last_dispatch_row(async_dal)
    assert row.target_type == "bundle"


def test_parse_envelope_ts_returns_none_for_malformed_ts() -> None:
    from services.runner import _parse_envelope_ts

    assert _parse_envelope_ts("not-a-timestamp") is None


async def test_stop_on_never_started_runner_is_a_safe_noop() -> None:
    """`stop()` before `start()` (all connections None) must not raise."""
    runner = ActionRunner(_config())
    await runner.stop()  # every `if self._x is not None` branch is False here
