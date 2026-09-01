"""Config/target CRUD + real start/stop/status lifecycle -- real DB, fake ffmpeg exec only."""

from __future__ import annotations

from typing import Any

import pytest

from services import streaming_service as svc
from services.errors import ApiError
from services.ffmpeg_engine import FFmpegSupervisor
from services.token_ledger_client import (
    REASON_INSUFFICIENT_BALANCE,
    REASON_LEDGER_UNAVAILABLE,
    TokenDebitResult,
)
from tests.fakes import FakeSubprocessExec


async def _debit_ok(*args: Any, **kwargs: Any) -> TokenDebitResult:
    return TokenDebitResult(ok=True, balance_after=55, blocked_reason=None)


async def _debit_insufficient(*args: Any, **kwargs: Any) -> TokenDebitResult:
    return TokenDebitResult(
        ok=False, balance_after=None, blocked_reason=REASON_INSUFFICIENT_BALANCE
    )


async def _debit_unreachable(*args: Any, **kwargs: Any) -> TokenDebitResult:
    return TokenDebitResult(ok=False, balance_after=None, blocked_reason=REASON_LEDGER_UNAVAILABLE)


# ---------------------------------------------------------------------------
# Config / target CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_config_returns_none_when_never_created(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    assert await svc.get_config(async_dal, dal, community_id=1) is None


