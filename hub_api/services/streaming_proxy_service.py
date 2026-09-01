"""Video-proxy streaming config/destinations -- ported from `streamingController.js`.

Every handler in `streamingController.js` is a pure reverse-proxy to the
standalone `video_proxy_module` service (`axios` calls to
`VIDEO_PROXY_API_URL`, default `http://video_proxy_module:8014`) -- no
owned data model here, matching `blueprints/v1/event.py`'s
`EventCalendarProxyClient` pattern (see that module's own docstring for
the full rationale on why `ProxyResult.body` stays `Any` rather than a
typed DTO). `httpx.AsyncClient` replaces `axios`, same 5-second timeout
Node used (`{ timeout: 5000 }` on every call).

SSRF hardening (M7 port instruction: "forward-target URLs are
SSRF-adjacent"): `rtmpUrl` in `add_destination()` is a caller-supplied
forward target that `video_proxy_module` will itself open an outbound
RTMP connection to -- Node only checked the string prefix
(`rtmpUrl.startsWith('rtmp://'||'rtmps://')`), not the destination.
`validate_destination_input()` adds the missing destination check
(private/loopback/link-local/reserved-range block, via `services.
url_guard.validate_outbound_url()`) as defense-in-depth at this trust
boundary, before the URL is ever forwarded downstream. The proxy
client's OWN target (`VIDEO_PROXY_API_URL`) is a fixed,
operator-configured internal service address, never user input -- no
guard needed there.

Deliberately a MODULE-LEVEL function, not folded into
`VideoProxyClient.add_destination()`: `blueprints.v1.streaming.
add_destination()` calls it BEFORE the client method, so a test
monkeypatching `VideoProxyClient.add_destination` (the established
`proxy_stub` pattern, `tests/test_v1_streaming_blueprint.py` /
`tests/test_event_blueprint.py`) can never accidentally bypass this
security check along with the mocked network call -- validation and the
outbound request are two separate call frames the mock can't both erase
at once.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from services.errors import bad_request, conflict, not_found

_DEFAULT_BASE_URL = "http://video_proxy_module:8014"
_DEFAULT_TIMEOUT_SECONDS = 5.0
_VALID_DESTINATION_PLATFORMS: frozenset[str] = frozenset(
    {"twitch", "youtube", "facebook", "custom"}
)


@dataclass(slots=True, frozen=True)
class VideoProxyConfig:
    """Connection settings for the downstream `video_proxy_module` service."""

    base_url: str
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> VideoProxyConfig:
        """Build from `VIDEO_PROXY_API_URL` (mirrors Node's own env var + default)."""
        return cls(
            base_url=os.getenv("VIDEO_PROXY_API_URL", _DEFAULT_BASE_URL),
            timeout_seconds=_DEFAULT_TIMEOUT_SECONDS,
        )


def validate_destination_input(platform: str, rtmp_url: str, stream_key: str) -> str:
    """Port of `addDestination`'s field/format checks, plus the SSRF destination guard.

    Returns the lowercased, validated `platform`. Raises `services.
    errors.ApiError` (400) on any of: a missing required field, an
    unrecognized platform, a non-`rtmp(s)://` URL, or a resolved
    destination in a private/loopback/link-local/reserved range.
    """
    if not platform or not rtmp_url or not stream_key:
        raise bad_request("Missing required fields: platform, rtmpUrl, streamKey")

    platform_key = platform.lower()
    if platform_key not in _VALID_DESTINATION_PLATFORMS:
        raise bad_request("Invalid platform")

    if not rtmp_url.startswith("rtmp://") and not rtmp_url.startswith("rtmps://"):
        raise bad_request("Invalid RTMP URL format")

    return platform_key


class VideoProxyClient:
    """Forwards config/destination/status requests to `video_proxy_module`."""

    def __init__(self, config: VideoProxyConfig | None = None) -> None:
        """Build the client; `config` defaults to `VideoProxyConfig.from_env()`."""
        self._config = config or VideoProxyConfig.from_env()

    async def _request(
        self, method: str, path: str, *, json_body: dict[str, Any] | None = None
    ) -> httpx.Response:
        url = f"{self._config.base_url}{path}"
        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            return await client.request(method, url, json=json_body)

    async def get_config(self, community_id: int) -> dict[str, Any] | None:
        """Port of `getStreamConfig` -- `None` (not a raised error) on a downstream 404."""
        try:
            response = await self._request("GET", f"/api/v1/streaming/config/{community_id}")
        except httpx.HTTPError as exc:
            raise bad_request("Failed to fetch stream configuration") from exc
        if response.status_code == 404:
            return None
        return dict(response.json())

    async def create_config(
        self, community_id: int, *, rtmp_port: int | None, http_port: int | None, enabled: bool
    ) -> dict[str, Any]:
        """Port of `createStreamConfig`."""
        try:
            response = await self._request(
                "POST",
                "/api/v1/streaming/config",
                json_body={
                    "communityId": community_id,
                    "rtmpPort": rtmp_port,
                    "httpPort": http_port,
                    "enabled": enabled,
                },
            )
        except httpx.HTTPError as exc:
            raise bad_request("Failed to create stream configuration") from exc
        if response.status_code == 409:
            raise conflict("Stream configuration already exists")
        return dict(response.json())

    async def regenerate_key(self, community_id: int) -> str:
        """Port of `regenerateStreamKey`."""
        try:
            response = await self._request(
                "POST", f"/api/v1/streaming/config/{community_id}/regenerate-key"
            )
        except httpx.HTTPError as exc:
            raise bad_request("Failed to regenerate stream key") from exc
        if response.status_code == 404:
            raise not_found("Stream configuration not found")
        return str(response.json()["streamKey"])

    async def get_destinations(self, community_id: int) -> list[dict[str, Any]]:
        """Port of `getDestinations`."""
        try:
            response = await self._request("GET", f"/api/v1/streaming/destinations/{community_id}")
        except httpx.HTTPError as exc:
            raise bad_request("Failed to fetch streaming destinations") from exc
        return list(response.json().get("destinations") or [])

    async def add_destination(
        self,
        community_id: int,
        *,
        platform: str,
        rtmp_url: str,
        stream_key: str,
        enabled: bool,
        force_cut: bool,
    ) -> dict[str, Any]:
        """Port of `addDestination`'s downstream POST -- caller must validate/normalize first.

        Deliberately a thin forwarder: `platform`/`rtmp_url`/`stream_key`
        validation (including the SSRF guard) lives in `blueprints.v1.
        streaming.add_destination` instead of here, so tests that
        monkeypatch this client method at the boundary (`tests/
        test_v1_streaming_blueprint.py`'s `proxy_stub` fixture, mirroring
        `tests/test_event_blueprint.py`'s own pattern) can never
        accidentally bypass the security check by mocking it away --
        validation and the network call are two different call frames.
        """
        try:
            response = await self._request(
                "POST",
                "/api/v1/streaming/destinations",
                json_body={
                    "communityId": community_id,
                    "platform": platform,
                    "rtmpUrl": rtmp_url,
                    "streamKey": stream_key,
                    "enabled": enabled,
                    "forceCut": force_cut,
                },
            )
        except httpx.HTTPError as exc:
            raise bad_request("Failed to add streaming destination") from exc
        if response.status_code == 404:
            raise not_found("Stream configuration not found")
        return dict(response.json()["destination"])

    async def remove_destination(self, community_id: int, destination_id: int) -> None:
        """Port of `removeDestination`."""
        try:
            response = await self._request(
                "DELETE",
                f"/api/v1/streaming/destinations/{destination_id}?communityId={community_id}",
            )
        except httpx.HTTPError as exc:
            raise bad_request("Failed to remove streaming destination") from exc
        if response.status_code == 404:
            raise not_found("Destination not found")

    async def toggle_force_cut(
        self, community_id: int, destination_id: int, *, force_cut: bool
    ) -> dict[str, Any]:
        """Port of `toggleForceCut`."""
        try:
            response = await self._request(
                "PUT",
                f"/api/v1/streaming/destinations/{destination_id}/force-cut",
                json_body={"communityId": community_id, "forceCut": force_cut},
            )
        except httpx.HTTPError as exc:
            raise bad_request("Failed to toggle force cut") from exc
        if response.status_code == 404:
            raise not_found("Destination not found")
        return dict(response.json()["destination"])

    async def get_status(self, community_id: int) -> dict[str, Any]:
        """Port of `getStreamStatus` -- `{active: False, destinations: []}` on a downstream 404."""
        try:
            response = await self._request("GET", f"/api/v1/streaming/status/{community_id}")
        except httpx.HTTPError as exc:
            raise bad_request("Failed to fetch streaming status") from exc
        if response.status_code == 404:
            return {"active": False, "destinations": []}
        return dict(response.json())
