"""`services/streaming_proxy_service.py` -- unit tests for the real HTTP-forwarding logic.

`tests/test_v1_streaming_blueprint.py` monkeypatches `VideoProxyClient`'s
methods entirely (no real network I/O in route-level tests) -- this file
closes the gap the same way `tests/test_event_calendar_proxy.py` does for
`event_calendar_proxy.py`: `httpx.MockTransport` (real `httpx`
request/response objects, no real socket) exercising every client method's
success/404/409/transport-failure branch, plus `validate_destination_input`'s
standalone validation branches.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from services.errors import ApiError
from services.streaming_proxy_service import (
    VideoProxyClient,
    VideoProxyConfig,
    validate_destination_input,
)

_CONFIG = VideoProxyConfig(base_url="http://video_proxy_module:8014", timeout_seconds=1.0)


def _patch_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Force every `httpx.AsyncClient` built inside the module onto a mock transport.

    Mirrors `tests/test_event_calendar_proxy.py::_patch_transport` exactly.
    """
    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self: httpx.AsyncClient, *args: object, **kwargs: object) -> None:
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


def _ok(body: object) -> Callable[[httpx.Request], httpx.Response]:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    return handler


def _status(code: int, body: object | None = None) -> Callable[[httpx.Request], httpx.Response]:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(code, json=body if body is not None else {})

    return handler


def _transport_error(_: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused")


class TestVideoProxyConfigFromEnv:
    def test_defaults_with_no_env_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VIDEO_PROXY_API_URL", raising=False)
        cfg = VideoProxyConfig.from_env()
        assert cfg.base_url == "http://video_proxy_module:8014"

    def test_reads_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VIDEO_PROXY_API_URL", "http://video-proxy.svc:9000")
        cfg = VideoProxyConfig.from_env()
        assert cfg.base_url == "http://video-proxy.svc:9000"


class TestValidateDestinationInput:
    def test_missing_fields_is_400(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            validate_destination_input("", "", "")
        assert exc_info.value.status_code == 400

    def test_invalid_platform_is_400(self) -> None:
        with pytest.raises(ApiError):
            validate_destination_input("myspace", "rtmp://8.8.8.8/x", "key")

    def test_invalid_url_prefix_is_400(self) -> None:
        with pytest.raises(ApiError):
            validate_destination_input("twitch", "https://8.8.8.8/x", "key")

    def test_success_lowercases_platform(self) -> None:
        assert validate_destination_input("TWITCH", "rtmp://8.8.8.8/x", "key") == "twitch"


class TestGetConfig:
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _ok({"rtmpPort": 1935}))
        client = VideoProxyClient(_CONFIG)
        assert await client.get_config(1) == {"rtmpPort": 1935}

    async def test_404_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _status(404))
        client = VideoProxyClient(_CONFIG)
        assert await client.get_config(1) is None

    async def test_transport_error_is_bad_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _transport_error)
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError) as exc_info:
            await client.get_config(1)
        assert exc_info.value.status_code == 400


class TestCreateConfig:
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _ok({"rtmpPort": 1935}))
        client = VideoProxyClient(_CONFIG)
        result = await client.create_config(1, rtmp_port=1935, http_port=None, enabled=True)
        assert result == {"rtmpPort": 1935}

    async def test_409_is_conflict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _status(409))
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError) as exc_info:
            await client.create_config(1, rtmp_port=None, http_port=None, enabled=True)
        assert exc_info.value.status_code == 409

    async def test_transport_error_is_bad_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _transport_error)
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError) as exc_info:
            await client.create_config(1, rtmp_port=None, http_port=None, enabled=True)
        assert exc_info.value.status_code == 400


class TestRegenerateKey:
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _ok({"streamKey": "abc123"}))
        client = VideoProxyClient(_CONFIG)
        assert await client.regenerate_key(1) == "abc123"

    async def test_404_is_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _status(404))
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError) as exc_info:
            await client.regenerate_key(1)
        assert exc_info.value.status_code == 404

    async def test_transport_error_is_bad_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _transport_error)
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError):
            await client.regenerate_key(1)


class TestGetDestinations:
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _ok({"destinations": [{"id": 1}]}))
        client = VideoProxyClient(_CONFIG)
        assert await client.get_destinations(1) == [{"id": 1}]

    async def test_transport_error_is_bad_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _transport_error)
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError):
            await client.get_destinations(1)


class TestAddDestination:
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _ok({"destination": {"id": 1}}))
        client = VideoProxyClient(_CONFIG)
        result = await client.add_destination(
            1,
            platform="twitch",
            rtmp_url="rtmp://8.8.8.8/x",
            stream_key="k",
            enabled=True,
            force_cut=False,
        )
        assert result == {"id": 1}

    async def test_404_is_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _status(404))
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError) as exc_info:
            await client.add_destination(
                1,
                platform="twitch",
                rtmp_url="rtmp://8.8.8.8/x",
                stream_key="k",
                enabled=True,
                force_cut=False,
            )
        assert exc_info.value.status_code == 404

    async def test_transport_error_is_bad_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _transport_error)
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError):
            await client.add_destination(
                1,
                platform="twitch",
                rtmp_url="rtmp://8.8.8.8/x",
                stream_key="k",
                enabled=True,
                force_cut=False,
            )


class TestRemoveDestination:
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _status(200))
        client = VideoProxyClient(_CONFIG)
        await client.remove_destination(1, 5)  # no exception == success

    async def test_404_is_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _status(404))
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError) as exc_info:
            await client.remove_destination(1, 5)
        assert exc_info.value.status_code == 404

    async def test_transport_error_is_bad_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _transport_error)
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError):
            await client.remove_destination(1, 5)


class TestToggleForceCut:
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _ok({"destination": {"id": 1, "forceCut": True}}))
        client = VideoProxyClient(_CONFIG)
        result = await client.toggle_force_cut(1, 5, force_cut=True)
        assert result == {"id": 1, "forceCut": True}

    async def test_404_is_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _status(404))
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError) as exc_info:
            await client.toggle_force_cut(1, 5, force_cut=True)
        assert exc_info.value.status_code == 404

    async def test_transport_error_is_bad_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _transport_error)
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError):
            await client.toggle_force_cut(1, 5, force_cut=True)


class TestGetStatus:
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _ok({"active": True, "destinations": []}))
        client = VideoProxyClient(_CONFIG)
        assert await client.get_status(1) == {"active": True, "destinations": []}

    async def test_404_returns_inactive_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _status(404))
        client = VideoProxyClient(_CONFIG)
        assert await client.get_status(1) == {"active": False, "destinations": []}

    async def test_transport_error_is_bad_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_transport(monkeypatch, _transport_error)
        client = VideoProxyClient(_CONFIG)
        with pytest.raises(ApiError):
            await client.get_status(1)