@pytest.mark.asyncio
async def test_create_config_then_get_round_trips(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    created = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    fetched = await svc.get_config(async_dal, dal, community_id=1)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.source_url == "rtmp://ingest/live/k"


@pytest.mark.asyncio
async def test_create_config_upserts_on_second_call(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    first = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://a",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    second = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://b",
        source_type="hls",
        record_enabled=True,
        transcode_enabled=True,
        transcode_bitrate_kbps=8000,
    )
    assert second.id == first.id  # same row, updated in place
    assert second.source_url == "rtmp://b"
    assert second.source_type == "hls"


@pytest.mark.asyncio
async def test_create_config_rejects_invalid_source_type(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    with pytest.raises(ApiError) as exc_info:
        await svc.create_or_update_config(
            async_dal,
            dal,
            community_id=1,
            source_url="rtmp://a",
            source_type="webrtc",
            record_enabled=False,
            transcode_enabled=False,
            transcode_bitrate_kbps=4000,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_config_rejects_non_positive_bitrate(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    with pytest.raises(ApiError):
        await svc.create_or_update_config(
            async_dal,
            dal,
            community_id=1,
            source_url="rtmp://a",
            source_type="rtmp",
            record_enabled=False,
            transcode_enabled=False,
            transcode_bitrate_kbps=0,
        )


@pytest.mark.asyncio
async def test_add_target_then_list(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://a",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    target = await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    targets = await svc.list_targets(async_dal, dal, config_id=config.id)
    assert [t.id for t in targets] == [target.id]


@pytest.mark.asyncio
async def test_add_target_rejects_unknown_platform(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://a",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    with pytest.raises(ApiError):
        await svc.add_target(
            async_dal, dal, config_id=config.id, platform="myspace", forward_url="rtmp://t1/live/k"
        )


@pytest.mark.asyncio
async def test_add_target_rejects_unknown_config(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    with pytest.raises(ApiError) as exc_info:
        await svc.add_target(
            async_dal, dal, config_id=99999, platform="twitch", forward_url="rtmp://t1/live/k"
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_remove_target_then_list_empty(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://a",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    target = await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    await svc.remove_target(async_dal, dal, config_id=config.id, target_id=target.id)
    assert await svc.list_targets(async_dal, dal, config_id=config.id) == []


@pytest.mark.asyncio
async def test_remove_target_raises_404_for_wrong_config(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config_a = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://a",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    config_b = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=2,
        source_url="rtmp://b",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    target = await svc.add_target(
        async_dal, dal, config_id=config_a.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    with pytest.raises(ApiError) as exc_info:
        await svc.remove_target(async_dal, dal, config_id=config_b.id, target_id=target.id)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# start_forwarding / stop_forwarding / get_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_forwarding_passthrough_starts_real_supervised_process(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    fake_exec = FakeSubprocessExec()
    supervisor = FFmpegSupervisor(subprocess_exec=fake_exec)

    status = await svc.start_forwarding(
        async_dal,
        dal,
        supervisor,
        community_id=1,
        bearer_token="tok",
        hub_api_url="http://hub-api-test.invalid",
        transcode_token_cost=5,
        transcode_product_key="transcoding_minutes",
        ffmpeg_binary="ffmpeg",
        recordings_dir="/tmp/does-not-matter",
    )

    assert status.running is True
    assert status.transcode_applied is False
    assert supervisor.is_running(config.id) is True
    assert "-c" in fake_exec.calls[0] and "copy" in fake_exec.calls[0]


@pytest.mark.asyncio
async def test_start_forwarding_transcode_admitted_when_debit_succeeds(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=True,
        transcode_bitrate_kbps=6000,
    )
    await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())

    status = await svc.start_forwarding(
        async_dal,
        dal,
        supervisor,
        community_id=1,
        bearer_token="tok",
        hub_api_url="http://hub-api-test.invalid",
        transcode_token_cost=5,
        transcode_product_key="transcoding_minutes",
        ffmpeg_binary="ffmpeg",
        recordings_dir="/tmp/does-not-matter",
        debit_fn=_debit_ok,
    )

    assert status.transcode_applied is True
    assert status.fallback_reason is None


@pytest.mark.asyncio
async def test_start_forwarding_falls_back_to_passthrough_on_insufficient_balance(
    dal_pair: Any,
) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=True,
        transcode_bitrate_kbps=6000,
    )
    await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    fake_exec = FakeSubprocessExec()
    supervisor = FFmpegSupervisor(subprocess_exec=fake_exec)

    status = await svc.start_forwarding(
        async_dal,
        dal,
        supervisor,
        community_id=1,
        bearer_token="tok",
        hub_api_url="http://hub-api-test.invalid",
        transcode_token_cost=5,
        transcode_product_key="transcoding_minutes",
        ffmpeg_binary="ffmpeg",
        recordings_dir="/tmp/does-not-matter",
        debit_fn=_debit_insufficient,
    )

    assert status.running is True  # job still starts
    assert status.transcode_applied is False  # but passthrough, not transcoded
    assert status.fallback_reason == REASON_INSUFFICIENT_BALANCE
    assert "-c" in fake_exec.calls[0] and "copy" in fake_exec.calls[0]
    assert "libx264" not in fake_exec.calls[0]


@pytest.mark.asyncio
async def test_start_forwarding_falls_back_on_ledger_unavailable(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=True,
        transcode_bitrate_kbps=6000,
    )
    await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())

    status = await svc.start_forwarding(
        async_dal,
        dal,
        supervisor,
        community_id=1,
        bearer_token="tok",
        hub_api_url="http://hub-api-test.invalid",
        transcode_token_cost=5,
        transcode_product_key="transcoding_minutes",
        ffmpeg_binary="ffmpeg",
        recordings_dir="/tmp/does-not-matter",
        debit_fn=_debit_unreachable,
    )
    assert status.running is True
    assert status.fallback_reason == REASON_LEDGER_UNAVAILABLE


@pytest.mark.asyncio
async def test_start_forwarding_raises_404_without_config(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
    with pytest.raises(ApiError) as exc_info:
        await svc.start_forwarding(
            async_dal,
            dal,
            supervisor,
            community_id=1,
            bearer_token="tok",
            hub_api_url="http://hub-api-test.invalid",
            transcode_token_cost=5,
            transcode_product_key="transcoding_minutes",
            ffmpeg_binary="ffmpeg",
            recordings_dir="/tmp/does-not-matter",
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_start_forwarding_raises_400_with_no_targets_and_no_recording(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
    with pytest.raises(ApiError) as exc_info:
        await svc.start_forwarding(
            async_dal,
            dal,
            supervisor,
            community_id=1,
            bearer_token="tok",
            hub_api_url="http://hub-api-test.invalid",
            transcode_token_cost=5,
            transcode_product_key="transcoding_minutes",
            ffmpeg_binary="ffmpeg",
            recordings_dir="/tmp/does-not-matter",
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_start_forwarding_raises_409_if_already_running(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
    await svc.start_forwarding(
        async_dal,
        dal,
        supervisor,
        community_id=1,
        bearer_token="tok",
        hub_api_url="http://hub-api-test.invalid",
        transcode_token_cost=5,
        transcode_product_key="transcoding_minutes",
        ffmpeg_binary="ffmpeg",
        recordings_dir="/tmp/does-not-matter",
    )
    with pytest.raises(ApiError) as exc_info:
        await svc.start_forwarding(
            async_dal,
            dal,
            supervisor,
            community_id=1,
            bearer_token="tok",
            hub_api_url="http://hub-api-test.invalid",
            transcode_token_cost=5,
            transcode_product_key="transcoding_minutes",
            ffmpeg_binary="ffmpeg",
            recordings_dir="/tmp/does-not-matter",
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_stop_forwarding_stops_real_process_and_updates_session(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
    await svc.start_forwarding(
        async_dal,
        dal,
        supervisor,
        community_id=1,
        bearer_token="tok",
        hub_api_url="http://hub-api-test.invalid",
        transcode_token_cost=5,
        transcode_product_key="transcoding_minutes",
        ffmpeg_binary="ffmpeg",
        recordings_dir="/tmp/does-not-matter",
    )
    status = await svc.stop_forwarding(async_dal, dal, supervisor, community_id=1)
    assert status.running is False
    assert supervisor.is_running(config.id) is False


@pytest.mark.asyncio
async def test_stop_forwarding_is_idempotent_when_not_running(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
    status = await svc.stop_forwarding(async_dal, dal, supervisor, community_id=1)
    assert status.running is False


@pytest.mark.asyncio
async def test_get_status_reflects_real_supervisor_state(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    config = await svc.create_or_update_config(
        async_dal,
        dal,
        community_id=1,
        source_url="rtmp://ingest/live/k",
        source_type="rtmp",
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
    )
    await svc.add_target(
        async_dal, dal, config_id=config.id, platform="twitch", forward_url="rtmp://t1/live/k"
    )
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())

    not_started = await svc.get_status(async_dal, dal, supervisor, community_id=1)
    assert not_started.running is False

    await svc.start_forwarding(
        async_dal,
        dal,
        supervisor,
        community_id=1,
        bearer_token="tok",
        hub_api_url="http://hub-api-test.invalid",
        transcode_token_cost=5,
        transcode_product_key="transcoding_minutes",
        ffmpeg_binary="ffmpeg",
        recordings_dir="/tmp/does-not-matter",
    )
    running = await svc.get_status(async_dal, dal, supervisor, community_id=1)
    assert running.running is True
    assert running.pid is not None


@pytest.mark.asyncio
async def test_get_status_raises_404_without_config(dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
    with pytest.raises(ApiError) as exc_info:
        await svc.get_status(async_dal, dal, supervisor, community_id=1)
    assert exc_info.value.status_code == 404
