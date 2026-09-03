"""services/adapters/__init__.py -- dispatch_action routes each type to its adapter."""

from __future__ import annotations

import httpx
import pytest

from config import ActionConfig
from services.action_target import ActionTarget
from services.adapters import dispatch_action
from services.adapters.base import NonRetryableDispatchError
from services.envelope import ActionEnvelope


def _config() -> ActionConfig:
    return ActionConfig(
        module_name="svc-action",
        module_version="0.1.0",
        module_port=8202,
        pipeline_stage="action",
        log_level="INFO",
        valkey_url="redis://fake",
        queue_scan_pattern="waddles:t:*:c:*:app:*:action",
        queue_scan_interval_seconds=5,
        queue_block_timeout_seconds=5,
        database_url="sqlite:memory",
        db_pool_size=1,
        http_timeout_seconds=5.0,
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


def _envelope() -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community="42",
        app_id="waddles.bot.shoutout.default",
        stage="action",
        payload={"x": 1},
        ts="2026-08-31T12:00:00Z",
        raw="{}",
    )


def _client(handler) -> httpx.AsyncClient:  # noqa: ANN001
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


async def test_routes_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGISTRY_TEST_SECRET", "s3cr3t")
    target = ActionTarget(
        type="webhook", url="https://8.8.8.8/hook", secret_ref="REGISTRY_TEST_SECRET"
    )
    async with _client(lambda r: httpx.Response(200)) as client:
        result = await dispatch_action(
            target, _envelope(), config=_config(), redis_client=None, http_client=client
        )
    assert result.target_type == "webhook"


async def test_routes_rest_api() -> None:
    target = ActionTarget(type="rest_api", url="https://8.8.8.8/api", method="GET")
    async with _client(lambda r: httpx.Response(200)) as client:
        result = await dispatch_action(
            target, _envelope(), config=_config(), redis_client=None, http_client=client
        )
    assert result.target_type == "rest_api"


async def test_routes_message_queue() -> None:
    import fakeredis.aioredis

    redis_client = fakeredis.aioredis.FakeRedis()
    target = ActionTarget(type="message_queue", channel="waddles:notify")
    async with _client(lambda r: httpx.Response(200)) as client:
        result = await dispatch_action(
            target, _envelope(), config=_config(), redis_client=redis_client, http_client=client
        )
    assert result.target_type == "message_queue"
    await redis_client.aclose()


async def test_routes_overlay() -> None:
    target = ActionTarget(type="overlay", surface="giveaway")
    async with _client(lambda r: httpx.Response(200)) as client:
        result = await dispatch_action(
            target, _envelope(), config=_config(), redis_client=None, http_client=client
        )
    assert result.target_type == "overlay"


async def test_routes_email(monkeypatch: pytest.MonkeyPatch) -> None:
    import aiosmtplib

    async def _fake_send(message, **kwargs):  # noqa: ANN001, ANN202
        return ({}, "OK")

    monkeypatch.setattr(aiosmtplib, "send", _fake_send)
    target = ActionTarget(type="email", to_addrs=("ops@example.com",), subject_template="Alert")
    async with _client(lambda r: httpx.Response(200)) as client:
        result = await dispatch_action(
            target, _envelope(), config=_config(), redis_client=None, http_client=client
        )
    assert result.target_type == "email"


async def test_routes_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    from services.adapters.base import AdapterResult

    async def _fake_send(envelope, config, *, http_client):  # noqa: ANN001, ANN202, ARG001
        return AdapterResult(target_type="bundle", detail="ok")

    fake_module = types.ModuleType("tests_registry_fake_bundle")
    fake_module.send = _fake_send  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tests_registry_fake_bundle", fake_module)

    target = ActionTarget(type="bundle", entrypoint="tests_registry_fake_bundle:send")
    async with _client(lambda r: httpx.Response(200)) as client:
        result = await dispatch_action(
            target, _envelope(), config=_config(), redis_client=None, http_client=client
        )
    assert result.target_type == "bundle"


async def test_unregistered_type_raises_non_retryable() -> None:
    """Defense-in-depth test.

    A type with no matching adapter arm can't happen via
    `parse_action_target`'s own validation -- exercised directly here.
    """
    target = ActionTarget(type="carrier_pigeon")  # bypasses parse_action_target on purpose
    async with _client(lambda r: httpx.Response(200)) as client:
        with pytest.raises(NonRetryableDispatchError, match="no adapter registered"):
            await dispatch_action(
                target, _envelope(), config=_config(), redis_client=None, http_client=client
            )
