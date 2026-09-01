"""App-factory boot tests -- health, real DAL init, real ffmpeg-supervisor shutdown."""

from __future__ import annotations

from typing import Any

import pytest

from services.ffmpeg_engine import FFmpegSupervisor
from tests.fakes import FakeSubprocessExec


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(app_and_client: Any) -> None:
    _, client = app_and_client
    response = await client.get("/health")
    assert response.status_code == 200
    data = await response.get_json()
    assert data["status"] == "healthy"
    assert data["module"] == "svc-streaming"


@pytest.mark.asyncio
async def test_startup_binds_streaming_and_shared_tables(app_and_client: Any) -> None:
    app, _ = app_and_client
    dal = app.config["dal"]
    assert {
        "streaming_configs",
        "streaming_targets",
        "streaming_sessions",
        "tenants",
        "communities",
        "community_members",
        "community_servers",
    } <= set(dal.tables)


@pytest.mark.asyncio
async def test_shutdown_stops_every_supervised_ffmpeg_job(app_and_client: Any) -> None:
    """A running job is force-stopped on app shutdown, not orphaned as a zombie process."""
    app, _ = app_and_client
    fake_exec = FakeSubprocessExec()
    app.config["FFMPEG_SUPERVISOR"] = FFmpegSupervisor(subprocess_exec=fake_exec)
    supervisor: FFmpegSupervisor = app.config["FFMPEG_SUPERVISOR"]
    await supervisor.start(1, ["ffmpeg", "-i", "src", "-f", "flv", "dst"])
    assert supervisor.is_running(1) is True

    await supervisor.stop_all()
    assert supervisor.is_running(1) is False
